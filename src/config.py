"""Configuration module for the Multi-Agent Research Assistant (Layer 2).

Manages environment configuration for the locked providers:
- LLM Provider: Groq (via GROQ_API_KEY)
- Web Search Provider: Tavily (via TAVILY_API_KEY)
"""

import os
from pathlib import Path
from typing import Optional

# Explicitly load .env from project root
env_path = Path(__file__).resolve().parent.parent / ".env"
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=env_path)
except ImportError:
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip().strip("\"'"))


class Settings:
    """Application and provider configuration settings."""

    # Project directories
    PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
    OUTPUT_DIR: Path = PROJECT_ROOT / os.getenv("OUTPUT_DIR", "reports")

    # Layer 2 Intended Providers: Groq & Tavily
    GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")

    TAVILY_API_KEY: Optional[str] = os.getenv("TAVILY_API_KEY")

    # Bounded execution limits for cost-effective hackathon MVP
    MAX_SEARCH_QUERIES: int = int(os.getenv("MAX_SEARCH_QUERIES", "3"))
    MAX_RESULTS_PER_QUERY: int = int(os.getenv("MAX_RESULTS_PER_QUERY", "3"))

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    def __init__(self):
        self.reload()
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def reload(self):
        """Reload configuration from environment."""
        self.GROQ_API_KEY = os.getenv("GROQ_API_KEY")
        self.GROQ_MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
        self.TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
        self.MAX_SEARCH_QUERIES = int(os.getenv("MAX_SEARCH_QUERIES", "3"))
        self.MAX_RESULTS_PER_QUERY = int(os.getenv("MAX_RESULTS_PER_QUERY", "3"))
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    @property
    def has_groq_credentials(self) -> bool:
        """Check if Groq API key is present and non-empty."""
        return bool(self.GROQ_API_KEY and self.GROQ_API_KEY.strip())

    @property
    def has_tavily_credentials(self) -> bool:
        """Check if Tavily API key is present and non-empty."""
        return bool(self.TAVILY_API_KEY and self.TAVILY_API_KEY.strip())

    def validate_groq_credentials(self) -> None:
        """Raise a descriptive error if GROQ_API_KEY is missing."""
        if not self.has_groq_credentials:
            raise ValueError(
                "Missing GROQ_API_KEY. Please set GROQ_API_KEY in your .env file "
                "or environment before executing real LLM operations."
            )

    def validate_tavily_credentials(self) -> None:
        """Raise a descriptive error if TAVILY_API_KEY is missing."""
        if not self.has_tavily_credentials:
            raise ValueError(
                "Missing TAVILY_API_KEY. Please set TAVILY_API_KEY in your .env file "
                "or environment before executing live web searches."
            )


# Singleton settings instance
settings = Settings()
