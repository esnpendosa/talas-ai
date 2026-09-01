"""
TALAS AI — AI Configuration & Status API
Provider status, model list, task config.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.dependencies import get_current_user, require_permissions
from app.models.user import User
from app.services.ai.router import get_ai_router

logger = logging.getLogger("talas_ai.ai")
router = APIRouter(prefix="/ai", tags=["AI & Model"])


class ProviderStatusOut(BaseModel):
    name: str
    status: str
    message: str
    models_available: int
    is_cloud: bool


class ModelOut(BaseModel):
    provider: str
    model_id: str
    display_name: str
    model_type: str


class TaskConfigIn(BaseModel):
    task_name: str
    provider_name: str
    model_id: str
    temperature: float = 0.1
    max_tokens: Optional[int] = None


@router.get(
    "/providers",
    response_model=List[ProviderStatusOut],
    summary="Status semua AI provider",
    dependencies=[Depends(require_permissions("ai_config:read"))],
)
async def get_providers():
    """Cek status dan koneksi semua provider AI yang terdaftar."""
    router_ = get_ai_router()
    health = await router_.health_check_all()
    result = []
    for name, h in health.items():
        provider = router_._providers.get(name)
        result.append(ProviderStatusOut(
            name=name,
            status=h.status,
            message=h.message,
            models_available=h.models_available,
            is_cloud=provider.is_cloud if provider else False,
        ))
    return result


@router.get(
    "/providers/{provider_name}/models",
    response_model=List[ModelOut],
    summary="Daftar model dari provider",
    dependencies=[Depends(require_permissions("ai_config:read"))],
)
async def list_provider_models(provider_name: str):
    """Ambil daftar model yang tersedia dari provider tertentu."""
    router_ = get_ai_router()
    models_map = await router_.list_models(provider_name)
    if not models_map:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_name}' tidak ditemukan.")
    result = []
    for provider, models in models_map.items():
        for m in models:
            result.append(ModelOut(
                provider=provider,
                model_id=m.model_id,
                display_name=m.display_name,
                model_type=m.model_type,
            ))
    return result


@router.post(
    "/providers/{provider_name}/test",
    summary="Test koneksi provider",
    dependencies=[Depends(require_permissions("ai_config:read"))],
)
async def test_provider(provider_name: str):
    """Kirim ping ke provider untuk verifikasi koneksi."""
    router_ = get_ai_router()
    provider = router_._providers.get(provider_name)
    if not provider:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_name}' tidak terdaftar.")
    health = await provider.health_check()
    return {"provider": provider_name, "status": health.status, "message": health.message}


@router.post(
    "/models/refresh",
    summary="Refresh daftar model semua provider",
    dependencies=[Depends(require_permissions("ai_config:read"))],
)
async def refresh_models():
    """Refresh model list dari semua provider lokal."""
    router_ = get_ai_router()
    all_models = await router_.list_models()
    total = sum(len(v) for v in all_models.values())
    return {"refreshed": True, "total_models": total, "providers": list(all_models.keys())}


@router.get(
    "/settings",
    summary="Konfigurasi AI saat ini",
    dependencies=[Depends(require_permissions("ai_config:read"))],
)
async def get_ai_settings():
    """Tampilkan konfigurasi AI aktif (tanpa API key)."""
    from app.config import settings
    return {
        "privacy_mode": settings.DEFAULT_AI_MODE,
        "ollama_enabled": settings.OLLAMA_ENABLED,
        "ollama_url": settings.OLLAMA_BASE_URL,
        "lmstudio_enabled": settings.LMSTUDIO_ENABLED,
        "cloud_enabled": settings.CLOUD_AI_ENABLED,
        # API key TIDAK ditampilkan
        "registered_providers": get_ai_router().get_registered_providers(),
        "disclaimer": "TINJAUAN AWAL AI — WAJIB VERIFIKASI MANUSIA.",
    }


@router.put(
    "/task-config",
    summary="Set model per task",
    dependencies=[Depends(require_permissions("ai_config:write"))],
)
async def set_task_config(body: TaskConfigIn):
    """Konfigurasi model yang digunakan untuk task tertentu."""
    router_ = get_ai_router()
    if body.provider_name not in router_.get_registered_providers():
        raise HTTPException(status_code=400, detail=f"Provider '{body.provider_name}' tidak terdaftar.")
    router_.set_task_config(
        task_name=body.task_name,
        provider_name=body.provider_name,
        model_id=body.model_id,
        temperature=body.temperature,
        max_tokens=body.max_tokens,
    )
    return {"message": f"Task '{body.task_name}' dikonfigurasi ke {body.provider_name}/{body.model_id}"}
