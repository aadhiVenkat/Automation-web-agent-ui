"""Synchronous Playwright browser wrapper that works on Windows with Python 3.14."""

import base64
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional, Callable
from functools import partial

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    sync_playwright,
)


class SyncBrowserWrapper:
    """Synchronous Playwright browser wrapper.
    
    This wrapper uses the sync Playwright API and runs browser operations
    in a thread pool to work around Windows + Python 3.14 asyncio issues.
    
    Usage:
        browser = SyncBrowserWrapper()
        browser.launch()
        try:
            browser.goto("https://example.com")
            browser.click("button#submit")
            screenshot = browser.screenshot()
        finally:
            browser.close()
    """

    def __init__(
        self,
        headless: bool = True,
        viewport_width: int = 1280,
        viewport_height: int = 720,
        timeout: int = 30000,
    ) -> None:
        """Initialize browser wrapper."""
        self.headless = headless
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.timeout = timeout
        
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    def launch(self) -> None:
        """Launch browser and create page."""
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=self.headless,
        )
        self._context = self._browser.new_context(
            viewport={"width": self.viewport_width, "height": self.viewport_height},
        )
        self._page = self._context.new_page()
        self._page.set_default_timeout(self.timeout)

    def close(self) -> None:
        """Close browser and cleanup resources."""
        if self._page:
            self._page.close()
        if self._context:
            self._context.close()
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()
        
        self._page = None
        self._context = None
        self._browser = None
        self._playwright = None

    @property
    def page(self) -> Page:
        """Get the current page."""
        if not self._page:
            raise RuntimeError("Browser not launched. Call launch() first.")
        return self._page

    def _highlight_element(self, selector: str, color: str = "red", duration: int = 1000) -> None:
        """Add a visual highlight border around an element for debugging."""
        try:
            self.page.evaluate(f'''
                (selector) => {{
                    const el = document.querySelector(selector);
                    if (el) {{
                        const originalOutline = el.style.outline;
                        const originalBoxShadow = el.style.boxShadow;
                        el.style.outline = "3px solid {color}";
                        el.style.boxShadow = "0 0 10px {color}";
                        setTimeout(() => {{
                            el.style.outline = originalOutline;
                            el.style.boxShadow = originalBoxShadow;
                        }}, {duration});
                    }}
                }}
            ''', selector)
        except Exception:
            pass  # Ignore highlight errors

    def _show_action_indicator(self, action: str, selector: str = "") -> None:
        """Show a floating indicator of the current action."""
        try:
            self.page.evaluate(f'''
                () => {{
                    // Remove existing indicator
                    const existing = document.getElementById('__agent_indicator__');
                    if (existing) existing.remove();
                    
                    // Create new indicator
                    const div = document.createElement('div');
                    div.id = '__agent_indicator__';
                    div.style.cssText = `
                        position: fixed;
                        top: 10px;
                        right: 10px;
                        background: rgba(0, 0, 0, 0.8);
                        color: #00ff00;
                        padding: 10px 15px;
                        border-radius: 5px;
                        font-family: monospace;
                        font-size: 14px;
                        z-index: 999999;
                        border: 2px solid #00ff00;
                        max-width: 400px;
                        word-wrap: break-word;
                    `;
                    div.innerHTML = `🤖 <strong>{action}</strong><br><span style="color: #aaa; font-size: 12px;">{selector[:80] if selector else ''}</span>`;
                    document.body.appendChild(div);
                    
                    // Auto-remove after 3 seconds
                    setTimeout(() => div.remove(), 3000);
                }}
            ''')
        except Exception:
            pass  # Ignore indicator errors

    # Navigation
    def goto(self, url: str, wait_until: str = "domcontentloaded") -> dict:
        """Navigate to a URL."""
        response = self.page.goto(url, wait_until=wait_until)
        return {
            "success": True,
            "url": self.page.url,
            "status": response.status if response else None,
            "title": self.page.title(),
        }

    def go_back(self) -> dict:
        """Navigate back in history."""
        self.page.go_back()
        return {"success": True, "url": self.page.url}

    def go_forward(self) -> dict:
        """Navigate forward in history."""
        self.page.go_forward()
        return {"success": True, "url": self.page.url}

    def reload(self) -> dict:
        """Reload the current page."""
        self.page.reload()
        return {"success": True, "url": self.page.url}

    # Element Interactions
    def click(self, selector: str, button: str = "left", click_count: int = 1, force: bool = False, timeout: int = 10000) -> dict:
        """Click an element with smart fallbacks for overlays and dynamic content.
        
        Args:
            selector: CSS selector for the element
            button: Mouse button to use
            click_count: Number of clicks
            force: Force click even if element is covered
            timeout: Max time to wait in ms
        """
        self._show_action_indicator("CLICK", selector)
        
        try:
            # First try: Standard click with shorter timeout
            self._highlight_element(selector, "red")
            self.page.click(selector, button=button, click_count=click_count, timeout=timeout, force=force)
            return {"success": True, "selector": selector, "action": "click"}
        except Exception as e:
            error_msg = str(e).lower()
            
            # If element is covered by overlay, try force click
            if "intercepts pointer events" in error_msg and not force:
                try:
                    self.page.click(selector, button=button, click_count=click_count, timeout=timeout, force=True)
                    return {"success": True, "selector": selector, "action": "click", "method": "force"}
                except Exception:
                    pass
            
            # Fallback: JavaScript click
            try:
                self.page.locator(selector).first.evaluate("el => el.click()")
                return {"success": True, "selector": selector, "action": "click", "method": "js_click"}
            except Exception:
                pass
            
            # Last resort: dispatch click event
            try:
                self.page.locator(selector).first.dispatch_event("click")
                return {"success": True, "selector": selector, "action": "click", "method": "dispatch"}
            except Exception as final_e:
                raise Exception(f"Click failed after all attempts: {final_e}")

    def double_click(self, selector: str) -> dict:
        """Double-click an element."""
        self._show_action_indicator("DOUBLE CLICK", selector)
        self._highlight_element(selector, "red")
        self.page.dblclick(selector)
        return {"success": True, "selector": selector, "action": "double_click"}

    def fill(self, selector: str, value: str) -> dict:
        """Fill an input field with text."""
        self._show_action_indicator(f"FILL: {value[:30]}", selector)
        self._highlight_element(selector, "blue")
        self.page.fill(selector, value)
        return {"success": True, "selector": selector, "value": value, "action": "fill"}

    def type_text(self, selector: str, text: str, delay: int = 50) -> dict:
        """Type text character by character."""
        self._show_action_indicator(f"TYPE: {text[:30]}", selector)
        self._highlight_element(selector, "blue")
        self.page.type(selector, text, delay=delay)
        return {"success": True, "selector": selector, "text": text, "action": "type"}

    def press_key(self, key: str, selector: Optional[str] = None) -> dict:
        """Press a keyboard key."""
        self._show_action_indicator(f"PRESS KEY: {key}", selector or "page")
        if selector:
            self._highlight_element(selector, "yellow")
            self.page.press(selector, key)
        else:
            self.page.keyboard.press(key)
        return {"success": True, "key": key, "action": "press_key"}

    def hover(self, selector: str) -> dict:
        """Hover over an element."""
        self._show_action_indicator("HOVER", selector)
        self._highlight_element(selector, "orange")
        self.page.hover(selector)
        return {"success": True, "selector": selector, "action": "hover"}

    def select_option(self, selector: str, value: Optional[str] = None, label: Optional[str] = None) -> dict:
        """Select an option from a dropdown."""
        self._show_action_indicator(f"SELECT: {value or label}", selector)
        self._highlight_element(selector, "purple")
        if value:
            self.page.select_option(selector, value=value)
        elif label:
            self.page.select_option(selector, label=label)
        return {"success": True, "selector": selector, "action": "select_option"}

    def check(self, selector: str) -> dict:
        """Check a checkbox."""
        self._show_action_indicator("CHECK", selector)
        self._highlight_element(selector, "green")
        self.page.check(selector)
        return {"success": True, "selector": selector, "action": "check"}

    def uncheck(self, selector: str) -> dict:
        """Uncheck a checkbox."""
        self._show_action_indicator("UNCHECK", selector)
        self._highlight_element(selector, "green")
        self.page.uncheck(selector)
        return {"success": True, "selector": selector, "action": "uncheck"}

    # Waiting
    def wait_for_selector(self, selector: str, state: str = "visible", timeout: Optional[int] = None) -> dict:
        """Wait for an element to appear with fallback for multiple selectors."""
        self._show_action_indicator(f"WAIT FOR: {state}", selector)
        
        # Use shorter default timeout to fail faster
        actual_timeout = timeout or 5000
        
        # Handle comma-separated selectors by trying each one
        if "," in selector:
            selectors = [s.strip() for s in selector.split(",")]
            for sel in selectors:
                try:
                    self.page.wait_for_selector(sel, state=state, timeout=actual_timeout // len(selectors))
                    self._highlight_element(sel, "cyan")
                    return {"success": True, "selector": sel, "state": state}
                except Exception:
                    continue
            raise Exception(f"None of the selectors found: {selector}")
        
        self.page.wait_for_selector(selector, state=state, timeout=actual_timeout)
        self._highlight_element(selector, "cyan")
        return {"success": True, "selector": selector, "state": state}

    def wait_for_navigation(self, wait_until: str = "domcontentloaded", timeout: Optional[int] = None) -> dict:
        """Wait for navigation to complete."""
        self.page.wait_for_load_state(wait_until, timeout=timeout)
        return {"success": True, "state": wait_until}

    def wait_for_timeout(self, timeout: int) -> dict:
        """Wait for a specified time in milliseconds."""
        self.page.wait_for_timeout(timeout)
        return {"success": True, "waited_ms": timeout}

    # Content Extraction
    def get_text(self, selector: str, timeout: int = 5000) -> dict:
        """Get text content of an element with timeout."""
        try:
            locator = self.page.locator(selector).first
            text = locator.text_content(timeout=timeout)
            return {"success": True, "selector": selector, "text": text}
        except Exception as e:
            # Try alternate approach
            try:
                text = self.page.evaluate(f"document.querySelector('{selector}')?.textContent || ''")
                return {"success": True, "selector": selector, "text": text, "method": "js"}
            except Exception:
                raise e

    def get_inner_text(self, selector: str) -> dict:
        """Get inner text of an element."""
        text = self.page.inner_text(selector)
        return {"success": True, "selector": selector, "text": text}

    def get_attribute(self, selector: str, attribute: str) -> dict:
        """Get an attribute value of an element."""
        value = self.page.get_attribute(selector, attribute)
        return {"success": True, "selector": selector, "attribute": attribute, "value": value}

    def get_value(self, selector: str) -> dict:
        """Get the value of an input element."""
        value = self.page.input_value(selector)
        return {"success": True, "selector": selector, "value": value}

    def get_page_content(self) -> dict:
        """Get the full HTML content of the page."""
        content = self.page.content()
        return {"success": True, "content": content[:50000]}  # Limit size

    def get_page_title(self) -> dict:
        """Get the page title."""
        return {"success": True, "title": self.page.title()}

    def get_current_url(self) -> dict:
        """Get the current URL."""
        return {"success": True, "url": self.page.url}

    # Screenshots
    def screenshot(self, full_page: bool = False) -> dict:
        """Take a screenshot of the page."""
        screenshot_bytes = self.page.screenshot(full_page=full_page)
        screenshot_base64 = base64.b64encode(screenshot_bytes).decode("utf-8")
        return {
            "success": True,
            "screenshot": screenshot_base64,
            "format": "base64",
            "full_page": full_page,
        }

    def screenshot_element(self, selector: str) -> dict:
        """Take a screenshot of a specific element."""
        element = self.page.locator(selector)
        screenshot_bytes = element.screenshot()
        screenshot_base64 = base64.b64encode(screenshot_bytes).decode("utf-8")
        return {
            "success": True,
            "selector": selector,
            "screenshot": screenshot_base64,
            "format": "base64",
        }

    # JavaScript Evaluation
    def evaluate(self, expression: str) -> dict:
        """Execute JavaScript in the page context."""
        result = self.page.evaluate(expression)
        return {"success": True, "result": result}

    # Scrolling
    def scroll_to(self, x: int = 0, y: int = 0) -> dict:
        """Scroll to specific coordinates."""
        self.page.evaluate(f"window.scrollTo({x}, {y})")
        return {"success": True, "x": x, "y": y}

    def scroll_by(self, x: int = 0, y: int = 0) -> dict:
        """Scroll by specific amount."""
        self.page.evaluate(f"window.scrollBy({x}, {y})")
        return {"success": True, "delta_x": x, "delta_y": y}

    def scroll_to_element(self, selector: str) -> dict:
        """Scroll an element into view."""
        self.page.locator(selector).scroll_into_view_if_needed()
        return {"success": True, "selector": selector}

    def scroll_page(self, direction: str = "down", amount: int = 500) -> dict:
        """Scroll the page in a direction."""
        if direction == "down":
            self.page.evaluate(f"window.scrollBy(0, {amount})")
        elif direction == "up":
            self.page.evaluate(f"window.scrollBy(0, -{amount})")
        elif direction == "left":
            self.page.evaluate(f"window.scrollBy(-{amount}, 0)")
        elif direction == "right":
            self.page.evaluate(f"window.scrollBy({amount}, 0)")
        return {"success": True, "direction": direction, "amount": amount}

    # Page structure extraction
    def get_page_structure(self, max_depth: int = 3) -> dict:
        """Extract only interactive elements for LLM context (optimized for token limits)."""
        self._show_action_indicator("ANALYZING PAGE", "")
        
        # First, highlight all interactive elements
        self._highlight_interactive_elements()
        
        # Instead of full DOM, extract only interactive elements
        script = """
        () => {
            const results = {
                url: window.location.href,
                title: document.title,
                inputs: [],
                buttons: [],
                links: [],
                selects: []
            };
            
            // Get visible inputs
            document.querySelectorAll('input:not([type="hidden"]), textarea').forEach((el, i) => {
                if (i >= 20) return;  // Limit
                const rect = el.getBoundingClientRect();
                if (rect.width === 0 || rect.height === 0) return;
                results.inputs.push({
                    selector: el.id ? '#' + el.id : (el.name ? `[name="${el.name}"]` : `input[type="${el.type || 'text'}"]`),
                    type: el.type || 'text',
                    placeholder: el.placeholder || '',
                    value: el.value?.slice(0, 30) || '',
                    id: el.id || '',
                    name: el.name || ''
                });
            });
            
            // Get visible buttons
            document.querySelectorAll('button, input[type="submit"], input[type="button"], [role="button"]').forEach((el, i) => {
                if (i >= 20) return;
                const rect = el.getBoundingClientRect();
                if (rect.width === 0 || rect.height === 0) return;
                const text = (el.innerText || el.value || '').slice(0, 50);
                if (!text) return;
                results.buttons.push({
                    selector: el.id ? '#' + el.id : (el.className ? '.' + el.className.split(' ')[0] : 'button'),
                    text: text,
                    id: el.id || ''
                });
            });
            
            // Get main navigation links (limit to 15)
            document.querySelectorAll('a[href]').forEach((el, i) => {
                if (i >= 15) return;
                const rect = el.getBoundingClientRect();
                if (rect.width === 0 || rect.height === 0) return;
                const text = (el.innerText || el.title || '').slice(0, 40);
                if (!text || text.length < 2) return;
                results.links.push({
                    text: text,
                    href: el.href?.slice(0, 100) || ''
                });
            });
            
            // Get selects
            document.querySelectorAll('select').forEach((el, i) => {
                if (i >= 10) return;
                results.selects.push({
                    selector: el.id ? '#' + el.id : (el.name ? `[name="${el.name}"]` : 'select'),
                    id: el.id || '',
                    name: el.name || ''
                });
            });
            
            return results;
        }
        """
        structure = self.page.evaluate(script)
        return {"success": True, "page": structure}

    def _highlight_interactive_elements(self) -> None:
        """Highlight all interactive elements on the page for visual debugging."""
        try:
            self.page.evaluate('''
                () => {
                    // Remove any existing highlights
                    document.querySelectorAll('.__agent_highlight__').forEach(el => el.remove());
                    
                    const colors = {
                        'input': '#3b82f6',      // blue
                        'textarea': '#3b82f6',   // blue
                        'button': '#ef4444',     // red
                        'a': '#22c55e',          // green
                        'select': '#a855f7',     // purple
                    };
                    
                    let index = 0;
                    ['input', 'textarea', 'button', 'a[href]', 'select', '[role="button"]'].forEach(selector => {
                        document.querySelectorAll(selector).forEach(el => {
                            if (el.offsetWidth === 0 || el.offsetHeight === 0) return;
                            
                            const rect = el.getBoundingClientRect();
                            if (rect.top > window.innerHeight || rect.bottom < 0) return;
                            
                            const tag = el.tagName.toLowerCase();
                            const color = colors[tag] || '#f59e0b';  // orange default
                            
                            // Add number label
                            const label = document.createElement('div');
                            label.className = '__agent_highlight__';
                            label.style.cssText = `
                                position: absolute;
                                left: ${rect.left + window.scrollX - 2}px;
                                top: ${rect.top + window.scrollY - 2}px;
                                width: ${rect.width + 4}px;
                                height: ${rect.height + 4}px;
                                border: 2px solid ${color};
                                background: ${color}22;
                                pointer-events: none;
                                z-index: 999998;
                                box-sizing: border-box;
                            `;
                            document.body.appendChild(label);
                            
                            index++;
                        });
                    });
                    
                    // Auto-remove highlights after 5 seconds
                    setTimeout(() => {
                        document.querySelectorAll('.__agent_highlight__').forEach(el => el.remove());
                    }, 5000);
                }
            ''')
        except Exception:
            pass  # Ignore highlight errors

    def get_all_links(self) -> dict:
        """Get all links on the page."""
        script = """
        () => {
            return Array.from(document.querySelectorAll('a[href]')).map(a => ({
                href: a.href,
                text: a.innerText?.slice(0, 100) || '',
                title: a.title || ''
            })).slice(0, 100);
        }
        """
        links = self.page.evaluate(script)
        return {"success": True, "links": links, "count": len(links)}

    def get_all_inputs(self) -> dict:
        """Get all input elements on the page."""
        script = """
        () => {
            return Array.from(document.querySelectorAll('input, textarea, select')).map(el => ({
                tag: el.tagName.toLowerCase(),
                type: el.type || '',
                name: el.name || '',
                id: el.id || '',
                placeholder: el.placeholder || '',
                value: el.value?.slice(0, 50) || ''
            })).slice(0, 50);
        }
        """
        inputs = self.page.evaluate(script)
        return {"success": True, "inputs": inputs, "count": len(inputs)}

    def get_all_buttons(self) -> dict:
        """Get all buttons on the page."""
        script = """
        () => {
            const buttons = document.querySelectorAll('button, input[type="submit"], input[type="button"], [role="button"]');
            return Array.from(buttons).map(btn => ({
                tag: btn.tagName.toLowerCase(),
                text: btn.innerText?.slice(0, 100) || btn.value || '',
                id: btn.id || '',
                class: btn.className?.split(' ').slice(0, 3).join(' ') || ''
            })).slice(0, 50);
        }
        """
        buttons = self.page.evaluate(script)
        return {"success": True, "buttons": buttons, "count": len(buttons)}

    def is_visible(self, selector: str) -> dict:
        """Check if an element is visible."""
        try:
            element = self.page.locator(selector)
            visible = element.is_visible()
            return {"success": True, "selector": selector, "visible": visible}
        except Exception:
            return {"success": True, "selector": selector, "visible": False}

    def count_elements(self, selector: str) -> dict:
        """Count elements matching selector."""
        count = self.page.locator(selector).count()
        return {"success": True, "selector": selector, "count": count}

    def get_bounding_box(self, selector: str) -> dict:
        """Get bounding box of an element."""
        box = self.page.locator(selector).bounding_box()
        if box:
            return {"success": True, "selector": selector, "box": box}
        return {"success": False, "selector": selector, "error": "Element not found or not visible"}

    # Text-based interactions (more reliable for dynamic pages)
    def click_text(self, text: str, element_type: str = "any", exact: bool = False) -> dict:
        """Click an element by its visible text content.
        
        Args:
            text: Text to search for
            element_type: Type of element ('any', 'button', 'link', 'heading')
            exact: Whether to require exact match
        """
        self._show_action_indicator(f"CLICK TEXT: {text}", element_type)
        
        try:
            if element_type == "button":
                locator = self.page.get_by_role("button", name=text, exact=exact)
            elif element_type == "link":
                locator = self.page.get_by_role("link", name=text, exact=exact)
            elif element_type == "heading":
                locator = self.page.get_by_role("heading", name=text, exact=exact)
            else:
                # Try multiple strategies
                locator = self.page.get_by_text(text, exact=exact)
            
            # Try clicking the first visible match
            locator.first.click(timeout=10000)
            return {"success": True, "text": text, "action": "click_text"}
            
        except Exception as e:
            # Fallback: JavaScript text search and click
            try:
                escaped_text = text.replace("'", "\\'").lower()
                self.page.evaluate(f'''
                    () => {{
                        const elements = document.querySelectorAll('a, button, [role="button"], input[type="submit"], h1, h2, h3, h4, span, div');
                        for (const el of elements) {{
                            const elText = (el.innerText || el.value || '').toLowerCase();
                            if (elText.includes('{escaped_text}')) {{
                                el.click();
                                return true;
                            }}
                        }}
                        return false;
                    }}
                ''')
                return {"success": True, "text": text, "action": "click_text", "method": "js_fallback"}
            except Exception as js_e:
                return {"success": False, "text": text, "error": str(e)}

    def click_nth(self, selector: str, index: int) -> dict:
        """Click the Nth element matching a selector.
        
        Args:
            selector: CSS selector
            index: 0-indexed position of element to click
        """
        self._show_action_indicator(f"CLICK #{index}", selector)
        
        try:
            locator = self.page.locator(selector).nth(index)
            locator.scroll_into_view_if_needed()
            locator.click(timeout=10000)
            return {"success": True, "selector": selector, "index": index, "action": "click_nth"}
        except Exception as e:
            # Try force click
            try:
                self.page.locator(selector).nth(index).click(force=True, timeout=5000)
                return {"success": True, "selector": selector, "index": index, "action": "click_nth", "method": "force"}
            except Exception:
                return {"success": False, "selector": selector, "index": index, "error": str(e)}

    def dismiss_overlays(self) -> dict:
        """Dismiss common popups, modals, cookie banners, and overlays."""
        self._show_action_indicator("DISMISS OVERLAYS", "")
        
        dismissed = []
        
        # Common close button selectors for various websites
        close_selectors = [
            # Generic close buttons (X icons)
            '[aria-label="Close"]',
            '[aria-label="close"]',
            '[aria-label="Dismiss"]',
            '[aria-label="Close dialog"]',
            '[aria-label="Close modal"]',
            'button[class*="close"]',
            'button[class*="Close"]',
            '[data-dismiss="modal"]',
            '[data-testid="close-button"]',
            '[data-testid="modal-close"]',
            '.modal-close',
            '.popup-close',
            '.overlay-close',
            '.dialog-close',
            '.btn-close',
            '.close-btn',
            '.close-button',
            # SVG/Icon close buttons
            'button svg[class*="close"]',
            'button[class*="close"] svg',
            '[class*="icon-close"]',
            '[class*="icon-x"]',
            '[class*="CloseIcon"]',
            # Cookie banners
            '[id*="cookie"] button',
            '[class*="cookie"] button',
            '[id*="consent"] button',
            '[class*="consent"] button[class*="accept"]',
            '[class*="consent"] button[class*="reject"]',
            '[class*="consent"] button[class*="decline"]',
            '[class*="gdpr"] button',
            '#onetrust-accept-btn-handler',
            '#onetrust-reject-btn-handler',
            '.cc-dismiss',
            '.cc-btn.cc-allow',
            '.cc-btn.cc-deny',
            '[data-cookie-accept]',
            '[data-cookie-reject]',
            # Newsletter/popup modals
            '[class*="newsletter"] button[class*="close"]',
            '[class*="popup"] button[class*="close"]',
            '[class*="modal"] button[class*="close"]',
            '[class*="dialog"] button[class*="close"]',
            '[class*="Modal"] button[class*="close"]',
            '[class*="Popup"] button[class*="close"]',
            # Dismiss/Skip/No thanks buttons
            'button[class*="dismiss"]',
            'button[class*="skip"]',
            'button[class*="cancel"]',
            '[class*="modal"] button[class*="no"]',
            '[class*="modal"] button[class*="later"]',
        ]
        
        # Text-based buttons to try clicking
        dismiss_texts = [
            "No thanks",
            "No, thanks", 
            "Maybe later",
            "Not now",
            "Skip",
            "Dismiss",
            "Close",
            "Got it",
            "I understand",
            "Accept",
            "Accept all",
            "Reject all",
            "Decline",
            "Continue",
            "OK",
            "×",  # X symbol
        ]
        
        # Try selector-based dismissal first
        for selector in close_selectors:
            try:
                locator = self.page.locator(selector).first
                if locator.is_visible(timeout=500):
                    locator.click(timeout=2000, force=True)
                    dismissed.append(selector)
                    self.page.wait_for_timeout(300)  # Brief pause after dismiss
            except Exception:
                pass
        
        # Try text-based dismissal
        for text in dismiss_texts:
            try:
                # Look for buttons/links with this text
                locator = self.page.get_by_role("button", name=text, exact=False)
                if locator.first.is_visible(timeout=300):
                    locator.first.click(timeout=1000, force=True)
                    dismissed.append(f"button:{text}")
                    self.page.wait_for_timeout(300)
                    break  # Stop after one successful text dismiss
            except Exception:
                pass
        
        # Press Escape key to dismiss any remaining modals
        try:
            self.page.keyboard.press("Escape")
            dismissed.append("Escape key")
            self.page.wait_for_timeout(200)
        except Exception:
            pass
        
        # Click outside modals (on body) and remove overlays via JS
        try:
            self.page.evaluate('''
                () => {
                    // Remove common overlay/backdrop elements
                    const overlaySelectors = [
                        '.modal-backdrop',
                        '.overlay',
                        '.popup-overlay',
                        '[class*="backdrop"]',
                        '[class*="Backdrop"]',
                        '[class*="Overlay"]',
                        '[class*="modal-bg"]',
                        '[class*="modal-mask"]',
                        '[role="presentation"]',
                    ];
                    overlaySelectors.forEach(sel => {
                        document.querySelectorAll(sel).forEach(el => {
                            // Try to hide or remove
                            if (el.style) {
                                el.style.display = 'none';
                                el.style.visibility = 'hidden';
                                el.style.opacity = '0';
                                el.style.pointerEvents = 'none';
                            }
                        });
                    });
                    
                    // Also try to close modals by removing aria-modal
                    document.querySelectorAll('[aria-modal="true"]').forEach(modal => {
                        const closeBtn = modal.querySelector('[aria-label*="close"], [aria-label*="Close"], button[class*="close"]');
                        if (closeBtn) closeBtn.click();
                    });
                    
                    // Re-enable body scrolling if disabled
                    document.body.style.overflow = 'auto';
                    document.body.style.position = '';
                    document.documentElement.style.overflow = 'auto';
                }
            ''')
            dismissed.append("js_overlay_removal")
        except Exception:
            pass
        
        return {
            "success": True,
            "dismissed": dismissed,
            "count": len(dismissed),
            "action": "dismiss_overlays"
        }

    def extract_modal_content(self) -> dict:
        """Extract content from any visible modal, popup, or dialog.
        
        Returns text content, buttons, inputs, and links from the modal.
        """
        self._show_action_indicator("EXTRACT MODAL", "")
        
        script = '''
            () => {
                // Find visible modals using common patterns
                const modalSelectors = [
                    '[role="dialog"]',
                    '[role="alertdialog"]',
                    '[aria-modal="true"]',
                    '.modal:not([style*="display: none"])',
                    '.modal.show',
                    '.modal.active',
                    '.modal.open',
                    '[class*="modal"]:not([style*="display: none"])',
                    '[class*="Modal"]:not([style*="display: none"])',
                    '.popup:not([style*="display: none"])',
                    '[class*="popup"]:not([style*="display: none"])',
                    '[class*="Popup"]:not([style*="display: none"])',
                    '.dialog:not([style*="display: none"])',
                    '[class*="dialog"]:not([style*="display: none"])',
                    '[class*="Dialog"]:not([style*="display: none"])',
                    '.overlay-content',
                    '[class*="drawer"]:not([style*="display: none"])',
                    '[class*="Drawer"]:not([style*="display: none"])',
                ];
                
                let modal = null;
                for (const sel of modalSelectors) {
                    const candidates = document.querySelectorAll(sel);
                    for (const el of candidates) {
                        // Check if truly visible
                        const rect = el.getBoundingClientRect();
                        const style = window.getComputedStyle(el);
                        if (rect.width > 0 && rect.height > 0 && 
                            style.display !== 'none' && 
                            style.visibility !== 'hidden' &&
                            style.opacity !== '0') {
                            modal = el;
                            break;
                        }
                    }
                    if (modal) break;
                }
                
                if (!modal) {
                    return { found: false, message: "No visible modal found" };
                }
                
                // Extract modal content
                const result = {
                    found: true,
                    title: '',
                    text: '',
                    buttons: [],
                    links: [],
                    inputs: [],
                    images: []
                };
                
                // Get title (h1, h2, h3, or aria-labelledby)
                const titleEl = modal.querySelector('h1, h2, h3, [class*="title"], [class*="header"] h1, [class*="header"] h2');
                if (titleEl) {
                    result.title = titleEl.innerText?.trim() || '';
                }
                
                // Get all text content (cleaned)
                result.text = modal.innerText?.trim().slice(0, 2000) || '';
                
                // Get buttons
                modal.querySelectorAll('button, input[type="submit"], input[type="button"], [role="button"]').forEach((btn, i) => {
                    if (i >= 10) return;
                    const text = (btn.innerText || btn.value || '').trim();
                    if (text) {
                        result.buttons.push({
                            text: text.slice(0, 50),
                            id: btn.id || '',
                            class: btn.className?.split(' ').slice(0, 2).join(' ') || ''
                        });
                    }
                });
                
                // Get links
                modal.querySelectorAll('a[href]').forEach((a, i) => {
                    if (i >= 10) return;
                    result.links.push({
                        text: (a.innerText || '').trim().slice(0, 50),
                        href: a.href?.slice(0, 100) || ''
                    });
                });
                
                // Get form inputs
                modal.querySelectorAll('input:not([type="hidden"]), textarea, select').forEach((input, i) => {
                    if (i >= 10) return;
                    result.inputs.push({
                        type: input.type || input.tagName.toLowerCase(),
                        name: input.name || '',
                        id: input.id || '',
                        placeholder: input.placeholder || '',
                        value: input.value?.slice(0, 50) || ''
                    });
                });
                
                // Get images (useful for product modals)
                modal.querySelectorAll('img').forEach((img, i) => {
                    if (i >= 5) return;
                    result.images.push({
                        src: img.src?.slice(0, 150) || '',
                        alt: img.alt || ''
                    });
                });
                
                return result;
            }
        '''
        
        try:
            content = self.page.evaluate(script)
            return {
                "success": True,
                "modal": content,
                "action": "extract_modal_content"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "action": "extract_modal_content"
            }

    def find_and_click(self, target: str, scroll_first: bool = True) -> dict:
        """Smart click that tries multiple strategies.
        
        Args:
            target: Text content or CSS selector
            scroll_first: Whether to scroll down first
        """
        self._show_action_indicator(f"FIND & CLICK: {target}", "")
        
        # First, try to dismiss any overlays
        self.dismiss_overlays()
        
        # Optional scroll
        if scroll_first:
            try:
                self.page.evaluate("window.scrollBy(0, 300)")
            except Exception:
                pass
        
        # Strategy 1: Try as text (most reliable for buttons/links)
        try:
            result = self.click_text(target, element_type="any", exact=False)
            if result.get("success"):
                return {**result, "strategy": "text_match"}
        except Exception:
            pass
        
        # Strategy 2: Try as CSS selector
        try:
            self.page.click(target, timeout=5000)
            return {"success": True, "target": target, "action": "find_and_click", "strategy": "selector"}
        except Exception:
            pass
        
        # Strategy 3: Try with force click
        try:
            self.page.click(target, timeout=5000, force=True)
            return {"success": True, "target": target, "action": "find_and_click", "strategy": "force_selector"}
        except Exception:
            pass
        
        # Strategy 4: JavaScript click by text content
        try:
            escaped = target.replace("'", "\\'").lower()
            clicked = self.page.evaluate(f'''
                () => {{
                    const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
                    while (walk.nextNode()) {{
                        const el = walk.currentNode;
                        const text = (el.innerText || el.textContent || '').toLowerCase();
                        if (text.includes('{escaped}') && el.offsetWidth > 0) {{
                            el.scrollIntoView({{block: 'center'}});
                            el.click();
                            return true;
                        }}
                    }}
                    return false;
                }}
            ''')
            if clicked:
                return {"success": True, "target": target, "action": "find_and_click", "strategy": "js_text_walk"}
        except Exception:
            pass
        
        return {"success": False, "target": target, "error": "Could not find or click target with any strategy"}


class AsyncBrowserAdapter:
    """Adapter to run SyncBrowserWrapper in async context using thread pool."""
    
    def __init__(
        self,
        headless: bool = True,
        viewport_width: int = 1280,
        viewport_height: int = 720,
        timeout: int = 30000,
    ) -> None:
        """Initialize the adapter."""
        self.headless = headless
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.timeout = timeout
        self._browser: Optional[SyncBrowserWrapper] = None
        self._executor = ThreadPoolExecutor(max_workers=1)

    async def _run_sync(self, func: Callable, *args, **kwargs) -> Any:
        """Run a sync function in the thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            partial(func, *args, **kwargs)
        )

    async def __aenter__(self) -> "AsyncBrowserAdapter":
        """Async context manager entry."""
        await self.launch()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    async def launch(self) -> None:
        """Launch browser in thread."""
        self._browser = SyncBrowserWrapper(
            headless=self.headless,
            viewport_width=self.viewport_width,
            viewport_height=self.viewport_height,
            timeout=self.timeout,
        )
        await self._run_sync(self._browser.launch)

    async def close(self) -> None:
        """Close browser and cleanup."""
        if self._browser:
            await self._run_sync(self._browser.close)
            self._browser = None
        self._executor.shutdown(wait=False)

    @property
    def browser(self) -> SyncBrowserWrapper:
        """Get the underlying sync browser."""
        if not self._browser:
            raise RuntimeError("Browser not launched.")
        return self._browser

    # Navigation
    async def goto(self, url: str, wait_until: str = "domcontentloaded") -> dict:
        return await self._run_sync(self.browser.goto, url, wait_until)

    async def go_back(self) -> dict:
        return await self._run_sync(self.browser.go_back)

    async def go_forward(self) -> dict:
        return await self._run_sync(self.browser.go_forward)

    async def reload(self) -> dict:
        return await self._run_sync(self.browser.reload)

    # Interactions
    async def click(self, selector: str, button: str = "left", click_count: int = 1) -> dict:
        return await self._run_sync(self.browser.click, selector, button, click_count)

    async def double_click(self, selector: str) -> dict:
        return await self._run_sync(self.browser.double_click, selector)

    async def fill(self, selector: str, value: str) -> dict:
        return await self._run_sync(self.browser.fill, selector, value)

    async def type_text(self, selector: str, text: str, delay: int = 50) -> dict:
        return await self._run_sync(self.browser.type_text, selector, text, delay)

    async def press_key(self, key: str, selector: Optional[str] = None) -> dict:
        return await self._run_sync(self.browser.press_key, key, selector)

    async def hover(self, selector: str) -> dict:
        return await self._run_sync(self.browser.hover, selector)

    async def select_option(self, selector: str, value: Optional[str] = None, label: Optional[str] = None) -> dict:
        return await self._run_sync(self.browser.select_option, selector, value, label)

    async def check(self, selector: str) -> dict:
        return await self._run_sync(self.browser.check, selector)

    async def uncheck(self, selector: str) -> dict:
        return await self._run_sync(self.browser.uncheck, selector)

    # Waiting
    async def wait_for_selector(self, selector: str, state: str = "visible", timeout: Optional[int] = None) -> dict:
        return await self._run_sync(self.browser.wait_for_selector, selector, state, timeout)

    async def wait_for_navigation(self, wait_until: str = "domcontentloaded", timeout: Optional[int] = None) -> dict:
        return await self._run_sync(self.browser.wait_for_navigation, wait_until, timeout)

    async def wait_for_timeout(self, timeout: int) -> dict:
        return await self._run_sync(self.browser.wait_for_timeout, timeout)

    # Extraction
    async def get_text(self, selector: str) -> dict:
        return await self._run_sync(self.browser.get_text, selector)

    async def get_inner_text(self, selector: str) -> dict:
        return await self._run_sync(self.browser.get_inner_text, selector)

    async def get_attribute(self, selector: str, attribute: str) -> dict:
        return await self._run_sync(self.browser.get_attribute, selector, attribute)

    async def get_value(self, selector: str) -> dict:
        return await self._run_sync(self.browser.get_value, selector)

    async def get_page_content(self) -> dict:
        return await self._run_sync(self.browser.get_page_content)

    async def get_page_title(self) -> dict:
        return await self._run_sync(self.browser.get_page_title)

    async def get_current_url(self) -> dict:
        return await self._run_sync(self.browser.get_current_url)

    # Screenshots
    async def screenshot(self, full_page: bool = False) -> dict:
        return await self._run_sync(self.browser.screenshot, full_page)

    async def screenshot_element(self, selector: str) -> dict:
        return await self._run_sync(self.browser.screenshot_element, selector)

    # JavaScript
    async def evaluate(self, expression: str) -> dict:
        return await self._run_sync(self.browser.evaluate, expression)

    # Scrolling
    async def scroll_to(self, x: int = 0, y: int = 0) -> dict:
        return await self._run_sync(self.browser.scroll_to, x, y)

    async def scroll_by(self, x: int = 0, y: int = 0) -> dict:
        return await self._run_sync(self.browser.scroll_by, x, y)

    async def scroll_to_element(self, selector: str) -> dict:
        return await self._run_sync(self.browser.scroll_to_element, selector)

    async def scroll_page(self, direction: str = "down", amount: int = 500) -> dict:
        return await self._run_sync(self.browser.scroll_page, direction, amount)

    # Structure
    async def get_page_structure(self, max_depth: int = 5) -> dict:
        return await self._run_sync(self.browser.get_page_structure, max_depth)

    async def get_all_links(self) -> dict:
        return await self._run_sync(self.browser.get_all_links)

    async def get_all_inputs(self) -> dict:
        return await self._run_sync(self.browser.get_all_inputs)

    async def get_all_buttons(self) -> dict:
        return await self._run_sync(self.browser.get_all_buttons)

    async def is_visible(self, selector: str) -> dict:
        return await self._run_sync(self.browser.is_visible, selector)

    async def count_elements(self, selector: str) -> dict:
        return await self._run_sync(self.browser.count_elements, selector)

    async def get_bounding_box(self, selector: str) -> dict:
        return await self._run_sync(self.browser.get_bounding_box, selector)

    # New text-based and smart click methods
    async def click_text(self, text: str, element_type: str = "any", exact: bool = False) -> dict:
        return await self._run_sync(self.browser.click_text, text, element_type, exact)

    async def click_nth(self, selector: str, index: int) -> dict:
        return await self._run_sync(self.browser.click_nth, selector, index)

    async def dismiss_overlays(self) -> dict:
        return await self._run_sync(self.browser.dismiss_overlays)

    async def extract_modal_content(self) -> dict:
        return await self._run_sync(self.browser.extract_modal_content)

    async def find_and_click(self, target: str, scroll_first: bool = True) -> dict:
        return await self._run_sync(self.browser.find_and_click, target, scroll_first)
