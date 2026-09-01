"""
TALAS AI — Auth Schemas
"""
from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, EmailStr, field_validator


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # detik


class UserMe(BaseModel):
    id: int
    uuid: str
    username: str
    email: str
    full_name: str
    position: Optional[str] = None
    department: Optional[str] = None
    is_active: bool
    is_superuser: bool
    must_change_password: bool
    ai_privacy_mode: str
    roles: List[str] = []

    model_config = {"from_attributes": True}


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password minimal 8 karakter.")
        return v


class UserCreate(BaseModel):
    username: str
    email: str
    full_name: str
    password: str
    position: Optional[str] = None
    department: Optional[str] = None
    role: str = "opd"

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password minimal 8 karakter.")
        return v

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.strip().lower()
        if len(v) < 3:
            raise ValueError("Username minimal 3 karakter.")
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Username hanya boleh huruf, angka, _ dan -.")
        return v


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    position: Optional[str] = None
    department: Optional[str] = None
    ai_privacy_mode: Optional[str] = None
    is_active: Optional[bool] = None
