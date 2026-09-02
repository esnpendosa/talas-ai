"""
TALAS AI — OpenAI-Compatible Provider
Untuk cloud AI (OpenAI, Groq, Together, OpenRouter, Mistral, DeepSeek, dll.)
atau llama.cpp server.
Cloud HANYA digunakan jika pengguna memberikan izin eksplisit.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

import httpx

from app.services.ai.base import (
    BaseLLMProvider, ChatMessage, LLMResponse, ModelInfo, ProviderHealth
)

logger = logging.getLogger("talas_ai.ai")


class OpenAICompatibleProvider(BaseLLMProvider):
    """Provider generik untuk semua server yang kompatibel dengan OpenAI API."""

    def __init__(
        self,
        base_url: str,
        api_key: str = "",
        provider_name: str = "openai_compatible",
        is_cloud: bool = True,
        timeout: int = 120,
        extra_headers: Optional[Dict[str, str]] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.provider_name = provider_name
        self.is_cloud = is_cloud
        self.timeout = timeout
        self._extra_headers = extra_headers or {}

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        h.update(self._extra_headers)
        return h

    async def chat(
        self,
        messages: List[ChatMessage],
        model: str,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> LLMResponse:
        # Cloud confirmation sudah dilakukan oleh AI Router sebelum memanggil ini
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "stream": False,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()

            choice = data.get("choices", [{}])[0]
            content = choice.get("message", {}).get("content", "")
            usage = data.get("usage", {})
            return LLMResponse(
                content=content,
                model=model,
                provider=self.provider_name,
                prompt_tokens=usage.get("prompt_tokens"),
                completion_tokens=usage.get("completion_tokens"),
                total_tokens=usage.get("total_tokens"),
                is_cloud=self.is_cloud,
                raw=data,
            )
        except httpx.ConnectError:
            return LLMResponse(
                content="", model=model, provider=self.provider_name,
                error=f"Tidak dapat menghubungi {self.provider_name}.",
            )
        except Exception as e:
            logger.error(f"{self.provider_name} chat error: {e}")
            return LLMResponse(
                content="", model=model, provider=self.provider_name,
                error=f"Terjadi kesalahan: {type(e).__name__}",
            )

    async def health_check(self) -> ProviderHealth:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(
                    f"{self.base_url}/models",
                    headers=self._headers(),
                )
                if resp.status_code in (200, 401):  # 401 = reachable tapi perlu auth
                    return ProviderHealth(
                        provider=self.provider_name,
                        status="connected",
                        message="Server tersedia.",
                    )
        except Exception:
            pass
        return ProviderHealth(
            provider=self.provider_name,
            status="disconnected",
            message=f"{self.provider_name} tidak dapat dihubungi.",
        )

    async def list_models(self) -> List[ModelInfo]:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self.base_url}/models",
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                return [
                    ModelInfo(model_id=m["id"], display_name=m["id"])
                    for m in data.get("data", [])
                ]
        except Exception:
            return []
