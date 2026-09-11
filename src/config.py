"""Configuration module for the Multi-Agent Research Assistant."""

import os
from pathlib import Path
from typing import Optional

# Try loading python-dotenv if installed, otherwise parse manually if .env exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip().strip("\"'"))


class Settings:
    """Application and agent execution settings."""

    # Project directories
    PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
    OUTPUT_DIR: Path = PROJECT_ROOT / os.getenv("OUTPUT_DIR", "reports")

    # LLM Settings
    # Options: "openai", "groq", "ollama", "mock"
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "mock").lower()
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    OPENAI_BASE_URL: Optional[str] = os.getenv("OPENAI_BASE_URL")

    # Search Tool Settings
    # Options: "duckduckgo", "tavily", "mock"
    SEARCH_PROVIDER: str = os.getenv("SEARCH_PROVIDER", "duckduckgo").lower()
    TAVILY_API_KEY: Optional[str] = os.getenv("TAVILY_API_KEY")
    MAX_SEARCH_QUERIES: int = int(os.getenv("MAX_SEARCH_QUERIES", "4"))
    MAX_RESULTS_PER_QUERY: int = int(os.getenv("MAX_RESULTS_PER_QUERY", "3"))

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    def __init__(self):
        # Ensure output directory exists
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def is_live_llm_available(self) -> bool:
        """Check if live LLM credentials are configured."""
        if self.LLM_PROVIDER == "mock":
            return False
        if self.LLM_PROVIDER in ("openai", "groq") and bool(self.OPENAI_API_KEY):
            return True
        if self.LLM_PROVIDER == "ollama":
            return True
        return False


# Singleton settings instance
settings = Settings()
