import { useState } from 'react';
import { Bot, AlertCircle, X, Settings, Activity, FileBarChart } from 'lucide-react';
import { ThemeProvider } from './context/ThemeContext';
import ThemeToggle from './components/ThemeToggle';
import ConfigurationTab from './components/ConfigurationTab';
import TaskDetailsTab from './components/TaskDetailsTab';
import ReportsTab from './components/ReportsTab';
import { useAgent } from './hooks/useAgent';
import { Language } from './types';

type MainTab = 'configuration' | 'task-details' | 'reports';

function AppContent() {
  const { logs, code, screenshots, isRunning, error, runAgent, stopAgent, clearError } = useAgent();
  const [language, setLanguage] = useState<Language>('typescript');
  const [activeTab, setActiveTab] = useState<MainTab>('configuration');

  const tabs: { id: MainTab; label: string; icon: React.ReactNode; badge?: number | string }[] = [
    { id: 'configuration', label: 'Configuration', icon: <Settings className="w-4 h-4" /> },
    { 
      id: 'task-details', 
      label: 'Task Details', 
      icon: <Activity className="w-4 h-4" />,
      badge: isRunning ? '•' : logs.length > 0 ? logs.length : undefined
    },
    { 
      id: 'reports', 
      label: 'Reports', 
      icon: <FileBarChart className="w-4 h-4" />,
      badge: screenshots.length + (code ? 1 : 0) || undefined
    },
  ];

  const handleRunAgent = (config: Parameters<typeof runAgent>[0]) => {
    setLanguage(config.language);
    setActiveTab('task-details'); // Auto-switch to task details when running
    runAgent(config);
  };

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      {/* Header */}
      <header className="border-b border-border bg-surface/50 backdrop-blur-sm sticky top-0 z-40">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-primary/10 rounded-xl">
                  <Bot className="w-7 h-7 text-primary" />
                </div>
                <div>
                  <h1 className="text-xl font-bold tracking-tight">BrowserForge AI</h1>
                  <p className="text-sm text-muted">Natural Language → Browser Automation → Test Code</p>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <ThemeToggle />
            </div>
          </div>
        </div>
      </header>

      {/* Error Banner */}
      {error && (
        <div className="bg-error/10 border-b border-error/20 px-6 py-3 flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-error flex-shrink-0" />
          <span className="text-error flex-1 text-sm">{error}</span>
          <button 
            onClick={clearError}
            className="text-error hover:text-error/80 p-1 hover:bg-error/10 rounded transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="border-b border-border bg-surface/30">
        <div className="px-6">
          <nav className="flex items-center gap-1 -mb-px">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-5 py-4 font-medium border-b-2 transition-all ${
                  activeTab === tab.id
                    ? 'border-primary text-primary bg-primary/5'
                    : 'border-transparent text-muted hover:text-foreground hover:border-border'
                }`}
              >
                {tab.icon}
                <span>{tab.label}</span>
                {tab.badge !== undefined && (
                  <span className={`min-w-[20px] h-5 flex items-center justify-center px-1.5 rounded-full text-xs font-semibold ${
                    activeTab === tab.id
                      ? 'bg-primary text-white'
                      : 'bg-surface-alt text-muted'
                  } ${tab.badge === '•' ? 'animate-pulse' : ''}`}>
                    {tab.badge}
                  </span>
                )}
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Main Content */}
      <main className="flex-1 overflow-hidden">
        <div className="h-full">
          {activeTab === 'configuration' && (
            <ConfigurationTab 
              onSubmit={handleRunAgent} 
              onStop={stopAgent}
              isRunning={isRunning} 
            />
          )}
          {activeTab === 'task-details' && (
            <TaskDetailsTab 
              logs={logs} 
              isRunning={isRunning}
              screenshotCount={screenshots.length}
              hasCode={!!code}
              onStop={stopAgent}
            />
          )}
          {activeTab === 'reports' && (
            <ReportsTab 
              screenshots={screenshots}
              code={code}
              language={language}
            />
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-border bg-surface/30 px-6 py-3">
        <div className="flex items-center justify-between text-sm text-muted">
          <span>© 2026 BrowserForge AI</span>
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1.5">
              <span className={`w-2 h-2 rounded-full ${isRunning ? 'bg-primary animate-pulse' : 'bg-muted'}`} />
              {isRunning ? 'Agent Running' : 'Ready'}
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <AppContent />
    </ThemeProvider>
  );
}
