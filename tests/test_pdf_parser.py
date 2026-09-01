"""
TALAS AI — Test PDF Parser & Document Processing
Test ekstraksi teks, parsing struktur regulasi, dan chunking.
"""
from __future__ import annotations

import io
import pytest
from pathlib import Path


class TestSanitizeText:
    def test_removes_null_bytes(self):
        from app.services.pdf.extractor import _sanitize_text
        result = _sanitize_text("hello\x00world")
        assert "\x00" not in result
        assert "hello" in result

    def test_normalizes_whitespace(self):
        from app.services.pdf.extractor import _sanitize_text
        result = _sanitize_text("line1\n\n\n\n\nline2")
        assert result.count("\n") <= 3

    def test_empty_string(self):
        from app.services.pdf.extractor import _sanitize_text
        assert _sanitize_text("") == ""
        assert _sanitize_text(None) == ""

    def test_strips_leading_trailing(self):
        from app.services.pdf.extractor import _sanitize_text
        result = _sanitize_text("  hello world  ")
        assert result == "hello world"


class TestRegulationParser:
    def test_detects_bab(self):
        from app.services.pdf.extractor import PageContent, parse_regulation_structure
        pages = [PageContent(
            page_number=1,
            text="BAB I\nKETENTUAN UMUM\nPasal 1\nDalam Peraturan ini yang dimaksud dengan:",
            word_count=10,
        )]
        chunks = parse_regulation_structure(pages)
        assert len(chunks) > 0
        bab_chunks = [c for c in chunks if c.bab]
        assert any(c.bab == "BAB I" for c in bab_chunks)

    def test_detects_pasal(self):
        from app.services.pdf.extractor import PageContent, parse_regulation_structure
        pages = [PageContent(
            page_number=1,
            text="Pasal 1\nBupati adalah Bupati Kabupaten.\nPasal 2\nSekretaris Daerah adalah pejabat.",
            word_count=15,
        )]
        chunks = parse_regulation_structure(pages)
        pasal_chunks = [c for c in chunks if c.pasal]
        assert len(pasal_chunks) >= 1

    def test_multiple_pages(self):
        from app.services.pdf.extractor import PageContent, parse_regulation_structure
        pages = [
            PageContent(page_number=1, text="BAB I\nPasal 1\nKetentuan umum.", word_count=5),
            PageContent(page_number=2, text="BAB II\nPasal 2\nPelaksanaan kegiatan.", word_count=5),
        ]
        chunks = parse_regulation_structure(pages)
        assert len(chunks) >= 2

    def test_empty_pages(self):
        from app.services.pdf.extractor import PageContent, parse_regulation_structure
        pages = [PageContent(page_number=1, text="", word_count=0)]
        chunks = parse_regulation_structure(pages)
        assert chunks == []

    def test_chunk_contains_text(self):
        from app.services.pdf.extractor import PageContent, parse_regulation_structure
        pages = [PageContent(
            page_number=1,
            text="Pasal 5\nBupati berwenang menetapkan kebijakan daerah.",
            word_count=8,
        )]
        chunks = parse_regulation_structure(pages)
        assert all(c.text.strip() for c in chunks)


class TestFileHash:
    def test_compute_hash(self, tmp_path):
        from app.services.pdf.extractor import compute_file_hash
        f = tmp_path / "test.txt"
        f.write_bytes(b"hello talas ai")
        h = compute_file_hash(f)
        assert len(h) == 64  # SHA-256 hex

    def test_same_content_same_hash(self, tmp_path):
        from app.services.pdf.extractor import compute_file_hash
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_bytes(b"same content")
        f2.write_bytes(b"same content")
        assert compute_file_hash(f1) == compute_file_hash(f2)

    def test_different_content_different_hash(self, tmp_path):
        from app.services.pdf.extractor import compute_file_hash
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_bytes(b"content a")
        f2.write_bytes(b"content b")
        assert compute_file_hash(f1) != compute_file_hash(f2)


class TestDocumentValidation:
    def test_valid_pdf(self):
        from app.services.pdf.document_service import _validate_upload
        ok, msg = _validate_upload("regulasi.pdf", 1024 * 1024)
        assert ok

    def test_invalid_extension(self):
        from app.services.pdf.document_service import _validate_upload
        ok, msg = _validate_upload("file.exe", 1024)
        assert not ok
        assert "tidak diizinkan" in msg

    def test_file_too_large(self):
        from app.services.pdf.document_service import _validate_upload
        from app.config import settings
        big = settings.max_upload_bytes + 1
        ok, msg = _validate_upload("big.pdf", big)
        assert not ok
        assert "melebihi" in msg

    def test_empty_file(self):
        from app.services.pdf.document_service import _validate_upload
        ok, msg = _validate_upload("empty.pdf", 0)
        assert not ok

    def test_safe_filename_no_traversal(self):
        from app.services.pdf.document_service import _safe_filename
        name = _safe_filename("../../../etc/passwd.pdf")
        assert "/" not in name
        assert ".." not in name
        assert name.endswith(".pdf")
