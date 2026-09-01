"""
TALAS AI — Base LLM Provider Interface
Semua provider harus mengimplementasikan interface ini.
Business logic TIDAK boleh memanggil provider langsung — harus via AI Router.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ChatMessage:
    role: str   # "system" | "user" | "assistant"
    content: str


@dataclass
class LLMResponse:
    content: str
    model: str
    provider: str
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    is_cloud: bool = False
    raw: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return bool(self.content) and not self.error


@dataclass
class ModelInfo:
    model_id: str
    display_name: str
    model_type: str = "chat"    # chat | embedding | completion
    context_length: Optional[int] = None
    size_gb: Optional[float] = None


@dataclass
class ProviderHealth:
    provider: str
    status: str         # connected | disconnected | error | unknown
    message: str = ""
    models_available: int = 0


class BaseLLMProvider(ABC):
    """
    Interface wajib untuk semua LLM provider.
    Implementasi baru cukup extend class ini tanpa mengubah business logic.
    """

    provider_name: str = "base"
    is_cloud: bool = False

    @abstractmethod
    async def chat(
        self,
        messages: List[ChatMessage],
        model: str,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> LLMResponse:
        """Kirim chat completion request."""
        ...

    @abstractmethod
    async def health_check(self) -> ProviderHealth:
        """Periksa koneksi ke provider."""
        ...

    @abstractmethod
    async def list_models(self) -> List[ModelInfo]:
        """Ambil daftar model yang tersedia."""
        ...

    async def embed(
        self,
        texts: List[str],
        model: str,
        **kwargs,
    ) -> List[List[float]]:
        """Buat embedding. Override jika provider mendukung."""
        raise NotImplementedError(
            f"Provider {self.provider_name} tidak mendukung embedding."
        )
