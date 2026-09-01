"""
TALAS AI — Regulation Schemas
"""
from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, field_validator


VALID_JENIS = [
    "UU", "PP", "Perpres", "Permen", "Permendagri",
    "Perda", "Pergub", "Perbup", "Perwali", "Raperbup", "Lainnya"
]
VALID_STATUS = [
    "BERLAKU", "DICABUT", "DIUBAH", "SEBAGIAN_BERLAKU", "TIDAK_DIKETAHUI"
]
LEVEL_MAP = {
    "UU": 1, "PP": 2, "Perpres": 3, "Permen": 4, "Permendagri": 5,
    "Perda": 6, "Pergub": 7, "Perbup": 8, "Perwali": 8,
    "Raperbup": 9, "Lainnya": 10,
}


class RegulationBase(BaseModel):
    jenis: str
    nomor: Optional[str] = None
    tahun: Optional[int] = None
    judul: str
    singkatan: Optional[str] = None
    tanggal_penetapan: Optional[date] = None
    tanggal_berlaku: Optional[date] = None
    status: str = "BERLAKU"
    sumber_url: Optional[str] = None
    catatan: Optional[str] = None
    is_draft: bool = False

    @field_validator("jenis")
    @classmethod
    def validate_jenis(cls, v: str) -> str:
        if v not in VALID_JENIS:
            raise ValueError(f"Jenis tidak valid. Pilih: {', '.join(VALID_JENIS)}")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in VALID_STATUS:
            raise ValueError(f"Status tidak valid. Pilih: {', '.join(VALID_STATUS)}")
        return v

    @field_validator("tahun")
    @classmethod
    def validate_tahun(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (1900 <= v <= 2100):
            raise ValueError("Tahun tidak valid.")
        return v


class RegulationCreate(RegulationBase):
    pass


class RegulationUpdate(BaseModel):
    jenis: Optional[str] = None
    nomor: Optional[str] = None
    tahun: Optional[int] = None
    judul: Optional[str] = None
    singkatan: Optional[str] = None
    tanggal_penetapan: Optional[date] = None
    tanggal_berlaku: Optional[date] = None
    status: Optional[str] = None
    sumber_url: Optional[str] = None
    catatan: Optional[str] = None
    is_draft: Optional[bool] = None


class RegulationOut(RegulationBase):
    id: int
    uuid: str
    level: int
    file_hash: Optional[str] = None
    sumber_file: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RegulationList(BaseModel):
    id: int
    uuid: str
    jenis: str
    nomor: Optional[str] = None
    tahun: Optional[int] = None
    judul: str
    status: str
    is_draft: bool
    level: int
    updated_at: datetime

    model_config = {"from_attributes": True}


class RegulationSearchResult(BaseModel):
    id: int
    uuid: str
    jenis: str
    nomor: Optional[str] = None
    tahun: Optional[int] = None
    judul: str
    status: str
    score: float = 1.0
    excerpt: Optional[str] = None

    model_config = {"from_attributes": True}
