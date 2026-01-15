"""Code generation service using Jinja2 templates."""

import re
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from browser_agent.models import CodeGenRequest, CodeGenResponse
from browser_agent.models.agent import Framework, Language
from browser_agent.models.codegen import TestStep


class CodeGenService:
    """Service for generating test code from test plans.
    
    Uses Jinja2 templates to generate executable Playwright test code
    in TypeScript, Python, or JavaScript.
    """

    def __init__(self, templates_dir: Optional[Path] = None) -> None:
        """Initialize the code generation service.
        
        Args:
            templates_dir: Path to the templates directory.
                          Defaults to the templates folder in this package.
        """
        if templates_dir is None:
            templates_dir = Path(__file__).parent.parent / "templates"
        
        self.templates_dir = templates_dir
        
        # Initialize Jinja2 environment if templates exist
        if templates_dir.exists():
            self.env = Environment(
                loader=FileSystemLoader(templates_dir),
                autoescape=select_autoescape(["html", "xml"]),
                trim_blocks=True,
                lstrip_blocks=True,
            )
        else:
            self.env = None

    async def generate(self, request: CodeGenRequest) -> CodeGenResponse:
        """Generate test code from a test plan.
        
        Args:
            request: The code generation request containing the test plan.
            
        Returns:
            CodeGenResponse: The generated code and suggested filename.
        """
        code = self._generate_code(request.test_plan, request.framework, request.language)
        filename = self._generate_filename(request.test_plan, request.language)
        
        return CodeGenResponse(code=code, filename=filename)

    def _generate_code(
        self,
        test_plan: list[TestStep],
        framework: Framework,
        language: Language,
    ) -> str:
        """Generate test code for the given test plan.
        
        Args:
            test_plan: List of test steps to generate code for.
            framework: Target automation framework.
            language: Target programming language.
            
        Returns:
            str: Generated test code.
        """
        # Use template if available
        template_name = f"{framework.value}_{language.value}.jinja2"
        if self.env and (self.templates_dir / template_name).exists():
            template = self.env.get_template(template_name)
            return template.render(steps=test_plan)
        
        # Fall back to inline generation
        return self._generate_inline(test_plan, framework, language)

    def _generate_inline(
        self,
        test_plan: list[TestStep],
        framework: Framework,
        language: Language,
    ) -> str:
        """Generate test code inline without templates.
        
        This is used as a fallback when templates are not available.
        """
        if language == Language.TYPESCRIPT:
            return self._generate_typescript(test_plan)
        elif language == Language.PYTHON:
            return self._generate_python(test_plan)
        else:
            return self._generate_javascript(test_plan)

    def _generate_typescript(self, test_plan: list[TestStep]) -> str:
        """Generate TypeScript Playwright test code."""
        steps_code = []
        for step in test_plan:
            steps_code.append(self._step_to_typescript(step))
        
        steps_str = "\n  ".join(steps_code)
        
        return f'''import {{ test, expect }} from '@playwright/test';

test('generated test', async ({{ page }}) => {{
  {steps_str}
}});
'''

    def _generate_python(self, test_plan: list[TestStep]) -> str:
        """Generate Python Playwright test code."""
        steps_code = []
        for step in test_plan:
            steps_code.append(self._step_to_python(step))
        
        steps_str = "\n    ".join(steps_code)
        
        return f'''import pytest
from playwright.sync_api import Page, expect

def test_generated(page: Page):
    """Generated Playwright test."""
    {steps_str}
'''

    def _generate_javascript(self, test_plan: list[TestStep]) -> str:
        """Generate JavaScript Playwright test code."""
        steps_code = []
        for step in test_plan:
            steps_code.append(self._step_to_javascript(step))
        
        steps_str = "\n  ".join(steps_code)
        
        return f'''const {{ test, expect }} = require('@playwright/test');

test('generated test', async ({{ page }}) => {{
  {steps_str}
}});
'''

    def _step_to_typescript(self, step: TestStep) -> str:
        """Convert a test step to TypeScript code."""
        action = step.action.lower()
        
        # Helper to escape strings for JS
        def escape(s: str) -> str:
            if s is None:
                return ""
            return s.replace("\\", "\\\\").replace("'", "\\'")
        
        selector = escape(step.selector) if step.selector else ""
        value = escape(step.value) if step.value else ""
        
        if action == "navigate":
            return f"await page.goto('{value}');"
        elif action == "click":
            return f"await page.click('{selector}');"
        elif action == "click_text":
            return f"await page.getByText('{value}').click();"
        elif action == "click_nth":
            index = step.value or "0"
            return f"await page.locator('{selector}').nth({index}).click();"
        elif action == "double_click":
            return f"await page.dblclick('{selector}');"
        elif action == "fill":
            return f"await page.fill('{selector}', '{value}');"
        elif action == "type":
            return f"await page.type('{selector}', '{value}');"
        elif action == "press":
            if selector:
                return f"await page.press('{selector}', '{value}');"
            return f"await page.keyboard.press('{value}');"
        elif action == "hover":
            return f"await page.hover('{selector}');"
        elif action == "select":
            return f"await page.selectOption('{selector}', '{value}');"
        elif action == "check":
            return f"await page.check('{selector}');"
        elif action == "uncheck":
            return f"await page.uncheck('{selector}');"
        elif action == "scroll":
            if value and ":" in value:
                direction, amount = value.split(":", 1)
                amount = int(amount) if amount.isdigit() else 500
                if direction == "up":
                    return f"await page.mouse.wheel(0, -{amount});"
                return f"await page.mouse.wheel(0, {amount});"
            return "await page.mouse.wheel(0, 500);"
        elif action == "scroll_to":
            return f"await page.locator('{selector}').scrollIntoViewIfNeeded();"
        elif action == "wait":
            timeout = value if value and value.isdigit() else "1000"
            return f"await page.waitForTimeout({timeout});"
        elif action == "wait_for":
            if step.expected == "visible":
                return f"await page.locator('{selector}').waitFor({{ state: 'visible' }});"
            return f"await page.waitForSelector('{selector}');"
        elif action == "assert" or action == "expect":
            if step.expected:
                return f"await expect(page.locator('{selector}')).toContainText('{escape(step.expected)}');"
            return f"await expect(page.locator('{selector}')).toBeVisible();"
        else:
            return f"// Unknown action: {action}"

    def _step_to_python(self, step: TestStep) -> str:
        """Convert a test step to Python code."""
        action = step.action.lower()
        
        # Helper to escape strings for Python
        def escape(s: str) -> str:
            if s is None:
                return ""
            return s.replace("\\", "\\\\").replace('"', '\\"')
        
        selector = escape(step.selector) if step.selector else ""
        value = escape(step.value) if step.value else ""
        
        if action == "navigate":
            return f'page.goto("{value}")'
        elif action == "click":
            return f'page.click("{selector}")'
        elif action == "click_text":
            return f'page.get_by_text("{value}").click()'
        elif action == "click_nth":
            index = step.value or "0"
            return f'page.locator("{selector}").nth({index}).click()'
        elif action == "double_click":
            return f'page.dblclick("{selector}")'
        elif action == "fill":
            return f'page.fill("{selector}", "{value}")'
        elif action == "type":
            return f'page.type("{selector}", "{value}")'
        elif action == "press":
            if selector:
                return f'page.press("{selector}", "{value}")'
            return f'page.keyboard.press("{value}")'
        elif action == "hover":
            return f'page.hover("{selector}")'
        elif action == "select":
            return f'page.select_option("{selector}", "{value}")'
        elif action == "check":
            return f'page.check("{selector}")'
        elif action == "uncheck":
            return f'page.uncheck("{selector}")'
        elif action == "scroll":
            if value and ":" in value:
                direction, amount = value.split(":", 1)
                amount = int(amount) if amount.isdigit() else 500
                if direction == "up":
                    return f'page.mouse.wheel(0, -{amount})'
                return f'page.mouse.wheel(0, {amount})'
            return 'page.mouse.wheel(0, 500)'
        elif action == "scroll_to":
            return f'page.locator("{selector}").scroll_into_view_if_needed()'
        elif action == "wait":
            timeout = value if value and value.isdigit() else "1000"
            return f'page.wait_for_timeout({timeout})'
        elif action == "wait_for":
            if step.expected == "visible":
                return f'page.locator("{selector}").wait_for(state="visible")'
            return f'page.wait_for_selector("{selector}")'
        elif action == "assert" or action == "expect":
            if step.expected:
                return f'expect(page.locator("{selector}")).to_contain_text("{escape(step.expected)}")'
            return f'expect(page.locator("{selector}")).to_be_visible()'
        else:
            return f"# Unknown action: {action}"

    def _step_to_javascript(self, step: TestStep) -> str:
        """Convert a test step to JavaScript code."""
        # JavaScript uses same syntax as TypeScript for Playwright
        return self._step_to_typescript(step)

    def _generate_filename(self, test_plan: list[TestStep], language: Language) -> str:
        """Generate a suggested filename for the test code."""
        # Try to extract a meaningful name from the first navigate action
        for step in test_plan:
            if step.action.lower() == "navigate" and step.value:
                # Extract domain or path
                url = step.value
                # Remove protocol
                url = re.sub(r'^https?://', '', url)
                # Get first part
                name = url.split('/')[0].split('.')[0]
                if name and name != "www":
                    break
        else:
            name = "generated"
        
        # Clean the name
        name = re.sub(r'[^a-zA-Z0-9]', '-', name.lower())
        name = re.sub(r'-+', '-', name).strip('-')
        
        # Add extension based on language
        extensions = {
            Language.TYPESCRIPT: ".spec.ts",
            Language.PYTHON: "_test.py",
            Language.JAVASCRIPT: ".spec.js",
        }
        
        return f"test-{name}{extensions.get(language, '.spec.ts')}"
