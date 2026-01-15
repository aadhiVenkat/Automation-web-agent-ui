import { useState, useEffect, FormEvent } from 'react';
import { 
  Play, Key, Globe, Code, FileText, Monitor, ListChecks, Zap, 
  User, Lock, ChevronDown, ChevronUp, Settings2, Cpu, Square
} from 'lucide-react';
import { AgentConfig, LLMProvider, Framework, Language } from '../types';

interface ConfigurationTabProps {
  onSubmit: (config: AgentConfig) => void;
  onStop: () => void;
  isRunning: boolean;
}

const STORAGE_KEY = 'browserforge-config';

interface PersistedConfig {
  provider: LLMProvider;
  apiKey: string;
  url: string;
  task: string;
  framework: Framework;
  language: Language;
  headless: boolean;
  useBoostPrompt: boolean;
  useStructuredExecution: boolean;
  urlUsername: string;
  urlPassword: string;
}

const getPersistedConfig = (): Partial<PersistedConfig> => {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? JSON.parse(stored) : {};
  } catch {
    return {};
  }
};

const persistConfig = (config: PersistedConfig) => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
  } catch {
    // Ignore storage errors
  }
};

const PROVIDERS: { value: LLMProvider; label: string; description: string }[] = [
  { value: 'gemini', label: 'Google Gemini', description: 'Best for general tasks' },
  { value: 'perplexity', label: 'Perplexity AI', description: 'Good for search-heavy tasks' },
  { value: 'hf', label: 'Hugging Face', description: 'Open-source models' },
];

const FRAMEWORKS: { value: Framework; label: string; icon: string; description: string }[] = [
  { value: 'playwright', label: 'Playwright', icon: '🎭', description: 'Modern E2E testing' },
];

const LANGUAGES: { value: Language; label: string; icon: string }[] = [
  { value: 'typescript', label: 'TypeScript', icon: 'TS' },
  { value: 'python', label: 'Python', icon: 'PY' },
  { value: 'javascript', label: 'JavaScript', icon: 'JS' },
];

export default function ConfigurationTab({ onSubmit, onStop, isRunning }: ConfigurationTabProps) {
  const persisted = getPersistedConfig();
  
  const [provider, setProvider] = useState<LLMProvider>(persisted.provider ?? 'gemini');
  const [apiKey, setApiKey] = useState(persisted.apiKey ?? '');
  const [url, setUrl] = useState(persisted.url ?? '');
  const [task, setTask] = useState(persisted.task ?? '');
  const [framework, setFramework] = useState<Framework>(persisted.framework ?? 'playwright');
  const [language, setLanguage] = useState<Language>(persisted.language ?? 'typescript');
  const [headless, setHeadless] = useState<boolean>(persisted.headless ?? false);
  const [useBoostPrompt, setUseBoostPrompt] = useState<boolean>(persisted.useBoostPrompt ?? true);
  const [useStructuredExecution, setUseStructuredExecution] = useState<boolean>(persisted.useStructuredExecution ?? false);
  const [showUrlAuth, setShowUrlAuth] = useState<boolean>(false);
  const [showAdvanced, setShowAdvanced] = useState<boolean>(false);
  const [urlUsername, setUrlUsername] = useState(persisted.urlUsername ?? '');
  const [urlPassword, setUrlPassword] = useState(persisted.urlPassword ?? '');

  // Persist config whenever any value changes
  useEffect(() => {
    persistConfig({
      provider,
      apiKey,
      url,
      task,
      framework,
      language,
      headless,
      useBoostPrompt,
      useStructuredExecution,
      urlUsername,
      urlPassword,
    });
  }, [provider, apiKey, url, task, framework, language, headless, useBoostPrompt, useStructuredExecution, urlUsername, urlPassword]);

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
      verifyEachStep: useStructuredExecution,
      urlUsername: urlUsername.trim() || undefined,
      urlPassword: urlPassword.trim() || undefined,
    });
  };

  const isValid = apiKey.trim() && url.trim() && task.trim();

  return (
    <div className="h-full overflow-auto">
      <form onSubmit={handleSubmit} className="max-w-3xl mx-auto p-6 space-y-8">
        {/* LLM Configuration Section */}
        <section className="space-y-4">
          <div className="flex items-center gap-2 pb-2 border-b border-border">
            <Cpu className="w-5 h-5 text-primary" />
            <h3 className="text-lg font-semibold">LLM Configuration</h3>
          </div>
          
          {/* Provider Selection */}
          <div className="grid grid-cols-3 gap-3">
            {PROVIDERS.map((p) => (
              <button
                key={p.value}
                type="button"
                onClick={() => setProvider(p.value)}
                disabled={isRunning}
                className={`p-4 rounded-xl border-2 text-left transition-all ${
                  provider === p.value
                    ? 'border-primary bg-primary/5 ring-2 ring-primary/20'
                    : 'border-border hover:border-primary/50 bg-surface'
                } disabled:opacity-50 disabled:cursor-not-allowed`}
              >
                <span className="font-medium block mb-1">{p.label}</span>
                <span className="text-xs text-muted">{p.description}</span>
              </button>
            ))}
          </div>

          {/* API Key */}
          <div className="space-y-2">
            <label className="flex items-center gap-2 text-sm font-medium text-foreground">
              <Key className="w-4 h-4 text-muted" />
              API Key
            </label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="Enter your API key"
              className="w-full bg-surface border border-border rounded-xl px-4 py-3 text-foreground placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary transition-all"
              disabled={isRunning}
            />
          </div>
        </section>

        {/* Target Configuration Section */}
        <section className="space-y-4">
          <div className="flex items-center gap-2 pb-2 border-b border-border">
            <Globe className="w-5 h-5 text-primary" />
            <h3 className="text-lg font-semibold">Target Configuration</h3>
          </div>

          {/* Target URL */}
          <div className="space-y-2">
            <label className="flex items-center gap-2 text-sm font-medium text-foreground">
              <Globe className="w-4 h-4 text-muted" />
              Target URL
            </label>
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://example.com"
              className="w-full bg-surface border border-border rounded-xl px-4 py-3 text-foreground placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary transition-all"
              disabled={isRunning}
            />
          </div>

          {/* URL Authentication (Collapsible) */}
          <div className="rounded-xl border border-border overflow-hidden">
            <button
              type="button"
              onClick={() => setShowUrlAuth(!showUrlAuth)}
              className="w-full flex items-center justify-between p-4 bg-surface hover:bg-surface-hover transition-colors"
              disabled={isRunning}
            >
              <div className="flex items-center gap-2">
                <Lock className="w-4 h-4 text-muted" />
                <span className="text-sm font-medium">URL Authentication</span>
                <span className="text-xs text-muted bg-surface-alt px-2 py-0.5 rounded-full">Optional</span>
              </div>
              {showUrlAuth ? (
                <ChevronUp className="w-4 h-4 text-muted" />
              ) : (
                <ChevronDown className="w-4 h-4 text-muted" />
              )}
            </button>
            
            {showUrlAuth && (
              <div className="p-4 border-t border-border bg-surface/50 space-y-4">
                <p className="text-xs text-muted">
                  For sites requiring HTTP basic authentication
                </p>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="flex items-center gap-1 text-xs font-medium text-muted">
                      <User className="w-3 h-3" />
                      Username
                    </label>
                    <input
                      type="text"
                      value={urlUsername}
                      onChange={(e) => setUrlUsername(e.target.value)}
                      placeholder="Username"
                      className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-primary transition-all"
                      disabled={isRunning}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="flex items-center gap-1 text-xs font-medium text-muted">
                      <Lock className="w-3 h-3" />
                      Password
                    </label>
                    <input
                      type="password"
                      value={urlPassword}
                      onChange={(e) => setUrlPassword(e.target.value)}
                      placeholder="Password"
                      className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-primary transition-all"
                      disabled={isRunning}
                    />
                  </div>
                </div>
              </div>
            )}
          </div>
        </section>

        {/* Task Section */}
        <section className="space-y-4">
          <div className="flex items-center gap-2 pb-2 border-b border-border">
            <FileText className="w-5 h-5 text-primary" />
            <h3 className="text-lg font-semibold">Task Description</h3>
          </div>

          <div className="space-y-2">
            <textarea
              value={task}
              onChange={(e) => setTask(e.target.value)}
              placeholder="Describe what you want the agent to do in natural language...&#10;&#10;Example: Search for iPhone 17 Pro Max, add to cart, and proceed to checkout"
              rows={5}
              className="w-full bg-surface border border-border rounded-xl px-4 py-3 text-foreground placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary transition-all resize-none"
              disabled={isRunning}
            />
          </div>
        </section>

        {/* Output Configuration */}
        <section className="space-y-4">
          <div className="flex items-center gap-2 pb-2 border-b border-border">
            <Code className="w-5 h-5 text-primary" />
            <h3 className="text-lg font-semibold">Output Settings</h3>
          </div>

          {/* Framework Selection */}
          <div className="space-y-3">
            <label className="text-sm font-medium text-foreground">Test Framework</label>
            <div className="grid grid-cols-1 gap-3">
              {FRAMEWORKS.map((f) => (
                <button
                  key={f.value}
                  type="button"
                  onClick={() => setFramework(f.value)}
                  disabled={isRunning}
                  className={`flex items-center gap-4 p-4 rounded-xl border-2 text-left transition-all ${
                    framework === f.value
                      ? 'border-primary bg-primary/5 ring-2 ring-primary/20'
                      : 'border-border hover:border-primary/50 bg-surface'
                  } disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                  <span className="text-2xl">{f.icon}</span>
                  <div className="flex-1">
                    <span className="font-semibold block">{f.label}</span>
                    <span className="text-xs text-muted">{f.description}</span>
                  </div>
                  {framework === f.value && (
                    <div className="w-5 h-5 rounded-full bg-primary flex items-center justify-center">
                      <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                      </svg>
                    </div>
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Language Selection */}
          <div className="space-y-3">
            <label className="text-sm font-medium text-foreground">Output Language</label>
            <div className="grid grid-cols-3 gap-3">
              {LANGUAGES.map((l) => (
                <button
                  key={l.value}
                  type="button"
                  onClick={() => setLanguage(l.value)}
                  disabled={isRunning}
                  className={`flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all ${
                    language === l.value
                      ? 'border-primary bg-primary/5 ring-2 ring-primary/20'
                      : 'border-border hover:border-primary/50 bg-surface'
                  } disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                  <span className={`text-lg font-bold px-2 py-1 rounded ${
                    l.value === 'typescript' ? 'bg-blue-500/20 text-blue-500' :
                    l.value === 'python' ? 'bg-yellow-500/20 text-yellow-600' :
                    'bg-amber-500/20 text-amber-500'
                  }`}>
                    {l.icon}
                  </span>
                  <span className="text-sm font-medium">{l.label}</span>
                </button>
              ))}
            </div>
          </div>
        </section>

        {/* Advanced Options (Collapsible) */}
        <section className="space-y-4">
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="flex items-center justify-between w-full pb-2 border-b border-border"
          >
            <div className="flex items-center gap-2">
              <Settings2 className="w-5 h-5 text-primary" />
              <h3 className="text-lg font-semibold">Advanced Options</h3>
            </div>
            {showAdvanced ? (
              <ChevronUp className="w-5 h-5 text-muted" />
            ) : (
              <ChevronDown className="w-5 h-5 text-muted" />
            )}
          </button>

          {showAdvanced && (
            <div className="space-y-4">
              {/* Show Browser Toggle */}
              <div className="flex items-center justify-between p-4 bg-surface border border-border rounded-xl">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-surface-alt rounded-lg">
                    <Monitor className="w-5 h-5 text-primary" />
                  </div>
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

              {/* Enhance Task Toggle */}
              <div className="flex items-center justify-between p-4 bg-surface border border-border rounded-xl">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-surface-alt rounded-lg">
                    <Zap className="w-5 h-5 text-amber-500" />
                  </div>
                  <div>
                    <label className="text-sm font-medium text-foreground">Enhance Task</label>
                    <p className="text-xs text-muted">Let LLM interpret and expand your task</p>
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
              <div className="flex items-center justify-between p-4 bg-surface border border-border rounded-xl">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-surface-alt rounded-lg">
                    <ListChecks className="w-5 h-5 text-success" />
                  </div>
                  <div>
                    <label className="text-sm font-medium text-foreground">Structured Execution</label>
                    <p className="text-xs text-muted">Break complex tasks into tracked steps</p>
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
            </div>
          )}
        </section>

        {/* Submit / Stop Button */}
        <div className="flex gap-3">
          {isRunning ? (
            <button
              type="button"
              onClick={onStop}
              className="w-full flex items-center justify-center gap-3 bg-error hover:bg-error/90 text-white font-semibold py-4 px-6 rounded-xl transition-all shadow-lg shadow-error/20 hover:shadow-xl hover:shadow-error/30"
            >
              <Square className="w-5 h-5" />
              Stop Agent
            </button>
          ) : (
            <button
              type="submit"
              disabled={!isValid}
              className="w-full flex items-center justify-center gap-3 bg-primary hover:bg-primary-hover disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold py-4 px-6 rounded-xl transition-all shadow-lg shadow-primary/20 hover:shadow-xl hover:shadow-primary/30"
            >
              <Play className="w-5 h-5" />
              Run Agent
            </button>
          )}
        </div>
      </form>
    </div>
  );
}
