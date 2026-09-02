"""TALAS AI — Test RAG Engine & Chatbot"""
from __future__ import annotations
import pytest


class TestRAGEngine:
    @pytest.mark.asyncio
    async def test_rag_no_documents_returns_graceful(self, test_engine):
        """RAG tanpa dokumen harus mengembalikan pesan yang jelas."""
        from sqlalchemy.ext.asyncio import async_sessionmaker
        from app.services.ai.router import setup_ai_router, get_ai_router, _ai_router
        from app.services.ai.providers.mock import MockProvider
        from app.services.rag.rag_engine import run_rag, DISCLAIMER
        from app.services.rag.search import ensure_fts_table
        import app.services.ai.router as router_module

        # Setup router dengan mock provider
        router_module._ai_router = None
        router = setup_ai_router(privacy_mode="local_only")
        mock = MockProvider(response="Berdasarkan context, tidak ditemukan informasi.")
        router.register_provider("mock", mock)

        factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)
        async with factory() as session:
            await ensure_fts_table(session)
            result = await run_rag(session, "Apa dasar hukum Pasal 8?")

        assert result.disclaimer == DISCLAIMER
        assert not result.has_sufficient_evidence
        assert "bukti" in result.answer.lower() or "database" in result.answer.lower()

        # Cleanup
        router_module._ai_router = None

    @pytest.mark.asyncio
    async def test_rag_disclaimer_always_present(self, test_engine):
        """Disclaimer wajib selalu muncul di setiap response RAG."""
        from sqlalchemy.ext.asyncio import async_sessionmaker
        from app.services.rag.rag_engine import run_rag, DISCLAIMER
        from app.services.rag.search import ensure_fts_table
        import app.services.ai.router as router_module

        router_module._ai_router = None

        factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)
        async with factory() as session:
            await ensure_fts_table(session)
            result = await run_rag(session, "Test pertanyaan")

        assert result.disclaimer == DISCLAIMER
        router_module._ai_router = None

    @pytest.mark.asyncio
    async def test_format_citation(self):
        """Citation harus dapat dilacak ke sumber."""
        from app.services.rag.rag_engine import RAGSource, _format_citation
        src = RAGSource(
            chunk_id=1, document_id=1, regulation_id=1,
            regulation_jenis="Perbup", regulation_nomor="1",
            regulation_tahun=2026, regulation_judul="Test",
            pasal="Pasal 8", bab="BAB I", page_start=12,
            excerpt="...", score=0.9,
        )
        citation = _format_citation(src)
        assert "Perbup" in citation
        assert "Pasal 8" in citation
        assert "2026" in citation

    @pytest.mark.asyncio
    async def test_estimate_confidence_no_sources(self):
        from app.services.rag.rag_engine import _estimate_confidence
        assert _estimate_confidence([]) == 0.0

    @pytest.mark.asyncio
    async def test_estimate_confidence_with_sources(self):
        from app.services.rag.rag_engine import RAGSource, _estimate_confidence
        sources = [
            RAGSource(
                chunk_id=i, document_id=1, regulation_id=1,
                regulation_jenis="UU", regulation_nomor=str(i),
                regulation_tahun=2020, regulation_judul="Test",
                pasal=f"Pasal {i}", bab="BAB I", page_start=i,
                excerpt="...", score=-0.5,
            )
            for i in range(1, 4)
        ]
        conf = _estimate_confidence(sources)
        assert 0.0 < conf <= 1.0


class TestChatAPI:
    @pytest.fixture
    async def chat_client(self, client, test_engine):
        from sqlalchemy.ext.asyncio import async_sessionmaker
        from app.models.user import User, Role, Permission, UserRole, RolePermission
        from app.services.security.hashing import hash_password
        from app.services.rag.search import ensure_fts_table
        import uuid as _uuid

        suffix = _uuid.uuid4().hex[:6]
        factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)

        async with factory() as session:
            await ensure_fts_table(session)
            role = Role(name=f"analis_{suffix}", display_name="Analis")
            session.add(role)
            await session.flush()
            perm = Permission(name=f"chat:use:{suffix}", resource="chat", action="use")
            session.add(perm)
            await session.flush()
            session.add(RolePermission(role_id=role.id, permission_id=perm.id))
            user = User(
                username=f"chatuser_{suffix}",
                email=f"chat_{suffix}@talas.local",
                full_name="Chat User",
                hashed_password=hash_password("Pass@123"),
                is_active=True,
            )
            session.add(user)
            await session.flush()
            session.add(UserRole(user_id=user.id, role_id=role.id))
            await session.commit()

        login = await client.post("/api/auth/login", json={
            "username": f"chatuser_{suffix}", "password": "Pass@123"
        })
        token = login.json()["access_token"]
        client.headers.update({"Authorization": f"Bearer {token}"})
        return client

    @pytest.mark.asyncio
    async def test_chat_returns_200(self, chat_client):
        response = await chat_client.post("/api/chat", json={
            "message": "Apa dasar hukum Pasal 1?"
        })
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_chat_response_has_disclaimer(self, chat_client):
        response = await chat_client.post("/api/chat", json={
            "message": "Jelaskan ketentuan Pasal 5."
        })
        assert response.status_code == 200
        data = response.json()
        assert "disclaimer" in data
        assert "WAJIB VERIFIKASI" in data["disclaimer"]

    @pytest.mark.asyncio
    async def test_chat_response_has_session_id(self, chat_client):
        response = await chat_client.post("/api/chat", json={
            "message": "Test session"
        })
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["session_id"] > 0

    @pytest.mark.asyncio
    async def test_chat_continues_session(self, chat_client):
        r1 = await chat_client.post("/api/chat", json={"message": "Pertanyaan 1"})
        session_id = r1.json()["session_id"]
        r2 = await chat_client.post("/api/chat", json={
            "message": "Pertanyaan 2", "session_id": session_id
        })
        assert r2.json()["session_id"] == session_id

    @pytest.mark.asyncio
    async def test_list_sessions(self, chat_client):
        await chat_client.post("/api/chat", json={"message": "Test"})
        response = await chat_client.get("/api/chat/sessions")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_chat_unauthenticated(self, client):
        response = await client.post("/api/chat", json={"message": "Test"})
        assert response.status_code == 401
