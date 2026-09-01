"""
TALAS AI — FastAPI Dependencies
Dependency injection untuk route handlers.
"""
from typing import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database.connection import get_db

# Re-export untuk kemudahan import di routes
__all__ = ["get_db", "get_settings"]
