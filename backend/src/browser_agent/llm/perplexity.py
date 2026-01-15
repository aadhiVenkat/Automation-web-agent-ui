"""Perplexity AI LLM client implementation."""

import json
import logging
import uuid
from typing import Any, AsyncGenerator, Optional

import httpx

from browser_agent.llm.base import BaseLLMClient, LLMMessage, LLMResponse, ToolCall
from browser_agent.llm.retry import with_retry

logger = logging.getLogger(__name__)


# Rough token estimation: ~4 chars per token on average
# Perplexity limit is 200k - we need to be much more conservative
MAX_INPUT_TOKENS = 80000  # More conservative limit
CHARS_PER_TOKEN = 4
MAX_TOOL_RESULT_CHARS = 15000  # ~3.75k tokens per tool result
MAX_CONTENT_CHARS = 20000  # ~5k tokens per message


def estimate_tokens(text: str) -> int:
    """Estimate token count from text length."""
    return len(text) // CHARS_PER_TOKEN


def truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Truncate text to approximately fit within token limit."""
    max_chars = max_tokens * CHARS_PER_TOKEN
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n... [truncated due to length]"


def truncate_json_structure(data: Any, max_chars: int = 10000) -> str:
    """Truncate a JSON structure intelligently."""
    text = json.dumps(data, indent=2) if not isinstance(data, str) else data
    if len(text) <= max_chars:
        return text
    # Try to keep the structure readable
    return text[:max_chars] + "\n... [structure truncated]"


class PerplexityClient(BaseLLMClient):
    """Client for Perplexity AI API.
    
    Perplexity uses an OpenAI-compatible API, making it straightforward
    to implement. Supports sonar models with online search capabilities.
    """

    BASE_URL = "https://api.perplexity.ai"
    DEFAULT_MODEL = "sonar"  # or "sonar-pro" for more powerful model

    def __init__(self, api_key: str, model: Optional[str] = None) -> None:
        """Initialize Perplexity client.
        
        Args:
            api_key: Perplexity API key.
            model: Model name (default: sonar).
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
        """Send chat completion request to Perplexity."""
        url = f"{self.BASE_URL}/chat/completions"
        
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": self._convert_messages(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        # Note: Perplexity has limited function calling support
        # We simulate tool calls through structured prompts when tools are provided
        if tools:
            # Add tool descriptions to system message
            tool_prompt = self._format_tools_prompt(tools)
            payload["messages"] = self._inject_tools_prompt(payload["messages"], tool_prompt)
        
        response = await self._client.post(url, json=payload)
        
        # Handle errors with more context
        if response.status_code == 400:
            error_body = response.json()
            error_msg = error_body.get("error", {}).get("message", "Bad request")
            raise ValueError(f"Perplexity API error: {error_msg}")
        elif response.status_code == 401:
            raise ValueError("Invalid Perplexity API key. Please provide a valid key from https://www.perplexity.ai/settings/api")
        elif response.status_code == 403:
            raise ValueError("Perplexity API key does not have access. Check your subscription.")
        elif response.status_code == 429:
            raise ValueError("Perplexity rate limit exceeded. Please wait and try again.")
        
        response.raise_for_status()
        
        return self._parse_response(response.json(), tools is not None)

    async def chat_stream(
        self,
        messages: list[LLMMessage],
        tools: Optional[list[dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncGenerator[str, None]:
        """Stream chat completion from Perplexity."""
        url = f"{self.BASE_URL}/chat/completions"
        
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": self._convert_messages(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        
        if tools:
            tool_prompt = self._format_tools_prompt(tools)
            payload["messages"] = self._inject_tools_prompt(payload["messages"], tool_prompt)
        
        async with self._client.stream("POST", url, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    if line.strip() == "data: [DONE]":
                        break
                    data = json.loads(line[6:])
                    if "choices" in data:
                        delta = data["choices"][0].get("delta", {})
                        if "content" in delta:
                            yield delta["content"]

    def _convert_messages(self, messages: list[LLMMessage]) -> list[dict]:
        """Convert LLMMessages to Perplexity format (OpenAI-compatible).
        
        Perplexity requires strict message alternation: user -> assistant -> user -> assistant
        We need to merge consecutive tool results and handle tool calls properly.
        Also truncates content to stay within token limits.
        """
        converted = []
        pending_tool_results = []
        
        for i, msg in enumerate(messages):
            content = msg.content or ""
            
            # Aggressively truncate large content
            if len(content) > MAX_CONTENT_CHARS:
                content = truncate_to_tokens(content, MAX_CONTENT_CHARS // CHARS_PER_TOKEN)
            
            if msg.role == "system":
                converted.append({
                    "role": "system",
                    "content": content,
                })
            elif msg.role == "tool":
                # Collect tool results to merge later - truncate large results
                tool_content = msg.content or ""
                if len(tool_content) > MAX_TOOL_RESULT_CHARS:
                    tool_content = truncate_to_tokens(tool_content, MAX_TOOL_RESULT_CHARS // CHARS_PER_TOKEN)
                pending_tool_results.append(f"Tool '{msg.name}': {tool_content}")
            elif msg.role == "assistant":
                # First, flush any pending tool results as a user message
                if pending_tool_results:
                    converted.append({
                        "role": "user",
                        "content": "\n\n".join(pending_tool_results),
                    })
                    pending_tool_results = []
                
                # Add assistant message
                if msg.tool_calls:
                    tool_text = content
                    if tool_text:
                        tool_text += "\n\n"
                    tool_text += "Using tools:\n"
                    for tc in msg.tool_calls:
                        tool_text += f"TOOL_CALL: {tc.name}\nARGUMENTS: {json.dumps(tc.arguments)}\n"
                    converted.append({
                        "role": "assistant",
                        "content": tool_text,
                    })
                else:
                    converted.append({
                        "role": "assistant",
                        "content": content,
                    })
            elif msg.role == "user":
                # First, flush any pending tool results
                if pending_tool_results:
                    # Merge with user message
                    merged = "\n\n".join(pending_tool_results) + "\n\n" + content
                    converted.append({
                        "role": "user",
                        "content": merged,
                    })
                    pending_tool_results = []
                else:
                    converted.append({
                        "role": "user",
                        "content": content,
                    })
        
        # Flush any remaining tool results
        if pending_tool_results:
            converted.append({
                "role": "user",
                "content": "\n\n".join(pending_tool_results),
            })
        
        # Ensure proper alternation - merge consecutive same-role messages
        final = []
        for msg in converted:
            if final and final[-1]["role"] == msg["role"] and msg["role"] != "system":
                # Merge with previous
                final[-1]["content"] += "\n\n" + msg["content"]
            else:
                final.append(msg)
        
        # CRITICAL: Perplexity requires conversation to end with user message
        # and strict alternation. Do a final validation pass.
        final = self._enforce_alternation(final)
        
        # Final check: truncate total context if still too large
        total_chars = sum(len(m["content"]) for m in final)
        if total_chars > MAX_INPUT_TOKENS * CHARS_PER_TOKEN:
            # Keep system message, truncate from older messages
            final = self._truncate_conversation(final, MAX_INPUT_TOKENS)
        
        return final

    def _enforce_alternation(self, messages: list[dict]) -> list[dict]:
        """Enforce strict user/assistant alternation for Perplexity API.
        
        Rules:
        1. System messages come first (optional)
        2. After system, must alternate user -> assistant -> user -> ...
        3. Conversation must end with user message
        """
        if not messages:
            return messages
        
        # Separate system from conversation
        system_msgs = [m for m in messages if m["role"] == "system"]
        conv_msgs = [m for m in messages if m["role"] != "system"]
        
        if not conv_msgs:
            return system_msgs
        
        # Build properly alternating conversation
        result = []
        expected_role = "user"  # Must start with user after system
        
        for msg in conv_msgs:
            if msg["role"] == expected_role:
                result.append(msg)
                expected_role = "assistant" if expected_role == "user" else "user"
            else:
                # Wrong role - merge with previous or create placeholder
                if result and result[-1]["role"] == msg["role"]:
                    # Same role as previous, merge
                    result[-1]["content"] += "\n\n" + msg["content"]
                elif not result:
                    # First message but wrong role - if assistant, add dummy user
                    if msg["role"] == "assistant":
                        result.append({"role": "user", "content": "Continue with the task."})
                        result.append(msg)
                        expected_role = "user"
                else:
                    # Need to insert placeholder to maintain alternation
                    if expected_role == "user" and msg["role"] == "assistant":
                        result.append({"role": "user", "content": "Acknowledged. Continue."})
                    elif expected_role == "assistant" and msg["role"] == "user":
                        result.append({"role": "assistant", "content": "Understood."})
                    result.append(msg)
                    expected_role = "assistant" if msg["role"] == "user" else "user"
        
        # Ensure ends with user message (LLM needs to respond)
        if result and result[-1]["role"] == "assistant":
            result.append({"role": "user", "content": "Please continue with the next action."})
        
        return system_msgs + result

    def _truncate_conversation(self, messages: list[dict], max_tokens: int) -> list[dict]:
        """Truncate conversation history to fit within token limit.
        
        Keeps system message and most recent messages, removes older ones.
        """
        if not messages:
            return messages
        
        # Separate system messages from conversation
        system_msgs = [m for m in messages if m["role"] == "system"]
        conv_msgs = [m for m in messages if m["role"] != "system"]
        
        # Calculate tokens used by system messages
        system_tokens = sum(estimate_tokens(m["content"]) for m in system_msgs)
        available_tokens = max_tokens - system_tokens - 5000  # Leave buffer
        
        # Keep messages from the end until we hit the limit
        kept_msgs = []
        current_tokens = 0
        
        for msg in reversed(conv_msgs):
            msg_tokens = estimate_tokens(msg["content"])
            if current_tokens + msg_tokens <= available_tokens:
                kept_msgs.insert(0, msg)
                current_tokens += msg_tokens
            else:
                # Truncate this message if it's very large
                if msg_tokens > 10000 and len(kept_msgs) == 0:
                    # Must keep at least one message
                    truncated = truncate_to_tokens(msg["content"], available_tokens - 1000)
                    kept_msgs.insert(0, {"role": msg["role"], "content": truncated})
                break
        
        return system_msgs + kept_msgs

    def _format_tools_prompt(self, tools: list[dict]) -> str:
        """Format tools as a text prompt for the model."""
        lines = [
            "## TOOL CALLING FORMAT (CRITICAL - FOLLOW EXACTLY)",
            "",
            "When you need to use a tool, you MUST respond with EXACTLY this format:",
            "```",
            "TOOL_CALL: <tool_name>",
            "ARGUMENTS: {\"param\": \"value\"}",
            "```",
            "",
            "IMPORTANT RULES:",
            "- Use TOOL_CALL: (not <function_calls> or any XML)",
            "- Put tool name directly after TOOL_CALL: (e.g., TOOL_CALL: click)",
            "- Put JSON arguments on the ARGUMENTS: line",
            "- JSON must use double quotes for strings: {\"selector\": \"button\"} NOT {'selector': 'button'}",
            "- Only ONE tool call per response - wait for result before next action",
            "- NEVER say TASK_COMPLETE until the ENTIRE task goal is achieved",
            "- Only say TASK_COMPLETE when you have VERIFIED the final result",
            "",
            "## AVAILABLE TOOLS:",
        ]
        
        for tool in tools:
            if tool.get("type") == "function":
                func = tool["function"]
            else:
                func = tool
            
            lines.append(f"\n### {func['name']}")
            lines.append(f"Description: {func.get('description', '')}")
            if "parameters" in func:
                params = func["parameters"].get("properties", {})
                required = func["parameters"].get("required", [])
                lines.append("Parameters:")
                for name, info in params.items():
                    req = " (required)" if name in required else ""
                    lines.append(f"  - {name}{req}: {info.get('description', info.get('type', 'any'))}")
        
        lines.append("\n## EXAMPLE TOOL CALLS:")
        lines.append("To fill a search box: TOOL_CALL: fill")
        lines.append('ARGUMENTS: {"selector": "input[type=search]", "value": "search query"}')
        lines.append("")
        lines.append("To click a button: TOOL_CALL: click")
        lines.append('ARGUMENTS: {"selector": "button[type=submit]"}')
        lines.append("")
        lines.append("Execute ONE action at a time. Wait for results before proceeding.")
        return "\n".join(lines)

    def _inject_tools_prompt(self, messages: list[dict], tool_prompt: str) -> list[dict]:
        """Inject tools prompt into the system message."""
        result = []
        system_found = False
        
        for msg in messages:
            if msg["role"] == "system":
                result.append({
                    "role": "system",
                    "content": f"{msg['content']}\n\n{tool_prompt}",
                })
                system_found = True
            else:
                result.append(msg)
        
        if not system_found:
            result.insert(0, {"role": "system", "content": tool_prompt})
        
        return result

    def _parse_response(self, data: dict, has_tools: bool) -> LLMResponse:
        """Parse Perplexity API response."""
        choices = data.get("choices", [])
        if not choices:
            return LLMResponse(
                content=None,
                tool_calls=None,
                finish_reason="error",
            )
        
        choice = choices[0]
        message = choice.get("message", {})
        content = message.get("content", "")
        
        tool_calls = None
        # Check for tool calls in various formats - be more permissive
        if has_tools and content:
            # Look for any indication of tool usage
            content_upper = content.upper()
            has_tool_indicator = (
                "TOOL_CALL:" in content_upper or
                "TOOL_CALL :" in content_upper or  # Handle space before colon
                "<INVOKE" in content_upper or
                "FUNCTION_CALL" in content_upper or
                "ARGUMENTS:" in content_upper or
                # Also check for common tool names directly
                any(tool_name in content.lower() for tool_name in 
                    ["click", "fill", "navigate", "scroll", "get_page"])
            )
            if has_tool_indicator:
                tool_calls = self._extract_tool_calls(content)
        
        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason="tool_calls" if tool_calls else choice.get("finish_reason", "stop"),
            usage=data.get("usage"),
        )

    def _extract_json_object(self, text: str, start_pos: int = 0) -> Optional[tuple[dict, int]]:
        """Extract a complete JSON object from text, handling nested braces.
        
        Args:
            text: The text to search in.
            start_pos: Position to start searching from.
            
        Returns:
            Tuple of (parsed dict, end position) or None if not found.
        """
        # Find the first opening brace
        brace_start = text.find('{', start_pos)
        if brace_start == -1:
            return None
        
        # Track nested braces to find matching close
        depth = 0
        in_string = False
        escape_next = False
        
        for i, char in enumerate(text[brace_start:], start=brace_start):
            if escape_next:
                escape_next = False
                continue
            
            if char == '\\' and in_string:
                escape_next = True
                continue
            
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            
            if in_string:
                continue
            
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    # Found matching brace
                    json_str = text[brace_start:i + 1]
                    try:
                        return (json.loads(json_str), i + 1)
                    except json.JSONDecodeError:
                        # Try to fix common issues
                        return self._try_fix_json(json_str, i + 1)
        
        return None

    def _try_fix_json(self, json_str: str, end_pos: int) -> Optional[tuple[dict, int]]:
        """Try to fix common JSON issues.
        
        Args:
            json_str: The malformed JSON string.
            end_pos: The end position in original text.
            
        Returns:
            Tuple of (parsed dict, end position) or None.
        """
        import re
        
        # Try common fixes
        fixes = [
            # Fix unquoted string values
            (r':\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*([,}])', r': "\1"\2'),
            # Fix single quotes
            (r"'([^']*)'", r'"\1"'),
            # Fix trailing commas
            (r',\s*}', r'}'),
            (r',\s*]', r']'),
        ]
        
        fixed = json_str
        for pattern, replacement in fixes:
            fixed = re.sub(pattern, replacement, fixed)
        
        try:
            return (json.loads(fixed), end_pos)
        except json.JSONDecodeError:
            return None

    def _extract_tool_calls(self, content: str) -> Optional[list[ToolCall]]:
        """Extract tool calls from response text.
        
        Supports multiple formats with robust parsing:
        1. TOOL_CALL: name / ARGUMENTS: {} (preferred)
        2. XML-style <invoke name="..."> (fallback)
        3. Inline format without newlines
        4. Various malformed JSON handling
        """
        import re
        tool_calls = []
        
        # Strategy 1: Find TOOL_CALL patterns and extract JSON properly
        tool_name_pattern = r'TOOL_CALL:\s*(\w+)'
        
        for match in re.finditer(tool_name_pattern, content, re.IGNORECASE):
            tool_name = match.group(1)
            search_start = match.end()
            arguments = {}
            
            # Look for ARGUMENTS: or just a JSON object after the tool name
            remaining = content[search_start:search_start + 500]  # Limit search area
            
            # Check for ARGUMENTS: prefix
            args_match = re.search(r'ARGUMENTS:\s*', remaining, re.IGNORECASE)
            if args_match:
                json_start = search_start + args_match.end()
            else:
                # Look for direct JSON object
                json_start = search_start
            
            # Extract JSON object with proper brace matching
            json_result = self._extract_json_object(content, json_start)
            if json_result:
                arguments = json_result[0]
            else:
                logger.warning("Failed to extract JSON arguments for tool %s", tool_name)
            
            if tool_name:
                logger.debug("Extracted tool call: %s with args: %s", tool_name, arguments)
                tool_calls.append(ToolCall(
                    id=str(uuid.uuid4()),
                    name=tool_name,
                    arguments=arguments,
                ))
        
        # Deduplicate tool calls (same tool+args)
        seen = set()
        unique_calls = []
        for tc in tool_calls:
            key = f"{tc.name}:{json.dumps(tc.arguments, sort_keys=True)}"
            if key not in seen:
                seen.add(key)
                unique_calls.append(tc)
        tool_calls = unique_calls
        
        # Strategy 2: XML-style parsing if no TOOL_CALL found
        if not tool_calls:
            # Match <invoke name="tool_name"> or <function_call name="...">
            invoke_pattern = r'<(?:invoke|function_call|tool)\s+name=["\']([^"\']+)["\']>'
            param_pattern = r'<(?:parameter|param|arg)\s+name=["\']([^"\']+)["\']>([^<]*)</(?:parameter|param|arg)>'
            
            for invoke_match in re.finditer(invoke_pattern, content, re.IGNORECASE):
                tool_name = invoke_match.group(1)
                start_pos = invoke_match.end()
                
                # Find closing tag
                end_match = re.search(r'</(?:invoke|function_call|tool)>', content[start_pos:], re.IGNORECASE)
                end_pos = start_pos + end_match.start() if end_match else len(content)
                
                invoke_content = content[start_pos:end_pos]
                arguments = {}
                
                # Try to find JSON object first
                json_result = self._extract_json_object(invoke_content, 0)
                if json_result:
                    arguments = json_result[0]
                else:
                    # Fall back to XML parameter extraction
                    for param_match in re.finditer(param_pattern, invoke_content, re.IGNORECASE):
                        param_name = param_match.group(1)
                        param_value = param_match.group(2).strip()
                        try:
                            arguments[param_name] = json.loads(param_value)
                        except json.JSONDecodeError:
                            arguments[param_name] = param_value
                
                tool_calls.append(ToolCall(
                    id=str(uuid.uuid4()),
                    name=tool_name,
                    arguments=arguments,
                ))
        
        # Strategy 3: Look for function-call style patterns
        if not tool_calls:
            # Match patterns like: function_name({"key": "value"}) or tool.function_name({...})
            func_pattern = r'(?:^|\s)(\w+)\s*\(\s*(\{[^)]+\})\s*\)'
            
            for match in re.finditer(func_pattern, content):
                func_name = match.group(1)
                # Skip common false positives
                if func_name.lower() in ('if', 'for', 'while', 'function', 'def', 'class'):
                    continue
                
                json_str = match.group(2)
                try:
                    arguments = json.loads(json_str)
                    tool_calls.append(ToolCall(
                        id=str(uuid.uuid4()),
                        name=func_name,
                        arguments=arguments,
                    ))
                except json.JSONDecodeError:
                    pass
        
        return tool_calls if tool_calls else None

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
