"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── Database ──────────────────────────────────────────────
    MYSQL_HOST: str = "mysql"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "story"
    MYSQL_PASSWORD: str = "story"
    MYSQL_DB: str = "story_agent"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}"
        )

    # ── Redis / Celery ─────────────────────────────────────────
    REDIS_URL: str = "redis://redis:6379/0"

    @property
    def CELERY_BROKER_URL(self) -> str:
        return self.REDIS_URL

    @property
    def CELERY_RESULT_BACKEND(self) -> str:
        return self.REDIS_URL

    # ── FalkorDB ───────────────────────────────────────────────
    FALKORDB_HOST: str = "falkordb"
    FALKORDB_PORT: int = 6379
    FALKORDB_GRAPH: str = "story_graph"

    # ── LLM ───────────────────────────────────────────────
    # Provider: "ollama" | "openai_compatible" | "gemini" | "openai"
    LLM_PROVIDER: str = "ollama"
    LLM_BASE_URL: str = "http://ollama:11434"  # Ollama / OpenAI-compat base URL
    LLM_MODEL: str = "llama3:8b"
    LLM_TIMEOUT: int = 600
    LLM_API_KEY_GEMINI: str = ""   # Google AI Studio API key
    LLM_API_KEY_OPENAI: str = ""   # OpenAI API key
    LLM_MAX_RETRIES: int = 3

    # ── Logging ────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/story_agent.log"

    # ── Reviewer ──────────────────────────────────────────────
    QUALITY_THRESHOLD: int = 7  # Score < this triggers rewrite

    # ── Scheduler ─────────────────────────────────────────────
    DAILY_PLAN_HOUR: int = 2
    DAILY_PLAN_MINUTE: int = 0


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
