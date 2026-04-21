
import { useState, useEffect } from 'react';
import { MemeAPI } from '../lib/api';
import { MemeCard } from '../components/MemeCard';
import type { GeneratedMeme } from '../types';
import { motion, AnimatePresence } from 'motion/react';
import { Search, SlidersHorizontal, ImageOff, Loader2 } from 'lucide-react';

export function Gallery() {
  const [memes, setMemes] = useState<GeneratedMeme[]>([]);
  const [search, setSearch] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    MemeAPI.getAll().then(data => {
      setMemes(data);
      setIsLoading(false);
    });
  }, []);

  const filteredMemes = memes.filter(m => 
    m.prompt.toLowerCase().includes(search.toLowerCase()) ||
    m.template_name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="py-12 space-y-12">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div className="space-y-2">
          <h1 className="font-display text-4xl font-bold">Public Gallery</h1>
          <p className="text-muted">The best community-synthesized humor.</p>
        </div>

        <div className="flex gap-4">
          <div className="relative flex-1 md:w-80">
            <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-muted" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search prompts..."
              className="w-full bg-surface border border-border rounded-xl pl-12 pr-4 py-3 text-sm focus:border-acid focus:ring-1 focus:ring-acid/20 outline-none transition-all"
            />
          </div>
          <button className="btn-ghost p-3 px-4">
            <SlidersHorizontal size={18} />
          </button>
        </div>
      </div>

      {filteredMemes.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {filteredMemes.map((meme) => (
            <MemeCard key={meme.id} meme={meme} />
          ))}
        </div>
      ) : (
        <div className="py-32 flex flex-col items-center justify-center text-center opacity-30">
          <ImageOff size={64} className="mb-4" />
          <h3 className="font-display text-2xl font-bold">Void Detected</h3>
          <p className="text-sm">No memes match your current semantic search.</p>
        </div>
      )}
    </div>
  );
}
