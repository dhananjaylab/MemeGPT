
import { MemeTemplate } from '../types';
import { motion } from 'motion/react';
import { Search, Info, Upload } from 'lucide-react';
import { useState, useRef, ChangeEvent } from 'react';

interface TemplateSelectorProps {
  templates: MemeTemplate[];
  onSelect: (template: MemeTemplate) => void;
  selectedId?: string;
  onCustomUpload?: (url: string) => void;
}

export function TemplateSelector({ templates, onSelect, selectedId, onCustomUpload }: TemplateSelectorProps) {
  const [search, setSearch] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const filtered = templates.filter(t => 
    t.name.toLowerCase().includes(search.toLowerCase()) ||
    t.description.toLowerCase().includes(search.toLowerCase())
  );

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && onCustomUpload) {
      const url = URL.createObjectURL(file);
      onCustomUpload(url);
    }
  };

  return (
    <div className="space-y-6">
      <div className="relative group">
        <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-muted group-focus-within:text-acid transition-colors" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search templates (e.g. 'Distracted', 'Drake')..."
          className="w-full bg-black/40 border border-border rounded-xl pl-12 pr-4 py-3 focus:border-acid outline-none transition-all"
        />
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
        {/* Custom Upload Button */}
        <motion.button
          whileHover={{ y: -2 }}
          whileTap={{ scale: 0.98 }}
          onClick={() => fileInputRef.current?.click()}
          className="relative aspect-square rounded-xl overflow-hidden border-2 border-dashed border-acid/40 bg-acid/5 flex flex-col items-center justify-center gap-3 group hover:border-acid hover:bg-acid/10 transition-all"
        >
          <div className="w-10 h-10 rounded-full bg-acid/10 flex items-center justify-center text-acid group-hover:scale-110 transition-transform">
            <Upload size={20} />
          </div>
          <span className="text-[10px] font-mono uppercase tracking-[0.2em] font-bold text-acid">Upload Asset</span>
          <input 
            type="file" 
            ref={fileInputRef} 
            onChange={handleFileChange} 
            accept="image/*" 
            className="hidden" 
          />
        </motion.button>

        {filtered.map((t) => (
          <motion.button
            key={t.id}
            whileHover={{ y: -2 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => onSelect(t)}
            className={`group relative aspect-square rounded-xl overflow-hidden border-2 transition-all ${
              selectedId === t.id ? 'border-acid shadow-lg shadow-acid/10' : 'border-border hover:border-white/20'
            }`}
          >
            <img src={t.url} alt={t.name} className="w-full h-full object-cover" />
            <div className={`absolute inset-0 bg-black/60 flex flex-col items-center justify-center p-4 text-center transition-opacity ${
              selectedId === t.id ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'
            }`}>
              <span className="text-xs font-bold text-white mb-1">{t.name}</span>
              <span className="text-[10px] text-muted line-clamp-2">{t.description}</span>
            </div>
          </motion.button>
        ))}
      </div>

      {filtered.length === 0 && (
        <div className="text-center py-12 text-muted">
           <Info size={32} className="mx-auto mb-2 opacity-20" />
           <p>No templates found matching your search.</p>
        </div>
      )}
    </div>
  );
}
