"""
TALAS AI — Search Engine
Keyword search via SQLite FTS5.
Semantic search via embedding abstraction (Phase 7).
Semua hasil harus dapat dilacak ke sumber dokumen.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("talas_ai.search")


@dataclass
class SearchHit:
    document_id: int
    chunk_id: int
    regulation_id: Optional[int]
    regulation_jenis: Optional[str]
    regulation_nomor: Optional[str]
    regulation_tahun: Optional[int]
    regulation_judul: Optional[str]
    pasal: Optional[str]
    bab: Optional[str]
    page_start: Optional[int]
    excerpt: str
    score: float = 1.0


async def ensure_fts_table(db: AsyncSession) -> None:
    """
    Buat FTS5 virtual table jika belum ada.
    Menggunakan standalone FTS5 (tanpa content table) untuk kompatibilitas maksimal.
    """
    await db.execute(text("""
        CREATE VIRTUAL TABLE IF NOT EXISTS document_chunks_fts
        USING fts5(
            chunk_id UNINDEXED,
            text,
            pasal,
            bab
        )
    """))
    await db.commit()
    logger.info("FTS5 table ensured.")


async def rebuild_fts_index(db: AsyncSession) -> int:
    """Rebuild FTS5 index dari semua chunk yang ada."""
    await ensure_fts_table(db)
    await db.execute(text("DELETE FROM document_chunks_fts"))
    await db.execute(text("""
        INSERT INTO document_chunks_fts(chunk_id, text, pasal, bab)
        SELECT id, text, COALESCE(pasal, ''), COALESCE(bab, '')
        FROM document_chunks
        WHERE text IS NOT NULL AND length(text) > 0
    """))
    result = await db.execute(text("SELECT COUNT(*) FROM document_chunks_fts"))
    count = result.scalar_one()
    await db.commit()
    logger.info(f"FTS5 index rebuilt: {count} chunks indexed.")
    return count


async def index_chunk(db: AsyncSession, chunk_id: int, text_: str,
                      pasal: str = "", bab: str = "") -> None:
    """Index satu chunk ke FTS5."""
    await ensure_fts_table(db)
    # Hapus entry lama jika ada
    await db.execute(
        text("DELETE FROM document_chunks_fts WHERE chunk_id = :cid"),
        {"cid": chunk_id}
    )
    await db.execute(
        text("INSERT INTO document_chunks_fts(chunk_id, text, pasal, bab) "
             "VALUES (:cid, :text, :pasal, :bab)"),
        {"cid": chunk_id, "text": text_, "pasal": pasal or "", "bab": bab or ""}
    )


async def keyword_search(
    db: AsyncSession,
    query: str,
    limit: int = 10,
    regulation_id: Optional[int] = None,
) -> List[SearchHit]:
    """
    Keyword search menggunakan SQLite FTS5.
    Mengembalikan daftar SearchHit yang dapat dilacak ke sumber.

    Sanitasi query untuk mencegah FTS injection.
    """
    # Sanitasi: hapus karakter khusus FTS yang bisa dieksploitasi
    safe_query = _sanitize_fts_query(query)
    if not safe_query:
        return []

    try:
        sql = """
            SELECT
                CAST(fts.chunk_id AS INTEGER) AS chunk_id,
                dc.document_id,
                dc.pasal,
                dc.bab,
                dc.page_start,
                dc.text,
                d.regulation_id,
                r.jenis      AS reg_jenis,
                r.nomor      AS reg_nomor,
                r.tahun      AS reg_tahun,
                r.judul      AS reg_judul,
                bm25(document_chunks_fts) AS score
            FROM document_chunks_fts fts
            JOIN document_chunks dc ON dc.id = CAST(fts.chunk_id AS INTEGER)
            JOIN documents d ON d.id = dc.document_id
            LEFT JOIN regulations r ON r.id = d.regulation_id
            WHERE document_chunks_fts MATCH :query
        """
        params: dict = {"query": safe_query}

        if regulation_id:
            sql += " AND d.regulation_id = :reg_id"
            params["reg_id"] = regulation_id

        sql += " ORDER BY score LIMIT :limit"
        params["limit"] = limit

        result = await db.execute(text(sql), params)
        rows = result.fetchall()

        hits: List[SearchHit] = []
        for row in rows:
            excerpt = _make_excerpt(row.text, query)
            hits.append(SearchHit(
                chunk_id=row.chunk_id,
                document_id=row.document_id,
                regulation_id=row.regulation_id,
                regulation_jenis=row.reg_jenis,
                regulation_nomor=row.reg_nomor,
                regulation_tahun=row.reg_tahun,
                regulation_judul=row.reg_judul,
                pasal=row.pasal,
                bab=row.bab,
                page_start=row.page_start,
                excerpt=excerpt,
                score=float(row.score) if row.score else 0.0,
            ))
        return hits

    except Exception as e:
        logger.warning(f"FTS search failed: {e}. Falling back to LIKE search.")
        return await _like_search(db, query, limit, regulation_id)


async def _like_search(
    db: AsyncSession,
    query: str,
    limit: int,
    regulation_id: Optional[int],
) -> List[SearchHit]:
    """Fallback ke LIKE search jika FTS tidak tersedia."""
    from sqlalchemy import select, or_
    from app.models.document import DocumentChunk, Document
    from app.models.regulation import Regulation

    term = f"%{query}%"
    q = (
        select(DocumentChunk, Document, Regulation)
        .join(Document, Document.id == DocumentChunk.document_id)
        .outerjoin(Regulation, Regulation.id == Document.regulation_id)
        .where(DocumentChunk.text.ilike(term))
    )
    if regulation_id:
        q = q.where(Document.regulation_id == regulation_id)
    q = q.limit(limit)

    result = await db.execute(q)
    hits = []
    for chunk, doc, reg in result.fetchall():
        hits.append(SearchHit(
            chunk_id=chunk.id,
            document_id=doc.id,
            regulation_id=doc.regulation_id,
            regulation_jenis=reg.jenis if reg else None,
            regulation_nomor=reg.nomor if reg else None,
            regulation_tahun=reg.tahun if reg else None,
            regulation_judul=reg.judul if reg else None,
            pasal=chunk.pasal,
            bab=chunk.bab,
            page_start=chunk.page_start,
            excerpt=_make_excerpt(chunk.text, query),
            score=0.5,
        ))
    return hits


def _sanitize_fts_query(query: str) -> str:
    """Sanitasi query FTS5 untuk mencegah injection."""
    if not query or not query.strip():
        return ""
    # Hapus karakter FTS khusus yang bisa manipulasi query
    import re
    # Escape tanda kutip, hapus operator berbahaya
    q = query.strip()
    q = re.sub(r'["\']', ' ', q)
    q = re.sub(r'\s+', ' ', q)
    # Ambil max 100 karakter
    q = q[:100]
    # Jika kosong setelah sanitasi, return empty
    return q.strip() if q.strip() else ""


def _make_excerpt(text: str, query: str, max_len: int = 200) -> str:
    """Buat excerpt yang relevan dari teks chunk."""
    if not text:
        return ""
    # Cari posisi query dalam teks
    lower_text = text.lower()
    lower_query = query.lower().split()[0] if query.split() else ""
    pos = lower_text.find(lower_query)
    if pos == -1:
        return text[:max_len] + ("..." if len(text) > max_len else "")
    # Ambil konteks sekitar kata kunci
    start = max(0, pos - 50)
    end = min(len(text), pos + max_len)
    excerpt = text[start:end]
    if start > 0:
        excerpt = "..." + excerpt
    if end < len(text):
        excerpt = excerpt + "..."
    return excerpt
