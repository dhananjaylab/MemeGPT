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

  useEffect(() => {
    setLocked(isLocked);
  }, [isLocked]);

  // Redraw canvas whenever texts or template changes
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const img = new Image();
    img.crossOrigin = 'anonymous';

    img.onload = () => {
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
      // Draw error state
      ctx.fillStyle = '#666';
      ctx.font = '24px Arial';
      ctx.textAlign = 'center';
      ctx.fillText('Failed to load template image', canvasWidth / 2, canvasHeight / 2);
    };

    img.src = templateImageUrl;
  }, [texts, templateImageUrl, canvasWidth, canvasHeight, draggedTextId, locked]);

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
        <h3 className="text-lg font-semibold">Preview</h3>
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

            {/* Zoom Controls */}
            <div className="flex gap-2 justify-center">
              <button
                onClick={() => zoomOut()}
                className="btn-ghost gap-2"
                title="Zoom out"
              >
                <ZoomOut size={16} />
                Zoom Out
              </button>
              <button
                onClick={() => resetTransform()}
                className="btn-ghost"
                title="Reset zoom"
              >
                Reset
              </button>
              <button
                onClick={() => zoomIn()}
                className="btn-ghost gap-2"
                title="Zoom in"
              >
                <ZoomIn size={16} />
                Zoom In
              </button>
            </div>
          </>
        )}
      </TransformWrapper>
    </div>
  );
}
