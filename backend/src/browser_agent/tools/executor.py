"""Tool executor that connects tool schemas to browser wrapper."""

import logging
from typing import Any, Optional, Union

from browser_agent.core.browser import BrowserWrapper
from browser_agent.core.sync_browser import AsyncBrowserAdapter
from browser_agent.tools.schemas import TOOL_DEFINITIONS, Tool, get_tool_by_name

logger = logging.getLogger(__name__)

# Type alias for browser instances
BrowserType = Union[BrowserWrapper, AsyncBrowserAdapter]


class ToolExecutor:
    """Executes browser tools using the BrowserWrapper.
    
    Maps tool names to browser wrapper methods and handles
    parameter validation and error handling.
    """

    def __init__(self, browser: BrowserType) -> None:
        """Initialize tool executor with a browser instance.
        
        Args:
            browser: BrowserWrapper or AsyncBrowserAdapter instance to execute tools with.
        """
        self.browser = browser
        
        # Map tool names to browser methods
        self._tool_handlers = {
            # Navigation
            "navigate": self._navigate,
            "go_back": self._go_back,
            "go_forward": self._go_forward,
            "reload": self._reload,
            
            # Interaction
            "click": self._click,
            "click_text": self._click_text,
            "click_nth": self._click_nth,
            "double_click": self._double_click,
            "hover": self._hover,
            "dismiss_overlays": self._dismiss_overlays,
            "extract_modal_content": self._extract_modal_content,
            "find_and_click": self._find_and_click,
            
            # Input
            "fill": self._fill,
            "type_text": self._type_text,
            "press_key": self._press_key,
            "select_option": self._select_option,
            "check": self._check,
            "uncheck": self._uncheck,
            
            # Scrolling
            "scroll": self._scroll,
            "scroll_to_element": self._scroll_to_element,
            
            # Wait
            "wait_for_element": self._wait_for_element,
            "wait": self._wait,
            
            # Extraction
            "extract_text": self._extract_text,
            "extract_attribute": self._extract_attribute,
            "extract_all_text": self._extract_all_text,
            "count_elements": self._count_elements,
            "is_visible": self._is_visible,
            
            # Page info
            "get_page_info": self._get_page_info,
            "get_page_structure": self._get_page_structure,
            "screenshot": self._screenshot,
        }
        
        # Validate that all defined tools have handlers
        self._validate_tool_handlers()

    def _validate_tool_handlers(self) -> None:
        """Validate that all defined tools have corresponding handlers.
        
        Logs warnings for any mismatches between tool definitions and handlers.
        """
        defined_tools = {tool.name for tool in TOOL_DEFINITIONS}
        handler_tools = set(self._tool_handlers.keys())
        
        # Tools defined but no handler
        missing_handlers = defined_tools - handler_tools
        if missing_handlers:
            logger.warning(
                "Tools defined but missing handlers: %s",
                ", ".join(sorted(missing_handlers))
            )
        
        # Handlers without tool definition (orphan handlers)
        orphan_handlers = handler_tools - defined_tools
        if orphan_handlers:
            logger.debug(
                "Handlers without tool definitions (internal tools): %s",
                ", ".join(sorted(orphan_handlers))
            )

    async def execute(self, tool_name: str, parameters: dict[str, Any]) -> dict:
        """Execute a tool by name with given parameters.
        
        Args:
            tool_name: Name of the tool to execute.
            parameters: Tool parameters as a dictionary.
            
        Returns:
            dict: Tool execution result.
            
        Raises:
            ValueError: If tool name is unknown.
        """
        handler = self._tool_handlers.get(tool_name)
        if not handler:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}. Available tools: {', '.join(self._tool_handlers.keys())}",
            }
        
        # Validate parameters is a dict
        if not isinstance(parameters, dict):
            logger.warning("Tool %s received non-dict parameters: %s", tool_name, type(parameters))
            parameters = {}
        
        # Log the tool execution
        logger.info("Executing tool: %s with parameters: %s", tool_name, parameters)
        
        try:
            result = await handler(parameters)
            result["tool"] = tool_name
            logger.debug("Tool %s result: %s", tool_name, result.get("success"))
            return result
        except Exception as e:
            logger.exception("Tool %s failed with error: %s", tool_name, str(e))
            return {
                "success": False,
                "tool": tool_name,
                "error": str(e),
                "error_type": type(e).__name__,
            }

    def get_available_tools(self) -> list[str]:
        """Get list of available tool names."""
        return list(self._tool_handlers.keys())

    # Navigation handlers
    async def _navigate(self, params: dict) -> dict:
        return await self.browser.goto(
            url=params["url"],
            wait_until=params.get("wait_until", "domcontentloaded"),
        )

    async def _go_back(self, params: dict) -> dict:
        return await self.browser.go_back()

    async def _go_forward(self, params: dict) -> dict:
        return await self.browser.go_forward()

    async def _reload(self, params: dict) -> dict:
        return await self.browser.reload()

    # Interaction handlers
    async def _click(self, params: dict) -> dict:
        return await self.browser.click(
            selector=params["selector"],
            button=params.get("button", "left"),
        )

    async def _click_text(self, params: dict) -> dict:
        return await self.browser.click_text(
            text=params["text"],
            element_type=params.get("element_type", "any"),
            exact=params.get("exact", False),
        )

    async def _click_nth(self, params: dict) -> dict:
        return await self.browser.click_nth(
            selector=params["selector"],
            index=params["index"],
        )

    async def _double_click(self, params: dict) -> dict:
        return await self.browser.double_click(selector=params["selector"])

    async def _hover(self, params: dict) -> dict:
        return await self.browser.hover(selector=params["selector"])

    async def _dismiss_overlays(self, params: dict) -> dict:
        return await self.browser.dismiss_overlays()

    async def _extract_modal_content(self, params: dict) -> dict:
        return await self.browser.extract_modal_content()

    async def _find_and_click(self, params: dict) -> dict:
        return await self.browser.find_and_click(
            target=params["target"],
            scroll_first=params.get("scroll_first", True),
        )

    # Input handlers
    async def _fill(self, params: dict) -> dict:
        return await self.browser.fill(
            selector=params["selector"],
            value=params["value"],
        )

    async def _type_text(self, params: dict) -> dict:
        return await self.browser.type_text(
            selector=params["selector"],
            text=params["text"],
            delay=params.get("delay", 50),
        )

    async def _press_key(self, params: dict) -> dict:
        return await self.browser.press_key(
            key=params["key"],
            selector=params.get("selector"),
        )

    async def _select_option(self, params: dict) -> dict:
        return await self.browser.select_option(
            selector=params["selector"],
            value=params.get("value"),
            label=params.get("label"),
        )

    async def _check(self, params: dict) -> dict:
        return await self.browser.check(selector=params["selector"])

    async def _uncheck(self, params: dict) -> dict:
        return await self.browser.uncheck(selector=params["selector"])

    # Scroll handlers
    async def _scroll(self, params: dict) -> dict:
        return await self.browser.scroll_page(
            direction=params["direction"],
            amount=params.get("amount", 500),
        )

    async def _scroll_to_element(self, params: dict) -> dict:
        return await self.browser.scroll_to_element(selector=params["selector"])

    # Wait handlers
    async def _wait_for_element(self, params: dict) -> dict:
        return await self.browser.wait_for_selector(
            selector=params["selector"],
            state=params.get("state", "visible"),
            timeout=params.get("timeout"),
        )

    async def _wait(self, params: dict) -> dict:
        return await self.browser.wait_for_timeout(timeout=params["timeout"])

    # Extraction handlers
    async def _extract_text(self, params: dict) -> dict:
        return await self.browser.get_text(selector=params["selector"])

    async def _extract_attribute(self, params: dict) -> dict:
        return await self.browser.get_attribute(
            selector=params["selector"],
            attribute=params["attribute"],
        )

    async def _extract_all_text(self, params: dict) -> dict:
        # get_all_text not available, use evaluate
        selector = params["selector"]
        result = await self.browser.evaluate(
            f"Array.from(document.querySelectorAll('{selector}')).map(el => el.textContent).join('\\n')"
        )
        return {"success": True, "text": result.get("result", "")}

    async def _count_elements(self, params: dict) -> dict:
        return await self.browser.count_elements(selector=params["selector"])

    async def _is_visible(self, params: dict) -> dict:
        return await self.browser.is_visible(selector=params["selector"])

    # Page info handlers
    async def _get_page_info(self, params: dict) -> dict:
        url_result = await self.browser.get_current_url()
        title_result = await self.browser.get_page_title()
        return {
            "success": True,
            "url": url_result.get("url", ""),
            "title": title_result.get("title", ""),
        }

    async def _get_page_structure(self, params: dict) -> dict:
        # Returns only interactive elements (inputs, buttons, links) - optimized for token limits
        return await self.browser.get_page_structure()

    async def _screenshot(self, params: dict) -> dict:
        return await self.browser.screenshot(
            full_page=params.get("full_page", False),
        )
