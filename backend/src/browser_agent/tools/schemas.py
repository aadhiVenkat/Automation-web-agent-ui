"""MCP-style tool definitions for browser automation.

This module defines tool schemas following the Model Context Protocol (MCP)
pattern, where each tool has:
- A unique name
- A description
- A JSON schema for parameters
- An execution function

Tools are designed to be used by LLMs to interact with web browsers.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine, Optional


@dataclass
class ToolParameter:
    """Definition of a tool parameter."""
    name: str
    type: str  # 'string', 'integer', 'boolean', 'array', 'object'
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[list] = None


@dataclass
class Tool:
    """MCP-style tool definition.
    
    Attributes:
        name: Unique tool identifier.
        description: What the tool does (shown to LLM).
        parameters: List of parameter definitions.
        handler: Async function that executes the tool.
        category: Tool category for organization.
    """
    name: str
    description: str
    parameters: list[ToolParameter]
    handler: Optional[Callable[..., Coroutine[Any, Any, dict]]] = None
    category: str = "browser"

    def to_schema(self) -> dict:
        """Convert tool definition to JSON schema format for LLM."""
        properties = {}
        required = []
        
        for param in self.parameters:
            prop = {
                "type": param.type,
                "description": param.description,
            }
            if param.enum:
                prop["enum"] = param.enum
            if param.default is not None:
                prop["default"] = param.default
            
            properties[param.name] = prop
            
            if param.required:
                required.append(param.name)
        
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            }
        }

    def to_openai_function(self) -> dict:
        """Convert to OpenAI function calling format."""
        schema = self.to_schema()
        return {
            "type": "function",
            "function": schema
        }


# Define all browser automation tools
TOOL_DEFINITIONS: list[Tool] = [
    # Navigation Tools
    Tool(
        name="navigate",
        description="Navigate the browser to a specified URL. Use this to go to a new web page.",
        parameters=[
            ToolParameter(
                name="url",
                type="string",
                description="The URL to navigate to (must include http:// or https://)",
            ),
            ToolParameter(
                name="wait_until",
                type="string",
                description="When to consider navigation complete",
                required=False,
                default="domcontentloaded",
                enum=["load", "domcontentloaded", "networkidle"],
            ),
        ],
        category="navigation",
    ),
    Tool(
        name="go_back",
        description="Navigate back to the previous page in browser history.",
        parameters=[],
        category="navigation",
    ),
    Tool(
        name="go_forward",
        description="Navigate forward in browser history.",
        parameters=[],
        category="navigation",
    ),
    Tool(
        name="reload",
        description="Reload the current page.",
        parameters=[],
        category="navigation",
    ),
    
    # Click/Interaction Tools
    Tool(
        name="click",
        description="Click on an element using CSS selector. Use force=true if element is blocked by overlays.",
        parameters=[
            ToolParameter(
                name="selector",
                type="string",
                description="CSS selector for the element to click (e.g., 'button#submit', '.login-btn', '[data-testid=\"login\"]')",
            ),
            ToolParameter(
                name="button",
                type="string",
                description="Mouse button to use",
                required=False,
                default="left",
                enum=["left", "right", "middle"],
            ),
            ToolParameter(
                name="force",
                type="boolean",
                description="Force click even if element is covered by overlay/popup. Use when normal click times out.",
                required=False,
                default=False,
            ),
        ],
        category="interaction",
    ),
    Tool(
        name="click_text",
        description="Click on an element by its visible text content. More reliable than CSS selectors for dynamic pages. Case-insensitive partial match.",
        parameters=[
            ToolParameter(
                name="text",
                type="string",
                description="Visible text to search for and click (e.g., 'Add to Cart', 'Sign In', 'Submit')",
            ),
            ToolParameter(
                name="element_type",
                type="string",
                description="Type of element to search in",
                required=False,
                default="any",
                enum=["any", "button", "link", "heading"],
            ),
            ToolParameter(
                name="exact",
                type="boolean",
                description="Require exact text match (default: false for partial match)",
                required=False,
                default=False,
            ),
        ],
        category="interaction",
    ),
    Tool(
        name="click_nth",
        description="Click the Nth element matching a selector. Use when multiple elements match and you need a specific one (0-indexed).",
        parameters=[
            ToolParameter(
                name="selector",
                type="string",
                description="CSS selector that matches multiple elements",
            ),
            ToolParameter(
                name="index",
                type="integer",
                description="Index of element to click (0-indexed, e.g., 0 for first, 1 for second)",
            ),
        ],
        category="interaction",
    ),
    Tool(
        name="double_click",
        description="Double-click on an element.",
        parameters=[
            ToolParameter(
                name="selector",
                type="string",
                description="CSS selector for the element to double-click",
            ),
        ],
        category="interaction",
    ),
    Tool(
        name="hover",
        description="Hover the mouse over an element. Useful for revealing dropdown menus or tooltips.",
        parameters=[
            ToolParameter(
                name="selector",
                type="string",
                description="CSS selector for the element to hover over",
            ),
        ],
        category="interaction",
    ),
    
    # Input Tools
    Tool(
        name="fill",
        description="Fill a text input field with a value. Clears existing content first.",
        parameters=[
            ToolParameter(
                name="selector",
                type="string",
                description="CSS selector for the input field (e.g., 'input[name=\"email\"]', '#username')",
            ),
            ToolParameter(
                name="value",
                type="string",
                description="Text value to fill into the input",
            ),
        ],
        category="input",
    ),
    Tool(
        name="type_text",
        description="Type text character by character, simulating real keyboard input. Use for fields that need keystroke events.",
        parameters=[
            ToolParameter(
                name="selector",
                type="string",
                description="CSS selector for the input field",
            ),
            ToolParameter(
                name="text",
                type="string",
                description="Text to type",
            ),
            ToolParameter(
                name="delay",
                type="integer",
                description="Delay between keystrokes in milliseconds",
                required=False,
                default=50,
            ),
        ],
        category="input",
    ),
    Tool(
        name="press_key",
        description="Press a keyboard key. Use for Enter, Tab, Escape, arrows, etc.",
        parameters=[
            ToolParameter(
                name="key",
                type="string",
                description="Key to press (e.g., 'Enter', 'Tab', 'Escape', 'ArrowDown', 'Backspace')",
            ),
            ToolParameter(
                name="selector",
                type="string",
                description="Optional: CSS selector to focus before pressing key",
                required=False,
            ),
        ],
        category="input",
    ),
    Tool(
        name="select_option",
        description="Select an option from a dropdown <select> element.",
        parameters=[
            ToolParameter(
                name="selector",
                type="string",
                description="CSS selector for the select element",
            ),
            ToolParameter(
                name="value",
                type="string",
                description="Option value attribute to select",
                required=False,
            ),
            ToolParameter(
                name="label",
                type="string",
                description="Option visible text to select",
                required=False,
            ),
        ],
        category="input",
    ),
    Tool(
        name="check",
        description="Check a checkbox or radio button.",
        parameters=[
            ToolParameter(
                name="selector",
                type="string",
                description="CSS selector for the checkbox/radio",
            ),
        ],
        category="input",
    ),
    Tool(
        name="uncheck",
        description="Uncheck a checkbox.",
        parameters=[
            ToolParameter(
                name="selector",
                type="string",
                description="CSS selector for the checkbox",
            ),
        ],
        category="input",
    ),
    
    # Scrolling Tools
    Tool(
        name="scroll",
        description="Scroll the page in a direction.",
        parameters=[
            ToolParameter(
                name="direction",
                type="string",
                description="Direction to scroll",
                enum=["up", "down", "left", "right"],
            ),
            ToolParameter(
                name="amount",
                type="integer",
                description="Pixels to scroll",
                required=False,
                default=500,
            ),
        ],
        category="scroll",
    ),
    Tool(
        name="scroll_to_element",
        description="Scroll until a specific element is visible in the viewport.",
        parameters=[
            ToolParameter(
                name="selector",
                type="string",
                description="CSS selector for the element to scroll to",
            ),
        ],
        category="scroll",
    ),
    
    # Wait Tools
    Tool(
        name="wait_for_element",
        description="Wait for an element to appear or reach a certain state.",
        parameters=[
            ToolParameter(
                name="selector",
                type="string",
                description="CSS selector for the element to wait for",
            ),
            ToolParameter(
                name="state",
                type="string",
                description="State to wait for",
                required=False,
                default="visible",
                enum=["attached", "detached", "visible", "hidden"],
            ),
            ToolParameter(
                name="timeout",
                type="integer",
                description="Maximum time to wait in milliseconds",
                required=False,
                default=30000,
            ),
        ],
        category="wait",
    ),
    Tool(
        name="wait",
        description="Wait for a specified amount of time. Use sparingly, prefer wait_for_element.",
        parameters=[
            ToolParameter(
                name="timeout",
                type="integer",
                description="Time to wait in milliseconds",
            ),
        ],
        category="wait",
    ),
    
    # Extraction Tools
    Tool(
        name="extract_text",
        description="Extract text content from an element.",
        parameters=[
            ToolParameter(
                name="selector",
                type="string",
                description="CSS selector for the element",
            ),
        ],
        category="extraction",
    ),
    Tool(
        name="extract_attribute",
        description="Extract an attribute value from an element.",
        parameters=[
            ToolParameter(
                name="selector",
                type="string",
                description="CSS selector for the element",
            ),
            ToolParameter(
                name="attribute",
                type="string",
                description="Attribute name to extract (e.g., 'href', 'src', 'data-id')",
            ),
        ],
        category="extraction",
    ),
    Tool(
        name="extract_all_text",
        description="Extract text from all elements matching a selector.",
        parameters=[
            ToolParameter(
                name="selector",
                type="string",
                description="CSS selector for the elements",
            ),
        ],
        category="extraction",
    ),
    Tool(
        name="count_elements",
        description="Count how many elements match a selector.",
        parameters=[
            ToolParameter(
                name="selector",
                type="string",
                description="CSS selector to count",
            ),
        ],
        category="extraction",
    ),
    Tool(
        name="is_visible",
        description="Check if an element is visible on the page.",
        parameters=[
            ToolParameter(
                name="selector",
                type="string",
                description="CSS selector for the element",
            ),
        ],
        category="extraction",
    ),
    
    # Page Info Tools
    Tool(
        name="get_page_info",
        description="Get current page URL and title.",
        parameters=[],
        category="info",
    ),
    Tool(
        name="get_page_structure",
        description="Get a summary of interactive elements on the page. Use this to understand what actions are available.",
        parameters=[],
        category="info",
    ),
    Tool(
        name="screenshot",
        description="Take a screenshot of the current page.",
        parameters=[
            ToolParameter(
                name="full_page",
                type="boolean",
                description="Capture the full scrollable page",
                required=False,
                default=False,
            ),
        ],
        category="info",
    ),
    
    # Overlay/Popup Handling Tools
    Tool(
        name="dismiss_overlays",
        description="Dismiss common popups, modals, cookie banners, and overlays. Use this when clicks fail due to overlays blocking elements.",
        parameters=[],
        category="interaction",
    ),
    Tool(
        name="extract_modal_content",
        description="Extract content from a visible modal, popup, or dialog. Returns title, text, buttons, links, inputs, and images from the modal. Use this to READ modal content before dismissing it.",
        parameters=[],
        category="extraction",
    ),
    Tool(
        name="find_and_click",
        description="Smart click that tries multiple strategies: by text, by selector, with scrolling. Use when simple click fails.",
        parameters=[
            ToolParameter(
                name="target",
                type="string",
                description="Text content OR CSS selector to find and click",
            ),
            ToolParameter(
                name="scroll_first",
                type="boolean",
                description="Scroll down before attempting click",
                required=False,
                default=True,
            ),
        ],
        category="interaction",
    ),
]


def get_tool_by_name(name: str) -> Optional[Tool]:
    """Get a tool definition by name."""
    for tool in TOOL_DEFINITIONS:
        if tool.name == name:
            return tool
    return None


def get_all_tool_schemas() -> list[dict]:
    """Get all tool schemas for LLM."""
    return [tool.to_schema() for tool in TOOL_DEFINITIONS]


def get_tools_for_openai() -> list[dict]:
    """Get all tools in OpenAI function calling format."""
    return [tool.to_openai_function() for tool in TOOL_DEFINITIONS]


def get_tools_prompt() -> str:
    """Generate a text description of all tools for LLM system prompt."""
    lines = ["Available browser automation tools:\n"]
    
    categories = {}
    for tool in TOOL_DEFINITIONS:
        if tool.category not in categories:
            categories[tool.category] = []
        categories[tool.category].append(tool)
    
    for category, tools in categories.items():
        lines.append(f"\n## {category.title()} Tools\n")
        for tool in tools:
            params = ", ".join([
                f"{p.name}: {p.type}" + ("?" if not p.required else "")
                for p in tool.parameters
            ])
            lines.append(f"- **{tool.name}**({params}): {tool.description}")
    
    return "\n".join(lines)
