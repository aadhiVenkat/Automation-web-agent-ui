"""Hugging Face Inference API client implementation."""

import json
import uuid
from typing import Any, AsyncGenerator, Optional

import httpx

from browser_agent.llm.base import BaseLLMClient, LLMMessage, LLMResponse, ToolCall
from browser_agent.llm.retry import with_retry


class HuggingFaceClient(BaseLLMClient):
    """Client for Hugging Face Inference API.
    
    Supports both the Inference API and Inference Endpoints.
    Uses instruction-following models like Mistral, Llama, etc.
    """

    BASE_URL = "https://api-inference.huggingface.co/models"
    DEFAULT_MODEL = "mistralai/Mistral-7B-Instruct-v0.3"

    def __init__(self, api_key: str, model: Optional[str] = None) -> None:
        """Initialize HuggingFace client.
        
        Args:
            api_key: Hugging Face API token.
            model: Model name (default: Mistral-7B-Instruct).
        """
        super().__init__(api_key, model or self.DEFAULT_MODEL)
        self._client = httpx.AsyncClient(
            timeout=120.0,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )

    @with_retry(max_attempts=3, min_wait=1, max_wait=10)
    async def chat(
        self,
        messages: list[LLMMessage],
        tools: Optional[list[dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Send chat completion request to HuggingFace."""
        url = f"{self.BASE_URL}/{self.model}"
        
        # Format messages as a single prompt
        prompt = self._format_prompt(messages, tools)
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "temperature": temperature,
                "max_new_tokens": max_tokens,
                "return_full_text": False,
                "do_sample": temperature > 0,
            },
        }
        
        response = await self._client.post(url, json=payload)
        
        # Handle errors with specific messages
        if response.status_code == 400:
            error_body = response.json()
            error_msg = error_body.get("error", "Bad request")
            raise ValueError(f"HuggingFace API error: {error_msg}")
        elif response.status_code == 401:
            raise ValueError("Invalid HuggingFace API token. Get one at https://huggingface.co/settings/tokens")
        elif response.status_code == 403:
            raise ValueError("Access denied. This model may require accepting terms at huggingface.co or a Pro subscription.")
        elif response.status_code == 404:
            raise ValueError(f"Model '{self.model}' not found. Check the model name or try 'mistralai/Mistral-7B-Instruct-v0.3'")
        elif response.status_code == 429:
            raise ValueError("HuggingFace rate limit exceeded. Please wait and try again.")
        elif response.status_code == 503:
            error_body = response.json()
            estimated_time = error_body.get("estimated_time", "unknown")
            raise ValueError(f"Model is loading. Estimated time: {estimated_time}s. Please retry shortly.")
        
        response.raise_for_status()
        
        return self._parse_response(response.json(), tools is not None)

    async def chat_stream(
        self,
        messages: list[LLMMessage],
        tools: Optional[list[dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncGenerator[str, None]:
        """Stream chat completion from HuggingFace."""
        url = f"{self.BASE_URL}/{self.model}"
        
        prompt = self._format_prompt(messages, tools)
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "temperature": temperature,
                "max_new_tokens": max_tokens,
                "return_full_text": False,
                "do_sample": temperature > 0,
            },
            "stream": True,
        }
        
        async with self._client.stream("POST", url, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    try:
                        data = json.loads(line[5:])
                        if "token" in data:
                            yield data["token"].get("text", "")
                    except json.JSONDecodeError:
                        continue

    def _format_prompt(self, messages: list[LLMMessage], tools: Optional[list[dict]]) -> str:
        """Format messages into a single prompt string.
        
        Uses Mistral/Llama chat format:
        <s>[INST] System prompt + User message [/INST] Assistant response</s>
        """
        parts = []
        system_content = ""
        
        # Extract system message
        for msg in messages:
            if msg.role == "system":
                system_content = msg.content or ""
                break
        
        # Add tools to system if provided
        if tools:
            tool_prompt = self._format_tools_prompt(tools)
            system_content = f"{system_content}\n\n{tool_prompt}" if system_content else tool_prompt
        
        # Build conversation
        for i, msg in enumerate(messages):
            if msg.role == "system":
                continue
            
            if msg.role == "user":
                content = msg.content or ""
                if i == 0 or (i == 1 and messages[0].role == "system"):
                    # First user message includes system
                    if system_content:
                        parts.append(f"<s>[INST] {system_content}\n\n{content} [/INST]")
                    else:
                        parts.append(f"<s>[INST] {content} [/INST]")
                else:
                    parts.append(f"[INST] {content} [/INST]")
            
            elif msg.role == "assistant":
                if msg.tool_calls:
                    tool_text = ""
                    for tc in msg.tool_calls:
                        tool_text += f"\nTOOL_CALL: {tc.name}\nARGUMENTS: {json.dumps(tc.arguments)}"
                    parts.append(f"{msg.content or ''}{tool_text}</s>")
                else:
                    parts.append(f"{msg.content or ''}</s>")
            
            elif msg.role == "tool":
                parts.append(f"[INST] Tool '{msg.name}' returned: {msg.content} [/INST]")
        
        return "".join(parts)

    def _format_tools_prompt(self, tools: list[dict]) -> str:
        """Format tools as instructions for the model."""
        lines = [
            "You have access to browser automation tools. To use a tool, respond with:",
            "TOOL_CALL: tool_name",
            "ARGUMENTS: {\"param\": \"value\"}",
            "",
            "Available tools:",
        ]
        
        for tool in tools:
            if tool.get("type") == "function":
                func = tool["function"]
            else:
                func = tool
            
            lines.append(f"\n- {func['name']}: {func.get('description', '')}")
            if "parameters" in func:
                required = func["parameters"].get("required", [])
                params = func["parameters"].get("properties", {})
                for name, info in params.items():
                    req = " (required)" if name in required else ""
                    lines.append(f"  - {name}{req}: {info.get('description', info.get('type', 'any'))}")
        
        lines.append("\nAnalyze the task, then use TOOL_CALL to perform actions.")
        return "\n".join(lines)

    def _parse_response(self, data: Any, has_tools: bool) -> LLMResponse:
        """Parse HuggingFace API response."""
        if isinstance(data, list):
            data = data[0] if data else {}
        
        content = data.get("generated_text", "")
        
        tool_calls = None
        if has_tools and "TOOL_CALL:" in content:
            tool_calls = self._extract_tool_calls(content)
        
        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason="tool_calls" if tool_calls else "stop",
        )

    def _extract_tool_calls(self, content: str) -> Optional[list[ToolCall]]:
        """Extract tool calls from response text."""
        import re
        tool_calls = []
        
        # Pattern to match TOOL_CALL with flexible whitespace
        tool_pattern = r'TOOL_CALL:\s*(\w+)'
        args_pattern = r'ARGUMENTS:\s*(\{[^}]+\})'
        
        for match in re.finditer(tool_pattern, content, re.IGNORECASE):
            tool_name = match.group(1)
            arguments = {}
            
            # Look for arguments after this match
            remaining = content[match.end():match.end() + 500]
            args_match = re.search(args_pattern, remaining, re.IGNORECASE)
            
            if args_match:
                try:
                    arguments = json.loads(args_match.group(1))
                except json.JSONDecodeError:
                    # Try fixing common JSON issues
                    try:
                        fixed = args_match.group(1).replace("'", '"')
                        arguments = json.loads(fixed)
                    except json.JSONDecodeError:
                        pass
            
            tool_calls.append(ToolCall(
                id=str(uuid.uuid4()),
                name=tool_name,
                arguments=arguments,
            ))
        
        return tool_calls if tool_calls else None

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
