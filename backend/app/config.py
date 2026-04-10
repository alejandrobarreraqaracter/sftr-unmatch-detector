import os
from dotenv import load_dotenv

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")          # default/fallback
LLM_MODEL = os.getenv("LLM_MODEL", "gemma4:e4b")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
LLM_API_KEY = os.getenv("LLM_API_KEY", "")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", os.getenv("LLM_API_KEY", ""))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", os.getenv("LLM_API_KEY", ""))
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", LLM_BASE_URL)

DEFAULT_LLM_PROFILES = [
    {
        "key": "anthropic_claude_sonnet_4_6",
        "label": "anthropic · claude-sonnet-4-6",
        "provider": "anthropic",
        "model": "claude-sonnet-4-6",
        "base_url": None,
        "input_cost_per_million": 3.0,
        "output_cost_per_million": 15.0,
        "is_active": LLM_PROVIDER == "anthropic",
    },
    {
        "key": "ollama_gemma4_e2b",
        "label": "ollama · gemma4:e2b",
        "provider": "ollama",
        "model": "gemma4:e2b",
        "base_url": OLLAMA_BASE_URL,
        "input_cost_per_million": 0.0,
        "output_cost_per_million": 0.0,
        "is_active": LLM_PROVIDER == "ollama",
    },
    {
        "key": "openai_gpt_5_4_mini",
        "label": "openai · gpt-4o-mini",
        "provider": "openai",
        "model": "gpt-4o-mini",
        "base_url": OPENAI_BASE_URL,
        "input_cost_per_million": 0.75,
        "output_cost_per_million": 4.50,
        "is_active": LLM_PROVIDER == "openai",
    },
]
