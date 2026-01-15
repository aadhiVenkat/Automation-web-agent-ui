# 🤖 BrowserForge AI

A full-stack AI-powered browser automation platform that enables natural language browser control and automatic Playwright test code generation.

## 🎯 Overview

BrowserForge AI combines cutting-edge AI with browser automation to transform natural language descriptions into executable browser actions and production-ready Playwright test code. Simply describe what you want to automate, and watch as AI agents navigate, interact, and generate reusable test code in real-time.

### Key Capabilities

- **Natural Language Automation**: Describe tasks in plain English, no code required
- **Multi-LLM Support**: Works with Google Gemini, Perplexity AI, and HuggingFace models
- **Real-time Execution**: Watch live screenshots and logs as the agent works
- **Code Generation**: Automatically generates Playwright tests in TypeScript, Python, or JavaScript
- **Production Ready**: Docker support with health checks and proper configuration

## ✨ Features

### UI Screenshots

<details>
<summary>📸 Click to view UI screenshots</summary>

#### Configuration Tab (Dark Theme)
The configuration tab provides an intuitive interface for setting up your automation task:
- **LLM Provider Selection**: Choose between Google Gemini, Perplexity AI, or Hugging Face
- **Target Configuration**: Enter URL with optional HTTP basic authentication
- **Task Description**: Natural language input for automation tasks
- **Output Settings**: Select test framework (Playwright) and language (TypeScript, Python, JavaScript)
- **Advanced Options**: Toggle headless mode, task enhancement, and structured execution

#### Task Details Tab
Monitor your automation in real-time:
- **Status Overview**: Current state, total steps, tool calls, screenshots count
- **Execution Log**: Color-coded logs with timestamps and copy functionality

#### Reports Tab
Access your automation results:
- **Screenshots Sub-tab**: Grid or single view, fullscreen mode, download individual or all
- **Generated Code Sub-tab**: Syntax-highlighted code with copy and download options

#### Theme Support
- 🌙 **Dark Theme**: Easy on the eyes for extended use
- ☀️ **Light Theme**: Softer tones for well-lit environments
- 🔄 **System Detection**: Automatically matches your OS preference

</details>

### Backend (FastAPI)
- 🧠 **AI-Powered Agent**: Intelligent browser automation using LLMs
- 🌐 **Playwright Integration**: Robust browser control with Chromium
- 📸 **Screenshot Capture**: Real-time visual feedback during execution
- 🔄 **Server-Sent Events**: Streaming logs and progress updates
- 🔒 **Security**: API key management and rate limiting
- 🐳 **Docker Ready**: Production-optimized containerization

### Frontend (React)
- 🎨 **Modern UI**: Clean, responsive interface with Tailwind CSS
- 🌓 **Dark/Light Theme**: System-aware theme with manual toggle
- 📑 **Tabbed Interface**: Organized Configuration, Task Details, and Reports tabs
- 💻 **Code Editor**: Monaco editor with syntax highlighting
- 📊 **Live Dashboard**: Real-time logs with status indicators
- 📸 **Screenshot Gallery**: Grid/single view with fullscreen and download options
- � **URL Authentication**: Support for HTTP basic auth on target sites
- 🎯 **Advanced Options**: Headless mode, boost prompts, structured execution

## 🏗️ Architecture

```
Automation-web-agent-ui/
├── backend/                 # FastAPI backend service
│   ├── src/
│   │   └── browser_agent/
│   │       ├── api/         # REST API routes
│   │       ├── core/        # Agent & browser logic
│   │       ├── llm/         # LLM integrations (Gemini, Perplexity, HF)
│   │       ├── models/      # Pydantic models
│   │       ├── services/    # Business logic
│   │       ├── templates/   # Jinja2 code generation templates
│   │       └── tools/       # Browser automation tools
│   ├── tests/               # Backend tests
│   ├── Dockerfile
│   └── pyproject.toml
│
├── frontend/                # React frontend application
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── hooks/           # Custom React hooks
│   │   ├── App.tsx          # Main application
│   │   └── types.ts         # TypeScript definitions
│   ├── Dockerfile
│   └── package.json
│
└── docker-compose.yml       # Orchestration configuration
```

## 🚀 Quick Start

### Prerequisites

- **Docker** & **Docker Compose** (recommended)
- OR manually:
  - **Python** 3.11+
  - **Node.js** 18+
  - **Playwright** browsers

### Option 1: Docker (Recommended)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/aadhiVenkat/Automation-web-agent-ui.git
   cd Automation-web-agent-ui
   ```

2. **Create backend .env file:**
   ```bash
   cd backend
   cp .env.example .env
   # Edit .env with your API keys (optional)
   ```

3. **Start the platform:**
   ```bash
   cd ..
   docker-compose up --build
   ```

4. **Access the application:**
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Option 2: Local Development

#### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -e ".[dev]"

# Install Playwright browsers
playwright install chromium

# Run backend with uvicorn (choose one):
# Option 1: Using the entry point script
browser-agent

# Option 2: Using uvicorn directly (recommended for development)
uvicorn browser_agent.main:app --reload --host 0.0.0.0 --port 8000

# Option 3: Running as Python module
python -m browser_agent.main
```

#### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

## 🔧 Configuration

### Backend Environment Variables

Create `backend/.env`:

```env
# LLM Provider API Keys (at least one required)
GOOGLE_API_KEY=your_gemini_api_key
PERPLEXITY_API_KEY=your_perplexity_api_key
HUGGINGFACE_API_KEY=your_huggingface_api_key

# Application Settings
HOST=0.0.0.0
PORT=8000
DEBUG=false
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]

# Rate Limiting (optional)
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60
```

### Frontend Configuration

The frontend automatically connects to `http://localhost:8000` in development. For production, set:

```env
VITE_API_URL=https://your-backend-url.com
```

## 📖 Usage

1. **Configure the Agent:**
   - Select your LLM provider (Gemini, Perplexity, or HuggingFace)
   - Enter your API key
   - Choose output language (TypeScript, Python, or JavaScript)

2. **Describe Your Task:**
   - Enter the target website URL
   - (Optional) If the URL requires HTTP basic authentication, expand "URL Authentication" and provide username/password
   - Describe the automation task in natural language
   - Example: "Search for 'machine learning', filter by date, and export results"

3. **Execute & Monitor:**
   - Click "Start Agent"
   - Watch real-time logs and screenshots
   - See the agent navigate and interact with the website

4. **Get Your Code:**
   - Review the generated Playwright test code
   - Copy and use in your projects
   - Customize as needed

## 🧪 Testing

### Backend Tests

```bash
cd backend
pytest tests/ -v --cov=src/browser_agent
```

### Frontend Tests

```bash
cd frontend
npm run lint
npm run build  # Type checking
```

## 🐳 Docker Commands

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild after changes
docker-compose up --build

# Check health
docker-compose ps
```

## 📚 API Documentation

Once the backend is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

- `POST /api/agent/execute` - Execute browser automation task
- `POST /api/codegen/generate` - Generate Playwright test code
- `GET /api/health` - Health check endpoint

## 🛠️ Development

### Backend Development

```bash
cd backend

# Install with dev dependencies
pip install -e ".[dev]"

# Run with hot reload
uvicorn browser_agent.main:app --reload

# Format code
ruff check src/ --fix

# Type checking
mypy src/
```

### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev

# Lint
npm run lint

# Build
npm run build
```

## 🔍 Project Structure Details

### Backend (`backend/`)

- **api/**: FastAPI route handlers and endpoints
- **core/**: Core agent logic and browser automation
- **llm/**: LLM provider integrations with retry logic
- **models/**: Pydantic models for validation
- **services/**: Business logic and orchestration
- **templates/**: Jinja2 templates for code generation
- **tools/**: Browser automation tool implementations

### Frontend (`frontend/`)

- **components/**: Reusable React components
  - `ConfigurationTab`: Agent configuration with LLM, target, task & output settings
  - `TaskDetailsTab`: Real-time execution logs and status monitoring
  - `ReportsTab`: Screenshots gallery and generated code viewer
  - `ScreenshotGallery`: Interactive screenshot viewer with grid/single views
  - `CodeReport`: Monaco-based code editor for generated tests
  - `ThemeToggle`: Dark/Light theme switcher
- **context/**: React context providers
  - `ThemeContext`: Theme management with system preference detection
- **hooks/**: Custom React hooks
  - `useAgent`: API integration and state management
- **types.ts**: TypeScript type definitions

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🐛 Troubleshooting

### Backend Issues

**Playwright browsers not found:**
```bash
playwright install chromium
```

**Port already in use:**
```bash
# Change port in docker-compose.yml or use:
uvicorn browser_agent.main:app --port 8001
```

**API key errors:**
- Verify `.env` file exists in `backend/` directory
- Check API keys are valid and have sufficient quota
- Ensure no extra spaces in `.env` values

### Frontend Issues

**Connection refused:**
- Ensure backend is running on port 8000
- Check CORS settings in backend `.env`

**Build errors:**
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

### Docker Issues

**Containers won't start:**
```bash
# Check logs
docker-compose logs

# Remove old containers
docker-compose down -v
docker-compose up --build
```

## 📞 Support

For issues and questions:
- Open an issue on GitHub
- Check existing documentation in `backend/README.md` and `frontend/README.md`
- Review API documentation at http://localhost:8000/docs

## 🎯 Roadmap

- [ ] Multi-browser support (Firefox, Safari)
- [ ] Cloud deployment templates (AWS, GCP, Azure)
- [ ] Test result visualization
- [ ] Batch automation support
- [ ] Enhanced code generation with assertions
- [ ] Integration with CI/CD pipelines
- [ ] Browser recording and replay features

## 🏆 Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Playwright](https://playwright.dev/) - Browser automation
- [React](https://react.dev/) - Frontend framework
- [Tailwind CSS](https://tailwindcss.com/) - Styling
- [Monaco Editor](https://microsoft.github.io/monaco-editor/) - Code editor

---

**Made with ❤️ by the BrowserForge AI Team**
