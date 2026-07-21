from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from medical_chat.models import LLMProvider


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    server_port: int = Field(default=8000, alias="SERVER_PORT")
    llm_provider: LLMProvider = Field(default=LLMProvider.MOCK, alias="LLM_PROVIDER")
    llm_model: str = Field(default="gpt-4o-mini", alias="LLM_MODEL")
    llm_temperature: float = Field(default=0.3, alias="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(default=1024, alias="LLM_MAX_TOKENS")
    retry_delay: float = Field(default=1.0, alias="RETRY_DELAY")
    max_retries: int = Field(default=3, alias="MAX_RETRIES")
    worker_idle_timeout: float = Field(default=30.0, alias="WORKER_IDLE_TIMEOUT")
    log_file: str = Field(default="logs/interactions.log", alias="LOG_FILE")
    static_dir: str | None = Field(default=None, alias="STATIC_DIR")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    enforce_medical_only: bool = Field(default=True, alias="ENFORCE_MEDICAL_ONLY")
    rate_limit_requests: int = Field(default=20, alias="RATE_LIMIT_REQUESTS")
    rate_limit_window_seconds: float = Field(default=60.0, alias="RATE_LIMIT_WINDOW_SECONDS")

    @property
    def max_workers(self) -> int:
        import os

        return os.cpu_count() or 1


def get_settings() -> Settings:
    return Settings()
