"""
Provider-agnostic LLM abstraction.

Supported providers:
  - ollama    -> local or dockerized Ollama server
  - anthropic -> Anthropic Messages API
  - openai    -> OpenAI Chat Completions API
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import httpx


class LLMProvider(ABC):
    name: str
    model: str

    def __init__(self) -> None:
        self.last_usage: dict[str, int] | None = None

    @abstractmethod
    async def complete(self, system: str, user: str) -> str:
        """Send a prompt and return the response text."""

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the provider is reachable."""


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self, base_url: str, model: str):
        super().__init__()
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def complete(self, system: str, user: str) -> str:
        prompt = f"{system}\n\n{user}"
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
            )
            resp.raise_for_status()
            data = resp.json()
            self.last_usage = {
                "input_tokens": int(data.get("prompt_eval_count") or 0),
                "output_tokens": int(data.get("eval_count") or 0),
                "cached_input_tokens": 0,
            }
            return (data.get("response") or "").strip()

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, api_key: str, model: str):
        super().__init__()
        self.api_key = api_key
        self.model = model

    async def complete(self, system: str, user: str) -> str:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": 1024,
                    "system": system,
                    "messages": [{"role": "user", "content": user}],
                },
            )
            resp.raise_for_status()
            data = resp.json()
            usage = data.get("usage") or {}
            self.last_usage = {
                "input_tokens": int(usage.get("input_tokens") or 0),
                "output_tokens": int(usage.get("output_tokens") or 0),
                "cached_input_tokens": int((usage.get("cache_read_input_tokens") or 0) + (usage.get("cache_creation_input_tokens") or 0)),
            }
            content = data.get("content") or []
            text_parts = [part.get("text", "") for part in content if isinstance(part, dict) and part.get("type") == "text"]
            return "\n".join(part for part in text_parts if part).strip()

    async def is_available(self) -> bool:
        return bool(self.api_key)


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, api_key: str, model: str, base_url: str = "https://api.openai.com/v1"):
        super().__init__()
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")

    async def complete(self, system: str, user: str) -> str:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "max_tokens": 1024,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            usage = data.get("usage") or {}
            prompt_details = usage.get("prompt_tokens_details") or {}
            self.last_usage = {
                "input_tokens": int(usage.get("prompt_tokens") or 0),
                "output_tokens": int(usage.get("completion_tokens") or 0),
                "cached_input_tokens": int(prompt_details.get("cached_tokens") or 0),
            }
            return ((data.get("choices") or [{}])[0].get("message") or {}).get("content", "").strip()

    async def is_available(self) -> bool:
        return bool(self.api_key)
