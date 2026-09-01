"""TALAS AI — Document Schemas"""
from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: int
    uuid: str
    regulation_id: Optional[int] = None
    original_filename: str
    file_size: int
    file_type: str
    processing_status: str
    page_count: Optional[int] = None
    extracted_text_length: Optional[int] = None
    ocr_used: bool
    processing_error: Optional[str] = None
    processed_at: Optional[datetime] = None
    created_at: datetime
    model_config = {"from_attributes": True}


class DocumentChunkOut(BaseModel):
    id: int
    chunk_index: int
    text: str
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    bab: Optional[str] = None
    bagian: Optional[str] = None
    pasal: Optional[str] = None
    ayat: Optional[str] = None
    model_config = {"from_attributes": True}
