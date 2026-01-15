import { useState } from 'react';
import { Bot, AlertCircle, X } from 'lucide-react';
import ConfigPanel from './components/ConfigPanel';
import LogsPanel from './components/LogsPanel';
import CodeEditor from './components/CodeEditor';
import BrowserPreview from './components/BrowserPreview';
import { useAgent } from './hooks/useAgent';
import { Language } from './types';

export default function App() {
  const { logs, code, screenshots, isRunning, error, runAgent } = useAgent();
  const [language, setLanguage] = useState<Language>('typescript');

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Header */}
      <header className="border-b border-border px-6 py-4">
        <div className="flex items-center gap-3">
          <Bot className="w-8 h-8 text-primary" />
          <div>
            <h1 className="text-xl font-bold">BrowserForge AI</h1>
            <p className="text-sm text-muted">Natural Language → Browser Automation → Test Code</p>
          </div>
        </div>
      </header>

      {/* Error Banner */}
      {error && (
        <div className="bg-error/10 border-b border-error/20 px-6 py-3 flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-error flex-shrink-0" />
          <span className="text-error flex-1">{error}</span>
          <button className="text-error hover:text-error/80">
            <X className="w-5 h-5" />
          </button>
        </div>
      )}

      {/* Main Content */}
      <main className="p-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-[calc(100vh-140px)]">
          {/* Left Column: Config + Logs */}
          <div className="flex flex-col gap-6">
            <ConfigPanel 
              onSubmit={(config) => {
                setLanguage(config.language);
                runAgent(config);
              }} 
              isRunning={isRunning} 
            />
            <div className="flex-1 min-h-0">
              <LogsPanel logs={logs} />
            </div>
          </div>

          {/* Right Column: Preview + Code Editor */}
          <div className="flex flex-col gap-6">
            <BrowserPreview screenshots={screenshots} />
            <div className="flex-1 min-h-0">
              <CodeEditor code={code} language={language} />
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
