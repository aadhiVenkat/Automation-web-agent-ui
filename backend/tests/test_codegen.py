"""Tests for code generation service."""

import pytest

from browser_agent.models.agent import Framework, Language
from browser_agent.models.codegen import TestStep
from browser_agent.services.codegen import CodeGenService


@pytest.fixture
def codegen_service():
    """Create a code generation service instance."""
    return CodeGenService()


class TestCodeGenService:
    """Tests for CodeGenService."""

    def test_generate_typescript_navigate(self, codegen_service):
        """Test generating TypeScript navigate action."""
        steps = [TestStep(action="navigate", value="https://example.com")]
        code = codegen_service._generate_typescript(steps)
        
        assert "import { test, expect }" in code
        assert "await page.goto('https://example.com')" in code

    def test_generate_typescript_click(self, codegen_service):
        """Test generating TypeScript click action."""
        steps = [TestStep(action="click", selector="button#submit")]
        code = codegen_service._generate_typescript(steps)
        
        assert "await page.click('button#submit')" in code

    def test_generate_typescript_fill(self, codegen_service):
        """Test generating TypeScript fill action."""
        steps = [TestStep(action="fill", selector="input#email", value="test@example.com")]
        code = codegen_service._generate_typescript(steps)
        
        assert "await page.fill('input#email', 'test@example.com')" in code

    def test_generate_typescript_wait_visible(self, codegen_service):
        """Test generating TypeScript wait for visible action."""
        steps = [TestStep(action="wait", selector=".dashboard", expected="visible")]
        code = codegen_service._generate_typescript(steps)
        
        assert "waitFor({ state: 'visible' })" in code

    def test_generate_typescript_assert(self, codegen_service):
        """Test generating TypeScript assertion."""
        steps = [TestStep(action="assert", selector=".message", expected="Success")]
        code = codegen_service._generate_typescript(steps)
        
        assert "toContainText('Success')" in code

    def test_generate_python_navigate(self, codegen_service):
        """Test generating Python navigate action."""
        steps = [TestStep(action="navigate", value="https://example.com")]
        code = codegen_service._generate_python(steps)
        
        assert "import pytest" in code
        assert 'page.goto("https://example.com")' in code

    def test_generate_python_click(self, codegen_service):
        """Test generating Python click action."""
        steps = [TestStep(action="click", selector="button#submit")]
        code = codegen_service._generate_python(steps)
        
        assert 'page.click("button#submit")' in code

    def test_generate_python_fill(self, codegen_service):
        """Test generating Python fill action."""
        steps = [TestStep(action="fill", selector="input#email", value="test@example.com")]
        code = codegen_service._generate_python(steps)
        
        assert 'page.fill("input#email", "test@example.com")' in code

    def test_generate_filename_from_url(self, codegen_service):
        """Test filename generation from URL."""
        steps = [TestStep(action="navigate", value="https://example.com/login")]
        
        filename = codegen_service._generate_filename(steps, Language.TYPESCRIPT)
        assert filename == "test-example.spec.ts"
        
        filename = codegen_service._generate_filename(steps, Language.PYTHON)
        assert filename == "test-example_test.py"
        
        filename = codegen_service._generate_filename(steps, Language.JAVASCRIPT)
        assert filename == "test-example.spec.js"

    def test_generate_filename_fallback(self, codegen_service):
        """Test filename generation fallback when no URL."""
        steps = [TestStep(action="click", selector="button")]
        
        filename = codegen_service._generate_filename(steps, Language.TYPESCRIPT)
        assert filename == "test-generated.spec.ts"

    def test_step_to_typescript_unknown_action(self, codegen_service):
        """Test handling unknown action in TypeScript generation."""
        step = TestStep(action="unknown", selector="test")
        code = codegen_service._step_to_typescript(step)
        
        assert "// Unknown action: unknown" in code

    def test_step_to_python_unknown_action(self, codegen_service):
        """Test handling unknown action in Python generation."""
        step = TestStep(action="unknown", selector="test")
        code = codegen_service._step_to_python(step)
        
        assert "# Unknown action: unknown" in code
