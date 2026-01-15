import { useState } from 'react';
import { Image, Code } from 'lucide-react';
import ScreenshotGallery from './ScreenshotGallery';
import CodeReport from './CodeReport';
import { Language } from '../types';

interface ReportsTabProps {
  screenshots: string[];
  code: string;
  language: Language;
}

type ReportSubTab = 'screenshots' | 'code';

export default function ReportsTab({ screenshots, code, language }: ReportsTabProps) {
  const [activeSubTab, setActiveSubTab] = useState<ReportSubTab>('screenshots');

  const subTabs: { id: ReportSubTab; label: string; icon: React.ReactNode; count?: number }[] = [
    { 
      id: 'screenshots', 
      label: 'Screenshots', 
      icon: <Image className="w-4 h-4" />,
      count: screenshots.length 
    },
    { 
      id: 'code', 
      label: 'Generated Code', 
      icon: <Code className="w-4 h-4" />,
      count: code ? 1 : 0
    },
  ];

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Sub-tab Navigation */}
      <div className="flex items-center gap-1 p-2 border-b border-border bg-surface/50 flex-shrink-0">
        {subTabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveSubTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg font-medium transition-all ${
              activeSubTab === tab.id
                ? 'bg-primary text-white shadow-md'
                : 'text-muted hover:text-foreground hover:bg-surface'
            }`}
          >
            {tab.icon}
            <span>{tab.label}</span>
            {tab.count !== undefined && (
              <span className={`px-2 py-0.5 rounded-full text-xs ${
                activeSubTab === tab.id
                  ? 'bg-white/20 text-white'
                  : 'bg-surface-alt text-muted'
              }`}>
                {tab.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Sub-tab Content */}
      <div className="flex-1 min-h-0 overflow-hidden">
        {activeSubTab === 'screenshots' && (
          <ScreenshotGallery screenshots={screenshots} />
        )}
        {activeSubTab === 'code' && (
          <div className="h-full">
            <CodeReport code={code} language={language} />
          </div>
        )}
      </div>
    </div>
  );
}
