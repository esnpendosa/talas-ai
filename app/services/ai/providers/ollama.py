"""
TALAS AI — Ollama Provider
Connects ke Ollama local server (http://localhost:11434).
Dokumen yang diproses adalah DATA, bukan instruksi.
"""
from __future__ import annotations

import logging
from typing import List, Optional

import httpx

from app.services.ai.base import (
    BaseLLMProvider, ChatMessage, LLMResponse, ModelInfo, ProviderHealth
)

logger = logging.getLogger("talas_ai.ai")


class OllamaProvider(BaseLLMProvider):
    provider_name = "ollama"
    is_cloud = False

    def __init__(self, base_url: str = "http://localhost:11434", timeout: int = 120):
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
            "stream": False,
            "options": {"temperature": temperature},
        }
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()

            content = data.get("message", {}).get("content", "")
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
            logger.warning("Ollama tidak dapat dihubungi.")
            return LLMResponse(
                content="", model=model, provider=self.provider_name,
                error="Ollama tidak tersedia. Pastikan Ollama berjalan.",
            )
        except Exception as e:
            logger.error(f"Ollama chat error: {e}")
            return LLMResponse(
                content="", model=model, provider=self.provider_name,
                error="Terjadi kesalahan saat menghubungi Ollama.",
            )

    async def health_check(self) -> ProviderHealth:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    models = data.get("models", [])
                    return ProviderHealth(
                        provider=self.provider_name,
                        status="connected",
                        message=f"Ollama tersedia. {len(models)} model.",
                        models_available=len(models),
                    )
        except Exception as e:
            logger.debug(f"Ollama health check failed: {e}")

        return ProviderHealth(
            provider=self.provider_name,
            status="disconnected",
            message="Ollama tidak dapat dihubungi.",
        )

    async def list_models(self) -> List[ModelInfo]:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                resp.raise_for_status()
                data = resp.json()
                return [
                    ModelInfo(
                        model_id=m["name"],
                        display_name=m["name"],
                        model_type="chat",
                        size_gb=round(m.get("size", 0) / 1e9, 2),
                    )
                    for m in data.get("models", [])
                ]
        except Exception as e:
            logger.debug(f"Ollama list models failed: {e}")
            return []

    async def embed(
        self,
        texts: List[str],
        model: str,
        **kwargs,
    ) -> List[List[float]]:
        embeddings = []
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                for text in texts:
                    resp = await client.post(
                        f"{self.base_url}/api/embeddings",
                        json={"model": model, "prompt": text},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    embeddings.append(data.get("embedding", []))
        except Exception as e:
            logger.error(f"Ollama embed error: {e}")
            raise
        return embeddings
