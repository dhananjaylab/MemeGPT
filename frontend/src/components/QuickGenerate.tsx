import { useState, useCallback, useRef } from 'react';
import { Zap, Loader2, Copy, Download, RefreshCw, Sparkles, Clock } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { toast } from 'react-hot-toast';
import confetti from 'canvas-confetti';
import { generateMemeQuick } from '../lib/api';
import type { QuickMemeResponse } from '../lib/api';

interface QuickGenerateProps {
  /** Optional: pre-fill the prompt from parent (e.g. trending topic click) */
  initialPrompt?: string;
  /** Called when a meme is successfully generated */
  onGenerated?: (meme: QuickMemeResponse) => void;
}

const PLACEHOLDER_PROMPTS = [
  'when the wifi drops right before submitting the assignment',
  'monday morning energy vs friday night energy',
  'me pretending to be productive while watching youtube',
  'that feeling when the vibe check passes',
  'adulting is just googling everything and hoping for the best',
  'my sleep schedule said "understood the assignment" and left',
  'touch grass they said, it would be fun they said',
  'npc behavior at its peak',
  'main character energy on a side quest budget',
  'slay now, process emotions later',
];

function getRandomPlaceholder() {
  return PLACEHOLDER_PROMPTS[Math.floor(Math.random() * PLACEHOLDER_PROMPTS.length)];
}

export function QuickGenerate({ initialPrompt = '', onGenerated }: QuickGenerateProps) {
  const [prompt, setPrompt] = useState(initialPrompt);
  const [placeholder] = useState(getRandomPlaceholder);
  const [isGenerating, setIsGenerating] = useState(false);
  const [result, setResult] = useState<QuickMemeResponse | null>(null);
  const [aiProvider, setAiProvider] = useState<'openai' | 'gemini'>('openai');
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const generate = useCallback(async () => {
    const trimmed = prompt.trim();
    if (!trimmed) {
      toast.error('Type something first — no cap');
      inputRef.current?.focus();
      return;
    }
    if (trimmed.length < 3) {
      toast.error('Give me more to work with 💀');
      return;
    }

    setIsGenerating(true);
    const startMs = performance.now();

    try {
      const res = await generateMemeQuick({ prompt: trimmed, ai_provider: aiProvider });
      setResult(res);
      onGenerated?.(res);

      const totalMs = Math.round(performance.now() - startMs);
      if (res.cache_hit) {
        toast.success(`Served from cache in ${totalMs}ms ⚡`, { duration: 2500 });
      } else {
        confetti({
          particleCount: 80,
          spread: 60,
          origin: { y: 0.7 },
          colors: ['#B0FF00', '#00FFFF', '#FF00FF', '#FFD700'],
        });
        toast.success(`Generated in ${totalMs}ms 🔥`, { duration: 2500 });
      }
    } catch (err: any) {
      const msg = err?.message || 'Generation failed';
      if (err?.isRateLimit) {
        toast.error('Rate limit hit — try again in a bit 😅');
      } else {
        toast.error(msg);
      }
    } finally {
      setIsGenerating(false);
    }
  }, [prompt, aiProvider, onGenerated]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      generate();
    }
  };

  const handleDownload = async () => {
    if (!result) return;
    try {
      const res = await fetch(result.image_url);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `memegpt-${result.meme_id.slice(0, 8)}.png`;
      document.body.appendChild(a);
      a.click();
      URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success('Downloaded! 📥');
    } catch {
      toast.error('Download failed');
    }
  };

  const handleCopyLink = async () => {
    if (!result) return;
    const link = `${window.location.origin}/meme/${result.meme_id}`;
    await navigator.clipboard.writeText(link);
    toast.success('Link copied! 🔗');
  };

  const handleRegenerate = () => {
    setResult(null);
    generate();
  };

  return (
    <div className="space-y-4">
      {/* ── Input area ─────────────────────────────────────────────────────── */}
      <div className="glass-card border border-border rounded-2xl p-5 space-y-4">
        {/* Header row */}
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 bg-acid/10 border border-acid/30 rounded-lg flex items-center justify-center">
              <Zap size={14} className="text-acid" />
            </div>
            <h3 className="font-semibold text-sm">Quick Generate</h3>
            <span className="badge-acid text-[10px]">Instant</span>
          </div>

          {/* Provider toggle */}
          <div className="flex items-center gap-1 bg-surface border border-border rounded-lg p-0.5">
            {(['openai', 'gemini'] as const).map((p) => (
              <button
                key={p}
                onClick={() => setAiProvider(p)}
                className={`px-3 py-1 rounded text-xs font-mono transition-all ${
                  aiProvider === p
                    ? 'bg-acid text-black font-semibold'
                    : 'text-muted hover:text-secondary'
                }`}
              >
                {p === 'openai' ? 'GPT-4o' : 'Gemini'}
              </button>
            ))}
          </div>
        </div>

        {/* Textarea */}
        <div className="relative">
          <textarea
            ref={inputRef}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={isGenerating}
            rows={3}
            maxLength={500}
            className="w-full bg-surface-2/80 border border-border hover:border-acid/30 focus:border-acid/60 rounded-xl px-4 py-3 text-sm placeholder:text-muted/60 focus:outline-none transition-all resize-none disabled:opacity-50"
          />
          <div className="absolute bottom-2 right-3 text-[10px] font-mono text-muted">
            {prompt.length}/500
          </div>
        </div>

        {/* Hint */}
        <p className="text-[11px] text-muted font-mono">
          ⌘ + Enter to generate · works best with short relatable situations
        </p>

        {/* Generate button */}
        <button
          onClick={generate}
          disabled={isGenerating || !prompt.trim()}
          className="w-full btn-acid justify-center py-3 text-sm font-bold tracking-wide disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isGenerating ? (
            <>
              <Loader2 size={16} className="animate-spin" />
              Generating...
            </>
          ) : (
            <>
              <Sparkles size={16} />
              Generate Meme
            </>
          )}
        </button>
      </div>

      {/* ── Result ─────────────────────────────────────────────────────────── */}
      <AnimatePresence mode="wait">
        {result && (
          <motion.div
            key={result.meme_id}
            initial={{ opacity: 0, y: 16, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.97 }}
            transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
            className="glass-card border border-acid/25 rounded-2xl overflow-hidden"
          >
            {/* Meta strip */}
            <div className="flex items-center justify-between px-4 py-2 bg-acid/5 border-b border-acid/15">
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono text-secondary truncate max-w-[200px]">
                  {result.template_name}
                </span>
                {result.cache_hit && (
                  <span className="flex items-center gap-1 text-[10px] font-mono text-acid">
                    <Clock size={10} />
                    cached
                  </span>
                )}
              </div>
              <span className="text-[10px] font-mono text-muted">
                {result.generation_time_ms}ms
              </span>
            </div>

            {/* Meme image */}
            <div className="bg-surface-2">
              <img
                src={result.image_url}
                alt={result.meme_text.join(' / ')}
                className="w-full object-contain max-h-[500px]"
                loading="lazy"
              />
            </div>

            {/* Caption preview */}
            <div className="px-4 py-3 space-y-1">
              {result.meme_text.map((t, i) => (
                <p key={i} className="text-xs text-secondary italic">
                  "{t}"
                </p>
              ))}
            </div>

            {/* Action bar */}
            <div className="flex items-center gap-2 px-4 pb-4">
              <button
                onClick={handleRegenerate}
                disabled={isGenerating}
                className="flex-1 btn-acid-outline py-2 text-xs justify-center"
              >
                <RefreshCw size={13} className={isGenerating ? 'animate-spin' : ''} />
                Regenerate
              </button>
              <button
                onClick={handleCopyLink}
                className="btn-ghost py-2 px-3 text-xs"
                title="Copy link"
              >
                <Copy size={13} />
              </button>
              <button
                onClick={handleDownload}
                className="btn-ghost py-2 px-3 text-xs"
                title="Download"
              >
                <Download size={13} />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
