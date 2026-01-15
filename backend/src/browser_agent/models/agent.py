"""Agent-related Pydantic models."""

from datetime import datetime
from enum import Enum
from typing import Optional
from urllib.parse import urlparse

from pydantic import BaseModel, Field, HttpUrl, field_validator


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    GEMINI = "gemini"
    PERPLEXITY = "perplexity"
    HUGGINGFACE = "hf"


class Framework(str, Enum):
    """Supported automation frameworks."""

    PLAYWRIGHT = "playwright"


class Language(str, Enum):
    """Supported output languages."""

    TYPESCRIPT = "typescript"
    PYTHON = "python"
    JAVASCRIPT = "javascript"


class AgentRequest(BaseModel):
    """Request model for the /api/agent endpoint.
    
    API key can be provided via:
    1. X-API-Key header (recommended, most secure)
    2. apiKey field in body (backwards compatible)
    3. Environment variable (server default)
    """

    api_key: Optional[str] = Field(
        default=None,
        alias="apiKey",
        description="API key for the LLM provider (prefer X-API-Key header instead)",
        min_length=1,
    )
    provider: LLMProvider = Field(
        ...,
        description="LLM provider to use for agent orchestration",
    )
    url: str = Field(
        ...,
        description="Target URL for browser automation (must be http:// or https://)",
    )
    task: str = Field(
        ...,
        description="Natural language description of the task to perform",
        min_length=1,
    )
    
    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate that URL has proper scheme and netloc."""
        try:
            parsed = urlparse(v)
            if parsed.scheme not in ("http", "https"):
                raise ValueError("URL must start with http:// or https://")
            if not parsed.netloc:
                raise ValueError("URL must have a valid domain")
            return v
        except Exception as e:
            raise ValueError(f"Invalid URL: {e}")
    
    framework: Framework = Field(
        default=Framework.PLAYWRIGHT,
        description="Automation framework to use",
    )
    language: Language = Field(
        default=Language.TYPESCRIPT,
        description="Output language for generated code",
    )
    headless: bool = Field(
        default=True,
        description="Run browser in headless mode (set to false to see the browser)",
    )
    use_boost_prompt: bool = Field(
        default=True,
        alias="useBoostPrompt",
        description="Enhance task with LLM before execution. Set to false for simpler, more consistent behavior.",
    )
    use_structured_execution: bool = Field(
        default=False,
        alias="useStructuredExecution",
        description="Break down complex tasks into explicit steps for more consistent execution.",
    )
    verify_each_step: bool = Field(
        default=True,
        alias="verifyEachStep",
        description="Verify each step completes before moving to next (only used with structured execution).",
    )

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "examples": [
                {
                    "apiKey": "your-api-key",
                    "provider": "gemini",
                    "url": "https://example.com",
                    "task": "Click the login button and fill in credentials",
                    "framework": "playwright",
                    "language": "typescript",
                }
            ]
        },
    }


class EventType(str, Enum):
    """Types of events streamed from the agent."""

    LOG = "log"
    SCREENSHOT = "screenshot"
    CODE = "code"
    ERROR = "error"
    COMPLETE = "complete"


class AgentEvent(BaseModel):
    """Event model for SSE streaming from the agent."""

    type: EventType = Field(
        ...,
        description="Type of the event",
    )
    message: Optional[str] = Field(
        default=None,
        description="Message content for log or error events",
    )
    screenshot: Optional[str] = Field(
        default=None,
        description="Base64-encoded screenshot data",
    )
    code: Optional[str] = Field(
        default=None,
        description="Generated code content",
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="ISO8601 timestamp of the event",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "type": "log",
                    "message": "Navigating to https://example.com",
                    "timestamp": "2026-01-15T10:30:00Z",
                },
                {
                    "type": "screenshot",
                    "screenshot": "base64-encoded-data...",
                    "timestamp": "2026-01-15T10:30:01Z",
                },
            ]
        }
    }
