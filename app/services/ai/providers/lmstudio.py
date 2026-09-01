"""
TALAS AI — LM Studio Provider
Compatible dengan OpenAI API format.
"""
from __future__ import annotations

import logging
from typing import List, Optional

import httpx

from app.services.ai.base import (
    BaseLLMProvider, ChatMessage, LLMResponse, ModelInfo, ProviderHealth
)

logger = logging.getLogger("talas_ai.ai")


class LMStudioProvider(BaseLLMProvider):
    provider_name = "lmstudio"
    is_cloud = False

    def __init__(self, base_url: str = "http://localhost:1234", timeout: int = 120):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def chat(
        self,
        messages: List[ChatMessage],
        model: str,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> LLMResponse:
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
                    f"{self.base_url}/v1/chat/completions",
                    json=payload,
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
                is_cloud=False,
                raw=data,
            )
        except httpx.ConnectError:
            return LLMResponse(
                content="", model=model, provider=self.provider_name,
                error="LM Studio tidak tersedia.",
            )
        except Exception as e:
            logger.error(f"LM Studio chat error: {e}")
            return LLMResponse(
                content="", model=model, provider=self.provider_name,
                error="Terjadi kesalahan saat menghubungi LM Studio.",
            )

    async def health_check(self) -> ProviderHealth:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/v1/models")
                if resp.status_code == 200:
                    data = resp.json()
                    models = data.get("data", [])
                    return ProviderHealth(
                        provider=self.provider_name,
                        status="connected",
                        message=f"LM Studio tersedia. {len(models)} model.",
                        models_available=len(models),
                    )
        except Exception:
            pass
        return ProviderHealth(
            provider=self.provider_name,
            status="disconnected",
            message="LM Studio tidak dapat dihubungi.",
        )

    async def list_models(self) -> List[ModelInfo]:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{self.base_url}/v1/models")
                resp.raise_for_status()
                data = resp.json()
                return [
                    ModelInfo(
                        model_id=m["id"],
                        display_name=m.get("id", ""),
                        model_type="chat",
                    )
                    for m in data.get("data", [])
                ]
        except Exception:
            return []
