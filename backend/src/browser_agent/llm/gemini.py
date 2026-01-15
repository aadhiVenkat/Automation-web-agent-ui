"""Google Gemini LLM client implementation."""

import json
import uuid
from typing import Any, AsyncGenerator, Optional

import httpx

from browser_agent.llm.base import BaseLLMClient, LLMMessage, LLMResponse, ToolCall
from browser_agent.llm.retry import with_retry


class GeminiClient(BaseLLMClient):
    """Client for Google Gemini API with function calling support.
    
    Uses the Gemini API to generate responses and handle tool calls.
    Supports gemini-1.5-flash, gemini-1.5-pro, and gemini-2.0-flash models.
    """

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
    DEFAULT_MODEL = "gemini-2.0-flash"

    def __init__(self, api_key: str, model: Optional[str] = None) -> None:
        """Initialize Gemini client.
        
        Args:
            api_key: Google AI API key.
            model: Model name (default: gemini-2.0-flash).
        """
        super().__init__(api_key, model or self.DEFAULT_MODEL)
        self._client = httpx.AsyncClient(timeout=120.0)

    @with_retry(max_attempts=3, min_wait=1, max_wait=10)
    async def chat(
        self,
        messages: list[LLMMessage],
        tools: Optional[list[dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Send chat completion request to Gemini."""
        url = f"{self.BASE_URL}/models/{self.model}:generateContent"
        
        # Extract system instruction and convert messages
        system_instruction = self._extract_system_instruction(messages)
        contents = self._convert_messages(messages)
        
        # Build generation config
        gen_config: dict[str, Any] = {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        }
        # Add seed for reproducibility when temperature is very low
        if temperature < 0.1:
            gen_config["seed"] = 42
        
        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": gen_config,
        }
        
        # Add system instruction using the proper Gemini field
        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }
        
        # Add tools if provided
        if tools:
            payload["tools"] = [{"functionDeclarations": self._convert_tools(tools)}]
            payload["toolConfig"] = {
                "functionCallingConfig": {"mode": "AUTO"}
            }
        
        response = await self._client.post(
            url,
            json=payload,
            params={"key": self.api_key},
        )
        
        # Handle errors with more context
        if response.status_code == 400:
            error_body = response.json()
            error_msg = error_body.get("error", {}).get("message", "Bad request")
            raise ValueError(f"Gemini API error: {error_msg}. Please check your API key is valid.")
        elif response.status_code == 401:
            raise ValueError("Invalid Gemini API key. Please provide a valid key from https://aistudio.google.com/apikey")
        elif response.status_code == 403:
            raise ValueError("API key does not have access to this model. Check your API key permissions.")
        
        response.raise_for_status()
        
        return self._parse_response(response.json())

    async def chat_stream(
        self,
        messages: list[LLMMessage],
        tools: Optional[list[dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncGenerator[str, None]:
        """Stream chat completion from Gemini."""
        url = f"{self.BASE_URL}/models/{self.model}:streamGenerateContent"
        
        contents = self._convert_messages(messages)
        
        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        
        if tools:
            payload["tools"] = [{"functionDeclarations": self._convert_tools(tools)}]
        
        async with self._client.stream(
            "POST",
            url,
            json=payload,
            params={"key": self.api_key, "alt": "sse"},
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    if "candidates" in data:
                        for candidate in data["candidates"]:
                            if "content" in candidate:
                                for part in candidate["content"].get("parts", []):
                                    if "text" in part:
                                        yield part["text"]

    def _extract_system_instruction(self, messages: list[LLMMessage]) -> Optional[str]:
        """Extract system instruction from messages.
        
        Args:
            messages: List of conversation messages.
            
        Returns:
            System instruction content or None.
        """
        for msg in messages:
            if msg.role == "system":
                return msg.content
        return None

    def _convert_messages(self, messages: list[LLMMessage]) -> list[dict]:
        """Convert LLMMessages to Gemini format.
        
        Note: System messages are handled separately via systemInstruction field.
        """
        contents = []
        
        for msg in messages:
            # Skip system messages - handled via systemInstruction
            if msg.role == "system":
                continue
            
            if msg.role == "assistant":
                parts = []
                if msg.content:
                    parts.append({"text": msg.content})
                if msg.tool_calls:
                    for tc in msg.tool_calls:
                        parts.append({
                            "functionCall": {
                                "name": tc.name,
                                "args": tc.arguments,
                            }
                        })
                contents.append({"role": "model", "parts": parts})
            
            elif msg.role == "tool":
                # Safely parse tool response content
                try:
                    response_data = json.loads(msg.content) if msg.content else {}
                except json.JSONDecodeError:
                    # If not JSON, wrap the content as a result
                    response_data = {"result": msg.content} if msg.content else {}
                
                contents.append({
                    "role": "function",
                    "parts": [{
                        "functionResponse": {
                            "name": msg.name,
                            "response": response_data,
                        }
                    }]
                })
            
            elif msg.role == "user":
                contents.append({
                    "role": "user",
                    "parts": [{"text": msg.content or ""}]
                })
        
        return contents

    def _convert_tools(self, tools: list[dict]) -> list[dict]:
        """Convert OpenAI-style tool schemas to Gemini format."""
        gemini_tools = []
        
        for tool in tools:
            if tool.get("type") == "function":
                func = tool["function"]
            else:
                func = tool
            
            gemini_tool = {
                "name": func["name"],
                "description": func.get("description", ""),
            }
            
            if "parameters" in func:
                # Convert JSON Schema to Gemini format
                params = func["parameters"]
                gemini_tool["parameters"] = {
                    "type": "object",
                    "properties": params.get("properties", {}),
                    "required": params.get("required", []),
                }
            
            gemini_tools.append(gemini_tool)
        
        return gemini_tools

    def _parse_response(self, data: dict) -> LLMResponse:
        """Parse Gemini API response."""
        candidates = data.get("candidates", [])
        if not candidates:
            return LLMResponse(
                content=None,
                tool_calls=None,
                finish_reason="error",
            )
        
        candidate = candidates[0]
        content = candidate.get("content", {})
        parts = content.get("parts", [])
        
        text_content = None
        tool_calls = []
        
        for part in parts:
            if "text" in part:
                text_content = (text_content or "") + part["text"]
            elif "functionCall" in part:
                fc = part["functionCall"]
                tool_calls.append(ToolCall(
                    id=str(uuid.uuid4()),
                    name=fc["name"],
                    arguments=fc.get("args", {}),
                ))
        
        finish_reason = candidate.get("finishReason", "STOP")
        if finish_reason == "STOP":
            finish_reason = "tool_calls" if tool_calls else "stop"
        
        return LLMResponse(
            content=text_content,
            tool_calls=tool_calls if tool_calls else None,
            finish_reason=finish_reason,
            usage=data.get("usageMetadata"),
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
