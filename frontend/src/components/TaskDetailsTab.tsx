import { useEffect, useRef, useState } from 'react';
import { 
  Terminal, CheckCircle, XCircle, Wrench, Info, Copy, Check, 
  Clock, Activity, Loader2, AlertTriangle, Square
} from 'lucide-react';
import { LogEntry } from '../types';

interface TaskDetailsTabProps {
  logs: LogEntry[];
  isRunning: boolean;
  screenshotCount: number;
  hasCode: boolean;
  onStop?: () => void;
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

export default function TaskDetailsTab({ logs, isRunning, screenshotCount, hasCode, onStop }: TaskDetailsTabProps) {
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

  // Calculate statistics
  const errorCount = logs.filter(l => l.type === 'error').length;
  const toolCount = logs.filter(l => l.type === 'tool').length;

  return (
    <div className="h-full flex flex-col">
      {/* Status Overview */}
      <div className="p-4 border-b border-border bg-surface/50">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {/* Status */}
          <div className="flex items-center gap-3 p-3 bg-surface rounded-xl border border-border">
            {isRunning ? (
              <Loader2 className="w-5 h-5 text-primary animate-spin" />
            ) : errorCount > 0 ? (
              <AlertTriangle className="w-5 h-5 text-error" />
            ) : logs.length > 0 ? (
              <CheckCircle className="w-5 h-5 text-success" />
            ) : (
              <Clock className="w-5 h-5 text-muted" />
            )}
            <div>
              <span className="text-xs text-muted block">Status</span>
              <span className="text-sm font-medium">
                {isRunning ? 'Running' : errorCount > 0 ? 'Error' : logs.length > 0 ? 'Complete' : 'Idle'}
              </span>
            </div>
          </div>

          {/* Total Steps */}
          <div className="flex items-center gap-3 p-3 bg-surface rounded-xl border border-border">
            <Activity className="w-5 h-5 text-primary" />
            <div>
              <span className="text-xs text-muted block">Total Steps</span>
              <span className="text-sm font-medium">{logs.length}</span>
            </div>
          </div>

          {/* Tool Calls */}
          <div className="flex items-center gap-3 p-3 bg-surface rounded-xl border border-border">
            <Wrench className="w-5 h-5 text-amber-500" />
            <div>
              <span className="text-xs text-muted block">Tool Calls</span>
              <span className="text-sm font-medium">{toolCount}</span>
            </div>
          </div>

          {/* Screenshots */}
          <div className="flex items-center gap-3 p-3 bg-surface rounded-xl border border-border">
            <CheckCircle className="w-5 h-5 text-success" />
            <div>
              <span className="text-xs text-muted block">Screenshots</span>
              <span className="text-sm font-medium">{screenshotCount}</span>
            </div>
          </div>

          {/* Code Status */}
          <div className="flex items-center gap-3 p-3 bg-surface rounded-xl border border-border">
            {hasCode ? (
              <CheckCircle className="w-5 h-5 text-success" />
            ) : (
              <Clock className="w-5 h-5 text-muted" />
            )}
            <div>
              <span className="text-xs text-muted block">Code</span>
              <span className="text-sm font-medium">{hasCode ? 'Generated' : 'Pending'}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Logs Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-border bg-surface/30">
        <Terminal className="w-5 h-5 text-success" />
        <h3 className="font-semibold">Execution Log</h3>
        <span className="text-sm text-muted ml-auto">{logs.length} entries</span>
        {logs.length > 0 && (
          <button
            onClick={copyLogs}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-surface hover:bg-surface-hover border border-border rounded-lg transition-colors"
            title="Copy logs"
          >
            {copied ? (
              <>
                <Check className="w-4 h-4 text-success" />
                Copied
              </>
            ) : (
              <>
                <Copy className="w-4 h-4" />
                Copy
              </>
            )}
          </button>
        )}
        {isRunning && onStop && (
          <button
            onClick={onStop}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-error hover:bg-error/90 text-white rounded-lg transition-colors"
            title="Stop agent"
          >
            <Square className="w-4 h-4" />
            Stop
          </button>
        )}
      </div>

      {/* Logs Content */}
      <div className="flex-1 overflow-auto p-4 bg-surface-alt font-mono text-sm">
        {logs.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-muted">
            <Terminal className="w-16 h-16 mb-4 opacity-40" />
            <h3 className="text-lg font-medium mb-2">No Activity Yet</h3>
            <p className="text-sm text-center max-w-xs">
              Execution logs will appear here once you start the agent
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {logs.map((log, index) => (
              <div 
                key={log.id} 
                className="flex items-start gap-3 p-2 rounded-lg hover:bg-surface/50 transition-colors group"
              >
                <span className="text-xs text-muted font-normal min-w-[24px]">
                  {String(index + 1).padStart(2, '0')}
                </span>
                {getLogIcon(log.type)}
                <span className="text-xs text-muted whitespace-nowrap">
                  {log.timestamp.toLocaleTimeString()}
                </span>
                <span className={`${getLogColor(log.type)} flex-1 break-words`}>
                  {log.message}
                </span>
              </div>
            ))}
            <div ref={logsEndRef} />
          </div>
        )}
      </div>
    </div>
  );
}
