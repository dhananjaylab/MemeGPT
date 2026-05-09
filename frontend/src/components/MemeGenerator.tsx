import { useState, useCallback, useEffect } from 'react';
import {
  Wand2, Loader2, Sparkles, RefreshCw, ChevronLeft, ChevronRight,
  Zap, Edit3, X,
} from 'lucide-react';
import { toast } from 'react-hot-toast';
import { motion, AnimatePresence } from 'framer-motion';
import confetti from 'canvas-confetti';
import { MemeCard } from './MemeCard';
import { MemePreview } from './MemePreview';
import { MemeEditor } from './MemeEditor';
import { TemplateSelector } from './TemplateSelector';
import { TrendingTopics } from './TrendingTopics';
import { QuickGenerate } from './QuickGenerate';
import type { GeneratedMeme, MemeTemplate } from '../lib/types';
import { generateMemes, apiClient } from '../lib/api';
import type { QuickMemeResponse } from '../lib/api';
import type { TextPosition } from '../lib/canvas';

// ─── Local types ──────────────────────────────────────────────────────────────

interface TextField {
  id: string;
  text: string;
  color: string;
  fontSize: number;
  uppercase: boolean;
  stroke: boolean;
  autoResize: boolean;
  x: number;
  y: number;
  width: number;
  height: number;
}

interface AISuggestion {
  id: string;
  template: MemeTemplate;
  captions: string[];
  reasoning?: string;
}

type Mode = 'quick' | 'auto' | 'manual';

// ─── Mode tab config ──────────────────────────────────────────────────────────

const MODES: { id: Mode; label: string; icon: typeof Zap; badge?: string }[] = [
  { id: 'quick',  label: 'Quick',   icon: Zap,   badge: '⚡ Instant' },
  { id: 'auto',   label: 'AI Mode', icon: Sparkles },
  { id: 'manual', label: 'Editor',  icon: Edit3 },
];

// ─── Component ────────────────────────────────────────────────────────────────

interface MemeGeneratorProps {
  topic?: string;
}

export function MemeGenerator({ topic }: MemeGeneratorProps) {
  const [mode, setMode] = useState<Mode>('quick');

  // Update prompt when external topic changes
  useEffect(() => {
    if (topic) {
      setPrompt(topic);
      setMode('auto'); // Switch to AI mode for trending topics
      window.scrollTo({ top: document.getElementById('generator-top')?.offsetTop || 0, behavior: 'smooth' });
    }
  }, [topic]);

  // Auto mode
  const [prompt, setPrompt] = useState('');
  const [autoSuggestions, setAutoSuggestions] = useState<AISuggestion[]>([]);
  const [currentSuggestionIdx, setCurrentSuggestionIdx] = useState(0);
  const [isLoadingSuggestions, setIsLoadingSuggestions] = useState(false);

  // Manual mode
  const [selectedTemplate, setSelectedTemplate] = useState<MemeTemplate | null>(null);
  const [textFields, setTextFields] = useState<TextField[]>([]);
  const [canvasSize] = useState({ width: 600, height: 400 });
  const [isGenerating, setIsGenerating] = useState(false);

  // Shared results
  const [memes, setMemes] = useState<GeneratedMeme[]>([]);

  // ── Quick mode: append generated meme to results list ──────────────────────
  const handleQuickGenerated = useCallback((res: QuickMemeResponse) => {
    const syntheticMeme: GeneratedMeme = {
      id: res.meme_id,
      template_id: 0,
      template_name: res.template_name,
      prompt: '',
      meme_text: res.meme_text,
      image_url: res.image_url,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      is_public: true,
      view_count: 0,
      like_count: 0,
      share_count: 0,
    };
    setMemes((prev) => [syntheticMeme, ...prev]);
  }, []);

  // ── Switch manual mode pre-filled from AI suggestion ─────────────────────
  const switchToManualWithSuggestion = useCallback((suggestion: AISuggestion) => {
    setSelectedTemplate(suggestion.template);
    const newFields: TextField[] = (suggestion.template.text_coordinates || []).map(
      (coord, idx) => {
        const c = Array.isArray(coord)
          ? { x: coord[0] ?? 10, y: coord[1] ?? 10, maxWidth: coord[2] ?? 80, maxHeight: coord[3] ?? 20 }
          : coord;
        return {
          id: `text-${idx}`,
          text: suggestion.captions[idx] || '',
          color: '#FFFFFF',
          fontSize: 32,
          uppercase: false,
          stroke: true,
          autoResize: true,
          x: c.x,
          y: c.y,
          width: c.maxWidth ?? 80,
          height: c.maxHeight ?? 20,
        };
      },
    );
    setTextFields(newFields);
    setMode('manual');
  }, []);

  // ── AI suggestions ────────────────────────────────────────────────────────
  const loadSuggestions = useCallback(async () => {
    if (!prompt.trim() || prompt.trim().length < 3) {
      toast.error('Type at least 3 characters');
      return;
    }

    setIsLoadingSuggestions(true);
    setAutoSuggestions([]);
    setCurrentSuggestionIdx(0);

    try {
      const [suggestResp, templatesResp] = await Promise.all([
        fetch('/api/ai/suggest', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt: prompt.trim() }),
        }),
        fetch('/api/memes/templates'),
      ]);

      if (!suggestResp.ok) throw new Error('Failed to get suggestions');
      if (!templatesResp.ok) throw new Error('Failed to load templates');

      const data = await suggestResp.json();
      const templates: MemeTemplate[] = await templatesResp.json();
      const byId = new Map(templates.map((t) => [t.id, t]));

      const suggestions: AISuggestion[] = (data.options || [])
        .map((opt: any, idx: number) => {
          const template = byId.get(opt.meme_id);
          if (!template) return null;
          return { id: `s-${idx}`, template, captions: opt.meme_text || [], reasoning: opt.reasoning };
        })
        .filter(Boolean) as AISuggestion[];

      if (!suggestions.length) {
        toast.error('No suggestions — try a different prompt');
      } else {
        setAutoSuggestions(suggestions);
        toast.success(`${suggestions.length} suggestions ready ✨`);
      }
    } catch (err: any) {
      toast.error(err.message || 'Failed to load suggestions');
    } finally {
      setIsLoadingSuggestions(false);
    }
  }, [prompt]);

  // ── Manual generation ─────────────────────────────────────────────────────
  const handleGenerateMeme = useCallback(async () => {
    if (!selectedTemplate || !textFields.length) {
      toast.error('Pick a template and add some text first');
      return;
    }
    setIsGenerating(true);
    try {
      const captions = textFields.map((f) => f.text.trim()).filter(Boolean);
      const result = await generateMemes(prompt.trim() || 'custom meme', {
        generation_mode: 'manual',
        template_id: selectedTemplate.id,
        captions,
      });

      if (result.job_id) {
        pollJobStatus(result.job_id);
      } else if (result.memes) {
        setMemes((prev) => [...(result.memes ?? []), ...prev]);
        confetti({ particleCount: 100, spread: 70, origin: { y: 0.6 } });
        toast.success(`${result.memes.length} meme${result.memes.length > 1 ? 's' : ''} generated!`);
        setIsGenerating(false);
      }
    } catch (err: any) {
      toast.error(err.message || 'Generation failed');
      setIsGenerating(false);
    }
  }, [selectedTemplate, textFields, prompt]);

  const pollJobStatus = useCallback(async (id: string) => {
    let attempts = 0;
    const poll = async () => {
      try {
        const data = await apiClient.getJobStatus(id);
        const completedMemes = data.memes || data.result?.memes || [];
        if (data.status === 'completed' && completedMemes.length) {
          setMemes((prev) => [...completedMemes, ...prev]);
          confetti({ particleCount: 100, spread: 70, origin: { y: 0.6 } });
          toast.success(`${completedMemes.length} meme${completedMemes.length > 1 ? 's' : ''} generated!`);
          setIsGenerating(false);
          return;
        }
        if (data.status === 'failed') {
          toast.error(data.error || 'Generation failed');
          setIsGenerating(false);
          return;
        }
        if (attempts++ < 60) setTimeout(poll, 1000);
        else { toast.error('Timed out — try again'); setIsGenerating(false); }
      } catch { toast.error('Status check failed'); setIsGenerating(false); }
    };
    poll();
  }, []);

  // ── Field helpers ─────────────────────────────────────────────────────────
  const handleTextUpdate = (id: string, text: string) =>
    setTextFields((prev) => prev.map((f) => (f.id === id ? { ...f, text } : f)));

  const handleStyleUpdate = (id: string, updates: Partial<TextField>) =>
    setTextFields((prev) => prev.map((f) => (f.id === id ? { ...f, ...updates } : f)));

  const handleTextPositionUpdate = (id: string, pos: TextPosition) =>
    setTextFields((prev) => prev.map((f) => (f.id === id ? { ...f, ...pos } : f)));

  const handleTrendingTopicSelect = (topic: string) => {
    setPrompt(topic);
    setMode('quick');
  };

  return (
    <div className="space-y-6">
      {/* Mode tabs */}
      <div className="flex gap-1 bg-surface border border-border rounded-xl p-1">
        {MODES.map(({ id, label, icon: Icon, badge }) => (
          <button
            key={id}
            onClick={() => setMode(id)}
            className={`flex-1 py-2.5 px-3 rounded-lg font-medium text-sm transition-all flex items-center justify-center gap-2 ${
              mode === id
                ? 'bg-acid text-black shadow-sm'
                : 'text-secondary hover:text-primary'
            }`}
          >
            <Icon size={15} />
            {label}
            {badge && mode === id && (
              <span className="hidden sm:inline text-[10px] font-bold opacity-70">{badge}</span>
            )}
          </button>
        ))}
      </div>

      {/* ── Quick Mode ────────────────────────────────────────────────────── */}
      <AnimatePresence mode="wait">
        {mode === 'quick' && (
          <motion.div
            key="quick"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
          >
            <QuickGenerate
              initialPrompt={prompt}
              onGenerated={handleQuickGenerated}
            />
          </motion.div>
        )}

        {/* ── AI Mode ─────────────────────────────────────────────────────── */}
        {mode === 'auto' && (
          <motion.div
            key="auto"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className={`grid grid-cols-1 ${autoSuggestions.length > 0 ? 'xl:grid-cols-2' : ''} gap-6 items-start`}
          >
            <div className="glass-card border border-border p-6 rounded-xl space-y-4">
              <h3 className="font-semibold flex items-center gap-2">
                <Sparkles size={18} className="text-acid" />
                What's the vibe?
              </h3>
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Describe any situation, feeling, or random thought..."
                className="w-full h-28 bg-surface-2/80 border border-border hover:border-acid/40 focus:border-acid/60 rounded-xl px-4 py-3 text-sm placeholder:text-muted/60 focus:outline-none transition-all resize-none"
              />
              <button
                onClick={loadSuggestions}
                disabled={isLoadingSuggestions || !prompt.trim()}
                className="w-full btn-acid justify-center py-3 disabled:opacity-50"
              >
                {isLoadingSuggestions ? (
                  <><Loader2 size={16} className="animate-spin" /> Generating suggestions...</>
                ) : (
                  <><Wand2 size={16} /> Get 3 AI Suggestions</>
                )}
              </button>
            </div>

            {/* Suggestion carousel */}
            {autoSuggestions.length > 0 && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold text-sm flex items-center gap-2">
                    <Sparkles size={16} className="text-acid" />
                    Pick your fav
                  </h3>
                  <span className="text-xs text-muted font-mono">
                    {currentSuggestionIdx + 1} / {autoSuggestions.length}
                  </span>
                </div>

                <div className="relative">
                  <AnimatePresence mode="wait">
                    <motion.div
                      key={currentSuggestionIdx}
                      initial={{ opacity: 0, x: 60 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -60 }}
                      transition={{ duration: 0.25 }}
                      className="glass-card border border-border rounded-xl overflow-hidden"
                    >
                      <div className="aspect-video bg-surface overflow-hidden">
                        <img
                          src={
                            autoSuggestions[currentSuggestionIdx].template.image_url
                            || autoSuggestions[currentSuggestionIdx].template.preview_image_url
                          }
                          alt={autoSuggestions[currentSuggestionIdx].template.name}
                          className="w-full h-full object-cover"
                        />
                      </div>
                      <div className="p-5 space-y-4">
                        <div>
                          <p className="text-xs text-muted mb-1">Template</p>
                          <p className="font-semibold">{autoSuggestions[currentSuggestionIdx].template.name}</p>
                        </div>
                        <div className="space-y-1.5">
                          {autoSuggestions[currentSuggestionIdx].captions.map((c, i) => (
                            <div key={i} className="flex items-start gap-2 p-2 bg-surface-2 rounded-lg">
                              <span className="text-acid font-bold text-xs mt-0.5">{i + 1}.</span>
                              <p className="text-sm">{c}</p>
                            </div>
                          ))}
                        </div>
                        {autoSuggestions[currentSuggestionIdx].reasoning && (
                          <p className="text-xs text-muted italic border-l-2 border-acid/30 pl-3">
                            {autoSuggestions[currentSuggestionIdx].reasoning}
                          </p>
                        )}
                        <button
                          onClick={() => switchToManualWithSuggestion(autoSuggestions[currentSuggestionIdx])}
                          className="w-full btn-acid justify-center"
                        >
                          Use This & Tweak
                        </button>
                      </div>
                    </motion.div>
                  </AnimatePresence>

                  {autoSuggestions.length > 1 && (
                    <>
                      <button
                        onClick={() => setCurrentSuggestionIdx((i) => (i - 1 + autoSuggestions.length) % autoSuggestions.length)}
                        className="absolute left-2 top-[30%] -translate-y-1/2 p-2 bg-black/60 hover:bg-black/80 rounded-full"
                      >
                        <ChevronLeft size={18} className="text-white" />
                      </button>
                      <button
                        onClick={() => setCurrentSuggestionIdx((i) => (i + 1) % autoSuggestions.length)}
                        className="absolute right-2 top-[30%] -translate-y-1/2 p-2 bg-black/60 hover:bg-black/80 rounded-full"
                      >
                        <ChevronRight size={18} className="text-white" />
                      </button>
                    </>
                  )}
                </div>
              </div>
            )}
          </motion.div>
        )}

        {/* ── Manual Mode ─────────────────────────────────────────────────── */}
        {mode === 'manual' && (
          <motion.div
            key="manual"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="space-y-6"
          >
            {!selectedTemplate ? (
              <div>
                <h3 className="font-semibold mb-4 flex items-center gap-2">
                  <Edit3 size={16} className="text-acid" />
                  Choose a Template
                  <span className="badge-dim">{26} templates</span>
                </h3>
                <TemplateSelector
                  onSelectTemplate={async (tpl) => {
                    try {
                      const data = await fetch(`/api/memes/templates/${tpl.id}`).then((r) => r.json());
                      setSelectedTemplate(data);
                      const fields: TextField[] = (data.text_coordinates || []).map(
                        (coord: any, idx: number) => {
                          const c = Array.isArray(coord)
                            ? { x: coord[0] ?? 10, y: coord[1] ?? 10, maxWidth: coord[2] ?? 80, maxHeight: coord[3] ?? 20 }
                            : coord;
                          return {
                            id: `text-${idx}`,
                            text: '',
                            color: '#FFFFFF',
                            fontSize: 32,
                            uppercase: false,
                            stroke: true,
                            autoResize: true,
                            x: c.x, y: c.y, width: c.maxWidth ?? 80, height: c.maxHeight ?? 20,
                          };
                        },
                      );
                      setTextFields(fields);
                    } catch { toast.error('Failed to load template'); }
                  }}
                />
              </div>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Editor */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="font-semibold flex items-center gap-2">
                      <Edit3 size={15} className="text-acid" />
                      Edit Text
                    </h3>
                    <button
                      onClick={() => { setSelectedTemplate(null); setTextFields([]); }}
                      className="flex items-center gap-1.5 text-xs text-muted hover:text-primary transition-colors"
                    >
                      <X size={12} /> Change template
                    </button>
                  </div>
                  <MemeEditor texts={textFields} onTextUpdate={handleTextUpdate} onStyleUpdate={handleStyleUpdate} />
                  <button
                    onClick={handleGenerateMeme}
                    disabled={isGenerating}
                    className="w-full btn-acid justify-center py-3"
                  >
                    {isGenerating ? (
                      <><Loader2 size={16} className="animate-spin" /> Generating...</>
                    ) : (
                      <><Wand2 size={16} /> Generate Meme</>
                    )}
                  </button>
                </div>

                {/* Preview */}
                <div>
                  <h3 className="font-semibold mb-4 text-sm">Live Preview</h3>
                  <MemePreview
                    templateImageUrl={selectedTemplate.image_url || selectedTemplate.preview_image_url || ''}
                    texts={textFields}
                    onTextPositionUpdate={handleTextPositionUpdate}
                    isLocked={false}
                    canvasWidth={canvasSize.width}
                    canvasHeight={canvasSize.height}
                  />
                </div>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Results ───────────────────────────────────────────────────────── */}
      {memes.length > 0 && (
        <div className="space-y-4 mt-8">
          <div className="flex items-center justify-between">
            <h2 className="font-bold text-lg">Your Memes</h2>
            <button
              onClick={() => setMemes([])}
              className="flex items-center gap-1.5 text-xs text-muted hover:text-red-400 transition-colors"
            >
              <RefreshCw size={12} /> Clear all
            </button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {memes.map((meme, i) => (
              <motion.div
                key={meme.id}
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.06, duration: 0.4 }}
              >
                <MemeCard meme={meme} priority={i < 3} />
              </motion.div>
            ))}
          </div>
        </div>
      )}
    </div>

  );
}
