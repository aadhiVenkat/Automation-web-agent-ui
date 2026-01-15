import { useState, useCallback, useRef } from 'react';
import { AgentConfig, AgentEvent, LogEntry } from '../types';

interface UseAgentReturn {
  logs: LogEntry[];
  code: string;
  screenshots: string[];
  isRunning: boolean;
  error: string | null;
  runAgent: (config: AgentConfig) => Promise<void>;
  clearLogs: () => void;
  clearError: () => void;
}

let logIdCounter = 0;

const createLogEntry = (type: LogEntry['type'], message: string): LogEntry => ({
  id: `log-${++logIdCounter}`,
  type,
  message,
  timestamp: new Date(),
});

export function useAgent(): UseAgentReturn {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [code, setCode] = useState('');
  const [screenshots, setScreenshots] = useState<string[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const clearLogs = useCallback(() => {
    setLogs([]);
    setCode('');
    setScreenshots([]);
    setError(null);
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const processEvent = useCallback((event: AgentEvent) => {
    console.log('Processing event:', event);
    
    switch (event.type) {
      case 'log':
        if (event.message) {
          const logType = event.message.toLowerCase().includes('tool:') ? 'tool' : 'info';
          setLogs((prev) => [...prev, createLogEntry(logType, event.message!)]);
        }
        break;
      case 'screenshot':
        if (event.screenshot) {
          const screenshotData = event.screenshot.startsWith('data:') 
            ? event.screenshot 
            : `data:image/png;base64,${event.screenshot}`;
          setScreenshots((prev) => [...prev, screenshotData]);
          setLogs((prev) => [...prev, createLogEntry('success', `Screenshot #${prev.filter(l => l.message?.includes('Screenshot')).length + 1} captured`)]);
        }
        break;
      case 'code':
        if (event.code) {
          setCode(event.code);
          setLogs((prev) => [...prev, createLogEntry('success', 'Test code generated')]);
        }
        break;
      case 'error':
        if (event.message) {
          setLogs((prev) => [...prev, createLogEntry('error', event.message!)]);
          setError(event.message);
        }
        break;
      case 'complete':
        setLogs((prev) => [...prev, createLogEntry('success', event.message || 'Agent completed')]);
        break;
    }
  }, []);

  const runAgent = useCallback(async (config: AgentConfig) => {
    // Cancel any existing request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    
    abortControllerRef.current = new AbortController();
    
    clearLogs();
    setIsRunning(true);
    setError(null);

    setLogs([createLogEntry('info', 'Starting agent...')]);

    try {
      const response = await fetch('/api/agent', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
        },
        body: JSON.stringify(config),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body');
      }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        
        if (done) {
          // Process any remaining data in buffer
          if (buffer.trim()) {
            const lines = buffer.split('\n');
            for (const line of lines) {
              if (line.startsWith('data: ')) {
                try {
                  const event: AgentEvent = JSON.parse(line.slice(6));
                  processEvent(event);
                } catch (e) {
                  console.error('Parse error:', e);
                }
              }
            }
          }
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        
        // Process complete events (separated by double newlines)
        const parts = buffer.split('\n\n');
        buffer = parts.pop() || '';

        for (const part of parts) {
          if (!part.trim()) continue;
          
          const lines = part.split('\n');
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const event: AgentEvent = JSON.parse(line.slice(6));
                processEvent(event);
              } catch (e) {
                console.error('Failed to parse SSE event:', e, line);
              }
            }
          }
        }
      }

      setLogs((prev) => [...prev, createLogEntry('success', 'Agent completed successfully')]);
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        setLogs((prev) => [...prev, createLogEntry('info', 'Agent stopped')]);
      } else {
        const message = err instanceof Error ? err.message : 'Unknown error occurred';
        setLogs((prev) => [...prev, createLogEntry('error', message)]);
        setError(message);
      }
    } finally {
      setIsRunning(false);
      abortControllerRef.current = null;
    }
  }, [clearLogs, processEvent]);

  return {
    logs,
    code,
    screenshots,
    isRunning,
    error,
    runAgent,
    clearLogs,
    clearError,
  };
}
