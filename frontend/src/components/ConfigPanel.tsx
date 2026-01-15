import { useState, FormEvent } from 'react';
import { Play, Settings, Key, Globe, Code, FileText, Monitor, ListChecks, Zap, User, Lock, ChevronDown, ChevronUp } from 'lucide-react';
import { AgentConfig, LLMProvider, Framework, Language } from '../types';

interface ConfigPanelProps {
  onSubmit: (config: AgentConfig) => void;
  isRunning: boolean;
}

const PROVIDERS: { value: LLMProvider; label: string }[] = [
  { value: 'gemini', label: 'Google Gemini' },
  { value: 'perplexity', label: 'Perplexity AI' },
  { value: 'hf', label: 'Hugging Face' },
];

const FRAMEWORKS: { value: Framework; label: string }[] = [
  { value: 'playwright', label: 'Playwright' },
];

const LANGUAGES: { value: Language; label: string }[] = [
  { value: 'typescript', label: 'TypeScript' },
  { value: 'python', label: 'Python' },
  { value: 'javascript', label: 'JavaScript' },
];

export default function ConfigPanel({ onSubmit, isRunning }: ConfigPanelProps) {
  const [provider, setProvider] = useState<LLMProvider>('gemini');
  const [apiKey, setApiKey] = useState('');
  const [url, setUrl] = useState('');
  const [task, setTask] = useState('');
  const [framework, setFramework] = useState<Framework>('playwright');
  const [language, setLanguage] = useState<Language>('typescript');
  const [headless, setHeadless] = useState<boolean>(false);
  const [useBoostPrompt, setUseBoostPrompt] = useState<boolean>(true);
  const [useStructuredExecution, setUseStructuredExecution] = useState<boolean>(false);
  const [showUrlAuth, setShowUrlAuth] = useState<boolean>(false);
  const [urlUsername, setUrlUsername] = useState('');
  const [urlPassword, setUrlPassword] = useState('');

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();

    onSubmit({ 
      apiKey, 
      provider, 
      url, 
      task, 
      framework, 
      language, 
      headless,
      useBoostPrompt,
      useStructuredExecution,
      verifyEachStep: useStructuredExecution,  // Enable verification with structured execution
      urlUsername: urlUsername.trim() || undefined,
      urlPassword: urlPassword.trim() || undefined,
    });
  };

  const isValid = apiKey.trim() && url.trim() && task.trim();

  return (
    <form onSubmit={handleSubmit} className="bg-card rounded-lg p-4 border border-border">
      <div className="flex items-center gap-2 mb-4">
        <Settings className="w-5 h-5 text-primary" />
        <h2 className="text-lg font-semibold">Configuration</h2>
      </div>

      <div className="space-y-4">
        {/* Provider Selection */}
        <div>
          <label className="block text-sm font-medium text-muted mb-1">LLM Provider</label>
          <select
            value={provider}
            onChange={(e) => setProvider(e.target.value as LLMProvider)}
            className="w-full bg-background border border-border rounded-md px-3 py-2 text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            disabled={isRunning}
          >
            {PROVIDERS.map((p) => (
              <option key={p.value} value={p.value}>{p.label}</option>
            ))}
          </select>
        </div>

        {/* API Key */}
        <div>
          <label className="block text-sm font-medium text-muted mb-1">
            <Key className="w-4 h-4 inline mr-1" />
            API Key
          </label>
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="Enter your API key"
            className="w-full bg-background border border-border rounded-md px-3 py-2 text-foreground placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-primary"
            disabled={isRunning}
          />
        </div>

        {/* Target URL */}
        <div>
          <label className="block text-sm font-medium text-muted mb-1">
            <Globe className="w-4 h-4 inline mr-1" />
            Target URL
          </label>
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://example.com"
            className="w-full bg-background border border-border rounded-md px-3 py-2 text-foreground placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-primary"
            disabled={isRunning}
          />
        </div>

        {/* URL Authentication (Optional) */}
        <div className="border border-border rounded-md overflow-hidden">
          <button
            type="button"
            onClick={() => setShowUrlAuth(!showUrlAuth)}
            className="w-full flex items-center justify-between p-3 bg-background hover:bg-card transition-colors"
            disabled={isRunning}
          >
            <div className="flex items-center gap-2">
              <Lock className="w-4 h-4 text-muted" />
              <span className="text-sm font-medium text-foreground">URL Authentication</span>
              <span className="text-xs text-muted">(optional)</span>
            </div>
            {showUrlAuth ? (
              <ChevronUp className="w-4 h-4 text-muted" />
            ) : (
              <ChevronDown className="w-4 h-4 text-muted" />
            )}
          </button>
          
          {showUrlAuth && (
            <div className="p-3 border-t border-border bg-card space-y-3">
              <p className="text-xs text-muted">
                If the target URL requires HTTP basic authentication, provide credentials below.
              </p>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-muted mb-1">
                    <User className="w-3 h-3 inline mr-1" />
                    Username
                  </label>
                  <input
                    type="text"
                    value={urlUsername}
                    onChange={(e) => setUrlUsername(e.target.value)}
                    placeholder="Enter username"
                    className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm text-foreground placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-primary"
                    disabled={isRunning}
                    autoComplete="off"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-muted mb-1">
                    <Lock className="w-3 h-3 inline mr-1" />
                    Password
                  </label>
                  <input
                    type="password"
                    value={urlPassword}
                    onChange={(e) => setUrlPassword(e.target.value)}
                    placeholder="Enter password"
                    className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm text-foreground placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-primary"
                    disabled={isRunning}
                    autoComplete="off"
                  />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Task Description */}
        <div>
          <label className="block text-sm font-medium text-muted mb-1">
            <FileText className="w-4 h-4 inline mr-1" />
            Task Description
          </label>
          <textarea
            value={task}
            onChange={(e) => setTask(e.target.value)}
            placeholder="Describe the task in natural language, e.g., 'Search for iPhone 17 Pro Max, add to cart, go to checkout'"
            rows={4}
            className="w-full bg-background border border-border rounded-md px-3 py-2 text-foreground placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-primary resize-none"
            disabled={isRunning}
          />
        </div>

        {/* Framework & Language */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-muted mb-1">
              <Code className="w-4 h-4 inline mr-1" />
              Framework
            </label>
            <select
              value={framework}
              onChange={(e) => setFramework(e.target.value as Framework)}
              className="w-full bg-background border border-border rounded-md px-3 py-2 text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              disabled={isRunning}
            >
              {FRAMEWORKS.map((f) => (
                <option key={f.value} value={f.value}>{f.label}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-muted mb-1">Language</label>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value as Language)}
              className="w-full bg-background border border-border rounded-md px-3 py-2 text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              disabled={isRunning}
            >
              {LANGUAGES.map((l) => (
                <option key={l.value} value={l.value}>{l.label}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Headless Mode Toggle */}
        <div className="flex items-center justify-between p-3 bg-background border border-border rounded-md">
          <div className="flex items-center gap-2">
            <Monitor className="w-4 h-4 text-muted" />
            <div>
              <label className="text-sm font-medium text-foreground">Show Browser</label>
              <p className="text-xs text-muted">Display browser window while running</p>
            </div>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={!headless}
            onClick={() => setHeadless(!headless)}
            disabled={isRunning}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50 ${
              !headless ? 'bg-primary' : 'bg-border'
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                !headless ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>

        {/* Boost Prompt Toggle */}
        <div className="flex items-center justify-between p-3 bg-background border border-border rounded-md">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-muted" />
            <div>
              <label className="text-sm font-medium text-foreground">Enhance Task</label>
              <p className="text-xs text-muted">Let LLM interpret and expand your task (may vary)</p>
            </div>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={useBoostPrompt}
            onClick={() => setUseBoostPrompt(!useBoostPrompt)}
            disabled={isRunning}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50 ${
              useBoostPrompt ? 'bg-primary' : 'bg-border'
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                useBoostPrompt ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>

        {/* Structured Execution Toggle */}
        <div className="flex items-center justify-between p-3 bg-background border border-border rounded-md">
          <div className="flex items-center gap-2">
            <ListChecks className="w-4 h-4 text-muted" />
            <div>
              <label className="text-sm font-medium text-foreground">Structured Execution</label>
              <p className="text-xs text-muted">Break complex tasks into tracked steps (more consistent)</p>
            </div>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={useStructuredExecution}
            onClick={() => setUseStructuredExecution(!useStructuredExecution)}
            disabled={isRunning}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50 ${
              useStructuredExecution ? 'bg-primary' : 'bg-border'
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                useStructuredExecution ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={!isValid || isRunning}
          className="w-full flex items-center justify-center gap-2 bg-primary hover:bg-primary-hover disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium py-3 px-4 rounded-md transition-colors"
        >
          {isRunning ? (
            <>
              <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Running Agent...
            </>
          ) : (
            <>
              <Play className="w-5 h-5" />
              Run Agent
            </>
          )}
        </button>
      </div>
    </form>
  );
}
