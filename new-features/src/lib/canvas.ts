
import { MemeTemplate, MemeSettings } from '../types';

export async function synthesizeMeme(
  template: MemeTemplate,
  texts: string[],
  settings: MemeSettings
): Promise<string> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = 'anonymous'; // Important for CORS
    img.src = template.url;

    img.onload = () => {
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      if (!ctx) {
        reject(new Error('Could not get canvas context'));
        return;
      }

      // Set canvas size to image size
      canvas.width = img.width;
      canvas.height = img.height;

      // Draw base image
      ctx.drawImage(img, 0, 0);

      // Configure text style
      const fontSize = (settings.fontSize * canvas.width) / 600; // Relative to 600px width
      ctx.fillStyle = settings.color;
      ctx.strokeStyle = '#000000';
      ctx.lineWidth = fontSize / 10; // Slightly thicker for canvas punch
      ctx.lineJoin = 'round';
      ctx.miterLimit = 2;
      ctx.textAlign = 'center';
      ctx.font = `900 ${fontSize}px "Impact", "Anton", sans-serif`;

      const drawText = (text: string, targetY: number, targetX: number = canvas.width / 2) => {
        if (!text || text.trim().length === 0) return;

        const displayText = settings.uppercase ? text.toUpperCase() : text;
        const maxWidth = canvas.width * 0.9;
        const maxHeight = canvas.height * 0.4; // Max block height is 40% of canvas
        
        let currentFontSize = fontSize;
        let lines: string[] = [];

        // Dynamic scaling loop
        const calculateLines = (fSize: number) => {
          ctx.font = `900 ${fSize}px "Impact", "Anton", sans-serif`;
          const words = displayText.split(/\s+/);
          const result: string[] = [];
          let currentLine = '';

          for (const word of words) {
            const testLine = currentLine ? `${currentLine} ${word}` : word;
            const metrics = ctx.measureText(testLine);
            
            if (metrics.width > maxWidth) {
              if (currentLine) {
                result.push(currentLine);
                // Check if single word is too wide
                if (ctx.measureText(word).width > maxWidth) {
                   let subWord = '';
                   for (const char of word) {
                     if (ctx.measureText(subWord + char).width > maxWidth) {
                       result.push(subWord);
                       subWord = char;
                     } else {
                       subWord += char;
                     }
                   }
                   currentLine = subWord;
                } else {
                  currentLine = word;
                }
              } else {
                let subWord = '';
                for (const char of word) {
                  if (ctx.measureText(subWord + char).width > maxWidth) {
                    result.push(subWord);
                    subWord = char;
                  } else {
                    subWord += char;
                  }
                }
                currentLine = subWord;
              }
            } else {
              currentLine = testLine;
            }
          }
          if (currentLine) result.push(currentLine);
          return result;
        };

        // If autoResize is enabled, perform aggressive fitting loop
        if (settings.autoResize) {
           let minFontSize = 12;
           while (currentFontSize > minFontSize) {
              lines = calculateLines(currentFontSize);
              if (lines.length * currentFontSize <= maxHeight) break;
              currentFontSize *= 0.9;
           }
        } else {
          // Default behavior: 2-pass safeguard
          lines = calculateLines(currentFontSize);
          if (lines.length * currentFontSize > maxHeight) {
            currentFontSize *= 0.8;
            lines = calculateLines(currentFontSize);
          }
          if (lines.length * currentFontSize > maxHeight) {
            currentFontSize *= 0.7;
            lines = calculateLines(currentFontSize);
          }
        }

        // Final style application
        ctx.font = `900 ${currentFontSize}px "Impact", "Anton", sans-serif`;
        ctx.lineWidth = currentFontSize / 10;
        
        const blockHeight = lines.length * currentFontSize;
        let startY = targetY;

        if (ctx.textBaseline === 'bottom') {
          startY = targetY - (blockHeight - currentFontSize);
        } else if (ctx.textBaseline === 'middle') {
          startY = targetY - (blockHeight / 2) + (currentFontSize / 2);
        }

        lines.forEach((l, i) => {
          const lineY = startY + (i * currentFontSize);
          ctx.strokeText(l, targetX, lineY);
          ctx.fillText(l, targetX, lineY);
        });
      };

      // Draw texts (Matched to Preview layout rules)
      const padding = fontSize * 0.8;
      
      if (settings.positions && settings.positions.length > 0) {
        settings.positions.forEach((pos, i) => {
          if (texts[i]) {
            ctx.textBaseline = 'middle';
            drawText(texts[i], (pos.y / 100) * canvas.height, (pos.x / 100) * canvas.width);
          }
        });
      } else if (texts.length === 1) {
        ctx.textBaseline = 'top';
        drawText(texts[0], padding);
      } else if (texts.length === 2) {
        ctx.textBaseline = 'top';
        drawText(texts[0], padding);
        ctx.textBaseline = 'bottom';
        drawText(texts[1], canvas.height - padding);
      } else if (texts.length >= 3) {
        ctx.textBaseline = 'top';
        drawText(texts[0], padding);
        
        ctx.textBaseline = 'middle';
        drawText(texts[1], canvas.height / 2);
        
        ctx.textBaseline = 'bottom';
        drawText(texts[2], canvas.height - padding);
      }

      resolve(canvas.toDataURL('image/jpeg', 0.8));
    };

    img.onerror = () => reject(new Error('Failed to load template image'));
  });
}
