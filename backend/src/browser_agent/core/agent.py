"""Agent orchestration with LLM planning and tool execution."""

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, AsyncGenerator, Optional

from browser_agent.core.sync_browser import AsyncBrowserAdapter
from browser_agent.llm import BaseLLMClient, LLMMessage, LLMResponse, ToolCall, create_llm_client
from browser_agent.models.agent import Framework, Language
from browser_agent.models.codegen import TestStep
from browser_agent.services.codegen import CodeGenService
from browser_agent.tools import ToolExecutor, get_tools_for_openai

logger = logging.getLogger(__name__)


# Structured task decomposition prompt - more deterministic than free-form
TASK_DECOMPOSITION_PROMPT = """You are a task decomposer for browser automation. Break down the task into NUMBERED STEPS.

TASK: {task}
URL: {url}

RULES:
1. Each step must be ONE atomic action (click, fill, scroll, wait)
2. Use SPECIFIC selectors when possible (IDs, names, data attributes)
3. Include verification after critical steps
4. Number steps sequentially: 1, 2, 3...

OUTPUT FORMAT (follow EXACTLY):
STEP 1: [action] - [target/selector] - [value if needed]
STEP 2: [action] - [target/selector] - [value if needed]
...
DONE: [how to verify task is complete]

EXAMPLE:
STEP 1: fill - #search-input - "laptop"
STEP 2: click - button[type="submit"]
STEP 3: wait - .search-results
STEP 4: click - first product link
DONE: Product page is displayed with product details

Now decompose this task:"""


@dataclass
class TaskStep:
    """A single step in a decomposed task."""
    number: int
    action: str
    target: str
    value: Optional[str] = None
    completed: bool = False
    attempts: int = 0
    max_attempts: int = 3


def parse_task_steps(decomposition: str) -> tuple[list[TaskStep], str]:
    """Parse LLM task decomposition into structured steps.
    
    Returns:
        Tuple of (list of TaskStep, completion criteria)
    """
    steps = []
    done_criteria = ""
    
    lines = decomposition.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        
        # Parse STEP lines
        step_match = re.match(r'STEP\s*(\d+):\s*(.+)', line, re.IGNORECASE)
        if step_match:
            step_num = int(step_match.group(1))
            step_content = step_match.group(2)
            
            # Parse: action - target - value (optional)
            parts = [p.strip() for p in step_content.split(' - ', 2)]
            
            if len(parts) >= 2:
                action = parts[0].lower()
                target = parts[1]
                value = parts[2].strip('"\'') if len(parts) > 2 else None
                
                steps.append(TaskStep(
                    number=step_num,
                    action=action,
                    target=target,
                    value=value,
                ))
        
        # Parse DONE line
        done_match = re.match(r'DONE:\s*(.+)', line, re.IGNORECASE)
        if done_match:
            done_criteria = done_match.group(1)
    
    return steps, done_criteria


async def decompose_task(llm_client: "BaseLLMClient", task: str, url: str) -> tuple[list[TaskStep], str]:
    """Decompose a complex task into structured steps using LLM.
    
    Args:
        llm_client: LLM client for decomposition.
        task: Original user task.
        url: Target URL.
        
    Returns:
        Tuple of (list of TaskStep, completion criteria)
    """
    try:
        prompt = TASK_DECOMPOSITION_PROMPT.format(task=task, url=url)
        response = await llm_client.chat(
            [LLMMessage(role="user", content=prompt)],
            temperature=0.0,  # Deterministic decomposition
        )
        
        if response.content:
            return parse_task_steps(response.content)
        
        return [], ""
    except Exception as e:
        logger.warning("Task decomposition failed: %s", e)
        return [], ""


BOOST_PROMPT = """You are a task planner for browser automation. Given a user's task and target URL, create an ENHANCED task description that is clear, specific, and actionable.

USER TASK: {task}
TARGET URL: {url}

Analyze the task and output an ENHANCED version that includes:
1. Clear step-by-step breakdown of what needs to be done
2. Specific actions (search, click, fill, scroll, etc.)
3. What to look for at each step (buttons, inputs, links)
4. Success criteria - how to know when task is complete

Output ONLY the enhanced task description, no explanations. Keep it concise but complete.
Format: A numbered list of specific actions to take."""


async def boost_prompt_with_llm(llm_client: "BaseLLMClient", task: str, url: str) -> str:
    """Use LLM to enhance the task description for better execution.
    
    Args:
        llm_client: LLM client to use for boosting.
        task: Original user task.
        url: Target URL.
        
    Returns:
        Enhanced task description with clear steps.
    """
    try:
        prompt = BOOST_PROMPT.format(task=task, url=url)
        # Use low temperature for consistent task planning
        response = await llm_client.chat(
            [LLMMessage(role="user", content=prompt)],
            temperature=0.1,
        )
        
        if response.content:
            # Return the boosted task with original task context
            return f"""ORIGINAL TASK: {task}

ENHANCED EXECUTION PLAN:
{response.content}

Execute this plan efficiently. Start with step 1."""
        else:
            # Fallback to original task if LLM fails
            return task
    except Exception as e:
        # On any error, just use original task
        logger.warning("Boost prompt failed: %s", e, exc_info=True)
        return task


@dataclass
class AgentConfig:
    """Configuration for the agent."""
    max_steps: int = 30
    timeout: int = 300  # seconds
    screenshot_on_step: bool = True
    headless: bool = False
    viewport_width: int = 1280
    viewport_height: int = 720
    # Code generation settings
    framework: Framework = Framework.PLAYWRIGHT
    language: Language = Language.TYPESCRIPT
    # Consistency settings
    use_boost_prompt: bool = True  # Set False for simpler, more consistent behavior
    temperature: float = 0.0  # 0.0 = deterministic, higher = more random
    # Structured execution for complex tasks
    use_structured_execution: bool = True  # Decompose task into steps for consistency
    verify_each_step: bool = True  # Verify step completion before proceeding


@dataclass
class AgentStep:
    """Record of a single agent step."""
    step_number: int
    tool_name: Optional[str]
    tool_args: Optional[dict]
    tool_result: Optional[dict]
    llm_response: Optional[str]
    screenshot: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    error: Optional[str] = None


class Agent:
    """Browser automation agent with LLM-driven planning.
    
    The agent follows an iterative loop:
    1. Observe: Get current page state
    2. Think: LLM analyzes state and decides next action
    3. Act: Execute the tool/action
    4. Repeat until task is complete or max steps reached
    """

    SYSTEM_PROMPT = """You are a browser automation agent. Execute tasks step by step.

## CRITICAL RULES:
1. Execute ONE tool call at a time - never skip steps
2. Wait for each action result before proceeding
3. ALWAYS CONTINUE until the user's ACTUAL GOAL is fully achieved
4. NEVER declare completion based on partial progress
5. BE CONSISTENT: Always use the same approach for similar tasks

## SELECTOR PRIORITY (use in this order for consistency):
1. ID selectors: #login-button, #search-input
2. Name attribute: [name="email"], [name="password"]
3. Data attributes: [data-testid="submit"], [data-action="login"]
4. Specific classes: .btn-primary, .search-box
5. Text-based: click_text("Sign In") - use for buttons/links with clear text
6. Generic selectors: button, input[type="submit"] - LAST RESORT

## TASK COMPLETION - VERY IMPORTANT:
To mark a task complete, you MUST:
1. Have PERFORMED all required actions to achieve the goal
2. Have VERIFIED the final result through observation
3. On your FINAL message, write ONLY: TASK_COMPLETE

WRONG - Premature completion:
- Completing after finding/locating something when user wanted action taken
- Completing after filling a form when user wanted it submitted
- Completing after searching when user wanted to interact with results
- Mixing "TASK_COMPLETE" with explanations or analysis

RIGHT - Proper completion:
- Perform the full action chain → Verify success → Say only "TASK_COMPLETE"

## IMPORTANT: VERIFY NAVIGATION
After clicking links:
1. Use get_page_info() to check the URL changed
2. If URL is the same, navigation FAILED - try again with different method
3. Don't perform final actions until you've reached the correct page

## Tool Usage:

### Basic Interactions:
- fill(selector, value) - Fill input fields
- click(selector, force=false) - Click by CSS selector. Use force=true if blocked
- click_text(text, element_type="any") - Click by visible text (PREFERRED - more reliable)
- click_nth(selector, index) - Click Nth element when multiple match (0-indexed)
- press_key(key) - Press keyboard keys like "Enter"

### Handling Blocked Elements:
When clicks fail due to overlays/popups:
1. First try: dismiss_overlays() - Dismisses popups, modals, cookie banners
2. Then try: click_text("button text") - More reliable than CSS selectors
3. Or try: find_and_click(target) - Smart click with multiple strategies
4. Last resort: click(selector, force=true) - Force click through overlays

### Navigation & Page Analysis:
- scroll(direction, amount) - Scroll page
- scroll_to_element(selector) - Scroll element into view
- screenshot() - Capture current state
- get_page_structure() - Get interactive elements (inputs, buttons, links)
- get_page_info() - Get current URL and title - USE THIS TO VERIFY NAVIGATION

## Execution Flow:
1. Navigate/search to find target
2. Click on the target item/link
3. **VERIFY URL changed** - if not, try different click method
4. Once on correct page, perform required actions
5. VERIFY the action succeeded (check confirmation, URL, page content)
6. ONLY THEN say TASK_COMPLETE

Remember: Finding something is NOT the same as acting on it. Always verify navigation succeeded before proceeding!"""

    def __init__(
        self,
        llm_client: BaseLLMClient,
        config: Optional[AgentConfig] = None,
    ) -> None:
        """Initialize the agent.
        
        Args:
            llm_client: LLM client for planning.
            config: Agent configuration.
        """
        self.llm = llm_client
        self.config = config or AgentConfig()
        self.browser: Optional[AsyncBrowserAdapter] = None
        self.executor: Optional[ToolExecutor] = None
        self.history: list[AgentStep] = []
        self.messages: list[LLMMessage] = []
        self._stuck_count: int = 0  # Track consecutive non-actionable responses
        self._last_tool_key: Optional[str] = None  # Track repeated tool calls
        # Structured task execution
        self._task_steps: list[TaskStep] = []  # Decomposed task steps
        self._current_step_index: int = 0  # Current step being executed
        self._done_criteria: str = ""  # How to verify task completion

    def _prune_messages(self, max_messages: int = 12) -> None:
        """Prune old messages to prevent context overflow.
        
        Keeps system prompt and the most recent messages.
        """
        if len(self.messages) <= max_messages + 1:  # +1 for system prompt
            return
        
        # Keep system message (first) and last N messages
        system_msgs = [m for m in self.messages if m.role == "system"]
        other_msgs = [m for m in self.messages if m.role != "system"]
        
        # Keep only recent messages
        kept_msgs = other_msgs[-(max_messages):]
        
        self.messages = system_msgs + kept_msgs

    def _tool_matches_step(self, tool_name: str, tool_args: dict, step: TaskStep) -> bool:
        """Check if a tool execution matches a task step.
        
        Args:
            tool_name: Name of the executed tool.
            tool_args: Arguments passed to the tool.
            step: The TaskStep to match against.
            
        Returns:
            bool: True if the tool execution corresponds to the step.
        """
        action = step.action.lower()
        
        # Map step actions to tool names
        action_to_tools = {
            "click": ["click", "click_text", "click_nth", "find_and_click"],
            "fill": ["fill", "type_text"],
            "type": ["fill", "type_text"],
            "scroll": ["scroll", "scroll_to_element"],
            "wait": ["wait", "wait_for_element"],
            "navigate": ["navigate"],
            "press": ["press_key"],
            "hover": ["hover"],
            "select": ["select_option"],
            "check": ["check"],
            "uncheck": ["uncheck"],
        }
        
        valid_tools = action_to_tools.get(action, [action])
        
        if tool_name not in valid_tools:
            return False
        
        # For fill actions, check if the value matches
        if action in ["fill", "type"] and step.value:
            tool_value = tool_args.get("value", "") or tool_args.get("text", "")
            # Fuzzy match - value should be similar
            if step.value.lower() not in tool_value.lower() and tool_value.lower() not in step.value.lower():
                return False
        
        # For click_text, check text matches
        if tool_name == "click_text" and step.target:
            tool_text = tool_args.get("text", "")
            if step.target.lower() not in tool_text.lower() and tool_text.lower() not in step.target.lower():
                return False
        
        return True

    async def run(
        self,
        task: str,
        url: str,
    ) -> AsyncGenerator[dict, None]:
        """Run the agent to complete a task.
        
        Args:
            task: Natural language description of the task.
            url: Starting URL.
            
        Yields:
            dict: Events with type 'log', 'screenshot', 'tool', 'code', 'complete', 'error'.
        """
        yield {"type": "log", "message": f"Starting agent for task: {task}"}
        yield {"type": "log", "message": f"Target URL: {url}"}
        
        # Initialize browser
        self.browser = AsyncBrowserAdapter(
            headless=self.config.headless,
            viewport_width=self.config.viewport_width,
            viewport_height=self.config.viewport_height,
        )
        self.executor = ToolExecutor(self.browser)
        
        try:
            await self.browser.launch()
            yield {"type": "log", "message": "Browser launched successfully"}
            
            # Auto-navigate to the starting URL
            yield {"type": "log", "message": f"Navigating to {url}..."}
            nav_result = await self.browser.goto(url)
            yield {"type": "log", "message": f"Page loaded: {nav_result.get('title', 'Unknown')}"}
            
            # Take initial screenshot
            if self.config.screenshot_on_step:
                try:
                    ss = await self.browser.screenshot()
                    yield {"type": "screenshot", "screenshot": ss.get("screenshot")}
                except Exception:
                    pass
            
            # Structured task decomposition for complex tasks
            structured_prompt = ""
            if self.config.use_structured_execution:
                yield {"type": "log", "message": "📋 Decomposing task into structured steps..."}
                self._task_steps, self._done_criteria = await decompose_task(self.llm, task, url)
                
                if self._task_steps:
                    steps_text = "\n".join([
                        f"  STEP {s.number}: {s.action} - {s.target}" + (f" - \"{s.value}\"" if s.value else "")
                        for s in self._task_steps
                    ])
                    yield {"type": "log", "message": f"Task decomposed into {len(self._task_steps)} steps:\n{steps_text}"}
                    yield {"type": "log", "message": f"Completion criteria: {self._done_criteria}"}
                    
                    # Build structured prompt
                    structured_prompt = f"""
## STRUCTURED TASK PLAN (follow these steps IN ORDER):
{steps_text}

## COMPLETION CRITERIA:
{self._done_criteria}

IMPORTANT: Execute steps in order. After each step, verify it succeeded before moving to the next.
Current step: STEP 1
"""
                else:
                    yield {"type": "log", "message": "Could not decompose task, using standard execution"}
            
            # Optionally boost the prompt using LLM for better execution
            if self.config.use_boost_prompt and not structured_prompt:
                yield {"type": "log", "message": "Enhancing task with LLM..."}
                boosted_task = await boost_prompt_with_llm(self.llm, task, url)
                yield {"type": "boosted_prompt", "content": boosted_task}
            else:
                boosted_task = task
            
            # Combine structured prompt with task
            if structured_prompt:
                final_task = f"{task}\n{structured_prompt}"
            else:
                final_task = boosted_task
            
            # Initialize conversation
            self.messages = [
                LLMMessage(role="system", content=self.SYSTEM_PROMPT),
                LLMMessage(
                    role="user",
                    content=f"{final_task}\n\nI have already navigated to {url}. The page is loaded.\n\nStart executing the task immediately. Be efficient and follow the steps in order.",
                ),
            ]
            
            # Get tools schema
            tools = get_tools_for_openai()
            
            step_count = 0
            task_complete = False
            
            while step_count < self.config.max_steps and not task_complete:
                step_count += 1
                yield {"type": "log", "message": f"--- Step {step_count} ---"}
                
                # Get LLM response
                try:
                    response = await self.llm.chat(
                        messages=self.messages,
                        tools=tools,
                        temperature=self.config.temperature,  # Use config temperature (default 0.0 for consistency)
                    )
                except Exception as e:
                    yield {"type": "error", "message": f"LLM error: {str(e)}"}
                    break
                
                # Process response content
                if response.content:
                    yield {"type": "log", "message": f"Agent: {response.content[:500]}"}
                
                # Execute tool calls
                if response.tool_calls:
                    # Reset stuck counter when we get tool calls
                    self._stuck_count = 0
                    
                    # Deduplicate tool calls (sometimes LLM returns same tool twice)
                    seen_tools = set()
                    unique_tool_calls = []
                    for tc in response.tool_calls:
                        key = f"{tc.name}:{json.dumps(tc.arguments, sort_keys=True)}"
                        if key not in seen_tools:
                            seen_tools.add(key)
                            unique_tool_calls.append(tc)
                    
                    # Check for repeated identical tool calls (agent stuck in loop)
                    if len(unique_tool_calls) == 1:
                        current_key = f"{unique_tool_calls[0].name}:{json.dumps(unique_tool_calls[0].arguments, sort_keys=True)}"
                        if current_key == self._last_tool_key:
                            self._stuck_count += 1
                            if self._stuck_count >= 3:
                                yield {"type": "log", "message": "⚠️ Agent repeating same action - attempting recovery"}
                                self.messages.append(LLMMessage(
                                    role="user",
                                    content="You are repeating the same action. This isn't working. Try a DIFFERENT approach or use a different tool/selector.",
                                ))
                                self._stuck_count = 0
                                self._last_tool_key = None
                                continue
                        else:
                            self._stuck_count = 0
                        self._last_tool_key = current_key
                    
                    # Add assistant message with tool calls
                    self.messages.append(LLMMessage(
                        role="assistant",
                        content=response.content,
                        tool_calls=unique_tool_calls,
                    ))
                    
                    for tool_call in unique_tool_calls:
                        yield {
                            "type": "tool",
                            "tool": tool_call.name,
                            "args": tool_call.arguments,
                        }
                        yield {
                            "type": "log",
                            "message": f"Executing: {tool_call.name}({tool_call.arguments})",
                        }
                        
                        # Execute the tool
                        result = await self.executor.execute(
                            tool_call.name,
                            tool_call.arguments,
                        )
                        
                        # Record step
                        step = AgentStep(
                            step_number=step_count,
                            tool_name=tool_call.name,
                            tool_args=tool_call.arguments,
                            tool_result=result,
                            llm_response=response.content,
                        )
                        
                        if result.get("success"):
                            yield {
                                "type": "log",
                                "message": f"Result: Success - {self._summarize_result(result)}",
                            }
                            
                            # Track structured step completion
                            if self._task_steps and self._current_step_index < len(self._task_steps):
                                current_step = self._task_steps[self._current_step_index]
                                # Check if this tool matches the current step
                                if self._tool_matches_step(tool_call.name, tool_call.arguments, current_step):
                                    current_step.completed = True
                                    self._current_step_index += 1
                                    remaining = len(self._task_steps) - self._current_step_index
                                    yield {
                                        "type": "log",
                                        "message": f"✅ Step {current_step.number} completed. {remaining} steps remaining.",
                                    }
                                    # Tell LLM about progress
                                    if remaining > 0:
                                        next_step = self._task_steps[self._current_step_index]
                                        self.messages.append(LLMMessage(
                                            role="user",
                                            content=f"Step {current_step.number} completed. Now execute STEP {next_step.number}: {next_step.action} - {next_step.target}" + (f" - \"{next_step.value}\"" if next_step.value else ""),
                                        ))
                            
                            # Take screenshot after certain actions
                            if tool_call.name in ["navigate", "click", "fill", "scroll", "click_text", "find_and_click"]:
                                try:
                                    ss_result = await self.browser.screenshot()
                                    step.screenshot = ss_result.get("screenshot")
                                    yield {
                                        "type": "screenshot",
                                        "screenshot": step.screenshot,
                                    }
                                except Exception as e:
                                    yield {"type": "log", "message": f"Screenshot failed: {e}"}
                        else:
                            error = result.get("error", "Unknown error")
                            step.error = error
                            yield {"type": "log", "message": f"Result: Failed - {error}"}
                        
                        self.history.append(step)
                        
                        # Add tool result to messages
                        self.messages.append(self.llm.format_tool_result(
                            tool_call.id,
                            tool_call.name,
                            result,
                        ))
                        
                        # Prune old messages to prevent context overflow
                        # Keep system prompt + last N messages
                        self._prune_messages(max_messages=12)
                else:
                    # No tool calls - increment stuck counter
                    self._stuck_count += 1
                    self._last_tool_key = None  # Reset tool tracking
                    
                    # Check if agent is stuck without making tool calls
                    if self._stuck_count >= 5:
                        yield {"type": "error", "message": "Agent appears stuck - no tool calls for 5 consecutive turns"}
                        break
                    
                    # No tool calls - check if task is complete or needs continuation
                    self.messages.append(LLMMessage(
                        role="assistant",
                        content=response.content,
                    ))
                    
                    # Check for task completion - must be explicit and standalone
                    # The response should be primarily "TASK_COMPLETE" without long analysis
                    if response.content:
                        content_stripped = response.content.strip().upper()
                        # Check for clean TASK_COMPLETE (with minimal surrounding text)
                        is_task_complete = (
                            content_stripped == "TASK_COMPLETE" or
                            content_stripped.startswith("TASK_COMPLETE") and len(content_stripped) < 50
                        )
                        
                        if is_task_complete:
                            # Verify we've actually done actionable steps (not just searches)
                            actionable_tools = {"click", "fill", "submit", "press_key", "check", "select_option"}
                            has_actionable_steps = any(
                                step.tool_name in actionable_tools and not step.error
                                for step in self.history
                            )
                            
                            if has_actionable_steps:
                                task_complete = True
                                yield {"type": "log", "message": "Agent marked task as complete"}
                            else:
                                # Agent tried to complete without doing real actions
                                yield {"type": "log", "message": "Agent tried to complete but no actionable steps performed - continuing"}
                                self.messages.append(LLMMessage(
                                    role="user",
                                    content="You have NOT completed the task yet. You only searched/viewed but didn't perform the actual action (e.g., clicking 'Add to Cart', submitting form, etc.). Continue with the task!",
                                ))
                        elif "TASK_COMPLETE" in content_stripped:
                            # Agent mixed TASK_COMPLETE with analysis - reject it
                            yield {"type": "log", "message": "Task completion rejected - mixed with other content, continuing"}
                            self.messages.append(LLMMessage(
                                role="user",
                                content="Do not mix TASK_COMPLETE with analysis. If task is done, respond ONLY with 'TASK_COMPLETE'. If not done, continue executing actions.",
                            ))
                        else:
                            # No TASK_COMPLETE mentioned - continue
                            pass
                    
                    if not task_complete:
                        # Ask for next step if we haven't already added a corrective message
                        if not response.content or "TASK_COMPLETE" not in response.content.upper():
                            self.messages.append(LLMMessage(
                                role="user",
                                content="Continue executing the task. What is the next action?",
                            ))
                
                # Small delay between steps
                await asyncio.sleep(0.5)
            
            # Generate final code using unified CodeGenService
            code = await self._generate_test_code(task, url)
            yield {"type": "code", "code": code}
            
            # Final status
            if task_complete:
                yield {"type": "complete", "message": "Task completed successfully", "steps": step_count}
            elif step_count >= self.config.max_steps:
                yield {"type": "complete", "message": f"Reached maximum steps ({self.config.max_steps})", "steps": step_count}
            else:
                yield {"type": "complete", "message": "Agent stopped", "steps": step_count}
                
        except Exception as e:
            yield {"type": "error", "message": f"Agent error: {str(e)}"}
        finally:
            if self.browser:
                await self.browser.close()
                yield {"type": "log", "message": "Browser closed"}

    def _summarize_result(self, result: dict) -> str:
        """Create a brief summary of a tool result."""
        if "url" in result:
            return f"URL: {result['url']}"
        if "text" in result:
            text = result["text"] or ""
            return f"Text: {text[:100]}..." if len(text) > 100 else f"Text: {text}"
        if "count" in result:
            return f"Count: {result['count']}"
        if "visible" in result:
            return f"Visible: {result['visible']}"
        if "screenshot" in result:
            return "Screenshot captured"
        return str(result.get("action", "Done"))

    def _history_to_test_steps(self, url: str) -> list[TestStep]:
        """Convert agent execution history to TestStep objects.
        
        Filters out:
        - Failed steps (those with errors)
        - Non-actionable tools (screenshot, get_page_structure, extract_text, get_page_info)
        - Duplicate actions on same selector/value
        
        Returns:
            list[TestStep]: List of test steps for code generation.
        """
        # Tools that don't produce actionable test code
        non_actionable_tools = {
            "screenshot", "get_page_structure", "extract_text", 
            "extract_all_text", "get_page_info", "get_element_text",
            "is_visible", "count_elements", "extract_attribute"
        }
        
        # Tool name to action mapping
        tool_to_action = {
            "navigate": "navigate",
            "click": "click",
            "click_text": "click_text",
            "click_nth": "click_nth",
            "find_and_click": "click_text",
            "fill": "fill",
            "type_text": "type",
            "press_key": "press",
            "hover": "hover",
            "select_option": "select",
            "check": "check",
            "uncheck": "uncheck",
            "scroll": "scroll",
            "scroll_to_element": "scroll_to",
            "wait": "wait",
            "wait_for_element": "wait_for",
            "double_click": "double_click",
        }
        
        test_steps: list[TestStep] = []
        seen_actions: set[str] = set()
        
        # Add initial navigate step
        test_steps.append(TestStep(action="navigate", value=url))
        
        for step in self.history:
            # Skip failed steps
            if step.error:
                continue
            
            # Skip non-actionable tools
            if not step.tool_name or step.tool_name in non_actionable_tools:
                continue
            
            # Get the mapped action name
            action = tool_to_action.get(step.tool_name)
            if not action:
                continue
            
            args = step.tool_args or {}
            
            # Extract selector and value based on tool type
            selector = args.get('selector')
            value = None
            
            if step.tool_name == "navigate":
                value = args.get('url')
                selector = None
            elif step.tool_name == "fill":
                value = args.get('value')
            elif step.tool_name == "type_text":
                value = args.get('text')
            elif step.tool_name == "press_key":
                value = args.get('key')
            elif step.tool_name in ("click_text", "find_and_click"):
                value = args.get('text') or args.get('target')
                selector = None  # Text-based, no selector
            elif step.tool_name == "click_nth":
                value = str(args.get('index', 0))
            elif step.tool_name == "select_option":
                value = args.get('value') or args.get('label')
            elif step.tool_name == "scroll":
                direction = args.get('direction', 'down')
                amount = args.get('amount', 500)
                value = f"{direction}:{amount}"
                selector = None
            elif step.tool_name == "scroll_to_element":
                pass  # Just uses selector
            elif step.tool_name == "wait":
                value = str(args.get('timeout', 1000))
                selector = None
            elif step.tool_name == "wait_for_element":
                pass  # Just uses selector
            
            # Create unique key for deduplication
            action_key = f"{action}:{selector}:{value}"
            if action_key in seen_actions:
                continue
            seen_actions.add(action_key)
            
            test_steps.append(TestStep(
                action=action,
                selector=selector,
                value=value,
            ))
        
        return test_steps

    async def _generate_test_code(self, task: str, url: str) -> str:
        """Generate test code from execution history using CodeGenService.
        
        Uses the unified CodeGenService for consistent code generation
        across the agent and the /api/generate-code endpoint.
        
        Args:
            task: The original task description.
            url: The starting URL.
            
        Returns:
            str: Generated test code in the configured language.
        """
        # Convert history to test steps
        test_steps = self._history_to_test_steps(url)
        
        if not test_steps:
            # Return a template if no steps recorded
            if self.config.language == Language.PYTHON:
                return f'''import pytest
from playwright.sync_api import Page, expect

def test_generated(page: Page):
    """Generated test for: {task}"""
    page.goto("{url}")
    # No steps recorded - add your automation code here
    # Example:
    # page.click("button")
    # page.fill("input", "value")
'''
            else:
                return f'''import {{ test, expect }} from '@playwright/test';

test('generated test', async ({{ page }}) => {{
  // Task: {task}
  await page.goto('{url}');
  // No steps recorded - add your automation code here
  // Example:
  // await page.click('button');
  // await page.fill('input', 'value');
}});
'''
        
        # Use CodeGenService for unified code generation
        from browser_agent.models.codegen import CodeGenRequest
        
        codegen_service = CodeGenService()
        request = CodeGenRequest(
            test_plan=test_steps,
            framework=self.config.framework,
            language=self.config.language,
        )
        
        response = await codegen_service.generate(request)
        return response.code
