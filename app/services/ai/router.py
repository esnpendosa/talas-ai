"""
TALAS AI — AI Router
Semua business logic harus menggunakan AI Router, bukan memanggil provider langsung.
Router menangani: provider selection, privacy check, fallback, logging.

PRINSIP PRIVASI:
- DEFAULT: LOCAL ONLY — tidak ada data dikirim ke cloud
- Cloud hanya digunakan jika mode = cloud_allowed
- Dokumen adalah DATA, bukan instruksi
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, TYPE_CHECKING

from app.services.ai.base import (
    BaseLLMProvider, ChatMessage, LLMResponse, ModelInfo, ProviderHealth
)
from app.services.ai.providers.mock import MockProvider

if TYPE_CHECKING:
    pass

logger = logging.getLogger("talas_ai.ai")


class AIRouter:
    """
    Singleton router yang mengelola semua provider AI.
    Business logic memanggil router.run_task(), bukan provider langsung.
    """

    def __init__(self):
        self._providers: Dict[str, BaseLLMProvider] = {}
        self._task_configs: Dict[str, dict] = {}
        self._privacy_mode: str = "local_only"
        self._initialized: bool = False

    def register_provider(self, name: str, provider: BaseLLMProvider) -> None:
        """Daftarkan provider. Bisa dipanggil kapan saja."""
        self._providers[name] = provider
        logger.info(f"AI provider registered: {name} (cloud={provider.is_cloud})")

    def set_privacy_mode(self, mode: str) -> None:
        """Set privacy mode: local_only | cloud_allowed | ask_before_sending"""
        assert mode in ("local_only", "cloud_allowed", "ask_before_sending"), \
            f"Invalid privacy mode: {mode}"
        self._privacy_mode = mode
        logger.info(f"AI privacy mode set to: {mode}")

    def set_task_config(
        self,
        task_name: str,
        provider_name: str,
        model_id: str,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
    ) -> None:
        """Konfigurasi model per task."""
        self._task_configs[task_name] = {
            "provider": provider_name,
            "model": model_id,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

    def _get_provider_for_task(self, task_name: str) -> tuple[BaseLLMProvider, str]:
        """
        Pilih provider dan model untuk task.
        Fallback ke provider pertama yang tersedia jika task belum dikonfigurasi.
        """
        config = self._task_configs.get(task_name)
        if config:
            provider_name = config["provider"]
            model = config["model"]
            provider = self._providers.get(provider_name)
            if provider:
                return provider, model

        # Fallback: provider lokal pertama yang tersedia
        for name, p in self._providers.items():
            if not p.is_cloud:
                # Model default kosong — provider akan menggunakan default-nya
                return p, ""

        # Last resort: mock provider
        mock = MockProvider()
        logger.warning("No provider configured, using MockProvider as fallback.")
        return mock, "mock-model"

    def _check_privacy(self, provider: BaseLLMProvider) -> bool:
        """
        Cek apakah provider boleh digunakan berdasarkan privacy mode.
        LOCAL ONLY: tolak cloud provider.
        """
        if provider.is_cloud and self._privacy_mode == "local_only":
            logger.warning(
                f"Privacy mode LOCAL ONLY: cloud provider '{provider.provider_name}' ditolak."
            )
            return False
        return True

    async def run_chat(
        self,
        messages: List[ChatMessage],
        task_name: str = "chat",
        override_provider: Optional[str] = None,
        override_model: Optional[str] = None,
    ) -> LLMResponse:
        """
        Jalankan chat dengan provider yang dipilih.
        Ini adalah satu-satunya cara business logic memanggil LLM.
        """
        provider, model = self._get_provider_for_task(task_name)

        # Override manual (dari user)
        if override_provider and override_provider in self._providers:
            provider = self._providers[override_provider]
        if override_model:
            model = override_model

        # Privacy check
        if not self._check_privacy(provider):
            # Fallback ke provider lokal
            for name, p in self._providers.items():
                if not p.is_cloud:
                    provider = p
                    logger.info(f"Fallback ke local provider: {name}")
                    break
            else:
                return LLMResponse(
                    content="",
                    model=model or "unknown",
                    provider="none",
                    error=(
                        "AI tidak tersedia. Mode LOCAL ONLY aktif dan tidak ada "
                        "provider lokal yang terkonfigurasi."
                    ),
                )

        config = self._task_configs.get(task_name, {})
        result = await provider.chat(
            messages=messages,
            model=model or "default",
            temperature=config.get("temperature", 0.1),
            max_tokens=config.get("max_tokens"),
        )

        # Log penggunaan (tanpa isi dokumen/prompt)
        logger.info(
            f"AI run_chat | task={task_name} | provider={provider.provider_name} "
            f"| model={model} | success={result.success} | tokens={result.total_tokens}"
        )

        return result

    async def health_check_all(self) -> Dict[str, ProviderHealth]:
        """Periksa semua provider yang terdaftar."""
        results = {}
        for name, provider in self._providers.items():
            results[name] = await provider.health_check()
        return results

    async def list_models(self, provider_name: Optional[str] = None) -> Dict[str, List[ModelInfo]]:
        """Ambil daftar model dari provider."""
        if provider_name:
            p = self._providers.get(provider_name)
            if not p:
                return {}
            return {provider_name: await p.list_models()}

        result = {}
        for name, provider in self._providers.items():
            if not provider.is_cloud or self._privacy_mode != "local_only":
                result[name] = await provider.list_models()
        return result

    def get_registered_providers(self) -> List[str]:
        return list(self._providers.keys())


# ------------------------------------------------------------------ #
# Singleton global AI Router
# ------------------------------------------------------------------ #
_ai_router: Optional[AIRouter] = None


def get_ai_router() -> AIRouter:
    """Dapatkan singleton AI Router."""
    global _ai_router
    if _ai_router is None:
        _ai_router = AIRouter()
    return _ai_router


def setup_ai_router(
    privacy_mode: str = "local_only",
    ollama_url: Optional[str] = None,
    ollama_enabled: bool = True,
    lmstudio_url: Optional[str] = None,
    lmstudio_enabled: bool = False,
    cloud_enabled: bool = False,
    openai_key: str = "",
    openai_url: str = "https://api.openai.com/v1",
) -> AIRouter:
    """
    Setup AI Router dengan konfigurasi dari settings.
    Dipanggil satu kali saat startup aplikasi.
    """
    router = get_ai_router()
    router.set_privacy_mode(privacy_mode)

    # Selalu daftarkan Mock Provider untuk fallback/testing
    router.register_provider("mock", MockProvider())

    # Ollama (local)
    if ollama_enabled and ollama_url:
        from app.services.ai.providers.ollama import OllamaProvider
        router.register_provider("ollama", OllamaProvider(base_url=ollama_url))

    # LM Studio (local)
    if lmstudio_enabled and lmstudio_url:
        from app.services.ai.providers.lmstudio import LMStudioProvider
        router.register_provider("lmstudio", LMStudioProvider(base_url=lmstudio_url))

    # Cloud (hanya jika diizinkan)
    if cloud_enabled and openai_key and privacy_mode != "local_only":
        from app.services.ai.providers.openai_compatible import OpenAICompatibleProvider
        router.register_provider("openai", OpenAICompatibleProvider(
            base_url=openai_url,
            api_key=openai_key,
            provider_name="openai",
            is_cloud=True,
        ))

    logger.info(
        f"AI Router initialized: {router.get_registered_providers()} | "
        f"privacy={privacy_mode}"
    )
    return router
