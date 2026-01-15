"""LLM client factory and initialization."""

from typing import Optional

from browser_agent.llm.base import BaseLLMClient, ImageData, LLMMessage, LLMResponse, ToolCall
from browser_agent.llm.gemini import GeminiClient
from browser_agent.llm.huggingface import HuggingFaceClient
from browser_agent.llm.perplexity import PerplexityClient


def create_llm_client(
    provider: str,
    api_key: str,
    model: Optional[str] = None,
) -> BaseLLMClient:
    """Create an LLM client for the specified provider.
    
    Args:
        provider: Provider name ('gemini', 'perplexity', 'hf').
        api_key: API key for the provider.
        model: Optional model name override.
        
    Returns:
        BaseLLMClient: Configured LLM client.
        
    Raises:
        ValueError: If provider is not supported.
    """
    provider = provider.lower()
    
    if provider == "gemini":
        return GeminiClient(api_key, model)
    elif provider == "perplexity":
        return PerplexityClient(api_key, model)
    elif provider in ("hf", "huggingface"):
        return HuggingFaceClient(api_key, model)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


__all__ = [
    "BaseLLMClient",
    "ImageData",
    "LLMMessage",
    "LLMResponse",
    "ToolCall",
    "GeminiClient",
    "PerplexityClient",
    "HuggingFaceClient",
    "create_llm_client",
]
