"""
TALAS AI — Chatbot API (Phase 8)
"Tanya Regulasi" — RAG-powered chatbot dengan citation.

Setiap response AI:
- Wajib tampilkan disclaimer
- Harus menyertakan sumber
- Tidak boleh mengarang regulasi
- Output adalah telaah awal
"""
from __future__ import annotations

import json
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.dependencies import get_current_user, require_permissions
from app.models.chat import ChatSession, ChatMessage as ChatMessageModel
from app.models.user import User
from app.services.rag.rag_engine import run_rag, DISCLAIMER

logger = logging.getLogger("talas_ai.chat")
router = APIRouter(prefix="/chat", tags=["Chatbot — Tanya Regulasi"])


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[int] = None
    regulation_id: Optional[int] = None


class SourceOut(BaseModel):
    regulation: Optional[str] = None
    nomor: Optional[str] = None
    tahun: Optional[int] = None
    pasal: Optional[str] = None
    halaman: Optional[int] = None
    excerpt: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: int
    message_id: int
    answer: str
    sources: List[SourceOut] = []
    confidence: float = 0.0
    has_sufficient_evidence: bool = False
    warning: str = ""
    disclaimer: str = DISCLAIMER
    provider: str = ""
    model: str = ""


class SessionOut(BaseModel):
    id: int
    title: Optional[str] = None
    regulation_id: Optional[int] = None
    ai_provider: Optional[str] = None
    ai_model: Optional[str] = None
    model_config = {"from_attributes": True}


@router.post(
    "",
    response_model=ChatResponse,
    summary="Kirim pertanyaan ke chatbot regulasi",
    dependencies=[Depends(require_permissions("chat:use"))],
)
async def chat(
    request: Request,
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Kirim pertanyaan tentang regulasi.
    AI akan menjawab berdasarkan dokumen yang tersedia di database.

    ⚠️ TINJAUAN AWAL AI — WAJIB VERIFIKASI MANUSIA.
    AI tidak boleh mengarang regulasi atau membuat citation palsu.
    """
    # Dapatkan atau buat session
    session = await _get_or_create_session(
        db, current_user.id, body.session_id, body.regulation_id
    )

    # Simpan pesan user
    user_msg = ChatMessageModel(
        session_id=session.id,
        role="user",
        content=body.message,
    )
    db.add(user_msg)
    await db.flush()

    # Jalankan RAG
    rag_result = await run_rag(
        db=db,
        question=body.message,
        regulation_id=body.regulation_id,
        task_name="chat",
    )

    # Simpan response AI
    ai_msg = ChatMessageModel(
        session_id=session.id,
        role="assistant",
        content=rag_result.answer,
        ai_provider=rag_result.provider,
        ai_model=rag_result.model,
        confidence=rag_result.confidence,
        sources_json=json.dumps([
            {
                "regulation": s.regulation_judul,
                "nomor": s.regulation_nomor,
                "tahun": s.regulation_tahun,
                "pasal": s.pasal,
                "halaman": s.page_start,
                "excerpt": s.excerpt,
            }
            for s in rag_result.sources
        ]),
        has_warning=bool(rag_result.warning),
        warning_message=rag_result.warning or None,
    )
    db.add(ai_msg)

    # Update session title jika belum ada
    if not session.title and body.message:
        session.title = body.message[:60]
    session.ai_provider = rag_result.provider
    session.ai_model = rag_result.model

    await db.commit()
    await db.refresh(ai_msg)

    sources_out = [
        SourceOut(
            regulation=s.regulation_judul,
            nomor=s.regulation_nomor,
            tahun=s.regulation_tahun,
            pasal=s.pasal,
            halaman=s.page_start,
            excerpt=s.excerpt[:200] if s.excerpt else None,
        )
        for s in rag_result.sources
    ]

    return ChatResponse(
        session_id=session.id,
        message_id=ai_msg.id,
        answer=rag_result.answer,
        sources=sources_out,
        confidence=rag_result.confidence,
        has_sufficient_evidence=rag_result.has_sufficient_evidence,
        warning=rag_result.warning,
        disclaimer=DISCLAIMER,
        provider=rag_result.provider,
        model=rag_result.model,
    )


@router.get(
    "/sessions",
    response_model=List[SessionOut],
    summary="Daftar sesi chat",
    dependencies=[Depends(require_permissions("chat:use"))],
)
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == current_user.id, ChatSession.is_active == True)
        .order_by(ChatSession.created_at.desc())
        .limit(20)
    )
    return [SessionOut.model_validate(s) for s in result.scalars().all()]


@router.get(
    "/sessions/{session_id}/messages",
    summary="Riwayat pesan sesi",
    dependencies=[Depends(require_permissions("chat:use"))],
)
async def get_session_messages(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id,
        )
    )
    s = session.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Sesi tidak ditemukan.")

    msgs = await db.execute(
        select(ChatMessageModel)
        .where(ChatMessageModel.session_id == session_id)
        .order_by(ChatMessageModel.created_at)
    )
    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "confidence": m.confidence,
            "disclaimer": DISCLAIMER if m.role == "assistant" else None,
        }
        for m in msgs.scalars().all()
    ]


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

async def _get_or_create_session(
    db: AsyncSession,
    user_id: int,
    session_id: Optional[int],
    regulation_id: Optional[int],
) -> ChatSession:
    if session_id:
        result = await db.execute(
            select(ChatSession).where(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id,
            )
        )
        session = result.scalar_one_or_none()
        if session:
            return session

    # Buat session baru
    session = ChatSession(
        user_id=user_id,
        regulation_id=regulation_id,
        is_active=True,
    )
    db.add(session)
    await db.flush()
    return session
