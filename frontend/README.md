# 🖥️ Browser Agent Frontend

A modern React-based user interface for the Browser Agent Platform, enabling natural language browser automation with real-time feedback and test code generation.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Development](#development)
- [Configuration](#configuration)
- [Components](#components)
- [Hooks](#hooks)
- [API Integration](#api-integration)
- [Styling](#styling)
- [Building for Production](#building-for-production)
- [Docker](#docker)
- [Troubleshooting](#troubleshooting)

## 🎯 Overview

The Browser Agent Frontend provides an intuitive interface for interacting with the Browser Agent Platform. Users can describe browser automation tasks in natural language, watch the agent execute actions in real-time through screenshots, and receive generated Playwright test code.

### Workflow

1. **Configure**: Select LLM provider and enter API key
2. **Describe**: Enter target URL and natural language task description
3. **Execute**: Watch real-time logs and screenshots as the agent works
4. **Generate**: Receive production-ready Playwright test code

## ✨ Features

- **🎨 Modern UI**: Clean, responsive interface built with React and Tailwind CSS
- **📝 Natural Language Input**: Describe automation tasks in plain English
- **📸 Live Screenshots**: Real-time browser screenshots as the agent executes
- **📊 Live Logs**: Streaming logs showing agent progress and tool calls
- **💻 Code Editor**: Monaco-based code editor with syntax highlighting
- **🔄 Multi-Provider Support**: Google Gemini, Perplexity AI, and HuggingFace
- **🌐 Multi-Language Output**: Generate TypeScript, Python, or JavaScript tests
- **💾 Persistent Settings**: Auto-save configuration to localStorage
- **🎯 Advanced Options**: Headless mode, boost prompts, structured execution

## 🛠️ Tech Stack

| Technology | Purpose |
|------------|---------|
| **React 19** | UI framework with latest features |
| **TypeScript** | Type-safe JavaScript development |
| **Vite** | Fast build tool and dev server |
| **Tailwind CSS** | Utility-first CSS framework |
| **Monaco Editor** | VS Code-based code editor component |
| **Lucide React** | Beautiful icon library |
| **Server-Sent Events** | Real-time streaming from backend |

## 📁 Project Structure

```
frontend/
├── src/
│   ├── main.tsx              # Application entry point
│   ├── App.tsx               # Main application component
│   ├── index.css             # Global styles & Tailwind config
│   ├── types.ts              # TypeScript type definitions
│   ├── vite-env.d.ts         # Vite environment types
│   │
│   ├── components/
│   │   ├── index.ts          # Component exports
│   │   ├── ConfigPanel.tsx   # Agent configuration form
│   │   ├── LogsPanel.tsx     # Real-time logs display
│   │   ├── BrowserPreview.tsx # Screenshot carousel
│   │   └── CodeEditor.tsx    # Monaco code editor wrapper
│   │
│   └── hooks/
│       └── useAgent.ts       # Agent API integration hook
│
├── public/                   # Static assets
│
├── index.html               # HTML entry point
├── package.json             # Dependencies & scripts
├── tsconfig.json            # TypeScript configuration
├── vite.config.ts           # Vite configuration
├── tailwind.config.ts       # Tailwind CSS configuration
├── postcss.config.js        # PostCSS configuration
└── README.md                # This file
```

## 🚀 Installation

### Prerequisites

- **Node.js** 18.x or higher
- **npm** 9.x or higher (or pnpm/yarn)

### Setup Steps

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Start development server:**
   ```bash
   npm run dev
   ```

4. **Open in browser:**
   ```
   http://localhost:5173
   ```

## 💻 Development

### Available Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start development server with hot reload |
| `npm run build` | Build for production |
| `npm run preview` | Preview production build locally |
| `npm run lint` | Run ESLint for code quality |

### Development Server

```bash
# Start with default port (5173)
npm run dev

# Start with custom port
npm run dev -- --port 3000
```

### Hot Module Replacement

Vite provides instant hot module replacement (HMR) for fast development. Changes to components, styles, and hooks are reflected immediately without full page reload.

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the frontend directory:

```env
# Backend API URL (used in production)
VITE_API_URL=http://localhost:8000
```

### Vite Configuration

The `vite.config.ts` includes proxy configuration for development:

```typescript
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000'
    }
  }
})
```

### TypeScript Configuration

The project uses strict TypeScript settings defined in `tsconfig.json`:

- Strict mode enabled
- No implicit any
- Strict null checks
- ES2020+ target

## 🧩 Components

### ConfigPanel

The main configuration form component with the following features:

**Fields:**
- **LLM Provider**: Dropdown to select AI provider (Gemini, Perplexity, HuggingFace)
- **API Key**: Secure input for provider API key
- **URL**: Target website URL for automation
- **Task**: Natural language task description (multiline textarea)
- **Framework**: Test framework selection (Playwright)
- **Language**: Output language (TypeScript, Python, JavaScript)

**Advanced Options:**
- **Headless Mode**: Run browser without visible window
- **Boost Prompt**: Enhanced prompting for better results
- **Structured Execution**: Break complex tasks into verified steps

**Props:**
```typescript
interface ConfigPanelProps {
  onSubmit: (config: AgentConfig) => void;
  isRunning: boolean;
}
```

---

### LogsPanel

Displays real-time streaming logs from the agent.

**Features:**
- Color-coded log types (info, success, error, tool)
- Auto-scroll to latest log
- Timestamp display
- Tool call highlighting

**Props:**
```typescript
interface LogsPanelProps {
  logs: LogEntry[];
}
```

---

### BrowserPreview

Screenshot carousel showing browser state during execution.

**Features:**
- Image carousel with navigation
- Screenshot counter
- Placeholder when no screenshots available
- Full-resolution display

**Props:**
```typescript
interface BrowserPreviewProps {
  screenshots: string[];
}
```

---

### CodeEditor

Monaco-based code editor for displaying generated test code.

**Features:**
- Syntax highlighting for TypeScript, Python, JavaScript
- Read-only mode
- VS Code-like editing experience
- Theme support

**Props:**
```typescript
interface CodeEditorProps {
  code: string;
  language: Language;
}
```

## 🪝 Hooks

### useAgent

Custom hook for managing agent state and API communication.

**Returns:**
```typescript
interface UseAgentReturn {
  logs: LogEntry[];           // Array of log entries
  code: string;               // Generated test code
  screenshots: string[];      // Base64 screenshot data
  isRunning: boolean;         // Agent execution state
  error: string | null;       // Error message if any
  runAgent: (config: AgentConfig) => Promise<void>;
  clearLogs: () => void;
}
```

**Usage:**
```typescript
const { logs, code, screenshots, isRunning, error, runAgent } = useAgent();

// Start agent
await runAgent({
  apiKey: 'your-api-key',
  provider: 'gemini',
  url: 'https://example.com',
  task: 'Click the login button',
  framework: 'playwright',
  language: 'typescript',
  headless: true
});
```

**Features:**
- Automatic SSE connection management
- Event parsing and state updates
- Error handling
- Request cancellation support

## 🔌 API Integration

### Server-Sent Events (SSE)

The frontend connects to the backend's `/api/agent` endpoint using SSE for real-time updates:

```typescript
const response = await fetch('/api/agent', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'text/event-stream',
  },
  body: JSON.stringify(config),
});

const reader = response.body?.getReader();
// Process SSE events...
```

### Event Types

| Event | Description | Data |
|-------|-------------|------|
| `log` | Progress message | `{ message: string }` |
| `screenshot` | Browser screenshot | `{ screenshot: string }` (base64) |
| `code` | Generated test code | `{ code: string }` |
| `error` | Error occurred | `{ message: string }` |
| `complete` | Agent finished | `{ message: string }` |

## 🎨 Styling

### Tailwind CSS

The project uses Tailwind CSS with custom configuration:

```typescript
// tailwind.config.ts
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        background: '#0d1117',
        foreground: '#c9d1d9',
        card: '#161b22',
        border: '#30363d',
        primary: '#58a6ff',
        muted: '#8b949e',
        success: '#3fb950',
        error: '#f85149',
      }
    }
  }
}
```

### CSS Variables

Global CSS variables defined in `index.css`:

```css
:root {
  --background: #0d1117;
  --foreground: #c9d1d9;
  --card: #161b22;
  --border: #30363d;
  --primary: #58a6ff;
  --muted: #8b949e;
  --success: #3fb950;
  --error: #f85149;
}
```

### Dark Theme

The UI uses a GitHub-inspired dark theme by default, designed for comfortable extended use.

## 📦 Building for Production

### Build Command

```bash
npm run build
```

### Output

Production files are generated in the `dist/` directory:

```
dist/
├── index.html
├── assets/
│   ├── index-[hash].js
│   └── index-[hash].css
└── ...
```

### Preview Production Build

```bash
npm run preview
```

### Deployment

The `dist/` folder can be deployed to any static hosting service:

- **Vercel**: `vercel deploy`
- **Netlify**: `netlify deploy`
- **GitHub Pages**: Copy to `gh-pages` branch
- **Nginx**: Copy to `/var/www/html`

## 🐳 Docker

### Building the Image

```bash
docker build -t browser-agent-frontend .
```

### Running the Container

```bash
docker run -p 5173:5173 \
  -e VITE_API_URL=http://localhost:8000 \
  browser-agent-frontend
```

### Using Docker Compose

From the project root:

```bash
# Start all services
docker-compose up -d

# View frontend logs
docker-compose logs -f frontend

# Stop services
docker-compose down
```

## 🔧 Troubleshooting

### Common Issues

#### 1. API Connection Failed

**Symptom:** "Failed to fetch" or network errors

**Solutions:**
- Ensure backend is running on port 8000
- Check CORS configuration in backend
- Verify proxy settings in `vite.config.ts`

#### 2. SSE Events Not Receiving

**Symptom:** Agent starts but no updates appear

**Solutions:**
- Check browser console for errors
- Verify `Accept: text/event-stream` header is sent
- Ensure backend is streaming correctly

#### 3. Monaco Editor Not Loading

**Symptom:** Code editor shows blank or errors

**Solutions:**
```bash
# Clear node_modules and reinstall
rm -rf node_modules
npm install
```

#### 4. TypeScript Errors

**Symptom:** Build fails with type errors

**Solutions:**
```bash
# Check for type errors
npx tsc --noEmit

# Update TypeScript types
npm install @types/react@latest @types/react-dom@latest
```

#### 5. Tailwind Styles Not Applied

**Symptom:** Components appear unstyled

**Solutions:**
- Check `tailwind.config.ts` content paths
- Ensure PostCSS is configured correctly
- Verify `index.css` imports Tailwind directives

### Debug Mode

Enable detailed logging in browser console:

```typescript
// In useAgent.ts, events are logged:
console.log('Processing event:', event);
```

### Browser DevTools

Use the Network tab to inspect:
- API requests to `/api/agent`
- SSE event stream
- Response headers and body

## 📄 License

MIT License - see the [LICENSE](../LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow TypeScript strict mode
- Use functional components with hooks
- Follow Tailwind CSS utility-first approach
- Write descriptive commit messages
- Add JSDoc comments for complex functions

---

**Browser Agent Frontend** - Beautiful UI for AI-powered browser automation! 🎨
