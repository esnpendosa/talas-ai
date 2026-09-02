"""
TALAS AI — Dynamic Provider Registry
Mengelola provider AI dari database secara dynamic.
Provider dapat ditambah/edit/hapus tanpa restart server.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai import AIProvider
from app.services.ai.key_store import decode_api_key

logger = logging.getLogger("talas_ai.ai")

# Daftar provider yang didukung dengan preset konfigurasi
PROVIDER_PRESETS = {
    "ollama": {
        "display_name": "Ollama (Local)",
        "provider_type": "ollama",
        "base_url": "http://localhost:11434",
        "is_cloud": False,
        "requires_api_key": False,
        "description": "Model AI lokal via Ollama. Mendukung Llama, Qwen, Gemma, Mistral, dll.",
        "sort_order": 10,
    },
    "lmstudio": {
        "display_name": "LM Studio (Local)",
        "provider_type": "lmstudio",
        "base_url": "http://localhost:1234",
        "is_cloud": False,
        "requires_api_key": False,
        "description": "Model AI lokal via LM Studio. Kompatibel dengan OpenAI API.",
        "sort_order": 20,
    },
    "llamacpp": {
        "display_name": "llama.cpp Server (Local)",
        "provider_type": "llamacpp",
        "base_url": "http://localhost:8080",
        "is_cloud": False,
        "requires_api_key": False,
        "description": "Model AI lokal via llama.cpp server.",
        "sort_order": 30,
    },
    "openai": {
        "display_name": "OpenAI",
        "provider_type": "openai",
        "base_url": "https://api.openai.com/v1",
        "is_cloud": True,
        "requires_api_key": True,
        "description": "GPT-4o, GPT-4 Turbo, GPT-3.5 Turbo. Memerlukan API key dari platform.openai.com",
        "sort_order": 40,
    },
    "openrouter": {
        "display_name": "OpenRouter",
        "provider_type": "openrouter",
        "base_url": "https://openrouter.ai/api/v1",
        "is_cloud": True,
        "requires_api_key": True,
        "description": "Akses 200+ model AI (GPT, Claude, Llama, Gemini, Mistral, dll.) via satu API. openrouter.ai",
        "sort_order": 41,
    },
    "anthropic": {
        "display_name": "Anthropic (Claude)",
        "provider_type": "anthropic",
        "base_url": "https://api.anthropic.com/v1",
        "is_cloud": True,
        "requires_api_key": True,
        "description": "Claude 3.5 Sonnet, Claude 3 Opus, Claude Haiku. console.anthropic.com",
        "sort_order": 42,
    },
    "google": {
        "display_name": "Google (Gemini)",
        "provider_type": "google",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "is_cloud": True,
        "requires_api_key": True,
        "description": "Gemini 1.5 Pro, Gemini 1.5 Flash. aistudio.google.com",
        "sort_order": 43,
    },
    "groq": {
        "display_name": "Groq",
        "provider_type": "groq",
        "base_url": "https://api.groq.com/openai/v1",
        "is_cloud": True,
        "requires_api_key": True,
        "description": "Inferensi ultra-cepat: Llama3, Mixtral, Gemma. console.groq.com",
        "sort_order": 44,
    },
    "together": {
        "display_name": "Together AI",
        "provider_type": "together",
        "base_url": "https://api.together.xyz/v1",
        "is_cloud": True,
        "requires_api_key": True,
        "description": "70+ open-source model: Llama, Mistral, Qwen, dll. api.together.ai",
        "sort_order": 45,
    },
    "mistral": {
        "display_name": "Mistral AI",
        "provider_type": "mistral",
        "base_url": "https://api.mistral.ai/v1",
        "is_cloud": True,
        "requires_api_key": True,
        "description": "Mistral Large, Mistral Small, Codestral. console.mistral.ai",
        "sort_order": 46,
    },
    "cohere": {
        "display_name": "Cohere",
        "provider_type": "cohere",
        "base_url": "https://api.cohere.ai/v1",
        "is_cloud": True,
        "requires_api_key": True,
        "description": "Command R+, Command R. dashboard.cohere.com",
        "sort_order": 47,
    },
    "deepseek": {
        "display_name": "DeepSeek",
        "provider_type": "deepseek",
        "base_url": "https://api.deepseek.com/v1",
        "is_cloud": True,
        "requires_api_key": True,
        "description": "DeepSeek Chat, DeepSeek Coder. platform.deepseek.com",
        "sort_order": 48,
    },
    "custom": {
        "display_name": "Custom OpenAI-Compatible",
        "provider_type": "custom",
        "base_url": "",
        "is_cloud": False,
        "requires_api_key": False,
        "description": "Server yang kompatibel dengan OpenAI API format. Isi Base URL sesuai server.",
        "sort_order": 99,
    },
}


async def load_provider_from_db(
    db: AsyncSession,
    provider_name: str,
) -> Optional[object]:
    """
    Load provider dari database dan instansiasi object provider-nya.
    Kembalikan instance BaseLLMProvider atau None.
    """
    result = await db.execute(
        select(AIProvider).where(
            AIProvider.name == provider_name,
            AIProvider.is_enabled == True,
        )
    )
    db_provider = result.scalar_one_or_none()
    if not db_provider:
        return None

    return _instantiate_provider(db_provider)


def _instantiate_provider(db_provider: AIProvider):
    """Buat instance provider dari data database."""
    api_key = ""
    if db_provider.api_key_encrypted:
        api_key = decode_api_key(db_provider.api_key_encrypted)

    extra_headers = {}
    if db_provider.extra_headers_json:
        try:
            extra_headers = json.loads(db_provider.extra_headers_json)
        except Exception:
            pass

    pt = db_provider.provider_type
    base_url = db_provider.base_url or ""
    timeout = db_provider.timeout or 120

    # Provider lokal
    if pt == "ollama":
        from app.services.ai.providers.ollama import OllamaProvider
        return OllamaProvider(base_url=base_url, timeout=timeout)

    if pt == "lmstudio":
        from app.services.ai.providers.lmstudio import LMStudioProvider
        return LMStudioProvider(base_url=base_url, timeout=timeout)

    if pt == "llamacpp":
        from app.services.ai.providers.openai_compatible import OpenAICompatibleProvider
        return OpenAICompatibleProvider(
            base_url=base_url, api_key=api_key,
            provider_name="llamacpp", is_cloud=False, timeout=timeout,
        )

    # Cloud providers — semua pakai OpenAI-compatible adapter kecuali Anthropic & Google
    if pt in ("openai", "openrouter", "groq", "together", "mistral",
              "deepseek", "cohere", "custom"):
        from app.services.ai.providers.openai_compatible import OpenAICompatibleProvider
        # OpenRouter memerlukan header tambahan
        if pt == "openrouter":
            extra_headers.setdefault("HTTP-Referer", "https://talas-ai.pemda.local")
            extra_headers.setdefault("X-Title", "TALAS AI")
        return OpenAICompatibleProvider(
            base_url=base_url, api_key=api_key,
            provider_name=db_provider.name, is_cloud=db_provider.is_cloud,
            timeout=timeout, extra_headers=extra_headers,
        )

    if pt == "anthropic":
        from app.services.ai.providers.anthropic import AnthropicProvider
        return AnthropicProvider(api_key=api_key, timeout=timeout)

    if pt == "google":
        from app.services.ai.providers.google import GoogleProvider
        return GoogleProvider(api_key=api_key, timeout=timeout)

    # Fallback custom
    from app.services.ai.providers.openai_compatible import OpenAICompatibleProvider
    return OpenAICompatibleProvider(
        base_url=base_url, api_key=api_key,
        provider_name=db_provider.name, is_cloud=db_provider.is_cloud,
        timeout=timeout,
    )


async def sync_providers_from_db(db: AsyncSession, ai_router) -> None:
    """
    Sync semua provider yang enabled dari database ke AI Router.
    Dipanggil saat startup dan saat ada perubahan konfigurasi.
    """
    result = await db.execute(
        select(AIProvider)
        .where(AIProvider.is_enabled == True)
        .order_by(AIProvider.sort_order)
    )
    providers = result.scalars().all()

    registered = 0
    for db_provider in providers:
        try:
            instance = _instantiate_provider(db_provider)
            if instance:
                ai_router.register_provider(db_provider.name, instance)
                registered += 1
        except Exception as e:
            logger.error(f"Failed to load provider {db_provider.name}: {e}")

    logger.info(f"Synced {registered} providers from database.")
