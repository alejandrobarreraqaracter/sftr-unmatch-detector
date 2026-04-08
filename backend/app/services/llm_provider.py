"""
Provider-agnostic LLM abstraction.

Supported providers:
  - ollama    → local Ollama server (default, free)
  - anthropic → Anthropic API (claude-sonnet-4-6)
  - openai    → OpenAI API (gpt-4o)

Configuration via environment variables (see .env):
  LLM_PROVIDER, LLM_MODEL, LLM_BASE_URL, LLM_API_KEY
"""

from abc import ABC, abstractmethod
import httpx
from app.config import LLM_PROVIDER, LLM_MODEL, LLM_BASE_URL, LLM_API_KEY


class LLMProvider(ABC):
    name: str
    model: str

    @abstractmethod
    async def complete(self, system: str, user: str) -> str:
        """Send a prompt and return the response text."""

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the provider is reachable."""


# ─── Ollama ───────────────────────────────────────────────────────────────────

class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self, base_url: str, model: str):
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
            return resp.json()["response"].strip()

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False


# ─── Anthropic ────────────────────────────────────────────────────────────────

class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, api_key: str, model: str):
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
            return resp.json()["content"][0]["text"].strip()

    async def is_available(self) -> bool:
        return bool(self.api_key)


# ─── OpenAI ───────────────────────────────────────────────────────────────────

class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, api_key: str, model: str, base_url: str = "https://api.openai.com/v1"):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

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
            return resp.json()["choices"][0]["message"]["content"].strip()

    async def is_available(self) -> bool:
        return bool(self.api_key)


# ─── Factory ──────────────────────────────────────────────────────────────────

def get_provider() -> LLMProvider:
    if LLM_PROVIDER == "anthropic":
        return AnthropicProvider(api_key=LLM_API_KEY, model=LLM_MODEL or "claude-sonnet-4-6")
    elif LLM_PROVIDER == "openai":
        return OpenAIProvider(api_key=LLM_API_KEY, model=LLM_MODEL or "gpt-4o")
    else:
        return OllamaProvider(base_url=LLM_BASE_URL, model=LLM_MODEL or "gemma4:e4b")
