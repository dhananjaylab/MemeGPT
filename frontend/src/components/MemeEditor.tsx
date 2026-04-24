import React, { useState } from 'react';
import { Type, Palette, ArrowUpToLine, Settings2 } from 'lucide-react';

export interface MemeEditorProps {
  texts: Array<{
    id: string;
    text: string;
    color?: string;
    fontSize?: number;
    uppercase?: boolean;
    stroke?: boolean;
    autoResize?: boolean;
  }>;
  onTextUpdate?: (textId: string, newText: string) => void;
  onStyleUpdate?: (textId: string, newStyle: Record<string, string | number | boolean>) => void;
}

const COLOR_PRESETS = [
  { name: 'White', value: '#ffffff' },
  { name: 'Black', value: '#000000' },
  { name: 'Lime', value: '#B0FF00' },
  { name: 'Red', value: '#ff3333' },
  { name: 'Cyan', value: '#00ccff' },
];

const FONT_SIZES = [12, 18, 24, 32, 40, 48, 56, 64, 72];

export function MemeEditor({
  texts,
  onTextUpdate,
  onStyleUpdate,
}: MemeEditorProps) {
  const [selectedTextId, setSelectedTextId] = useState<string | null>(texts[0]?.id || null);

  const selectedText = texts.find((t) => t.id === selectedTextId);

  if (!selectedText) {
    return (
      <div className="card-dark">
        <p className="text-secondary">No text fields available</p>
      </div>
    );
  }

  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    onTextUpdate?.(selectedTextId!, e.target.value);
  };

  const handleColorChange = (color: string) => {
    onStyleUpdate?.(selectedTextId!, { color });
  };

  const handleFontSizeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const fontSize = parseInt(e.target.value, 10);
    onStyleUpdate?.(selectedTextId!, { fontSize });
  };

  const handleUppercaseToggle = () => {
    onStyleUpdate?.(selectedTextId!, {
      uppercase: !(selectedText.uppercase || false),
    });
  };

  const handleStrokeToggle = () => {
    onStyleUpdate?.(selectedTextId!, {
      stroke: !(selectedText.stroke || false),
    });
  };

  const handleAutoResizeToggle = () => {
    onStyleUpdate?.(selectedTextId!, {
      autoResize: !(selectedText.autoResize ?? true),
    });
  };

  return (
    <div className="card-dark space-y-6">
      <div>
        <h3 className="text-lg font-semibold mb-4">Text Editor</h3>

        {/* Text Field Selector */}
        {texts.length > 1 && (
          <div className="mb-4">
            <label className="block text-sm text-secondary mb-2">Text Field</label>
            <select
              value={selectedTextId || ''}
              onChange={(e) => setSelectedTextId(e.target.value)}
              className="input-dark w-full"
            >
              {texts.map((text, idx) => (
                <option key={text.id} value={text.id}>
                  Text {idx + 1}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Text Input */}
      <div>
        <label className="block text-sm text-secondary mb-2 flex items-center gap-2">
          <Type size={16} />
          Caption Text
        </label>
        <textarea
          value={selectedText.text}
          onChange={handleTextChange}
          className="input-dark w-full h-20 resize-none"
          placeholder="Enter your meme caption..."
          maxLength={200}
        />
        <p className="text-xs text-muted mt-1">
          {selectedText.text.length}/200 characters
        </p>
      </div>

      {/* Color Picker */}
      <div>
        <label className="block text-sm text-secondary mb-3 flex items-center gap-2">
          <Palette size={16} />
          Text Color
        </label>
        <div className="grid grid-cols-5 gap-2">
          {COLOR_PRESETS.map((color) => (
            <button
              key={color.value}
              onClick={() => handleColorChange(color.value)}
              className={`p-3 rounded-lg border-2 transition-all ${
                selectedText.color === color.value
                  ? 'border-acid'
                  : 'border-border hover:border-border-light'
              }`}
              style={{ backgroundColor: color.value }}
              title={color.name}
            >
              {selectedText.color === color.value && (
                <div className="text-black text-sm font-bold">✓</div>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Font Size Slider */}
      <div>
        <label className="block text-sm text-secondary mb-2 flex items-center justify-between">
          <span className="flex items-center gap-2">
            <ArrowUpToLine size={16} />
            Font Size
          </span>
          <span className="text-acid font-semibold">{selectedText.fontSize || 24}px</span>
        </label>
        <input
          type="range"
          min="12"
          max="72"
          value={selectedText.fontSize || 24}
          onChange={handleFontSizeChange}
          className="w-full accent-acid"
        />
        <div className="flex justify-between text-xs text-muted mt-1">
          <span>Small</span>
          <span>Large</span>
        </div>
      </div>

      {/* Quick Size Presets */}
      <div className="flex gap-2 flex-wrap">
        {FONT_SIZES.map((size) => (
          <button
            key={size}
            onClick={() => onStyleUpdate?.(selectedTextId!, { fontSize: size })}
            className={`px-3 py-1 text-sm rounded border transition-all ${
              selectedText.fontSize === size
                ? 'bg-acid text-black border-acid'
                : 'border-border hover:border-acid/50 text-secondary'
            }`}
          >
            {size}px
          </button>
        ))}
      </div>

      {/* Text Style Toggles */}
      <div className="space-y-2">
        <button
          onClick={handleUppercaseToggle}
          className={`w-full px-4 py-2 rounded-lg border transition-all text-sm font-medium flex items-center justify-center gap-2 ${
            selectedText.uppercase
              ? 'bg-acid/20 border-acid text-acid'
              : 'border-border hover:border-acid/50 text-secondary'
          }`}
        >
          <Settings2 size={16} />
          {selectedText.uppercase ? 'UPPERCASE (On)' : 'Uppercase (Off)'}
        </button>

        <button
          onClick={handleStrokeToggle}
          className={`w-full px-4 py-2 rounded-lg border transition-all text-sm font-medium flex items-center justify-center gap-2 ${
            selectedText.stroke
              ? 'bg-acid/20 border-acid text-acid'
              : 'border-border hover:border-acid/50 text-secondary'
          }`}
        >
          <Settings2 size={16} />
          Text Stroke: {selectedText.stroke ? 'On' : 'Off'}
        </button>

        <button
          onClick={handleAutoResizeToggle}
          className={`w-full px-4 py-2 rounded-lg border transition-all text-sm font-medium flex items-center justify-center gap-2 ${
            (selectedText.autoResize ?? true)
              ? 'bg-acid/20 border-acid text-acid'
              : 'border-border hover:border-acid/50 text-secondary'
          }`}
        >
          <Settings2 size={16} />
          Auto Resize: {(selectedText.autoResize ?? true) ? 'On' : 'Off'}
        </button>
      </div>

      {/* Current Style Summary */}
      <div className="bg-surface-2 rounded-lg p-3 border border-border">
        <p className="text-xs text-muted mb-1">Current Style</p>
        <div className="text-sm font-mono text-secondary space-y-1">
          <div>Color: {selectedText.color || '#ffffff'}</div>
          <div>Size: {selectedText.fontSize || 24}px</div>
          <div>Uppercase: {selectedText.uppercase ? 'Yes' : 'No'}</div>
          <div>Stroke: {selectedText.stroke ? 'Yes' : 'No'}</div>
          <div>Auto Resize: {(selectedText.autoResize ?? true) ? 'Yes' : 'No'}</div>
        </div>
      </div>
    </div>
  );
}
