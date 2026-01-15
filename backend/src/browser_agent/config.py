"""Application configuration using pydantic-settings."""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Server settings
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    debug: bool = Field(default=False, description="Enable debug mode")

    # CORS settings
    cors_origins: list[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000"],
        description="Allowed CORS origins",
    )
    cors_allow_credentials: bool = Field(default=True)
    cors_allow_methods: list[str] = Field(default=["*"])
    cors_allow_headers: list[str] = Field(default=["*"])

    # LLM API Keys (optional, can be passed per-request)
    gemini_api_key: Optional[str] = Field(default=None, description="Default Gemini API key")
    perplexity_api_key: Optional[str] = Field(
        default=None, description="Default Perplexity API key"
    )
    huggingface_api_key: Optional[str] = Field(
        default=None, description="Default HuggingFace API key"
    )

    # Timeout settings (centralized)
    llm_timeout: int = Field(default=120, description="LLM API request timeout in seconds")
    browser_timeout: int = Field(default=30000, description="Browser operation timeout in milliseconds")
    agent_timeout: int = Field(default=300, description="Total agent execution timeout in seconds")
    
    # Retry settings
    llm_retry_attempts: int = Field(default=3, description="Number of retry attempts for LLM calls")
    llm_retry_min_wait: float = Field(default=1.0, description="Minimum wait between retries in seconds")
    llm_retry_max_wait: float = Field(default=10.0, description="Maximum wait between retries in seconds")

    # Rate limiting settings
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_agent: str = Field(default="5/minute", description="Rate limit for agent endpoint (requests/period)")
    rate_limit_codegen: str = Field(default="20/minute", description="Rate limit for code generation endpoint")
    rate_limit_default: str = Field(default="60/minute", description="Default rate limit for other endpoints")

    # Agent settings
    max_steps: int = Field(default=50, description="Maximum steps per agent run")
    screenshot_quality: int = Field(default=80, description="Screenshot JPEG quality (0-100)")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
