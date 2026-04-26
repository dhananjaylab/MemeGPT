
import React, { MouseEvent } from 'react';
import { Heart, Download, Eye, RotateCcw } from 'lucide-react';
import { ShareMenu } from './ShareMenu';
import type { GeneratedMeme } from '../types';
import { motion } from 'motion/react';

interface MemeCardProps {
  meme: GeneratedMeme;
  onRemix?: (meme: GeneratedMeme) => void;
  key?: any;
}

export function MemeCard({ meme, onRemix }: MemeCardProps) {
  const handleDownload = async (e: MouseEvent) => {
    e.stopPropagation();
    try {
      const response = await fetch(meme.image_url);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `memegpt-${meme.id}.png`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Download failed', err);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -4 }}
      className="glass-card flex flex-col p-4 group"
    >
      <div className="relative aspect-square rounded-xl overflow-hidden bg-black/40 mb-4">
        <img
          src={meme.image_url}
          alt={meme.prompt}
          className="w-full h-full object-contain"
          loading="lazy"
        />
        <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-center justify-center gap-3">
          <button 
            className="p-3 bg-white/10 hover:bg-white/20 rounded-full backdrop-blur-md transition-colors"
            onClick={(e) => e.stopPropagation()}
          >
            <Heart size={20} className="text-white" />
          </button>
          
          <ShareMenu meme={meme} />
          
          {onRemix && (
            <button 
              onClick={(e) => { e.stopPropagation(); onRemix(meme); }}
              className="p-3 bg-acid/20 hover:bg-acid/40 rounded-full backdrop-blur-md transition-colors group/btn"
              title="Edit / Remix"
            >
              <RotateCcw size={20} className="text-acid group-hover/btn:rotate-180 transition-transform duration-500" />
            </button>
          )}

          <button 
            onClick={handleDownload}
            className="p-3 bg-white/10 hover:bg-white/20 rounded-full backdrop-blur-md transition-colors"
          >
            <Download size={20} className="text-white" />
          </button>
        </div>
      </div>

      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white/5 text-acid uppercase tracking-wider border border-acid/10">
            {meme.template_name}
          </span>
          <div className="flex items-center gap-1.5 text-muted">
            <Eye size={12} />
            <span className="text-xs">{meme.view_count}</span>
          </div>
        </div>
        <p className="text-[11px] font-mono text-muted line-clamp-1 opacity-60 uppercase tracking-tighter">
          {meme.prompt}
        </p>
      </div>
    </motion.div>
  );
}
