import React, { useRef, useEffect, useState } from 'react';
import { TransformWrapper, TransformComponent } from 'react-zoom-pan-pinch';
import { Lock, Unlock, ZoomIn, ZoomOut } from 'lucide-react';
import { drawText, TextPosition, TextStyle } from '../lib/canvas';

export interface MemePreviewProps {
  templateImageUrl: string;
  texts: Array<{
    id: string;
    text: string;
    position: TextPosition;
    style: Partial<TextStyle>;
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
  const [draggedTextId, setDraggedTextId] = useState<string | null>(null);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

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
          x: (textItem.position.x / 100) * canvasWidth,
          y: (textItem.position.y / 100) * canvasHeight,
          width: (textItem.position.width / 100) * canvasWidth,
          height: (textItem.position.height / 100) * canvasHeight,
        };

        drawText(
          ctx,
          textItem.text,
          absPosition,
          textItem.style,
          canvasWidth,
          canvasHeight
        );

        // Draw selection border if dragging
        if (draggedTextId === textItem.id && !isLocked) {
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
  }, [texts, templateImageUrl, canvasWidth, canvasHeight, draggedTextId, isLocked]);

  const handleCanvasMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (isLocked) return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    // Check if clicked on any text region
    for (const textItem of texts) {
      const absPosition: TextPosition = {
        x: (textItem.position.x / 100) * canvasWidth,
        y: (textItem.position.y / 100) * canvasHeight,
        width: (textItem.position.width / 100) * canvasWidth,
        height: (textItem.position.height / 100) * canvasHeight,
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
    if (!isDragging || !draggedTextId || isLocked) return;

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
    const newX = textItem.position.x + (deltaX / canvasWidth) * 100;
    const newY = textItem.position.y + (deltaY / canvasHeight) * 100;

    // Clamp to canvas bounds
    const clampedX = Math.max(0, Math.min(newX, 100 - textItem.position.width));
    const clampedY = Math.max(0, Math.min(newY, 100 - textItem.position.height));

    onTextPositionUpdate?.(draggedTextId, {
      ...textItem.position,
      x: clampedX,
      y: clampedY,
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
          {isLocked ? (
            <Lock size={16} className="text-acid" />
          ) : (
            <Unlock size={16} className="text-secondary" />
          )}
          <span className="text-sm text-secondary">
            {isLocked ? 'Layout locked' : 'Drag text to reposition'}
          </span>
        </div>
      </div>

      <TransformWrapper
        initialScale={1}
        minScale={0.5}
        maxScale={4}
        wheel={{ step: 0.1 }}
        pinch={{ step: 5 }}
      >
        {({ zoomIn, zoomOut, resetTransform }) => (
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
