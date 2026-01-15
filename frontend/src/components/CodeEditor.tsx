import { useState } from 'react';
import Editor from '@monaco-editor/react';
import { Copy, Download, Check, Code } from 'lucide-react';
import { Language } from '../types';

interface CodeEditorProps {
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

export default function CodeEditor({ code, language }: CodeEditorProps) {
  const [copied, setCopied] = useState(false);

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

  return (
    <div className="bg-card rounded-lg border border-border flex flex-col h-full">
      <div className="flex items-center gap-2 p-3 border-b border-border">
        <Code className="w-5 h-5 text-primary" />
        <h2 className="text-lg font-semibold">Generated Test Code</h2>
        
        <div className="ml-auto flex items-center gap-2">
          <button
            onClick={handleCopy}
            disabled={!code}
            className="flex items-center gap-1 px-3 py-1.5 text-sm bg-background hover:bg-border disabled:opacity-50 disabled:cursor-not-allowed rounded-md transition-colors"
          >
            {copied ? (
              <>
                <Check className="w-4 h-4 text-success" />
                Copied!
              </>
            ) : (
              <>
                <Copy className="w-4 h-4" />
                Copy
              </>
            )}
          </button>
          
          <button
            onClick={handleDownload}
            disabled={!code}
            className="flex items-center gap-1 px-3 py-1.5 text-sm bg-background hover:bg-border disabled:opacity-50 disabled:cursor-not-allowed rounded-md transition-colors"
          >
            <Download className="w-4 h-4" />
            Download
          </button>
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-hidden relative">
        {code ? (
          <div className="absolute inset-0">
            <Editor
              height="100%"
              language={getMonacoLanguage(language)}
              value={code}
              theme="vs-dark"
              options={{
                readOnly: true,
                minimap: { enabled: false },
                fontSize: 14,
                lineNumbers: 'on',
                scrollBeyondLastLine: false,
                wordWrap: 'on',
                padding: { top: 16 },
              }}
            />
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-muted">
            <div className="text-center">
              <Code className="w-12 h-12 mx-auto mb-2 opacity-50" />
              <p>Generated code will appear here</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
