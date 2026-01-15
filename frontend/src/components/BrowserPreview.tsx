import { useState, useEffect } from 'react';
import { Monitor, ImageOff, ChevronLeft, ChevronRight, Maximize2, X } from 'lucide-react';

interface BrowserPreviewProps {
  screenshots: string[];
}

export default function BrowserPreview({ screenshots }: BrowserPreviewProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isFullscreen, setIsFullscreen] = useState(false);

  const hasScreenshots = screenshots.length > 0;
  const currentScreenshot = hasScreenshots ? screenshots[currentIndex] : null;

  const goToPrevious = () => {
    setCurrentIndex((prev) => (prev > 0 ? prev - 1 : screenshots.length - 1));
  };

  const goToNext = () => {
    setCurrentIndex((prev) => (prev < screenshots.length - 1 ? prev + 1 : 0));
  };

  // Auto-advance to latest screenshot when new one arrives
  useEffect(() => {
    if (screenshots.length > 0) {
      setCurrentIndex(screenshots.length - 1);
    }
  }, [screenshots.length]);

  return (
    <>
      <div className="bg-card rounded-lg border border-border flex flex-col">
        <div className="flex items-center gap-2 p-3 border-b border-border">
          <Monitor className="w-5 h-5 text-primary" />
          <h2 className="text-lg font-semibold">Browser Preview</h2>
          {hasScreenshots && (
            <>
              <span className="text-sm text-muted ml-auto">
                {currentIndex + 1} / {screenshots.length}
              </span>
              <button
                onClick={() => setIsFullscreen(true)}
                className="p-1 hover:bg-border rounded transition-colors"
                title="Fullscreen"
              >
                <Maximize2 className="w-4 h-4" />
              </button>
            </>
          )}
        </div>

        <div className="relative aspect-video bg-[#0a0a0a] flex items-center justify-center overflow-hidden">
          {currentScreenshot ? (
            <>
              <img
                src={currentScreenshot}
                alt={`Screenshot ${currentIndex + 1}`}
                className="w-full h-full object-contain"
              />
              
              {/* Navigation buttons */}
              {screenshots.length > 1 && (
                <>
                  <button
                    onClick={goToPrevious}
                    className="absolute left-2 top-1/2 -translate-y-1/2 p-2 bg-black/50 hover:bg-black/70 rounded-full transition-colors"
                  >
                    <ChevronLeft className="w-5 h-5" />
                  </button>
                  <button
                    onClick={goToNext}
                    className="absolute right-2 top-1/2 -translate-y-1/2 p-2 bg-black/50 hover:bg-black/70 rounded-full transition-colors"
                  >
                    <ChevronRight className="w-5 h-5" />
                  </button>
                </>
              )}
            </>
          ) : (
            <div className="text-center text-muted">
              <ImageOff className="w-12 h-12 mx-auto mb-2 opacity-50" />
              <p>Screenshots will appear here</p>
            </div>
          )}
        </div>

        {/* Thumbnail strip */}
        {screenshots.length > 1 && (
          <div className="p-2 border-t border-border overflow-x-auto">
            <div className="flex gap-2">
              {screenshots.map((screenshot, index) => (
                <button
                  key={index}
                  onClick={() => setCurrentIndex(index)}
                  className={`flex-shrink-0 w-16 h-10 rounded overflow-hidden border-2 transition-colors ${
                    index === currentIndex ? 'border-primary' : 'border-transparent hover:border-border'
                  }`}
                >
                  <img
                    src={screenshot}
                    alt={`Thumbnail ${index + 1}`}
                    className="w-full h-full object-cover"
                  />
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Fullscreen modal */}
      {isFullscreen && currentScreenshot && (
        <div 
          className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center"
          onClick={() => setIsFullscreen(false)}
        >
          <button
            onClick={() => setIsFullscreen(false)}
            className="absolute top-4 right-4 p-2 bg-white/10 hover:bg-white/20 rounded-full transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
          
          <img
            src={currentScreenshot}
            alt={`Screenshot ${currentIndex + 1}`}
            className="max-w-[95vw] max-h-[95vh] object-contain"
            onClick={(e) => e.stopPropagation()}
          />
          
          {screenshots.length > 1 && (
            <>
              <button
                onClick={(e) => { e.stopPropagation(); goToPrevious(); }}
                className="absolute left-4 top-1/2 -translate-y-1/2 p-3 bg-white/10 hover:bg-white/20 rounded-full transition-colors"
              >
                <ChevronLeft className="w-8 h-8" />
              </button>
              <button
                onClick={(e) => { e.stopPropagation(); goToNext(); }}
                className="absolute right-4 top-1/2 -translate-y-1/2 p-3 bg-white/10 hover:bg-white/20 rounded-full transition-colors"
              >
                <ChevronRight className="w-8 h-8" />
              </button>
            </>
          )}
          
          <div className="absolute bottom-4 left-1/2 -translate-x-1/2 text-white/80">
            {currentIndex + 1} / {screenshots.length}
          </div>
        </div>
      )}
    </>
  );
}
