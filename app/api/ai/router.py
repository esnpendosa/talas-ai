"""
TALAS AI — AI Configuration API (Dynamic)
CRUD provider, model, task config — semua dinamis dari database.
API key tidak pernah dikembalikan ke client.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.dependencies import get_current_user, require_permissions
from app.models.ai import AIProvider, AIModel, AITaskConfig
from app.models.user import User
from app.services.ai.key_store import encode_api_key, decode_api_key, mask_api_key
from app.services.ai.provider_registry import (
    PROVIDER_PRESETS,
    sync_providers_from_db,
    _instantiate_provider,
)
from app.services.ai.router import get_ai_router

logger = logging.getLogger("talas_ai.ai")
router = APIRouter(prefix="/ai", tags=["AI & Model"])


# ------------------------------------------------------------------ #
# Schemas
# ------------------------------------------------------------------ #

class ProviderOut(BaseModel):
    id: int
    name: str
    display_name: str
    provider_type: str
    base_url: Optional[str]
    is_enabled: bool
    is_cloud: bool
    requires_api_key: bool
    has_api_key: bool       # True jika API key sudah diset (tidak mengembalikan key-nya)
    api_key_hint: Optional[str]  # 4 karakter terakhir
    description: Optional[str]
    last_health_check: Optional[str]
    last_health_check_at: Optional[str]
    sort_order: int
    model_config = {"from_attributes": True}


class ProviderCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    display_name: str = Field(..., min_length=2, max_length=200)
    provider_type: str
    base_url: Optional[str] = None
    api_key: Optional[str] = None    # Tidak disimpan plaintext
    is_enabled: bool = True
    is_cloud: bool = False
    requires_api_key: bool = False
    description: Optional[str] = None
    extra_headers_json: Optional[str] = None
    timeout: int = 120
    sort_order: int = 100


class ProviderUpdate(BaseModel):
    display_name: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None    # None = tidak ubah, "" = hapus
    is_enabled: Optional[bool] = None
    timeout: Optional[int] = None
    description: Optional[str] = None
    extra_headers_json: Optional[str] = None
    sort_order: Optional[int] = None


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
    context_length: Optional[int] = None
    size_gb: Optional[float] = None


class TaskConfigOut(BaseModel):
    task_name: str
    provider_name: Optional[str]
    model_id: Optional[str]
    temperature: Optional[float]
    max_tokens: Optional[int]


class TaskConfigIn(BaseModel):
    task_name: str
    provider_name: str
    model_id: str
    temperature: float = 0.1
    max_tokens: Optional[int] = None


class PrivacyModeUpdate(BaseModel):
    mode: str  # local_only | cloud_allowed | ask_before_sending


class PresetOut(BaseModel):
    key: str
    display_name: str
    provider_type: str
    base_url: str
    is_cloud: bool
    requires_api_key: bool
    description: str


# ------------------------------------------------------------------ #
# Provider CRUD
# ------------------------------------------------------------------ #

@router.get(
    "/providers",
    response_model=List[ProviderOut],
    summary="Daftar semua AI provider",
)
async def list_providers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("ai_config:read")),
):
    """Daftar semua provider AI yang terdaftar di database."""
    result = await db.execute(
        select(AIProvider).order_by(AIProvider.sort_order, AIProvider.name)
    )
    providers = result.scalars().all()
    return [
        ProviderOut(
            id=p.id,
            name=p.name,
            display_name=p.display_name,
            provider_type=p.provider_type,
            base_url=p.base_url,
            is_enabled=p.is_enabled,
            is_cloud=p.is_cloud,
            requires_api_key=p.requires_api_key,
            has_api_key=bool(p.api_key_encrypted),
            api_key_hint=p.api_key_hint,
            description=p.description,
            last_health_check=p.last_health_check,
            last_health_check_at=p.last_health_check_at,
            sort_order=p.sort_order,
        )
        for p in providers
    ]


@router.post(
    "/providers",
    response_model=ProviderOut,
    status_code=status.HTTP_201_CREATED,
    summary="Tambah AI provider",
)
async def create_provider(
    body: ProviderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("ai_config:write")),
):
    """Tambah provider AI baru ke database."""
    # Cek nama duplikat
    existing = await db.execute(
        select(AIProvider).where(AIProvider.name == body.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Provider '{body.name}' sudah ada.")

    # Encode API key
    encrypted = ""
    hint = None
    if body.api_key:
        encrypted = encode_api_key(body.api_key)
        hint = mask_api_key(body.api_key)

    provider = AIProvider(
        name=body.name,
        display_name=body.display_name,
        provider_type=body.provider_type,
        base_url=body.base_url,
        api_key_encrypted=encrypted or None,
        api_key_hint=hint,
        is_enabled=body.is_enabled,
        is_cloud=body.is_cloud,
        requires_api_key=body.requires_api_key,
        description=body.description,
        extra_headers_json=body.extra_headers_json,
        timeout=body.timeout,
        sort_order=body.sort_order,
    )
    db.add(provider)
    await db.commit()
    await db.refresh(provider)

    # Sync ke AI Router jika enabled
    if provider.is_enabled:
        await _reload_provider_in_router(provider)

    return ProviderOut(
        id=provider.id, name=provider.name, display_name=provider.display_name,
        provider_type=provider.provider_type, base_url=provider.base_url,
        is_enabled=provider.is_enabled, is_cloud=provider.is_cloud,
        requires_api_key=provider.requires_api_key,
        has_api_key=bool(provider.api_key_encrypted),
        api_key_hint=provider.api_key_hint, description=provider.description,
        last_health_check=provider.last_health_check,
        last_health_check_at=provider.last_health_check_at,
        sort_order=provider.sort_order,
    )


@router.put(
    "/providers/{provider_name}",
    response_model=ProviderOut,
    summary="Update AI provider",
)
async def update_provider(
    provider_name: str,
    body: ProviderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("ai_config:write")),
):
    """Update konfigurasi provider. API key tidak dikembalikan."""
    result = await db.execute(
        select(AIProvider).where(AIProvider.name == provider_name)
    )
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_name}' tidak ditemukan.")

    if body.display_name is not None:
        provider.display_name = body.display_name
    if body.base_url is not None:
        provider.base_url = body.base_url
    if body.is_enabled is not None:
        provider.is_enabled = body.is_enabled
    if body.timeout is not None:
        provider.timeout = body.timeout
    if body.description is not None:
        provider.description = body.description
    if body.extra_headers_json is not None:
        provider.extra_headers_json = body.extra_headers_json
    if body.sort_order is not None:
        provider.sort_order = body.sort_order

    # API key: None = tidak ubah, "" = hapus, string = update
    if body.api_key is not None:
        if body.api_key == "":
            provider.api_key_encrypted = None
            provider.api_key_hint = None
        else:
            provider.api_key_encrypted = encode_api_key(body.api_key)
            provider.api_key_hint = mask_api_key(body.api_key)

    await db.commit()
    await db.refresh(provider)

    # Reload di router
    await _reload_provider_in_router(provider)

    return ProviderOut(
        id=provider.id, name=provider.name, display_name=provider.display_name,
        provider_type=provider.provider_type, base_url=provider.base_url,
        is_enabled=provider.is_enabled, is_cloud=provider.is_cloud,
        requires_api_key=provider.requires_api_key,
        has_api_key=bool(provider.api_key_encrypted),
        api_key_hint=provider.api_key_hint, description=provider.description,
        last_health_check=provider.last_health_check,
        last_health_check_at=provider.last_health_check_at,
        sort_order=provider.sort_order,
    )


@router.delete(
    "/providers/{provider_name}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Hapus AI provider",
)
async def delete_provider(
    provider_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("ai_config:write")),
):
    """Hapus provider dari database dan unregister dari AI Router."""
    result = await db.execute(
        select(AIProvider).where(AIProvider.name == provider_name)
    )
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_name}' tidak ditemukan.")

    await db.execute(delete(AIProvider).where(AIProvider.name == provider_name))
    await db.commit()

    # Unregister dari router
    ai_router = get_ai_router()
    if provider_name in ai_router._providers:
        del ai_router._providers[provider_name]

    return None


@router.post(
    "/providers/{provider_name}/test",
    summary="Test koneksi provider",
)
async def test_provider(
    provider_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("ai_config:read")),
):
    """Test koneksi ke provider. Tidak mengirim dokumen, hanya ping."""
    # Cari di database
    result = await db.execute(
        select(AIProvider).where(AIProvider.name == provider_name)
    )
    db_provider = result.scalar_one_or_none()

    # Atau cari di router jika ada
    ai_router = get_ai_router()
    provider_instance = ai_router._providers.get(provider_name)

    if not provider_instance and db_provider:
        provider_instance = _instantiate_provider(db_provider)

    if not provider_instance:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_name}' tidak ditemukan.")

    health = await provider_instance.health_check()

    # Update status di database
    if db_provider:
        db_provider.last_health_check = health.status
        db_provider.last_health_check_at = datetime.now(timezone.utc).isoformat()
        await db.commit()

    return {
        "provider": provider_name,
        "status": health.status,
        "message": health.message,
        "models_available": health.models_available,
    }


@router.get(
    "/providers/{provider_name}/models",
    response_model=List[ModelOut],
    summary="Daftar model dari provider",
)
async def list_provider_models(
    provider_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("ai_config:read")),
):
    """Ambil daftar model dari provider tertentu."""
    ai_router = get_ai_router()
    provider_instance = ai_router._providers.get(provider_name)

    if not provider_instance:
        # Coba load dari database
        result = await db.execute(
            select(AIProvider).where(AIProvider.name == provider_name)
        )
        db_provider = result.scalar_one_or_none()
        if db_provider:
            provider_instance = _instantiate_provider(db_provider)

    if not provider_instance:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_name}' tidak ditemukan.")

    models = await provider_instance.list_models()
    return [
        ModelOut(
            provider=provider_name,
            model_id=m.model_id,
            display_name=m.display_name,
            model_type=m.model_type,
            context_length=m.context_length,
            size_gb=m.size_gb,
        )
        for m in models
    ]


@router.post(
    "/models/refresh",
    summary="Refresh model semua provider",
)
async def refresh_all_models(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("ai_config:read")),
):
    """Refresh daftar model dari semua provider yang aktif."""
    ai_router = get_ai_router()
    summary = {}
    for name, provider in ai_router._providers.items():
        try:
            models = await provider.list_models()
            summary[name] = len(models)
        except Exception as e:
            summary[name] = f"error: {e}"

    total = sum(v for v in summary.values() if isinstance(v, int))
    return {"refreshed": True, "total_models": total, "by_provider": summary}


# ------------------------------------------------------------------ #
# Status semua provider aktif
# ------------------------------------------------------------------ #

@router.get(
    "/status",
    summary="Status semua provider yang aktif",
)
async def get_all_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("ai_config:read")),
):
    """Health check semua provider yang sedang aktif di AI Router."""
    ai_router = get_ai_router()
    health_map = await ai_router.health_check_all()
    result = []
    for name, h in health_map.items():
        p = ai_router._providers.get(name)
        result.append({
            "name": name,
            "status": h.status,
            "message": h.message,
            "models_available": h.models_available,
            "is_cloud": p.is_cloud if p else False,
        })
    return result


# ------------------------------------------------------------------ #
# Presets
# ------------------------------------------------------------------ #

@router.get(
    "/presets",
    response_model=List[PresetOut],
    summary="Daftar template provider yang tersedia",
)
async def list_presets(
    current_user: User = Depends(require_permissions("ai_config:read")),
):
    """Daftar preset provider yang dapat digunakan sebagai template."""
    return [
        PresetOut(
            key=key,
            display_name=v["display_name"],
            provider_type=v["provider_type"],
            base_url=v["base_url"],
            is_cloud=v["is_cloud"],
            requires_api_key=v["requires_api_key"],
            description=v["description"],
        )
        for key, v in PROVIDER_PRESETS.items()
    ]


@router.post(
    "/providers/from-preset/{preset_key}",
    response_model=ProviderOut,
    status_code=status.HTTP_201_CREATED,
    summary="Tambah provider dari preset",
)
async def create_from_preset(
    preset_key: str,
    api_key: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("ai_config:write")),
):
    """Tambah provider baru menggunakan konfigurasi preset."""
    preset = PROVIDER_PRESETS.get(preset_key)
    if not preset:
        raise HTTPException(status_code=404, detail=f"Preset '{preset_key}' tidak ditemukan.")

    # Cek duplikat
    existing = await db.execute(
        select(AIProvider).where(AIProvider.name == preset_key)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400,
                            detail=f"Provider '{preset_key}' sudah ada. Gunakan PUT untuk update.")

    encrypted = ""
    hint = None
    if api_key:
        encrypted = encode_api_key(api_key)
        hint = mask_api_key(api_key)

    provider = AIProvider(
        name=preset_key,
        display_name=preset["display_name"],
        provider_type=preset["provider_type"],
        base_url=preset["base_url"],
        is_enabled=bool(api_key or not preset["requires_api_key"]),
        is_cloud=preset["is_cloud"],
        requires_api_key=preset["requires_api_key"],
        api_key_encrypted=encrypted or None,
        api_key_hint=hint,
        description=preset["description"],
        sort_order=preset["sort_order"],
    )
    db.add(provider)
    await db.commit()
    await db.refresh(provider)

    if provider.is_enabled:
        await _reload_provider_in_router(provider)

    return ProviderOut(
        id=provider.id, name=provider.name, display_name=provider.display_name,
        provider_type=provider.provider_type, base_url=provider.base_url,
        is_enabled=provider.is_enabled, is_cloud=provider.is_cloud,
        requires_api_key=provider.requires_api_key,
        has_api_key=bool(provider.api_key_encrypted),
        api_key_hint=provider.api_key_hint, description=provider.description,
        last_health_check=provider.last_health_check,
        last_health_check_at=provider.last_health_check_at,
        sort_order=provider.sort_order,
    )


# ------------------------------------------------------------------ #
# Task Configuration
# ------------------------------------------------------------------ #

TASK_NAMES = [
    "chat", "legal_basis", "conflict", "consistency",
    "comparison", "summary", "report", "embedding",
]

TASK_LABELS = {
    "chat": "Chatbot Regulasi",
    "legal_basis": "Cek Dasar Hukum",
    "conflict": "Cek Konflik",
    "consistency": "Cek Konsistensi",
    "comparison": "Perbandingan",
    "summary": "Ringkasan",
    "report": "Generate Laporan",
    "embedding": "Pencarian Semantik",
}


@router.get(
    "/task-configs",
    summary="Konfigurasi model per task",
)
async def get_task_configs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("ai_config:read")),
):
    """Ambil konfigurasi model untuk setiap task (global default)."""
    result = await db.execute(
        select(AITaskConfig).where(AITaskConfig.user_id == None)
    )
    configs = {c.task_name: c for c in result.scalars().all()}

    ai_router = get_ai_router()
    router_configs = ai_router._task_configs

    output = []
    for task in TASK_NAMES:
        db_cfg = configs.get(task)
        router_cfg = router_configs.get(task, {})
        output.append({
            "task_name": task,
            "task_label": TASK_LABELS.get(task, task),
            "provider_name": db_cfg.provider_name if db_cfg else router_cfg.get("provider"),
            "model_id": db_cfg.model_id if db_cfg else router_cfg.get("model"),
            "temperature": db_cfg.temperature if db_cfg else router_cfg.get("temperature", 0.1),
            "max_tokens": db_cfg.max_tokens if db_cfg else router_cfg.get("max_tokens"),
        })

    return {
        "tasks": output,
        "available_providers": ai_router.get_registered_providers(),
    }


@router.put(
    "/task-configs",
    summary="Update konfigurasi model untuk task",
)
async def update_task_config(
    body: TaskConfigIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("ai_config:write")),
):
    """Update model yang digunakan untuk task tertentu."""
    ai_router = get_ai_router()
    if body.provider_name not in ai_router.get_registered_providers():
        raise HTTPException(
            status_code=400,
            detail=f"Provider '{body.provider_name}' tidak aktif. Aktifkan provider terlebih dahulu."
        )

    # Update di AI Router
    ai_router.set_task_config(
        task_name=body.task_name,
        provider_name=body.provider_name,
        model_id=body.model_id,
        temperature=body.temperature,
        max_tokens=body.max_tokens,
    )

    # Simpan ke database (global config)
    result = await db.execute(
        select(AITaskConfig).where(
            AITaskConfig.task_name == body.task_name,
            AITaskConfig.user_id == None,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.provider_name = body.provider_name
        existing.model_id = body.model_id
        existing.temperature = body.temperature
        existing.max_tokens = body.max_tokens
    else:
        db.add(AITaskConfig(
            user_id=None,
            task_name=body.task_name,
            provider_name=body.provider_name,
            model_id=body.model_id,
            temperature=body.temperature,
            max_tokens=body.max_tokens,
        ))
    await db.commit()

    return {
        "success": True,
        "task_name": body.task_name,
        "provider_name": body.provider_name,
        "model_id": body.model_id,
        "message": f"Task '{body.task_name}' dikonfigurasi ke {body.provider_name}/{body.model_id}",
    }


# ------------------------------------------------------------------ #
# Privacy Mode & Settings
# ------------------------------------------------------------------ #

@router.get(
    "/settings",
    summary="Konfigurasi AI saat ini",
)
async def get_ai_settings(
    current_user: User = Depends(require_permissions("ai_config:read")),
):
    """Tampilkan konfigurasi AI aktif. API key tidak dikembalikan."""
    ai_router = get_ai_router()
    return {
        "privacy_mode": ai_router._privacy_mode,
        "registered_providers": ai_router.get_registered_providers(),
        "disclaimer": "TINJAUAN AWAL AI — WAJIB VERIFIKASI MANUSIA.",
    }


@router.put(
    "/settings/privacy",
    summary="Update mode privasi AI",
)
async def update_privacy_mode(
    body: PrivacyModeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("ai_config:write")),
):
    """Ubah mode privasi AI. LOCAL ONLY = tidak ada data ke cloud."""
    valid = ("local_only", "cloud_allowed", "ask_before_sending")
    if body.mode not in valid:
        raise HTTPException(status_code=400,
                            detail=f"Mode tidak valid. Pilih: {', '.join(valid)}")

    ai_router = get_ai_router()
    ai_router.set_privacy_mode(body.mode)

    # Simpan ke AppSettings
    from app.models.settings import AppSettings
    result = await db.execute(
        select(AppSettings).where(AppSettings.key == "ai.default_mode")
    )
    setting = result.scalar_one_or_none()
    if setting:
        setting.value = body.mode
    else:
        db.add(AppSettings(key="ai.default_mode", value=body.mode,
                           value_type="string", is_public=True))
    await db.commit()

    return {"privacy_mode": body.mode, "message": f"Mode privasi diubah ke: {body.mode}"}


@router.post(
    "/sync",
    summary="Sync provider dari database ke AI Router",
)
async def sync_providers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("ai_config:write")),
):
    """Reload semua provider yang enabled dari database ke AI Router."""
    ai_router = get_ai_router()
    await sync_providers_from_db(db, ai_router)
    return {
        "success": True,
        "registered": ai_router.get_registered_providers(),
        "message": "Provider berhasil disync dari database.",
    }


# ------------------------------------------------------------------ #
# Helper
# ------------------------------------------------------------------ #

async def _reload_provider_in_router(db_provider: AIProvider) -> None:
    """Instansiasi ulang provider dan daftarkan ke AI Router."""
    ai_router = get_ai_router()
    try:
        if not db_provider.is_enabled:
            # Nonaktifkan dari router jika ada
            if db_provider.name in ai_router._providers:
                del ai_router._providers[db_provider.name]
            return
        instance = _instantiate_provider(db_provider)
        if instance:
            ai_router.register_provider(db_provider.name, instance)
    except Exception as e:
        logger.error(f"Failed to reload provider {db_provider.name}: {e}")
