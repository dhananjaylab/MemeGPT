
import { MemeTemplate, MemeSettings, TextPosition } from '../types';
import { motion, useDragControls } from 'motion/react';
import { TransformWrapper, TransformComponent } from 'react-zoom-pan-pinch';
import { ZoomIn, ZoomOut, RotateCcw, MousePointer2, Move } from 'lucide-react';
import { useRef } from 'react';

interface MemePreviewProps {
  template: MemeTemplate | null;
  texts: string[];
  settings: MemeSettings;
  onPositionChange?: (index: number, pos: TextPosition) => void;
}

export function MemePreview({ template, texts, settings, onPositionChange }: MemePreviewProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  if (!template) {
    return (
      <div className="aspect-square bg-black/40 border-2 border-dashed border-border rounded-2xl flex flex-col items-center justify-center text-center p-6 text-muted">
        <div className="w-12 h-12 rounded-full border-2 border-current border-t-transparent animate-spin mb-4 opacity-10" />
        <p className="text-sm font-mono uppercase tracking-widest">Select a template to preview</p>
      </div>
    );
  }

  const handleDragEnd = (index: number, e: any, info: any) => {
    if (!containerRef.current || !onPositionChange) return;

    const rect = containerRef.current.getBoundingClientRect();
    
    // Use the actual target element's center to determine new percentages
    // This prevents "jumping" when grabbing the text from the edges
    const target = e.target as HTMLElement;
    const elementRect = target.getBoundingClientRect();
    
    const centerX = elementRect.left + elementRect.width / 2;
    const centerY = elementRect.top + elementRect.height / 2;

    let x = ((centerX - rect.left) / rect.width) * 100;
    let y = ((centerY - rect.top) / rect.height) * 100;

    // Clamp with a safer buffer to account for text width/height
    // This combined with dragConstraints ensures the text stays visible
    x = Math.max(5, Math.min(95, x));
    y = Math.max(5, Math.min(95, y));

    onPositionChange(index, { x, y });
  };

  return (
    <div className="flex flex-col gap-4 w-full">
      <div className="relative rounded-2xl overflow-hidden bg-black border border-border shadow-2xl group">
        <TransformWrapper
          initialScale={1}
          minScale={0.5}
          maxScale={4}
          centerOnInit={true}
          panning={{
            excluded: ['no-pan'], // Prevent image panning when dragging text
          }}
        >
          {({ zoomIn, zoomOut, resetTransform }) => (
            <>
              {/* Zoom Controls Overlay */}
              <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-2 px-3 py-2 bg-black/60 backdrop-blur-md rounded-full border border-white/10 opacity-0 group-hover:opacity-100 transition-opacity duration-300 z-30 font-mono">
                <button onClick={() => zoomIn()} className="p-1.5 hover:text-acid transition-colors"><ZoomIn size={18} /></button>
                <div className="w-px h-4 bg-white/10" />
                <button onClick={() => zoomOut()} className="p-1.5 hover:text-acid transition-colors"><ZoomOut size={18} /></button>
                <div className="w-px h-4 bg-white/10" />
                <button onClick={() => resetTransform()} className="p-1.5 hover:text-acid transition-colors"><RotateCcw size={18} /></button>
              </div>

              <div className="absolute top-4 left-4 flex items-center gap-2 bg-black/40 backdrop-blur-sm px-3 py-1.5 rounded-full border border-white/5 text-[10px] font-mono text-muted uppercase tracking-widest z-20 pointer-events-none">
                <Move size={12} className={settings.manualLayout ? "text-acid" : "text-white/20"} />
                {settings.manualLayout ? "Drag Text to Position" : "Auto-Layout Locked"}
              </div>

              <TransformComponent
                wrapperStyle={{ width: "100%", height: "auto", maxHeight: "650px", borderRadius: "1rem" }}
                contentStyle={{ width: "100%", display: "flex", justifyContent: "center" }}
              >
                <div ref={containerRef} className={`relative inline-block max-w-full ${!settings.manualLayout ? 'cursor-grab active:cursor-grabbing' : ''}`}>
                  <img 
                    src={template.url} 
                    alt="Preview" 
                    className="max-w-full h-auto block z-0 pointer-events-none select-none" 
                  />
                  
                  {/* Text Overlays - Manual or Auto */}
                  <div className="absolute inset-0 z-10 pointer-events-none">
                    {texts.map((text, i) => {
                      const manualPos = settings.positions?.[i];
                      
                      return (
                        <motion.div
                          key={i}
                          drag={settings.manualLayout}
                          dragConstraints={containerRef}
                          dragElastic={0.1}
                          dragMomentum={false}
                          onDragEnd={(e, info) => handleDragEnd(i, e, info)}
                          onPointerDown={(e) => settings.manualLayout && e.stopPropagation()} // Direct isolation
                          className={`absolute select-none flex items-center justify-center p-2 ${
                            settings.manualLayout ? 'pointer-events-auto cursor-move no-pan' : 'pointer-events-none'
                          }`}
                          animate={{ 
                            left: manualPos ? `${manualPos.x}%` : '50%',
                            top: manualPos ? `${manualPos.y}%` : i === 0 ? '15%' : i === 1 ? '85%' : '50%',
                            x: "-50%",
                            y: "-50%"
                          }}
                          transition={{ type: "spring", stiffness: 400, damping: 35 }}
                          style={{
                            color: settings.color,
                            fontSize: `${Math.max(16, settings.fontSize)}px`,
                            textTransform: settings.uppercase ? 'uppercase' : 'none',
                            fontFamily: '"Impact", "Anton", "Arial Black", sans-serif',
                            WebkitTextStroke: `${settings.fontSize / 15}px black`,
                            paintOrder: 'stroke fill',
                            fontWeight: 900,
                            lineHeight: 1,
                            textAlign: 'center',
                            minWidth: '100px',
                            maxWidth: '90%',
                            wordBreak: 'break-word',
                            filter: 'drop-shadow(0 4px 8px rgba(0,0,0,0.6))',
                            zIndex: 10 + i,
                          }}
                        >
                          {text && text.trim().length > 0 ? text : ''}
                        </motion.div>
                      );
                    })}
                  </div>
                </div>
              </TransformComponent>
            </>
          )}
        </TransformWrapper>
      </div>
    </div>
  );
}
