import { useRef, useEffect, useState } from 'react';
import { TransformWrapper, TransformComponent } from 'react-zoom-pan-pinch';
import { Lock, Unlock, ZoomIn, ZoomOut } from 'lucide-react';
import { drawText } from '../lib/canvas';
import type { TextPosition } from '../lib/canvas';

export interface MemePreviewProps {
  templateImageUrl: string;
  texts: Array<{
    id: string;
    text: string;
    color?: string;
    fontSize?: number;
    uppercase?: boolean;
    stroke?: boolean;
    autoResize?: boolean;
    x: number;
    y: number;
    width?: number;
    height?: number;
  }>;
  onTextPositionUpdate?: (textId: string, newPosition: TextPosition) => void;
  isLocked?: boolean;
  canvasWidth?: number;
  canvasHeight?: number;
}

export function MemePreview({
  templateImageUrl,
  texts,
  onTextPositionUpdate,
  isLocked = false,
  canvasWidth = 800,
  canvasHeight = 600,
}: MemePreviewProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [locked, setLocked] = useState(isLocked);
  const [draggedTextId, setDraggedTextId] = useState<string | null>(null);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [imageLoadError, setImageLoadError] = useState(false);
  const [isImageLoading, setIsImageLoading] = useState(true);
  const [retryCount, setRetryCount] = useState(0);

  useEffect(() => {
    setLocked(isLocked);
  }, [isLocked]);

  // Redraw canvas whenever texts or template changes
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Reset states
    setImageLoadError(false);
    setIsImageLoading(true);

    const img = new Image();
    // Note: Local images from /frames/ don't need CORS since they're same-origin
    // Only set crossOrigin for external proxy URLs
    if (templateImageUrl.startsWith('/api/memes/proxy-image')) {
      img.crossOrigin = 'anonymous';
    }
    
    img.onload = () => {
      setIsImageLoading(false);
      setImageLoadError(false);
      
      // Draw base image
      ctx.drawImage(img, 0, 0, canvasWidth, canvasHeight);

      // Draw all text overlays
      texts.forEach((textItem) => {
        const absPosition: TextPosition = {
          x: (textItem.x / 100) * canvasWidth,
          y: (textItem.y / 100) * canvasHeight,
          width: ((textItem.width || 40) / 100) * canvasWidth,
          height: ((textItem.height || 20) / 100) * canvasHeight,
        };

        drawText(
          ctx,
          textItem.text,
          absPosition,
          {
            color: textItem.color,
            fontSize: textItem.fontSize,
            uppercase: textItem.uppercase,
            stroke: textItem.stroke,
          },
          canvasWidth,
          canvasHeight
        );

        // Draw selection border if dragging
        if (draggedTextId === textItem.id && !locked) {
          ctx.strokeStyle = '#9eff00';
          ctx.lineWidth = 3;
          ctx.strokeRect(absPosition.x, absPosition.y, absPosition.width, absPosition.height);
        }
      });
    };

    img.onerror = () => {
      setIsImageLoading(false);
      setImageLoadError(true);
      
      // Draw error state with better styling
      ctx.fillStyle = '#1a1a1a';
      ctx.fillRect(0, 0, canvasWidth, canvasHeight);
      
      ctx.fillStyle = '#666';
      ctx.font = 'bold 20px Arial';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText('Failed to load template image', canvasWidth / 2, canvasHeight / 2 - 20);
      
      ctx.font = '14px Arial';
      ctx.fillStyle = '#888';
      ctx.fillText('Click "Retry" below to try again', canvasWidth / 2, canvasHeight / 2 + 10);
      
      // Draw icon
      ctx.font = '48px Arial';
      ctx.fillText('🖼️', canvasWidth / 2, canvasHeight / 2 - 60);
    };

    img.src = templateImageUrl;
  }, [texts, templateImageUrl, canvasWidth, canvasHeight, draggedTextId, locked, retryCount]);

  const handleRetryImageLoad = () => {
    setRetryCount(prev => prev + 1);
  };

  const handleCanvasMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (locked) return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    // Check if clicked on any text region
    for (const textItem of texts) {
      const absPosition: TextPosition = {
        x: (textItem.x / 100) * canvasWidth,
        y: (textItem.y / 100) * canvasHeight,
        width: ((textItem.width || 40) / 100) * canvasWidth,
        height: ((textItem.height || 20) / 100) * canvasHeight,
      };

      if (
        x >= absPosition.x &&
        x <= absPosition.x + absPosition.width &&
        y >= absPosition.y &&
        y <= absPosition.y + absPosition.height
      ) {
        setIsDragging(true);
        setDraggedTextId(textItem.id);
        setDragStart({ x, y });
        return;
      }
    }
  };

  const handleCanvasMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDragging || !draggedTextId || locked) return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const currentX = e.clientX - rect.left;
    const currentY = e.clientY - rect.top;

    const deltaX = currentX - dragStart.x;
    const deltaY = currentY - dragStart.y;

    const textItem = texts.find((t) => t.id === draggedTextId);
    if (!textItem) return;

    // Calculate new percentage position
    const newX = textItem.x + (deltaX / canvasWidth) * 100;
    const newY = textItem.y + (deltaY / canvasHeight) * 100;

    // Clamp to canvas bounds
    const clampedX = Math.max(0, Math.min(newX, 100 - (textItem.width || 40)));
    const clampedY = Math.max(0, Math.min(newY, 100 - (textItem.height || 20)));

    onTextPositionUpdate?.(draggedTextId, {
      x: clampedX,
      y: clampedY,
      width: textItem.width || 40,
      height: textItem.height || 20,
    });

    setDragStart({ x: currentX, y: currentY });
  };

  const handleCanvasMouseUp = () => {
    setIsDragging(false);
    setDraggedTextId(null);
  };

  return (
    <div className="card-dark">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <h3 className="text-lg font-semibold">Preview</h3>
          {isImageLoading && (
            <div className="flex items-center gap-1 text-xs text-secondary">
              <div className="w-3 h-3 border-2 border-acid border-t-transparent rounded-full animate-spin" />
              Loading...
            </div>
          )}
          {imageLoadError && (
            <span className="text-xs text-red-500">⚠️ Image failed to load</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {locked ? (
            <Lock size={16} className="text-acid" />
          ) : (
            <Unlock size={16} className="text-secondary" />
          )}
          <span className="text-sm text-secondary">
            {locked ? 'Layout locked' : 'Drag text to reposition'}
          </span>
          <button
            onClick={() => setLocked((prev) => !prev)}
            className="btn-ghost py-1 px-2 text-xs"
          >
            {locked ? 'Unlock' : 'Lock'}
          </button>
        </div>
      </div>

      <TransformWrapper
        initialScale={1}
        minScale={0.5}
        maxScale={4}
        wheel={{ step: 0.1 }}
        pinch={{ step: 5 }}
      >
        {({ zoomIn, zoomOut, resetTransform }: { zoomIn: () => void; zoomOut: () => void; resetTransform: () => void }) => (
          <>
            <div className="relative bg-surface-2 rounded-lg overflow-hidden mb-4 border border-border">
              <TransformComponent
                wrapperClass="w-full"
                contentClass="flex justify-center"
              >
                <canvas
                  ref={canvasRef}
                  width={canvasWidth}
                  height={canvasHeight}
                  className="max-w-full h-auto cursor-move"
                  onMouseDown={handleCanvasMouseDown}
                  onMouseMove={handleCanvasMouseMove}
                  onMouseUp={handleCanvasMouseUp}
                  onMouseLeave={handleCanvasMouseUp}
                />
              </TransformComponent>
            </div>

            {/* Zoom Controls and Retry Button */}
            <div className="flex gap-2 justify-center flex-wrap">
              <button
                onClick={() => zoomOut()}
                className="btn-ghost gap-2"
                title="Zoom out"
                disabled={imageLoadError}
              >
                <ZoomOut size={16} />
                Zoom Out
              </button>
              <button
                onClick={() => resetTransform()}
                className="btn-ghost"
                title="Reset zoom"
                disabled={imageLoadError}
              >
                Reset
              </button>
              <button
                onClick={() => zoomIn()}
                className="btn-ghost gap-2"
                title="Zoom in"
                disabled={imageLoadError}
              >
                <ZoomIn size={16} />
                Zoom In
              </button>
              {imageLoadError && (
                <button
                  onClick={handleRetryImageLoad}
                  className="btn-primary gap-2"
                  title="Retry loading image"
                >
                  <svg
                    className="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                    />
                  </svg>
                  Retry
                </button>
              )}
            </div>
          </>
        )}
      </TransformWrapper>
    </div>
  );
}
