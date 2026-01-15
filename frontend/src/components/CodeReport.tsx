import { useState } from 'react';
import Editor from '@monaco-editor/react';
import { Copy, Download, Check, Code, FileCode } from 'lucide-react';
import { Language } from '../types';
import { useTheme } from '../context/ThemeContext';

interface CodeReportProps {
  code: string;
  language: Language;
}

const getMonacoLanguage = (lang: Language) => {
  switch (lang) {
    case 'typescript':
    case 'javascript':
      return 'typescript';
    case 'python':
      return 'python';
    default:
      return 'typescript';
  }
};

const getFileExtension = (lang: Language) => {
  switch (lang) {
    case 'typescript':
      return '.spec.ts';
    case 'javascript':
      return '.spec.js';
    case 'python':
      return '.py';
    default:
      return '.ts';
  }
};

const getLanguageLabel = (lang: Language) => {
  switch (lang) {
    case 'typescript':
      return 'TypeScript';
    case 'javascript':
      return 'JavaScript';
    case 'python':
      return 'Python';
    default:
      return 'TypeScript';
  }
};

export default function CodeReport({ code, language }: CodeReportProps) {
  const [copied, setCopied] = useState(false);
  const { theme } = useTheme();

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([code], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `generated_test${getFileExtension(language)}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  if (!code) {
    return (
      <div className="flex flex-col items-center justify-center h-full py-16 text-muted">
        <FileCode className="w-16 h-16 mb-4 opacity-40" />
        <h3 className="text-lg font-medium mb-2">No Code Generated Yet</h3>
        <p className="text-sm text-center max-w-xs">
          Generated test code will appear here after the agent completes
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header Controls */}
      <div className="flex items-center justify-between p-4 border-b border-border bg-surface/50 flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 bg-surface border border-border rounded-lg">
            <Code className="w-4 h-4 text-primary" />
            <span className="text-sm font-medium">{getLanguageLabel(language)}</span>
          </div>
          <span className="text-sm text-muted">
            {code.split('\n').length} lines
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleCopy}
            className="flex items-center gap-2 px-3 py-1.5 text-sm bg-surface hover:bg-surface-hover border border-border rounded-lg transition-colors"
          >
            {copied ? (
              <>
                <Check className="w-4 h-4 text-success" />
                Copied!
              </>
            ) : (
              <>
                <Copy className="w-4 h-4" />
                Copy Code
              </>
            )}
          </button>
          
          <button
            onClick={handleDownload}
            className="flex items-center gap-2 px-3 py-1.5 text-sm bg-primary hover:bg-primary-hover text-white rounded-lg transition-colors"
          >
            <Download className="w-4 h-4" />
            Download
          </button>
        </div>
      </div>

      {/* Editor */}
      <div className="flex-1 min-h-[500px] overflow-hidden relative">
        <div className="absolute inset-0">
          <Editor
            height="100%"
            language={getMonacoLanguage(language)}
            value={code}
            theme={theme === 'dark' ? 'vs-dark' : 'light'}
            options={{
              readOnly: true,
              minimap: { enabled: true },
              fontSize: 14,
              lineNumbers: 'on',
              scrollBeyondLastLine: false,
              wordWrap: 'on',
              padding: { top: 16, bottom: 16 },
              renderLineHighlight: 'all',
              smoothScrolling: true,
            }}
          />
        </div>
      </div>
    </div>
  );
}
