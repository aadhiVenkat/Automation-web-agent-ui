"""Tests for Pydantic models."""

import pytest
from datetime import datetime

from browser_agent.models import AgentEvent, AgentRequest, CodeGenRequest, CodeGenResponse
from browser_agent.models.agent import EventType, Framework, Language, LLMProvider
from browser_agent.models.codegen import TestStep


class TestAgentRequest:
    """Tests for AgentRequest model."""

    def test_valid_request(self):
        """Test creating a valid agent request."""
        request = AgentRequest(
            apiKey="test-key",
            provider="gemini",
            url="https://example.com",
            task="Click the login button",
            framework="playwright",
            language="typescript",
        )
        assert request.api_key == "test-key"
        assert request.provider == LLMProvider.GEMINI
        assert request.url == "https://example.com"
        assert request.task == "Click the login button"
        assert request.framework == Framework.PLAYWRIGHT
        assert request.language == Language.TYPESCRIPT

    def test_default_values(self):
        """Test default values are applied."""
        request = AgentRequest(
            apiKey="test-key",
            provider="perplexity",
            url="https://test.com",
            task="Do something",
        )
        assert request.framework == Framework.PLAYWRIGHT
        assert request.language == Language.TYPESCRIPT

    def test_invalid_provider(self):
        """Test that invalid provider raises validation error."""
        with pytest.raises(ValueError):
            AgentRequest(
                apiKey="test-key",
                provider="invalid",
                url="https://example.com",
                task="Test task",
            )

    def test_empty_api_key_rejected(self):
        """Test that empty API key is rejected."""
        with pytest.raises(ValueError):
            AgentRequest(
                apiKey="",
                provider="gemini",
                url="https://example.com",
                task="Test task",
            )


class TestAgentEvent:
    """Tests for AgentEvent model."""

    def test_log_event(self):
        """Test creating a log event."""
        event = AgentEvent(
            type=EventType.LOG,
            message="Test message",
        )
        assert event.type == EventType.LOG
        assert event.message == "Test message"
        assert event.screenshot is None
        assert event.code is None
        assert isinstance(event.timestamp, datetime)

    def test_screenshot_event(self):
        """Test creating a screenshot event."""
        event = AgentEvent(
            type=EventType.SCREENSHOT,
            screenshot="base64-data",
        )
        assert event.type == EventType.SCREENSHOT
        assert event.screenshot == "base64-data"

    def test_code_event(self):
        """Test creating a code event."""
        event = AgentEvent(
            type=EventType.CODE,
            code="const test = 1;",
        )
        assert event.type == EventType.CODE
        assert event.code == "const test = 1;"


class TestCodeGenRequest:
    """Tests for CodeGenRequest model."""

    def test_valid_request(self):
        """Test creating a valid code generation request."""
        request = CodeGenRequest(
            testPlan=[
                {"action": "navigate", "value": "https://example.com"},
                {"action": "click", "selector": "button#login"},
            ],
            framework="playwright",
            language="typescript",
        )
        assert len(request.test_plan) == 2
        assert request.test_plan[0].action == "navigate"
        assert request.framework == Framework.PLAYWRIGHT
        assert request.language == Language.TYPESCRIPT

    def test_empty_test_plan_rejected(self):
        """Test that empty test plan is rejected."""
        with pytest.raises(ValueError):
            CodeGenRequest(testPlan=[])


class TestTestStep:
    """Tests for TestStep model."""

    def test_navigate_step(self):
        """Test creating a navigate step."""
        step = TestStep(action="navigate", value="https://example.com")
        assert step.action == "navigate"
        assert step.value == "https://example.com"
        assert step.selector is None

    def test_click_step(self):
        """Test creating a click step."""
        step = TestStep(action="click", selector="button#submit")
        assert step.action == "click"
        assert step.selector == "button#submit"

    def test_fill_step(self):
        """Test creating a fill step."""
        step = TestStep(action="fill", selector="input#email", value="test@example.com")
        assert step.action == "fill"
        assert step.selector == "input#email"
        assert step.value == "test@example.com"


class TestCodeGenResponse:
    """Tests for CodeGenResponse model."""

    def test_response_creation(self):
        """Test creating a code generation response."""
        response = CodeGenResponse(
            code="const test = 1;",
            filename="test-example.spec.ts",
        )
        assert response.code == "const test = 1;"
        assert response.filename == "test-example.spec.ts"
