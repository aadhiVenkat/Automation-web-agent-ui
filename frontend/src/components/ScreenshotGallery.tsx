import { useState, useEffect } from 'react';
import { Monitor, ImageOff, ChevronLeft, ChevronRight, Maximize2, X, Download, Grid3X3 } from 'lucide-react';

interface ScreenshotGalleryProps {
  screenshots: string[];
}

export default function ScreenshotGallery({ screenshots }: ScreenshotGalleryProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [viewMode, setViewMode] = useState<'single' | 'grid'>('single');

  const hasScreenshots = screenshots.length > 0;
  const currentScreenshot = hasScreenshots ? screenshots[currentIndex] : null;

  const goToPrevious = () => {
    setCurrentIndex((prev) => (prev > 0 ? prev - 1 : screenshots.length - 1));
  };

  const goToNext = () => {
    setCurrentIndex((prev) => (prev < screenshots.length - 1 ? prev + 1 : 0));
  };

  const downloadScreenshot = (index: number) => {
    const link = document.createElement('a');
    link.href = screenshots[index];
    link.download = `screenshot-${index + 1}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const downloadAllScreenshots = () => {
    screenshots.forEach((_, index) => {
      setTimeout(() => downloadScreenshot(index), index * 200);
    });
  };

  // Auto-advance to latest screenshot when new one arrives
  useEffect(() => {
    if (screenshots.length > 0) {
      setCurrentIndex(screenshots.length - 1);
    }
  }, [screenshots.length]);

  if (!hasScreenshots) {
    return (
      <div className="flex flex-col items-center justify-center h-full py-16 text-muted">
        <ImageOff className="w-16 h-16 mb-4 opacity-40" />
        <h3 className="text-lg font-medium mb-2">No Screenshots Yet</h3>
        <p className="text-sm text-center max-w-xs">
          Screenshots will appear here as the agent interacts with the browser
        </p>
      </div>
    );
  }

  return (
    <>
      <div className="flex flex-col h-full">
        {/* Header Controls */}
        <div className="flex items-center justify-between p-4 border-b border-border bg-surface/50">
          <div className="flex items-center gap-4">
            <span className="text-sm font-medium text-foreground">
              {screenshots.length} Screenshot{screenshots.length !== 1 ? 's' : ''}
            </span>
            <div className="flex items-center bg-surface rounded-lg border border-border p-1">
              <button
                onClick={() => setViewMode('single')}
                className={`p-1.5 rounded ${viewMode === 'single' ? 'bg-primary text-white' : 'text-muted hover:text-foreground'}`}
                title="Single view"
              >
                <Monitor className="w-4 h-4" />
              </button>
              <button
                onClick={() => setViewMode('grid')}
                className={`p-1.5 rounded ${viewMode === 'grid' ? 'bg-primary text-white' : 'text-muted hover:text-foreground'}`}
                title="Grid view"
              >
                <Grid3X3 className="w-4 h-4" />
              </button>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={downloadAllScreenshots}
              className="flex items-center gap-2 px-3 py-1.5 text-sm bg-surface hover:bg-surface-hover border border-border rounded-lg transition-colors"
            >
              <Download className="w-4 h-4" />
              Download All
            </button>
          </div>
        </div>

        {/* Content */}
        {viewMode === 'single' ? (
          <div className="flex-1 flex flex-col">
            {/* Main Preview */}
            <div className="flex-1 relative bg-surface-alt flex items-center justify-center p-4 min-h-[400px]">
              <img
                src={currentScreenshot!}
                alt={`Screenshot ${currentIndex + 1}`}
                className="max-w-full max-h-full object-contain rounded-lg shadow-lg cursor-pointer"
                onClick={() => setIsFullscreen(true)}
              />
              
              {/* Navigation buttons */}
              {screenshots.length > 1 && (
                <>
                  <button
                    onClick={goToPrevious}
                    className="absolute left-4 top-1/2 -translate-y-1/2 p-2 bg-background/80 hover:bg-background border border-border rounded-full transition-colors shadow-lg"
                  >
                    <ChevronLeft className="w-5 h-5" />
                  </button>
                  <button
                    onClick={goToNext}
                    className="absolute right-4 top-1/2 -translate-y-1/2 p-2 bg-background/80 hover:bg-background border border-border rounded-full transition-colors shadow-lg"
                  >
                    <ChevronRight className="w-5 h-5" />
                  </button>
                </>
              )}

              {/* Expand button */}
              <button
                onClick={() => setIsFullscreen(true)}
                className="absolute top-4 right-4 p-2 bg-background/80 hover:bg-background border border-border rounded-lg transition-colors"
                title="View fullscreen"
              >
                <Maximize2 className="w-4 h-4" />
              </button>

              {/* Download current */}
              <button
                onClick={() => downloadScreenshot(currentIndex)}
                className="absolute bottom-4 right-4 p-2 bg-background/80 hover:bg-background border border-border rounded-lg transition-colors"
                title="Download this screenshot"
              >
                <Download className="w-4 h-4" />
              </button>
            </div>

            {/* Thumbnail Strip */}
            <div className="p-3 border-t border-border bg-surface overflow-x-auto">
              <div className="flex gap-2">
                {screenshots.map((screenshot, index) => (
                  <button
                    key={index}
                    onClick={() => setCurrentIndex(index)}
                    className={`flex-shrink-0 relative group rounded-lg overflow-hidden border-2 transition-all ${
                      index === currentIndex 
                        ? 'border-primary ring-2 ring-primary/30' 
                        : 'border-border hover:border-primary/50'
                    }`}
                  >
                    <img
                      src={screenshot}
                      alt={`Thumbnail ${index + 1}`}
                      className="w-20 h-12 object-cover"
                    />
                    <span className="absolute bottom-0 left-0 right-0 bg-black/60 text-white text-xs py-0.5 text-center">
                      #{index + 1}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          /* Grid View */
          <div className="flex-1 overflow-auto p-4">
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {screenshots.map((screenshot, index) => (
                <div
                  key={index}
                  className="group relative bg-surface rounded-lg overflow-hidden border border-border hover:border-primary/50 transition-all cursor-pointer"
                  onClick={() => {
                    setCurrentIndex(index);
                    setViewMode('single');
                  }}
                >
                  <div className="aspect-video">
                    <img
                      src={screenshot}
                      alt={`Screenshot ${index + 1}`}
                      className="w-full h-full object-cover"
                    />
                  </div>
                  <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors flex items-center justify-center">
                    <Maximize2 className="w-6 h-6 text-white opacity-0 group-hover:opacity-100 transition-opacity" />
                  </div>
                  <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 to-transparent p-2">
                    <span className="text-white text-sm font-medium">Step {index + 1}</span>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      downloadScreenshot(index);
                    }}
                    className="absolute top-2 right-2 p-1.5 bg-black/50 hover:bg-black/70 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <Download className="w-4 h-4 text-white" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Fullscreen Modal */}
      {isFullscreen && currentScreenshot && (
        <div 
          className="fixed inset-0 z-50 bg-black/95 flex items-center justify-center"
          onClick={() => setIsFullscreen(false)}
        >
          <button
            onClick={() => setIsFullscreen(false)}
            className="absolute top-4 right-4 p-2 bg-white/10 hover:bg-white/20 rounded-full transition-colors z-10"
          >
            <X className="w-6 h-6 text-white" />
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
                <ChevronLeft className="w-8 h-8 text-white" />
              </button>
              <button
                onClick={(e) => { e.stopPropagation(); goToNext(); }}
                className="absolute right-4 top-1/2 -translate-y-1/2 p-3 bg-white/10 hover:bg-white/20 rounded-full transition-colors"
              >
                <ChevronRight className="w-8 h-8 text-white" />
              </button>
            </>
          )}
          
          <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-4">
            <span className="text-white/80 bg-black/50 px-3 py-1 rounded-full">
              {currentIndex + 1} / {screenshots.length}
            </span>
            <button
              onClick={(e) => { e.stopPropagation(); downloadScreenshot(currentIndex); }}
              className="flex items-center gap-2 px-3 py-1.5 bg-white/10 hover:bg-white/20 rounded-full text-white text-sm transition-colors"
            >
              <Download className="w-4 h-4" />
              Download
            </button>
          </div>
        </div>
      )}
    </>
  );
}
