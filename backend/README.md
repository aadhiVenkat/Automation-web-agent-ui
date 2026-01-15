# 🤖 Browser Agent Backend

A powerful FastAPI backend for the Browser Agent Platform that enables AI-powered browser automation and Playwright test code generation.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Development](#development)
- [Testing](#testing)
- [Docker](#docker)
- [Troubleshooting](#troubleshooting)

## 🎯 Overview

The Browser Agent Backend is a FastAPI-based service that orchestrates AI-powered browser automation. It takes natural language instructions, uses LLMs (Large Language Models) to plan and execute browser actions, and generates production-ready Playwright test code.

### How It Works

1. **User Input**: Receive natural language task descriptions and target URLs
2. **LLM Planning**: AI models plan the necessary browser actions
3. **Browser Execution**: Playwright executes actions in a real browser
4. **Code Generation**: Automatically generates reusable Playwright test code
5. **Real-time Streaming**: Stream progress, screenshots, and results via SSE

## ✨ Features

- **🧠 Multi-LLM Support**: Integrates with Google Gemini, Perplexity AI, and HuggingFace
- **🌐 Browser Automation**: Headless/headful browser control via Playwright
- **📸 Real-time Screenshots**: Capture and stream browser screenshots
- **📝 Code Generation**: Generate Playwright tests in TypeScript, Python, or JavaScript
- **🔄 Server-Sent Events**: Real-time streaming of logs, screenshots, and code
- **🔒 Security**: API key management with multiple authentication methods
- **⚡ Rate Limiting**: Configurable rate limiting per endpoint
- **🐳 Docker Support**: Production-ready Docker configuration

## 🏗️ Architecture

```
backend/
├── src/
│   └── browser_agent/
│       ├── __init__.py          # Package initialization & version
│       ├── main.py              # FastAPI application entry point
│       ├── config.py            # Application settings (pydantic-settings)
│       ├── logging.py           # Logging configuration
│       ├── ratelimit.py         # Rate limiting configuration
│       ├── security.py          # API key & security utilities
│       │
│       ├── api/
│       │   ├── __init__.py
│       │   └── routes.py        # API endpoint definitions
│       │
│       ├── core/
│       │   ├── __init__.py
│       │   ├── agent.py         # Agent orchestration logic
│       │   ├── browser.py       # Async Playwright browser wrapper
│       │   └── sync_browser.py  # Sync Playwright browser wrapper
│       │
│       ├── llm/
│       │   ├── __init__.py
│       │   ├── base.py          # Base LLM interface
│       │   ├── gemini.py        # Google Gemini integration
│       │   ├── perplexity.py    # Perplexity AI integration
│       │   ├── huggingface.py   # HuggingFace integration
│       │   └── retry.py         # Retry logic for LLM calls
│       │
│       ├── models/
│       │   ├── __init__.py
│       │   ├── agent.py         # Agent request/response models
│       │   └── codegen.py       # Code generation models
│       │
│       ├── services/
│       │   ├── __init__.py
│       │   ├── agent.py         # Agent service implementation
│       │   └── codegen.py       # Code generation service
│       │
│       ├── templates/
│       │   ├── playwright_typescript.jinja2
│       │   ├── playwright_python.jinja2
│       │   └── playwright_javascript.jinja2
│       │
│       └── tools/
│           ├── __init__.py
│           ├── executor.py      # Tool execution logic
│           └── schemas.py       # Tool schemas for LLM
│
├── tests/
│   ├── __init__.py
│   ├── test_api.py              # API endpoint tests
│   ├── test_codegen.py          # Code generation tests
│   └── test_models.py           # Model validation tests
│
├── debugger.py                  # Debug utilities
├── Dockerfile                   # Docker configuration
├── pyproject.toml               # Project configuration & dependencies
└── README.md                    # This file
```

## 🚀 Installation

### Prerequisites

- Python 3.11 or higher
- pip or uv package manager

### Local Development Setup

1. **Clone the repository and navigate to backend:**
   ```bash
   cd backend
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv .venv
   
   # On Windows:
   .venv\Scripts\activate
   
   # On macOS/Linux:
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   # Install with development dependencies
   pip install -e ".[dev]"
   ```

4. **Install Playwright browsers:**
   ```bash
   playwright install chromium
   ```

5. **Create environment file (optional):**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

6. **Run the development server:**
   ```bash
   uvicorn browser_agent.main:app --reload --host 0.0.0.0 --port 8000
   ```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the backend directory with the following variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `HOST` | Server host | `0.0.0.0` |
| `PORT` | Server port | `8000` |
| `DEBUG` | Enable debug mode | `false` |
| `CORS_ORIGINS` | Allowed CORS origins (JSON array) | `["http://localhost:5173", "http://localhost:3000"]` |
| `GEMINI_API_KEY` | Default Google Gemini API key | `None` |
| `PERPLEXITY_API_KEY` | Default Perplexity API key | `None` |
| `HUGGINGFACE_API_KEY` | Default HuggingFace API key | `None` |
| `LLM_TIMEOUT` | LLM API request timeout (seconds) | `120` |
| `BROWSER_TIMEOUT` | Browser operation timeout (ms) | `30000` |
| `AGENT_TIMEOUT` | Total agent execution timeout (seconds) | `300` |
| `LLM_RETRY_ATTEMPTS` | Number of retry attempts for LLM calls | `3` |
| `RATE_LIMIT_ENABLED` | Enable rate limiting | `true` |
| `RATE_LIMIT_AGENT` | Rate limit for agent endpoint | `5/minute` |
| `RATE_LIMIT_CODEGEN` | Rate limit for code generation | `20/minute` |
| `MAX_STEPS` | Maximum steps per agent run | `50` |
| `SCREENSHOT_QUALITY` | Screenshot JPEG quality (0-100) | `80` |

### Example `.env` file

```env
# Server
HOST=0.0.0.0
PORT=8000
DEBUG=false

# CORS
CORS_ORIGINS=["http://localhost:5173", "http://localhost:3000"]

# API Keys (can also be passed per-request)
GEMINI_API_KEY=your_gemini_api_key_here
PERPLEXITY_API_KEY=your_perplexity_api_key_here

# Timeouts
LLM_TIMEOUT=120
BROWSER_TIMEOUT=30000
AGENT_TIMEOUT=300

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_AGENT=5/minute
```

## 📚 API Reference

### Interactive Documentation

Once the server is running, access the API documentation at:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI JSON**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

### Endpoints

#### `POST /api/agent`

Run a browser automation agent with streaming output.

**Request Body:**
```json
{
  "url": "https://example.com",
  "task": "Navigate to the login page and fill in the username field with 'testuser'",
  "provider": "gemini",
  "apiKey": "your_api_key",
  "framework": "playwright",
  "language": "typescript",
  "headless": true,
  "useBoostPrompt": true,
  "useStructuredExecution": false
}
```

**Response:** Server-Sent Events (SSE) stream with event types:
- `log` - Progress messages
- `screenshot` - Base64-encoded screenshots
- `code` - Generated test code
- `error` - Error messages
- `complete` - Agent finished

**Rate Limit:** 5 requests/minute

---

#### `POST /api/generate-code`

Generate Playwright test code from a structured test plan.

**Request Body:**
```json
{
  "steps": [
    {"action": "navigate", "url": "https://example.com"},
    {"action": "click", "selector": "#login-button"},
    {"action": "fill", "selector": "#username", "value": "testuser"}
  ],
  "language": "typescript",
  "testName": "Login Test"
}
```

**Response:**
```json
{
  "code": "import { test, expect } from '@playwright/test';...",
  "filename": "login-test.spec.ts"
}
```

**Rate Limit:** 20 requests/minute

---

#### `GET /api/health`

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": "2026-01-15T10:30:00.000000"
}
```

### Authentication

API keys can be provided via (in order of priority):

1. **X-API-Key header** (recommended, most secure)
   ```bash
   curl -H "X-API-Key: your_api_key" ...
   ```

2. **apiKey in request body**
   ```json
   { "apiKey": "your_api_key", ... }
   ```

3. **Environment variable** (server default)
   - `GEMINI_API_KEY`, `PERPLEXITY_API_KEY`, or `HUGGINGFACE_API_KEY`

## 🛠️ Development

### Code Quality Tools

```bash
# Format code
ruff format .

# Lint code
ruff check .

# Fix linting issues automatically
ruff check . --fix

# Type checking
mypy src
```

### Project Scripts

```bash
# Run the server directly
browser-agent

# Or with uvicorn
uvicorn browser_agent.main:app --reload
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_api.py

# Run tests with verbose output
pytest -v
```

### Test Coverage

Coverage reports are generated in `htmlcov/` directory after running tests with coverage.

## 🐳 Docker

### Build and Run

```bash
# Build the Docker image
docker build -t browser-agent-backend .

# Run the container
docker run -p 8000:8000 \
  -e GEMINI_API_KEY=your_api_key \
  browser-agent-backend
```

### Using Docker Compose

From the project root directory:

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop services
docker-compose down
```

### Health Check

The container includes a health check that verifies the `/api/health` endpoint is responding.

## 🔧 Troubleshooting

### Common Issues

#### 1. Playwright browsers not installed
```bash
# Install Playwright browsers
playwright install chromium

# Or install all browsers
playwright install
```

#### 2. Windows asyncio issues
The application automatically sets the Windows event loop policy for compatibility:
```python
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
```

#### 3. Rate limit exceeded
Wait for the rate limit window to reset, or adjust `RATE_LIMIT_*` environment variables.

#### 4. LLM API errors
- Verify your API key is valid
- Check your API quota/limits
- Increase `LLM_TIMEOUT` for slower responses
- Adjust `LLM_RETRY_ATTEMPTS` for transient failures

#### 5. Browser timeout
Increase `BROWSER_TIMEOUT` for slow-loading pages:
```env
BROWSER_TIMEOUT=60000  # 60 seconds
```

### Debug Mode

Enable debug mode for more verbose logging:
```env
DEBUG=true
```

## 📄 License

MIT License - see the [LICENSE](../LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

**Browser Agent Backend** - Transform natural language into browser automation! 🚀
