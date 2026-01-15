"""Base LLM client interface for agent orchestration."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Optional


@dataclass
class ToolCall:
    """Represents a tool call from the LLM."""
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ImageData:
    """Represents an image for vision-enabled LLMs."""
    base64_data: str  # Base64-encoded image data
    mime_type: str = "image/jpeg"  # MIME type (image/jpeg, image/png, etc.)


@dataclass
class LLMMessage:
    """A message in the conversation."""
    role: str  # 'system', 'user', 'assistant', 'tool'
    content: Optional[str] = None
    tool_calls: Optional[list[ToolCall]] = None
    tool_call_id: Optional[str] = None  # For tool response messages
    name: Optional[str] = None  # Tool name for tool responses
    images: Optional[list[ImageData]] = None  # Images for vision models


@dataclass
class LLMResponse:
    """Response from the LLM."""
    content: Optional[str]
    tool_calls: Optional[list[ToolCall]]
    finish_reason: str  # 'stop', 'tool_calls', 'length', 'error'
    usage: Optional[dict] = None


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients.
    
    All LLM providers (Gemini, Perplexity, HuggingFace) must implement
    this interface to work with the agent.
    """

    def __init__(self, api_key: str, model: Optional[str] = None) -> None:
        """Initialize the LLM client.
        
        Args:
            api_key: API key for the provider.
            model: Model name to use.
        """
        self.api_key = api_key
        self.model = model

    @abstractmethod
    async def chat(
        self,
        messages: list[LLMMessage],
        tools: Optional[list[dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Send a chat completion request.
        
        Args:
            messages: List of conversation messages.
            tools: Optional list of tool schemas.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens in response.
            
        Returns:
            LLMResponse: The model's response.
        """
        pass

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[LLMMessage],
        tools: Optional[list[dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncGenerator[str, None]:
        """Stream a chat completion response.
        
        Args:
            messages: List of conversation messages.
            tools: Optional list of tool schemas.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens in response.
            
        Yields:
            str: Chunks of the response text.
        """
        pass

    def format_tool_result(self, tool_call_id: str, name: str, result: dict) -> LLMMessage:
        """Format a tool execution result as a message.
        
        Args:
            tool_call_id: ID of the tool call.
            name: Tool name.
            result: Tool execution result.
            
        Returns:
            LLMMessage: Formatted tool result message.
        """
        import json
        return LLMMessage(
            role="tool",
            content=json.dumps(result),
            tool_call_id=tool_call_id,
            name=name,
        )
