"""
TALAS AI — API Key Store
Menyimpan dan mengambil API key dari database dengan obfuskasi sederhana.

CATATAN KEAMANAN:
- Ini bukan enkripsi production-grade.
- API key diencode dengan XOR + base64 untuk mencegah exposure plaintext langsung.
- Untuk environment production dengan data sensitif, gunakan secret manager
  seperti HashiCorp Vault, AWS Secrets Manager, atau Windows Credential Manager.
- API key TIDAK PERNAH dikembalikan ke client/API response.
"""
from __future__ import annotations

import base64
import logging
import os

logger = logging.getLogger("talas_ai.security")

# Kunci obfuskasi — dibaca dari env agar tidak hardcoded
# Jika tidak ada, gunakan fallback yang deterministik dari SECRET_KEY
def _get_obfuscation_key() -> bytes:
    try:
        from app.config import settings
        secret = settings.SECRET_KEY
    except Exception:
        secret = "talas-ai-default-key"
    # Ambil 32 byte dari secret key
    key_bytes = secret.encode("utf-8")
    # Pad atau trim ke 32 byte
    return (key_bytes * 4)[:32]


def encode_api_key(plaintext: str) -> str:
    """
    Encode API key dengan XOR + base64.
    Bukan enkripsi, tapi mencegah API key tersimpan plaintext di database.
    """
    if not plaintext:
        return ""
    key = _get_obfuscation_key()
    encoded = bytearray()
    pt_bytes = plaintext.encode("utf-8")
    for i, byte in enumerate(pt_bytes):
        encoded.append(byte ^ key[i % len(key)])
    return base64.b64encode(bytes(encoded)).decode("ascii")


def decode_api_key(encoded: str) -> str:
    """Decode API key yang sudah di-encode."""
    if not encoded:
        return ""
    try:
        key = _get_obfuscation_key()
        decoded_bytes = base64.b64decode(encoded.encode("ascii"))
        result = bytearray()
        for i, byte in enumerate(decoded_bytes):
            result.append(byte ^ key[i % len(key)])
        return result.decode("utf-8")
    except Exception as e:
        logger.error(f"Failed to decode API key: {e}")
        return ""


def mask_api_key(plaintext: str) -> str:
    """
    Buat hint dari API key — 4 karakter terakhir saja.
    Digunakan untuk konfirmasi ke user bahwa API key sudah tersimpan.
    """
    if not plaintext or len(plaintext) < 4:
        return "****"
    return "..." + plaintext[-4:]
