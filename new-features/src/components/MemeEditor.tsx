
import { useState } from 'react';
import { Type, Palette, Type as FontIcon, AlignCenter, RotateCcw, Maximize2 } from 'lucide-react';
import type { MemeSettings } from '../types';

interface MemeEditorProps {
  numFields: number;
  onTextChange: (texts: string[]) => void;
  onSettingsChange: (settings: MemeSettings) => void;
  initialTexts: string[];
  settings: MemeSettings;
}

export function MemeEditor({ numFields, onTextChange, onSettingsChange, initialTexts, settings }: MemeEditorProps) {
  const [texts, setTexts] = useState<string[]>(initialTexts);

  const handleTextChange = (index: number, val: string) => {
    const newTexts = [...texts];
    newTexts[index] = val;
    setTexts(newTexts);
    onTextChange(newTexts);
  };

  const colors = ['#FFFFFF', '#000000', '#B0FF00', '#FF0000', '#00FFFF'];

  return (
    <div className="space-y-8">
      <div className="space-y-4">
        <h3 className="flex items-center gap-2 font-mono text-xs uppercase tracking-widest text-muted">
          <Type size={14} />
          Text Captions
        </h3>
        <div className="space-y-3">
          {Array.from({ length: numFields }).map((_, i) => (
            <div key={i} className="relative">
              <span className="absolute right-4 top-1/2 -translate-y-1/2 font-mono text-[10px] text-muted">
                Line {i + 1}
              </span>
              <input
                type="text"
                value={texts[i] || ''}
                onChange={(e) => handleTextChange(i, e.target.value)}
                placeholder={`Caption ${i + 1}...`}
                className="w-full bg-black/40 border border-border rounded-xl px-4 py-3 focus:border-acid outline-none transition-all pr-12"
              />
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
        <div className="space-y-4">
          <h3 className="flex items-center gap-2 font-mono text-xs uppercase tracking-widest text-muted">
            <Palette size={14} />
            Text Color
          </h3>
          <div className="flex gap-2">
            {colors.map(c => (
              <button
                key={c}
                onClick={() => onSettingsChange({ ...settings, color: c })}
                className={`w-8 h-8 rounded-full border-2 transition-transform ${
                  settings.color === c ? 'border-acid scale-110' : 'border-transparent hover:scale-105'
                }`}
                style={{ backgroundColor: c }}
              />
            ))}
          </div>
        </div>

        <div className="space-y-4">
          <h3 className="flex items-center gap-2 font-mono text-xs uppercase tracking-widest text-muted">
            <FontIcon size={14} />
            Font Size ({settings.fontSize}px)
          </h3>
          <input
            type="range"
            min="12"
            max="72"
            value={settings.fontSize}
            onChange={(e) => onSettingsChange({ ...settings, fontSize: parseInt(e.target.value) })}
            className="w-full accent-acid bg-black/40 h-1.5 rounded-full appearance-none cursor-pointer"
          />
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-6">
        <button
          onClick={() => onSettingsChange({ ...settings, uppercase: !settings.uppercase })}
          className={`px-4 py-2 rounded-lg border text-xs font-mono uppercase tracking-wider transition-all ${
            settings.uppercase ? 'bg-acid text-black border-acid font-bold' : 'border-border text-muted hover:text-white'
          }`}
        >
          {settings.uppercase ? 'All Caps: ON' : 'All Caps: OFF'}
        </button>

        <button
          onClick={() => onSettingsChange({ ...settings, autoResize: !settings.autoResize })}
          className={`px-4 py-2 rounded-lg border text-xs font-mono uppercase tracking-wider transition-all flex items-center gap-2 ${
            settings.autoResize ? 'bg-acid text-black border-acid font-bold shadow-[0_0_10px_rgba(176,255,0,0.2)]' : 'border-border text-muted hover:text-white'
          }`}
        >
          <Maximize2 size={14} />
          {settings.autoResize ? 'Auto-Fit: ON' : 'Auto-Fit: OFF'}
        </button>

        <button
          onClick={() => {
            const isManual = !settings.manualLayout;
            onSettingsChange({ 
              ...settings, 
              manualLayout: isManual,
              positions: isManual ? settings.positions : undefined 
            });
          }}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg border text-xs font-mono uppercase tracking-wider transition-all ${
            settings.manualLayout 
              ? 'bg-acid text-black border-acid font-bold shadow-[0_0_10px_rgba(176,255,0,0.3)]' 
              : 'border-border text-muted hover:text-white'
          }`}
        >
          {settings.manualLayout ? (
            <><RotateCcw size={14} className="animate-spin-slow" /> Manual Mode: ON</>
          ) : (
            <><AlignCenter size={14} /> Manual Mode: OFF</>
          )}
        </button>

        {settings.manualLayout && (
           <p className="text-[10px] font-mono text-acid/60 uppercase tracking-widest animate-pulse">
             Note: Interactive Dragging Enabled
           </p>
        )}
      </div>
    </div>
  );
}
