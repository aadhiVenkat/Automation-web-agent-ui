export type LLMProvider = 'gemini' | 'perplexity' | 'hf';
export type Framework = 'playwright';
export type Language = 'typescript' | 'python' | 'javascript';

export interface AgentConfig {
  apiKey: string;
  provider: LLMProvider;
  url: string;
  task: string;
  framework: Framework;
  language: Language;
  headless?: boolean;
  useBoostPrompt?: boolean;  // Set false for more consistent behavior
  useStructuredExecution?: boolean;  // Break down complex tasks into steps
  verifyEachStep?: boolean;  // Verify each step completes (with structured execution)
  // URL authentication (for sites requiring basic auth)
  urlUsername?: string;
  urlPassword?: string;
}

export interface AgentEvent {
  type: 'log' | 'screenshot' | 'code' | 'error' | 'complete';
  message?: string;
  screenshot?: string;
  code?: string;
  timestamp: string;
}

export interface LogEntry {
  id: string;
  type: 'info' | 'success' | 'error' | 'tool';
  message: string;
  timestamp: Date;
}
