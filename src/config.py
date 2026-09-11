"""Configuration module for the Multi-Agent Research Assistant (Layer 1).

Establishes the environment configuration foundation for Layer 2:
- LLM Provider: Groq (via GROQ_API_KEY)
- Web Search Provider: Tavily (via TAVILY_API_KEY)
"""

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
    """Application and provider configuration settings."""

    # Project directories
    PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
    OUTPUT_DIR: Path = PROJECT_ROOT / os.getenv("OUTPUT_DIR", "reports")

    # Layer 2 Intended Providers: Groq & Tavily
    GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    TAVILY_API_KEY: Optional[str] = os.getenv("TAVILY_API_KEY")

    # Bounded execution limits for cost-effective hackathon MVP
    MAX_SEARCH_QUERIES: int = int(os.getenv("MAX_SEARCH_QUERIES", "3"))
    MAX_RESULTS_PER_QUERY: int = int(os.getenv("MAX_RESULTS_PER_QUERY", "3"))

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    def __init__(self):
        # Ensure output directory exists
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    @property
    def has_groq_credentials(self) -> bool:
        """Check if Groq API key is present in environment."""
        return bool(self.GROQ_API_KEY and self.GROQ_API_KEY.strip())

    @property
    def has_tavily_credentials(self) -> bool:
        """Check if Tavily API key is present in environment."""
        return bool(self.TAVILY_API_KEY and self.TAVILY_API_KEY.strip())


# Singleton settings instance
settings = Settings()
