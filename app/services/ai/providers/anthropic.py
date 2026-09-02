"""
TALAS AI — Anthropic Provider (Claude)
Menggunakan Anthropic Messages API.
"""
from __future__ import annotations

import logging
from typing import List, Optional

import httpx

from app.services.ai.base import (
    BaseLLMProvider, ChatMessage, LLMResponse, ModelInfo, ProviderHealth
)

logger = logging.getLogger("talas_ai.ai")

ANTHROPIC_MODELS = [
    ModelInfo("claude-3-5-sonnet-20241022", "Claude 3.5 Sonnet", "chat", 200000),
    ModelInfo("claude-3-5-haiku-20241022", "Claude 3.5 Haiku", "chat", 200000),
    ModelInfo("claude-3-opus-20240229", "Claude 3 Opus", "chat", 200000),
    ModelInfo("claude-3-haiku-20240307", "Claude 3 Haiku", "chat", 200000),
]


class AnthropicProvider(BaseLLMProvider):
    provider_name = "anthropic"
    is_cloud = True

    def __init__(self, api_key: str = "", timeout: int = 120):
        self.api_key = api_key
        self.timeout = timeout
        self.base_url = "https://api.anthropic.com"

    def _headers(self) -> dict:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

    async def chat(
        self,
        messages: List[ChatMessage],
        model: str = "claude-3-5-sonnet-20241022",
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> LLMResponse:
        # Pisahkan system message
        system_content = ""
        user_messages = []
        for m in messages:
            if m.role == "system":
                system_content = m.content
            else:
                user_messages.append({"role": m.role, "content": m.content})

        payload = {
            "model": model,
            "messages": user_messages,
            "max_tokens": max_tokens or 4096,
            "temperature": temperature,
        }
        if system_content:
            payload["system"] = system_content

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/v1/messages",
                    json=payload,
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()

            content = ""
            for block in data.get("content", []):
                if block.get("type") == "text":
                    content += block.get("text", "")

            usage = data.get("usage", {})
            return LLMResponse(
                content=content,
                model=model,
                provider=self.provider_name,
                prompt_tokens=usage.get("input_tokens"),
                completion_tokens=usage.get("output_tokens"),
                total_tokens=(usage.get("input_tokens", 0) + usage.get("output_tokens", 0)),
                is_cloud=True,
                raw=data,
            )
        except httpx.ConnectError:
            return LLMResponse(content="", model=model, provider=self.provider_name,
                               error="Tidak dapat menghubungi Anthropic API.")
        except Exception as e:
            logger.error(f"Anthropic error: {e}")
            return LLMResponse(content="", model=model, provider=self.provider_name,
                               error=f"Error: {type(e).__name__}")

    async def health_check(self) -> ProviderHealth:
        if not self.api_key:
            return ProviderHealth(self.provider_name, "error", "API key tidak dikonfigurasi.")
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(
                    f"{self.base_url}/v1/models",
                    headers=self._headers(),
                )
                if resp.status_code in (200, 404):
                    return ProviderHealth(self.provider_name, "connected",
                                         "Anthropic API tersedia.", len(ANTHROPIC_MODELS))
        except Exception:
            pass
        return ProviderHealth(self.provider_name, "disconnected", "Tidak dapat menghubungi Anthropic.")

    async def list_models(self) -> List[ModelInfo]:
        return ANTHROPIC_MODELS
