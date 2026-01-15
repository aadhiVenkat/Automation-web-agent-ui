import { useEffect, useRef, useState } from 'react';
import { Terminal, CheckCircle, XCircle, Wrench, Info, Copy, Check } from 'lucide-react';
import { LogEntry } from '../types';

interface LogsPanelProps {
  logs: LogEntry[];
}

const getLogIcon = (type: LogEntry['type']) => {
  switch (type) {
    case 'success':
      return <CheckCircle className="w-4 h-4 text-success flex-shrink-0" />;
    case 'error':
      return <XCircle className="w-4 h-4 text-error flex-shrink-0" />;
    case 'tool':
      return <Wrench className="w-4 h-4 text-primary flex-shrink-0" />;
    default:
      return <Info className="w-4 h-4 text-muted flex-shrink-0" />;
  }
};

const getLogColor = (type: LogEntry['type']) => {
  switch (type) {
    case 'success':
      return 'text-success';
    case 'error':
      return 'text-error';
    case 'tool':
      return 'text-primary';
    default:
      return 'text-foreground';
  }
};

export default function LogsPanel({ logs }: LogsPanelProps) {
  const logsEndRef = useRef<HTMLDivElement>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const copyLogs = async () => {
    const logText = logs
      .map((log) => `[${log.timestamp.toLocaleTimeString()}] [${log.type.toUpperCase()}] ${log.message}`)
      .join('\n');
    
    await navigator.clipboard.writeText(logText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="bg-card rounded-lg border border-border flex flex-col h-full">
      <div className="flex items-center gap-2 p-3 border-b border-border">
        <Terminal className="w-5 h-5 text-success" />
        <h2 className="text-lg font-semibold">Live Logs</h2>
        <span className="text-sm text-muted ml-auto">{logs.length} entries</span>
        {logs.length > 0 && (
          <button
            onClick={copyLogs}
            className="p-1.5 hover:bg-border rounded transition-colors"
            title="Copy logs"
          >
            {copied ? (
              <Check className="w-4 h-4 text-success" />
            ) : (
              <Copy className="w-4 h-4 text-muted hover:text-foreground" />
            )}
          </button>
        )}
      </div>

      <div className="flex-1 overflow-auto p-3 font-mono text-sm bg-[#0a0a0a]">
        {logs.length === 0 ? (
          <div className="text-muted text-center py-8">
            Waiting for agent to start...
          </div>
        ) : (
          <div className="space-y-1">
            {logs.map((log) => (
              <div key={log.id} className="flex items-start gap-2">
                {getLogIcon(log.type)}
                <span className="text-muted text-xs">
                  [{log.timestamp.toLocaleTimeString()}]
                </span>
                <span className={getLogColor(log.type)}>{log.message}</span>
              </div>
            ))}
            <div ref={logsEndRef} />
          </div>
        )}
      </div>
    </div>
  );
}
