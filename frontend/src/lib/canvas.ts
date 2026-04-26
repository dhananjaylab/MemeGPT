/**
 * Canvas Utilities for Meme Rendering
 * Handles dynamic text rendering with word-wrap, auto-resize, and text positioning
 */

export interface TextPosition {
  x: number;
  y: number;
  width: number;
  height: number;
  maxWidth?: number;
}

export interface TextStyle {
  text: string;
  color: string;
  fontSize: number;
  fontFamily: string;
  stroke: boolean;
  strokeColor?: string;
  uppercase?: boolean;
}

export interface CanvasConfig {
  width: number;
  height: number;
  baseImageUrl: string;
  texts: Array<TextStyle & TextPosition>;
}

const FONTS = {
  impact: 'bold Impact, Arial Black, sans-serif',
  anton: 'Anton, sans-serif',
  mono: '"JetBrains Mono", monospace',
};

const MIN_FONT_SIZE = 12;
const MAX_FONT_SIZE = 72;
const BASELINE_WIDTH = 600;

/**
 * Calculate responsive font size based on canvas width
 * Scales from a 600px baseline
 */
export function calculateResponsiveFontSize(
  baseFontSize: number,
  canvasWidth: number
): number {
  const scaleFactor = canvasWidth / BASELINE_WIDTH;
  const scaled = baseFontSize * scaleFactor;
  return Math.max(MIN_FONT_SIZE, Math.min(scaled, MAX_FONT_SIZE));
}

/**
 * Wrap text to fit within maxWidth with given font
 */
export function wrapText(
  ctx: CanvasRenderingContext2D,
  text: string,
  maxWidth: number,
  fontSize: number,
  fontFamily: string
): string[] {
  ctx.font = `${fontSize}px ${fontFamily}`;
  
  const words = text.split(' ');
  const lines: string[] = [];
  let currentLine = '';

  for (const word of words) {
    const testLine = currentLine ? `${currentLine} ${word}` : word;
    const metrics = ctx.measureText(testLine);

    if (metrics.width > maxWidth && currentLine) {
      lines.push(currentLine);
      currentLine = word;
    } else {
      currentLine = testLine;
    }
  }

  if (currentLine) {
    lines.push(currentLine);
  }

  return lines.length > 0 ? lines : [text];
}

/**
 * Draw text on canvas with auto-resize, word-wrap, and styling
 */
export function drawText(
  ctx: CanvasRenderingContext2D,
  text: string,
  position: TextPosition,
  style: Partial<TextStyle>,
  canvasWidth: number,
  _canvasHeight: number
): void {
  if (!text) return;

  const {
    color = '#ffffff',
    fontSize = 24,
    fontFamily = FONTS.impact,
    stroke = false,
    strokeColor = '#000000',
    uppercase = false,
  } = style;

  const displayText = uppercase ? text.toUpperCase() : text;
  const responsiveFontSize = calculateResponsiveFontSize(fontSize, canvasWidth);
  const maxWidth = position.maxWidth || canvasWidth * 0.9;

  // Wrap text to fit
  const lines = wrapText(ctx, displayText, maxWidth, responsiveFontSize, fontFamily);

  // Calculate total height needed
  const lineHeight = responsiveFontSize * 1.2;
  const totalHeight = lines.length * lineHeight;

  // Vertical centering if needed
  const startY = position.y + (position.height - totalHeight) / 2 + responsiveFontSize;

  // Draw each line
  lines.forEach((line, index) => {
    const y = startY + index * lineHeight;

    // Draw stroke (outline)
    if (stroke) {
      ctx.strokeStyle = strokeColor;
      ctx.lineWidth = responsiveFontSize * 0.08;
      ctx.font = `bold ${responsiveFontSize}px ${fontFamily}`;
      ctx.textAlign = 'center';
      ctx.strokeText(line, position.x + position.width / 2, y);
    }

    // Draw fill text
    ctx.fillStyle = color;
    ctx.font = `bold ${responsiveFontSize}px ${fontFamily}`;
    ctx.textAlign = 'center';
    ctx.fillText(line, position.x + position.width / 2, y);
  });
}

/**
 * Render complete meme to canvas
 * Returns canvas element for preview or image data URL for saving
 */
export async function renderMemeCanvas(config: CanvasConfig): Promise<HTMLCanvasElement> {
  const canvas = document.createElement('canvas');
  canvas.width = config.width;
  canvas.height = config.height;
  const ctx = canvas.getContext('2d');

  if (!ctx) {
    throw new Error('Failed to get canvas context');
  }

  // Load and draw base image
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = 'anonymous';

    img.onload = () => {
      ctx.drawImage(img, 0, 0, config.width, config.height);

      // Draw each text overlay
      config.texts.forEach((textConfig) => {
        drawText(
          ctx,
          textConfig.text,
          {
            x: (textConfig.x / 100) * config.width,
            y: (textConfig.y / 100) * config.height,
            width: (textConfig.width / 100) * config.width,
            height: (textConfig.height / 100) * config.height,
            maxWidth: (textConfig.maxWidth || 90) / 100 * config.width,
          },
          {
            color: textConfig.color,
            fontSize: textConfig.fontSize,
            fontFamily: textConfig.fontFamily,
            stroke: textConfig.stroke,
            strokeColor: textConfig.strokeColor,
            uppercase: textConfig.uppercase,
          },
          config.width,
          config.height
        );
      });

      resolve(canvas);
    };

    img.onerror = () => {
      reject(new Error(`Failed to load image: ${config.baseImageUrl}`));
    };

    img.src = config.baseImageUrl;
  });
}

/**
 * Convert canvas to blob for download/upload
 */
export async function canvasToBlob(canvas: HTMLCanvasElement): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (blob) {
        resolve(blob);
      } else {
        reject(new Error('Failed to convert canvas to blob'));
      }
    }, 'image/png');
  });
}

/**
 * Get image data URL from canvas
 */
export function canvasToDataURL(canvas: HTMLCanvasElement, format: 'png' | 'jpeg' = 'png'): string {
  const mimeType = format === 'jpeg' ? 'image/jpeg' : 'image/png';
  return canvas.toDataURL(mimeType);
}

/**
 * Measure text dimensions
 */
export function measureText(
  ctx: CanvasRenderingContext2D,
  text: string,
  fontSize: number,
  fontFamily: string
): { width: number; height: number } {
  ctx.font = `${fontSize}px ${fontFamily}`;
  const metrics = ctx.measureText(text);
  return {
    width: metrics.width,
    height: fontSize,
  };
}

/**
 * Calculate auto font size to fit text in box
 */
export function calculateAutoFontSize(
  ctx: CanvasRenderingContext2D,
  text: string,
  maxWidth: number,
  maxHeight: number,
  fontFamily: string,
  minSize: number = MIN_FONT_SIZE,
  maxSize: number = MAX_FONT_SIZE
): number {
  let fontSize = maxSize;

  while (fontSize > minSize) {
    ctx.font = `${fontSize}px ${fontFamily}`;
    const metrics = ctx.measureText(text);

    if (metrics.width <= maxWidth && fontSize <= maxHeight) {
      return fontSize;
    }

    fontSize -= 2;
  }

  return minSize;
}
