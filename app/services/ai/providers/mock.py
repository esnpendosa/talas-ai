"""
TALAS AI — Mock Provider
Untuk testing tanpa LLM nyata.
Selalu mengembalikan response deterministik.
"""
from __future__ import annotations

from typing import List, Optional
from app.services.ai.base import (
    BaseLLMProvider, ChatMessage, LLMResponse, ModelInfo, ProviderHealth
)


class MockProvider(BaseLLMProvider):
    provider_name = "mock"
    is_cloud = False

    def __init__(self, response: str = "Mock response dari TALAS AI."):
        self._response = response

    async def chat(
        self,
        messages: List[ChatMessage],
        model: str = "mock-model",
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> LLMResponse:
        # Simulasi response minimal yang selalu valid
        last_user = next(
            (m.content for m in reversed(messages) if m.role == "user"),
            ""
        )
        content = self._response or f"[Mock] Merespons: {last_user[:50]}"
        return LLMResponse(
            content=content,
            model=model,
            provider=self.provider_name,
            prompt_tokens=len(" ".join(m.content for m in messages).split()),
            completion_tokens=len(content.split()),
            total_tokens=len(" ".join(m.content for m in messages).split()) + len(content.split()),
            is_cloud=False,
        )

    async def health_check(self) -> ProviderHealth:
        return ProviderHealth(
            provider=self.provider_name,
            status="connected",
            message="Mock provider selalu tersedia.",
            models_available=1,
        )

    async def list_models(self) -> List[ModelInfo]:
        return [ModelInfo(
            model_id="mock-model",
            display_name="Mock Model (Testing)",
            model_type="chat",
        )]

    async def embed(self, texts: List[str], model: str = "mock-embed", **kwargs):
        # Return zero vectors untuk testing
        return [[0.0] * 384 for _ in texts]
