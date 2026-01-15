"""Tests for API routes."""

import pytest
from fastapi.testclient import TestClient

from browser_agent.main import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    def test_health_check(self, client):
        """Test that health check returns healthy status."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "timestamp" in data


class TestGenerateCodeEndpoint:
    """Tests for the code generation endpoint."""

    def test_generate_typescript_code(self, client):
        """Test generating TypeScript code."""
        payload = {
            "testPlan": [
                {"action": "navigate", "value": "https://example.com"},
                {"action": "click", "selector": "button#login"},
            ],
            "framework": "playwright",
            "language": "typescript",
        }
        response = client.post("/api/generate-code", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "code" in data
        assert "filename" in data
        assert "import { test, expect }" in data["code"]
        assert data["filename"].endswith(".spec.ts")

    def test_generate_python_code(self, client):
        """Test generating Python code."""
        payload = {
            "testPlan": [
                {"action": "navigate", "value": "https://example.com"},
            ],
            "framework": "playwright",
            "language": "python",
        }
        response = client.post("/api/generate-code", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "import pytest" in data["code"]
        assert data["filename"].endswith("_test.py")

    def test_generate_javascript_code(self, client):
        """Test generating JavaScript code."""
        payload = {
            "testPlan": [
                {"action": "navigate", "value": "https://example.com"},
            ],
            "framework": "playwright",
            "language": "javascript",
        }
        response = client.post("/api/generate-code", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "require('@playwright/test')" in data["code"]
        assert data["filename"].endswith(".spec.js")

    def test_empty_test_plan_rejected(self, client):
        """Test that empty test plan is rejected."""
        payload = {
            "testPlan": [],
            "framework": "playwright",
            "language": "typescript",
        }
        response = client.post("/api/generate-code", json=payload)
        assert response.status_code == 422

    def test_invalid_language_rejected(self, client):
        """Test that invalid language is rejected."""
        payload = {
            "testPlan": [{"action": "navigate", "value": "https://example.com"}],
            "language": "invalid",
        }
        response = client.post("/api/generate-code", json=payload)
        assert response.status_code == 422


class TestAgentEndpoint:
    """Tests for the agent endpoint."""

    def test_agent_endpoint_returns_sse(self, client):
        """Test that agent endpoint returns SSE stream."""
        payload = {
            "apiKey": "test-key",
            "provider": "gemini",
            "url": "https://example.com",
            "task": "Click the button",
        }
        response = client.post(
            "/api/agent",
            json=payload,
            headers={"Accept": "text/event-stream"},
        )
        # SSE responses return 200
        assert response.status_code == 200
        # Content type should be event-stream
        assert "text/event-stream" in response.headers.get("content-type", "")

    def test_agent_invalid_provider_rejected(self, client):
        """Test that invalid provider is rejected."""
        payload = {
            "apiKey": "test-key",
            "provider": "invalid-provider",
            "url": "https://example.com",
            "task": "Click the button",
        }
        response = client.post("/api/agent", json=payload)
        assert response.status_code == 422

    def test_agent_missing_fields_rejected(self, client):
        """Test that missing required fields are rejected."""
        payload = {
            "apiKey": "test-key",
            # Missing provider, url, task
        }
        response = client.post("/api/agent", json=payload)
        assert response.status_code == 422
