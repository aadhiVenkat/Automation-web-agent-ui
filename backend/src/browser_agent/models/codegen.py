"""Code generation Pydantic models."""

from typing import Any, Optional

from pydantic import BaseModel, Field

from browser_agent.models.agent import Framework, Language


class TestStep(BaseModel):
    """A single step in a test plan."""

    action: str = Field(
        ...,
        description="Action to perform (e.g., click, fill, navigate, wait)",
    )
    selector: Optional[str] = Field(
        default=None,
        description="CSS/XPath selector for the target element",
    )
    value: Optional[str] = Field(
        default=None,
        description="Value to use (e.g., text to fill, URL to navigate to)",
    )
    expected: Optional[str] = Field(
        default=None,
        description="Expected result or assertion",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "action": "navigate",
                    "value": "https://example.com",
                },
                {
                    "action": "click",
                    "selector": "button#login",
                },
                {
                    "action": "fill",
                    "selector": "input[name='email']",
                    "value": "test@example.com",
                },
                {
                    "action": "wait",
                    "selector": ".dashboard",
                    "expected": "visible",
                },
            ]
        }
    }


class CodeGenRequest(BaseModel):
    """Request model for the /api/generate-code endpoint."""

    test_plan: list[TestStep] = Field(
        ...,
        alias="testPlan",
        description="List of test steps to generate code for",
        min_length=1,
    )
    framework: Framework = Field(
        default=Framework.PLAYWRIGHT,
        description="Automation framework to generate code for",
    )
    language: Language = Field(
        default=Language.TYPESCRIPT,
        description="Programming language for the generated code",
    )

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "examples": [
                {
                    "testPlan": [
                        {"action": "navigate", "value": "https://example.com"},
                        {"action": "click", "selector": "button#login"},
                        {
                            "action": "fill",
                            "selector": "input[name='email']",
                            "value": "test@example.com",
                        },
                    ],
                    "framework": "playwright",
                    "language": "typescript",
                }
            ]
        },
    }


class CodeGenResponse(BaseModel):
    """Response model for the /api/generate-code endpoint."""

    code: str = Field(
        ...,
        description="Generated test code",
    )
    filename: str = Field(
        ...,
        description="Suggested filename for the generated code",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "code": "import { test, expect } from '@playwright/test';\\n\\ntest('example test', async ({ page }) => {\\n  await page.goto('https://example.com');\\n});",
                    "filename": "test-example.spec.ts",
                }
            ]
        }
    }
