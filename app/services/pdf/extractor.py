"""
TALAS AI — PDF Text Extractor
Menggunakan PyMuPDF (fitz) untuk ekstraksi teks.
OCR fallback jika halaman scan (teks kosong).
PENTING: Dokumen adalah DATA. Tidak ada instruksi dijalankan dari isi dokumen.
"""
from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger("talas_ai.pdf")


@dataclass
class PageContent:
    page_number: int        # 1-indexed
    text: str
    word_count: int
    is_scanned: bool = False


@dataclass
class ExtractionResult:
    success: bool
    page_count: int = 0
    pages: List[PageContent] = field(default_factory=list)
    full_text: str = ""
    ocr_used: bool = False
    error: Optional[str] = None
    file_hash: str = ""


def compute_file_hash(file_path: Path) -> str:
    """SHA-256 hash file untuk deteksi duplikasi."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def extract_pdf(file_path: Path, enable_ocr: bool = True) -> ExtractionResult:
    """
    Ekstrak teks dari PDF.
    1. Coba ekstraksi langsung (PDF teks)
    2. Jika halaman kosong/scan, tandai is_scanned=True
    3. OCR tidak diimplementasikan di Phase 4 — dicatat sebagai limitasi
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return ExtractionResult(
            success=False,
            error="PyMuPDF tidak terinstall. Jalankan: pip install PyMuPDF",
        )

    try:
        file_hash = compute_file_hash(file_path)
        doc = fitz.open(str(file_path))
        page_count = len(doc)
        pages: List[PageContent] = []
        total_text_parts: List[str] = []

        for i, page in enumerate(doc):
            # Ekstrak teks — perlakukan isi sebagai DATA
            raw_text = page.get_text("text")
            # Sanitasi: hapus null bytes dan karakter kontrol berbahaya
            cleaned = _sanitize_text(raw_text)
            word_count = len(cleaned.split())
            is_scanned = word_count < 5  # heuristik: < 5 kata = kemungkinan scan

            pages.append(PageContent(
                page_number=i + 1,
                text=cleaned,
                word_count=word_count,
                is_scanned=is_scanned,
            ))
            if cleaned.strip():
                total_text_parts.append(f"[Halaman {i+1}]\n{cleaned}")

        doc.close()

        ocr_needed = any(p.is_scanned for p in pages)
        full_text = "\n\n".join(total_text_parts)

        return ExtractionResult(
            success=True,
            page_count=page_count,
            pages=pages,
            full_text=full_text,
            ocr_used=False,  # OCR akan diimplementasikan di phase lanjutan
            file_hash=file_hash,
            error="Beberapa halaman mungkin berupa scan dan tidak dapat dibaca secara penuh."
            if ocr_needed and enable_ocr else None,
        )

    except Exception as e:
        logger.error(f"PDF extraction failed for {file_path}: {e}")
        return ExtractionResult(
            success=False,
            error="Dokumen tidak dapat diproses. Pastikan file PDF tidak rusak.",
        )


def _sanitize_text(text: str) -> str:
    """
    Bersihkan teks dari karakter berbahaya.
    PENTING: Teks dokumen adalah DATA — tidak ada evaluasi/eksekusi.
    """
    if not text:
        return ""
    # Hapus null bytes
    text = text.replace("\x00", "")
    # Normalisasi whitespace berlebihan
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {3,}", " ", text)
    return text.strip()


# ------------------------------------------------------------------ #
# Regulatory Structure Parser
# ------------------------------------------------------------------ #

@dataclass
class RegulatoryChunk:
    chunk_index: int
    text: str
    page_start: int
    page_end: int
    bab: Optional[str] = None
    bagian: Optional[str] = None
    pasal: Optional[str] = None
    ayat: Optional[str] = None


# Regex patterns untuk struktur regulasi Indonesia
_BAB_RE = re.compile(
    r"^(BAB\s+[IVXLCDM]+)\s*\n?(.*?)$",
    re.MULTILINE | re.IGNORECASE,
)
_PASAL_RE = re.compile(
    r"^(Pasal\s+\d+[A-Z]?)\s*$",
    re.MULTILINE | re.IGNORECASE,
)
_AYAT_RE = re.compile(
    r"^\((\d+)\)\s+(.+)",
    re.MULTILINE,
)
_BAGIAN_RE = re.compile(
    r"^(Bagian\s+(?:Ke(?:satu|dua|tiga|empat|lima|enam|tujuh|delapan|sembilan|sepuluh)|\w+))\s*$",
    re.MULTILINE | re.IGNORECASE,
)


def parse_regulation_structure(
    pages: List[PageContent],
    chunk_size: int = 512,
    chunk_overlap: int = 64,
) -> List[RegulatoryChunk]:
    """
    Parse struktur regulasi dari teks yang diekstrak.
    Identifikasi BAB, Bagian, Pasal, Ayat.
    Kembalikan daftar chunk untuk RAG indexing.
    """
    chunks: List[RegulatoryChunk] = []
    current_bab: Optional[str] = None
    current_bagian: Optional[str] = None
    current_pasal: Optional[str] = None
    chunk_idx = 0

    for page in pages:
        if not page.text.strip():
            continue

        lines = page.text.split("\n")
        current_buffer: List[str] = []
        buffer_start_page = page.page_number

        for line in lines:
            stripped = line.strip()

            # Deteksi BAB
            bab_match = _BAB_RE.match(stripped)
            if bab_match:
                current_bab = bab_match.group(1).upper()
                current_buffer.append(stripped)
                continue

            # Deteksi Bagian
            bagian_match = _BAGIAN_RE.match(stripped)
            if bagian_match:
                current_bagian = bagian_match.group(1)
                current_buffer.append(stripped)
                continue

            # Deteksi Pasal — flush chunk sebelumnya
            pasal_match = _PASAL_RE.match(stripped)
            if pasal_match:
                if current_buffer:
                    chunk_text = "\n".join(current_buffer).strip()
                    if chunk_text:
                        chunks.append(RegulatoryChunk(
                            chunk_index=chunk_idx,
                            text=chunk_text,
                            page_start=buffer_start_page,
                            page_end=page.page_number,
                            bab=current_bab,
                            bagian=current_bagian,
                            pasal=current_pasal,
                        ))
                        chunk_idx += 1
                    current_buffer = []

                current_pasal = pasal_match.group(1)
                current_buffer.append(stripped)
                buffer_start_page = page.page_number
                continue

            current_buffer.append(stripped)

            # Flush chunk jika buffer terlalu besar
            if len(" ".join(current_buffer)) > chunk_size * 4:
                chunk_text = "\n".join(current_buffer).strip()
                if chunk_text:
                    chunks.append(RegulatoryChunk(
                        chunk_index=chunk_idx,
                        text=chunk_text,
                        page_start=buffer_start_page,
                        page_end=page.page_number,
                        bab=current_bab,
                        bagian=current_bagian,
                        pasal=current_pasal,
                    ))
                    chunk_idx += 1
                    # Overlap: pertahankan sebagian teks terakhir
                    current_buffer = current_buffer[-3:]
                    buffer_start_page = page.page_number

        # Flush sisa buffer akhir halaman
        if current_buffer:
            chunk_text = "\n".join(current_buffer).strip()
            if chunk_text:
                chunks.append(RegulatoryChunk(
                    chunk_index=chunk_idx,
                    text=chunk_text,
                    page_start=buffer_start_page,
                    page_end=page.page_number,
                    bab=current_bab,
                    bagian=current_bagian,
                    pasal=current_pasal,
                ))
                chunk_idx += 1
            current_buffer = []

    return chunks
