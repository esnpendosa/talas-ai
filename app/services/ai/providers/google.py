"""
TALAS AI — Google Gemini Provider
"""
from __future__ import annotations

import logging
from typing import List, Optional

import httpx

from app.services.ai.base import (
    BaseLLMProvider, ChatMessage, LLMResponse, ModelInfo, ProviderHealth
)

logger = logging.getLogger("talas_ai.ai")

GOOGLE_MODELS = [
    ModelInfo("gemini-1.5-pro", "Gemini 1.5 Pro", "chat", 2000000),
    ModelInfo("gemini-1.5-flash", "Gemini 1.5 Flash", "chat", 1000000),
    ModelInfo("gemini-1.5-flash-8b", "Gemini 1.5 Flash 8B", "chat", 1000000),
    ModelInfo("gemini-2.0-flash-exp", "Gemini 2.0 Flash (Exp)", "chat", 1000000),
]


class GoogleProvider(BaseLLMProvider):
    provider_name = "google"
    is_cloud = True

    def __init__(self, api_key: str = "", timeout: int = 120):
        self.api_key = api_key
        self.timeout = timeout
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    async def chat(
        self,
        messages: List[ChatMessage],
        model: str = "gemini-1.5-flash",
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> LLMResponse:
        system_parts = []
        contents = []

        for m in messages:
            if m.role == "system":
                system_parts.append({"text": m.content})
            elif m.role == "user":
                contents.append({"role": "user", "parts": [{"text": m.content}]})
            elif m.role == "assistant":
                contents.append({"role": "model", "parts": [{"text": m.content}]})

        payload: dict = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens or 8192,
            },
        }
        if system_parts:
            payload["systemInstruction"] = {"parts": system_parts}

        url = f"{self.base_url}/models/{model}:generateContent?key={self.api_key}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()

            candidates = data.get("candidates", [])
            content = ""
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                content = "".join(p.get("text", "") for p in parts)

            usage = data.get("usageMetadata", {})
            return LLMResponse(
                content=content,
                model=model,
                provider=self.provider_name,
                prompt_tokens=usage.get("promptTokenCount"),
                completion_tokens=usage.get("candidatesTokenCount"),
                total_tokens=usage.get("totalTokenCount"),
                is_cloud=True,
                raw=data,
            )
        except httpx.ConnectError:
            return LLMResponse(content="", model=model, provider=self.provider_name,
                               error="Tidak dapat menghubungi Google AI API.")
        except Exception as e:
            logger.error(f"Google AI error: {e}")
            return LLMResponse(content="", model=model, provider=self.provider_name,
                               error=f"Error: {type(e).__name__}")

    async def health_check(self) -> ProviderHealth:
        if not self.api_key:
            return ProviderHealth(self.provider_name, "error", "API key tidak dikonfigurasi.")
        try:
            url = f"{self.base_url}/models?key={self.api_key}"
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    return ProviderHealth(self.provider_name, "connected",
                                         "Google AI API tersedia.", len(GOOGLE_MODELS))
        except Exception:
            pass
        return ProviderHealth(self.provider_name, "disconnected", "Tidak dapat menghubungi Google AI.")

    async def list_models(self) -> List[ModelInfo]:
        return GOOGLE_MODELS
