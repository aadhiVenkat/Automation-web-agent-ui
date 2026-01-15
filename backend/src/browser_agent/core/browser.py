"""Playwright browser wrapper for async browser automation."""

import asyncio
import base64
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Optional

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)


class BrowserWrapper:
    """Async wrapper for Playwright browser automation.
    
    Provides a high-level interface for browser interactions with
    automatic resource management and error handling.
    
    Usage:
        async with BrowserWrapper() as browser:
            await browser.goto("https://example.com")
            await browser.click("button#submit")
            screenshot = await browser.screenshot()
    """

    def __init__(
        self,
        headless: bool = True,
        viewport_width: int = 1280,
        viewport_height: int = 720,
        timeout: int = 30000,
        http_credentials: Optional[dict] = None,
    ) -> None:
        """Initialize browser wrapper.
        
        Args:
            headless: Run browser in headless mode.
            viewport_width: Browser viewport width.
            viewport_height: Browser viewport height.
            timeout: Default timeout in milliseconds.
            http_credentials: Optional dict with 'username' and 'password' for HTTP basic auth.
        """
        self.headless = headless
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.timeout = timeout
        self.http_credentials = http_credentials
        
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    async def __aenter__(self) -> "BrowserWrapper":
        """Async context manager entry - launch browser."""
        await self.launch()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit - close browser."""
        await self.close()

    async def launch(self) -> None:
        """Launch browser and create page."""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
        )
        
        # Build context options
        context_options = {
            "viewport": {"width": self.viewport_width, "height": self.viewport_height},
        }
        
        # Add HTTP basic auth credentials if provided
        if self.http_credentials:
            context_options["http_credentials"] = self.http_credentials
        
        self._context = await self._browser.new_context(**context_options)
        self._page = await self._context.new_page()
        self._page.set_default_timeout(self.timeout)

    async def close(self) -> None:
        """Close browser and cleanup resources."""
        if self._page:
            await self._page.close()
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    @property
    def page(self) -> Page:
        """Get the current page."""
        if not self._page:
            raise RuntimeError("Browser not launched. Use 'async with BrowserWrapper()' or call launch() first.")
        return self._page

    # Navigation
    async def goto(self, url: str, wait_until: str = "domcontentloaded") -> dict:
        """Navigate to a URL.
        
        Args:
            url: URL to navigate to.
            wait_until: When to consider navigation complete.
                       Options: 'load', 'domcontentloaded', 'networkidle'
        
        Returns:
            dict: Result with status and current URL.
        """
        response = await self.page.goto(url, wait_until=wait_until)
        return {
            "success": True,
            "url": self.page.url,
            "status": response.status if response else None,
            "title": await self.page.title(),
        }

    async def go_back(self) -> dict:
        """Navigate back in history."""
        await self.page.go_back()
        return {"success": True, "url": self.page.url}

    async def go_forward(self) -> dict:
        """Navigate forward in history."""
        await self.page.go_forward()
        return {"success": True, "url": self.page.url}

    async def reload(self) -> dict:
        """Reload the current page."""
        await self.page.reload()
        return {"success": True, "url": self.page.url}

    # Element Interactions
    async def click(self, selector: str, button: str = "left", click_count: int = 1) -> dict:
        """Click an element.
        
        Args:
            selector: CSS or XPath selector.
            button: Mouse button ('left', 'right', 'middle').
            click_count: Number of clicks.
        
        Returns:
            dict: Result with success status.
        """
        await self.page.click(selector, button=button, click_count=click_count)
        return {"success": True, "selector": selector, "action": "click"}

    async def double_click(self, selector: str) -> dict:
        """Double-click an element."""
        await self.page.dblclick(selector)
        return {"success": True, "selector": selector, "action": "double_click"}

    async def fill(self, selector: str, value: str) -> dict:
        """Fill an input field with text.
        
        Args:
            selector: CSS or XPath selector for input element.
            value: Text to fill.
        
        Returns:
            dict: Result with success status.
        """
        await self.page.fill(selector, value)
        return {"success": True, "selector": selector, "value": value, "action": "fill"}

    async def type_text(self, selector: str, text: str, delay: int = 50) -> dict:
        """Type text character by character (simulates real typing).
        
        Args:
            selector: CSS or XPath selector.
            text: Text to type.
            delay: Delay between keystrokes in ms.
        """
        await self.page.type(selector, text, delay=delay)
        return {"success": True, "selector": selector, "text": text, "action": "type"}

    async def press_key(self, key: str, selector: Optional[str] = None) -> dict:
        """Press a keyboard key.
        
        Args:
            key: Key to press (e.g., 'Enter', 'Tab', 'Escape').
            selector: Optional element to focus first.
        """
        if selector:
            await self.page.press(selector, key)
        else:
            await self.page.keyboard.press(key)
        return {"success": True, "key": key, "action": "press_key"}

    async def hover(self, selector: str) -> dict:
        """Hover over an element."""
        await self.page.hover(selector)
        return {"success": True, "selector": selector, "action": "hover"}

    async def select_option(self, selector: str, value: Optional[str] = None, label: Optional[str] = None) -> dict:
        """Select an option from a dropdown.
        
        Args:
            selector: CSS selector for select element.
            value: Option value to select.
            label: Option label to select.
        """
        if value:
            await self.page.select_option(selector, value=value)
        elif label:
            await self.page.select_option(selector, label=label)
        return {"success": True, "selector": selector, "action": "select"}

    async def check(self, selector: str) -> dict:
        """Check a checkbox."""
        await self.page.check(selector)
        return {"success": True, "selector": selector, "action": "check"}

    async def uncheck(self, selector: str) -> dict:
        """Uncheck a checkbox."""
        await self.page.uncheck(selector)
        return {"success": True, "selector": selector, "action": "uncheck"}

    # Scrolling
    async def scroll(self, direction: str = "down", amount: int = 500) -> dict:
        """Scroll the page.
        
        Args:
            direction: 'up', 'down', 'left', 'right'.
            amount: Pixels to scroll.
        """
        delta_x, delta_y = 0, 0
        if direction == "down":
            delta_y = amount
        elif direction == "up":
            delta_y = -amount
        elif direction == "right":
            delta_x = amount
        elif direction == "left":
            delta_x = -amount
        
        await self.page.mouse.wheel(delta_x, delta_y)
        return {"success": True, "direction": direction, "amount": amount, "action": "scroll"}

    async def scroll_to_element(self, selector: str) -> dict:
        """Scroll an element into view."""
        await self.page.locator(selector).scroll_into_view_if_needed()
        return {"success": True, "selector": selector, "action": "scroll_to_element"}

    # Waiting
    async def wait_for_selector(self, selector: str, state: str = "visible", timeout: Optional[int] = None) -> dict:
        """Wait for an element to reach a state.
        
        Args:
            selector: CSS or XPath selector.
            state: 'attached', 'detached', 'visible', 'hidden'.
            timeout: Max wait time in ms.
        """
        await self.page.wait_for_selector(selector, state=state, timeout=timeout)
        return {"success": True, "selector": selector, "state": state, "action": "wait"}

    async def wait_for_navigation(self, wait_until: str = "domcontentloaded", timeout: Optional[int] = None) -> dict:
        """Wait for navigation to complete."""
        await self.page.wait_for_load_state(wait_until, timeout=timeout)
        return {"success": True, "wait_until": wait_until, "action": "wait_navigation"}

    async def wait_for_timeout(self, timeout: int) -> dict:
        """Wait for a specified time.
        
        Args:
            timeout: Time to wait in milliseconds.
        """
        await self.page.wait_for_timeout(timeout)
        return {"success": True, "timeout": timeout, "action": "wait_timeout"}

    # Data Extraction
    async def get_text(self, selector: str) -> dict:
        """Get text content of an element."""
        text = await self.page.text_content(selector)
        return {"success": True, "selector": selector, "text": text}

    async def get_attribute(self, selector: str, attribute: str) -> dict:
        """Get an attribute value from an element."""
        value = await self.page.get_attribute(selector, attribute)
        return {"success": True, "selector": selector, "attribute": attribute, "value": value}

    async def get_input_value(self, selector: str) -> dict:
        """Get the value of an input element."""
        value = await self.page.input_value(selector)
        return {"success": True, "selector": selector, "value": value}

    async def get_inner_html(self, selector: str) -> dict:
        """Get inner HTML of an element."""
        html = await self.page.inner_html(selector)
        return {"success": True, "selector": selector, "html": html}

    async def get_all_text(self, selector: str) -> dict:
        """Get text from all matching elements."""
        elements = await self.page.locator(selector).all_text_contents()
        return {"success": True, "selector": selector, "texts": elements}

    async def count_elements(self, selector: str) -> dict:
        """Count elements matching a selector."""
        count = await self.page.locator(selector).count()
        return {"success": True, "selector": selector, "count": count}

    async def is_visible(self, selector: str) -> dict:
        """Check if an element is visible."""
        visible = await self.page.locator(selector).is_visible()
        return {"success": True, "selector": selector, "visible": visible}

    async def is_enabled(self, selector: str) -> dict:
        """Check if an element is enabled."""
        enabled = await self.page.locator(selector).is_enabled()
        return {"success": True, "selector": selector, "enabled": enabled}

    # Page Information
    async def get_url(self) -> dict:
        """Get the current URL."""
        return {"success": True, "url": self.page.url}

    async def get_title(self) -> dict:
        """Get the page title."""
        title = await self.page.title()
        return {"success": True, "title": title}

    async def get_page_content(self) -> dict:
        """Get the full page HTML content."""
        content = await self.page.content()
        return {"success": True, "content": content[:10000]}  # Truncate for safety

    # Screenshots
    async def screenshot(self, full_page: bool = False, quality: int = 80) -> dict:
        """Take a screenshot.
        
        Args:
            full_page: Capture full scrollable page.
            quality: JPEG quality (0-100).
        
        Returns:
            dict: Result with base64-encoded screenshot.
        """
        screenshot_bytes = await self.page.screenshot(
            full_page=full_page,
            type="jpeg",
            quality=quality,
        )
        screenshot_base64 = base64.b64encode(screenshot_bytes).decode("utf-8")
        return {
            "success": True,
            "screenshot": screenshot_base64,
            "full_page": full_page,
        }

    async def screenshot_element(self, selector: str, quality: int = 80) -> dict:
        """Take a screenshot of a specific element."""
        screenshot_bytes = await self.page.locator(selector).screenshot(
            type="jpeg",
            quality=quality,
        )
        screenshot_base64 = base64.b64encode(screenshot_bytes).decode("utf-8")
        return {
            "success": True,
            "selector": selector,
            "screenshot": screenshot_base64,
        }

    # JavaScript Execution
    async def evaluate(self, expression: str) -> dict:
        """Execute JavaScript in the page context.
        
        Args:
            expression: JavaScript code to execute.
        
        Returns:
            dict: Result with evaluation result.
        """
        result = await self.page.evaluate(expression)
        return {"success": True, "result": result}

    # Utility
    async def get_page_structure(self, max_depth: int = 3) -> dict:
        """Get a simplified structure of the page for LLM context.
        
        Returns interactive elements, headings, and key content.
        """
        structure = await self.page.evaluate("""
            (maxDepth) => {
                const elements = [];
                
                // Get interactive elements
                const interactiveSelectors = [
                    'a[href]', 'button', 'input', 'select', 'textarea',
                    '[role="button"]', '[role="link"]', '[onclick]'
                ];
                
                interactiveSelectors.forEach(selector => {
                    document.querySelectorAll(selector).forEach((el, idx) => {
                        if (idx < 50) {  // Limit per type
                            const rect = el.getBoundingClientRect();
                            if (rect.width > 0 && rect.height > 0) {
                                elements.push({
                                    tag: el.tagName.toLowerCase(),
                                    type: el.type || null,
                                    id: el.id || null,
                                    class: el.className || null,
                                    text: el.innerText?.substring(0, 100) || null,
                                    href: el.href || null,
                                    name: el.name || null,
                                    placeholder: el.placeholder || null,
                                    ariaLabel: el.getAttribute('aria-label') || null,
                                    visible: rect.top < window.innerHeight && rect.bottom > 0
                                });
                            }
                        }
                    });
                });
                
                // Get headings
                document.querySelectorAll('h1, h2, h3').forEach(el => {
                    elements.push({
                        tag: el.tagName.toLowerCase(),
                        text: el.innerText?.substring(0, 200)
                    });
                });
                
                return {
                    url: window.location.href,
                    title: document.title,
                    elements: elements.slice(0, 100)  // Limit total
                };
            }
        """, max_depth)
        return {"success": True, "structure": structure}
