import { useState, useCallback, useRef } from 'react';
import { Wand2, Loader2, Sparkles, RefreshCw, ChevronLeft, ChevronRight, Zap, Edit3 } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { motion, AnimatePresence } from 'framer-motion';
import confetti from 'canvas-confetti';
import { MemeCard } from './MemeCard';
import { MemePreview } from './MemePreview';
import { MemeEditor } from './MemeEditor';
import { TemplateSelector } from './TemplateSelector';
import { TrendingTopics } from './TrendingTopics';
import type { GeneratedMeme } from '../lib/types';
import { generateMemes, apiClient } from '../lib/api';

interface TextField {
  id: string;
  text: string;
  color: string;
  fontSize: number;
  uppercase: boolean;
  stroke: boolean;
  x: number;
  y: number;
}

interface Template {
  id: string;
  name: string;
  image_url: string;
  text_field_count: number;
  text_coordinates: Array<{ x: number; y: number; maxWidth: number; maxHeight: number }>;
  preview_image_url: string;
  font_path: string;
}

interface AISuggestion {
  id: string;
  template: Template;
  captions: string[];
}

export function MemeGenerator() {
  // Mode state
  const [mode, setMode] = useState<'auto' | 'manual'>('auto');
  
  // Auto mode states
  const [prompt, setPrompt] = useState('');
  const [autoSuggestions, setAutoSuggestions] = useState<AISuggestion[]>([]);
  const [currentSuggestionIdx, setCurrentSuggestionIdx] = useState(0);
  const [isLoadingSuggestions, setIsLoadingSuggestions] = useState(false);
  
  // Manual mode states
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null);
  const [textFields, setTextFields] = useState<TextField[]>([]);
  const [canvasSize, setCanvasSize] = useState({ width: 600, height: 400 });
  const [isGenerating, setIsGenerating] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  
  // Results
  const [memes, setMemes] = useState<GeneratedMeme[]>([]);
  const confettiRef = useRef<HTMLCanvasElement>(null);

  // Handle mode switch
  const switchToManualWithSuggestion = useCallback((suggestion: AISuggestion) => {
    setSelectedTemplate(suggestion.template);
    
    // Initialize text fields from suggestion
    const newFields: TextField[] = suggestion.template.text_coordinates.map((coord, idx) => ({
      id: `text-${idx}`,
      text: suggestion.captions[idx] || '',
      color: '#FFFFFF',
      fontSize: 32,
      uppercase: false,
      stroke: true,
      x: coord.x,
      y: coord.y,
    }));
    setTextFields(newFields);
    setMode('manual');
  }, []);

  // Load AI suggestions in auto mode
  const loadSuggestions = useCallback(async () => {
    if (!prompt.trim()) {
      toast.error('Please enter a topic or situation');
      return;
    }

    if (prompt.trim().length < 3) {
      toast.error('Please provide more context');
      return;
    }

    setIsLoadingSuggestions(true);
    setAutoSuggestions([]);
    setCurrentSuggestionIdx(0);

    try {
      // Call /api/ai/suggest endpoint
      const response = await fetch('/api/ai/suggest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: prompt.trim() }),
      });

      if (!response.ok) {
        throw new Error('Failed to load suggestions');
      }

      const data = await response.json();
      const suggestions: AISuggestion[] = (data.options || []).map((option: any, idx: number) => ({
        id: `suggestion-${idx}`,
        template: option.template,
        captions: option.captions,
      }));

      if (suggestions.length === 0) {
        toast.error('No suggestions generated. Try a different prompt.');
      } else {
        setAutoSuggestions(suggestions);
        toast.success(`Generated ${suggestions.length} suggestions!`);
      }
    } catch (error: any) {
      console.error('Suggestion error:', error);
      toast.error(error.message || 'Failed to load suggestions');
    } finally {
      setIsLoadingSuggestions(false);
    }
  }, [prompt]);

  const handleGenerateMeme = useCallback(async () => {
    if (!selectedTemplate || textFields.length === 0) {
      toast.error('Please select a template and add text');
      return;
    }

    setIsGenerating(true);
    setJobId(null);

    try {
      const result = await generateMemes(prompt.trim() || 'custom meme');
      
      if (result.job_id) {
        setJobId(result.job_id);
        pollJobStatus(result.job_id);
      } else if (result.memes) {
        setMemes(prev => [...(result.memes || []), ...prev]);
        triggerConfetti();
        toast.success(`Generated ${result.memes.length} memes!`);
        setIsGenerating(false);
      }
    } catch (error: any) {
      console.error('Generation error:', error);
      toast.error(error.message || 'Failed to generate memes');
      setIsGenerating(false);
    }
  }, [selectedTemplate, textFields, prompt]);

  const pollJobStatus = useCallback(async (id: string) => {
    const maxAttempts = 30;
    let attempts = 0;

    const poll = async () => {
      try {
        const data = await apiClient.getJobStatus(id);

        if (data.status === 'completed' && data.result?.memes) {
          setMemes(prev => [...(data.result?.memes || []), ...prev]);
          triggerConfetti();
          toast.success(`Generated ${data.result.memes.length} memes!`);
          setIsGenerating(false);
          setJobId(null);
          return;
        }

        if (data.status === 'failed') {
          toast.error(data.error || 'Generation failed');
          setIsGenerating(false);
          setJobId(null);
          return;
        }

        if (data.status === 'processing' && attempts < maxAttempts) {
          attempts++;
          setTimeout(poll, 1000);
        } else if (attempts >= maxAttempts) {
          toast.error('Generation timed out');
          setIsGenerating(false);
          setJobId(null);
        }
      } catch (error) {
        console.error('Polling error:', error);
        toast.error('Failed to check generation status');
        setIsGenerating(false);
        setJobId(null);
      }
    };

    poll();
  }, []);

  const triggerConfetti = () => {
    if (confettiRef.current) {
      confetti({
        particleCount: 100,
        spread: 70,
        origin: { y: 0.6 },
        colors: ['#B0FF00', '#9eff00', '#00FFFF', '#FF00FF'],
      });
    }
  };

  const handleTextUpdate = (id: string, newText: string) => {
    setTextFields(prev =>
      prev.map(field => (field.id === id ? { ...field, text: newText } : field))
    );
  };

  const handleStyleUpdate = (id: string, updates: Partial<TextField>) => {
    setTextFields(prev =>
      prev.map(field => (field.id === id ? { ...field, ...updates } : field))
    );
  };

  const handleTextPositionUpdate = (id: string, x: number, y: number) => {
    setTextFields(prev =>
      prev.map(field => (field.id === id ? { ...field, x, y } : field))
    );
  };

  const handleTrendingTopicSelect = (topic: string) => {
    setPrompt(topic);
    setMode('auto');
  };

  const clearMemes = () => {
    setMemes([]);
    toast.success('Cleared all memes');
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
      {/* Canvas for confetti */}
      <canvas ref={confettiRef} style={{ position: 'fixed', top: 0, left: 0, pointerEvents: 'none' }} />

      {/* Main Content */}
      <div className="lg:col-span-3 space-y-8">
        {/* Mode Toggle */}
        <div className="flex gap-3 bg-surface border border-border rounded-xl p-1">
          <button
            onClick={() => setMode('auto')}
            className={`flex-1 py-2 px-4 rounded-lg font-medium transition-all flex items-center justify-center gap-2 ${
              mode === 'auto'
                ? 'bg-acid text-black'
                : 'text-secondary hover:text-primary'
            }`}
          >
            <Zap size={16} />
            AI Synthesis
          </button>
          <button
            onClick={() => setMode('manual')}
            className={`flex-1 py-2 px-4 rounded-lg font-medium transition-all flex items-center justify-center gap-2 ${
              mode === 'manual'
                ? 'bg-acid text-black'
                : 'text-secondary hover:text-primary'
            }`}
          >
            <Edit3 size={16} />
            Manual Editor
          </button>
        </div>

        {/* Auto Synthesis Mode */}
        <AnimatePresence mode="wait">
          {mode === 'auto' && (
            <motion.div
              key="auto-mode"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="space-y-6"
            >
              {/* Input Section */}
              <div className="glass-card border border-border p-6 rounded-xl space-y-4">
                <h3 className="font-semibold flex items-center gap-2">
                  <Sparkles size={18} className="text-acid" />
                  What's your vibe?
                </h3>
                
                <textarea
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="Describe any situation, feeling, or random thought..."
                  className="w-full h-32 bg-surface/50 backdrop-blur-sm border border-border hover:border-acid/40 focus:border-acid/60 rounded-lg px-4 py-3 text-primary placeholder:text-muted/70 focus:outline-none transition-all resize-none"
                />

                <div className="flex gap-3">
                  <button
                    onClick={loadSuggestions}
                    disabled={isLoadingSuggestions || !prompt.trim()}
                    className="flex-1 btn-acid gap-2 justify-center"
                  >
                    {isLoadingSuggestions ? (
                      <>
                        <Loader2 size={16} className="animate-spin" />
                        Generating...
                      </>
                    ) : (
                      <>
                        <Wand2 size={16} />
                        Get Suggestions
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Suggestions Carousel */}
              {autoSuggestions.length > 0 && (
                <div className="space-y-4">
                  <h3 className="font-semibold flex items-center gap-2">
                    <Sparkles size={18} className="text-acid" />
                    AI Suggestions ({currentSuggestionIdx + 1}/{autoSuggestions.length})
                  </h3>

                  <div className="relative">
                    <AnimatePresence mode="wait">
                      <motion.div
                        key={currentSuggestionIdx}
                        initial={{ opacity: 0, x: 100 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -100 }}
                        className="glass-card border border-border rounded-xl overflow-hidden"
                      >
                        <div className="aspect-video bg-surface overflow-hidden">
                          <img
                            src={autoSuggestions[currentSuggestionIdx].template.image_url}
                            alt={autoSuggestions[currentSuggestionIdx].template.name}
                            className="w-full h-full object-cover"
                          />
                        </div>

                        <div className="p-6 space-y-4">
                          <div>
                            <p className="text-sm text-muted mb-2">Template:</p>
                            <p className="font-medium">{autoSuggestions[currentSuggestionIdx].template.name}</p>
                          </div>

                          <div>
                            <p className="text-sm text-muted mb-2">Suggested Captions:</p>
                            <div className="space-y-2">
                              {autoSuggestions[currentSuggestionIdx].captions.map((caption, idx) => (
                                <div key={idx} className="flex items-start gap-2 p-2 bg-surface-2 rounded">
                                  <span className="text-acid font-bold">{idx + 1}.</span>
                                  <p className="text-sm">{caption}</p>
                                </div>
                              ))}
                            </div>
                          </div>

                          <button
                            onClick={() => switchToManualWithSuggestion(autoSuggestions[currentSuggestionIdx])}
                            className="w-full btn-acid justify-center"
                          >
                            Use This & Edit
                          </button>
                        </div>
                      </motion.div>
                    </AnimatePresence>

                    {/* Carousel Controls */}
                    {autoSuggestions.length > 1 && (
                      <>
                        <button
                          onClick={() => setCurrentSuggestionIdx(idx => (idx - 1 + autoSuggestions.length) % autoSuggestions.length)}
                          className="absolute left-2 top-1/2 -translate-y-1/2 p-2 bg-black/60 hover:bg-black/80 rounded-full transition-all"
                        >
                          <ChevronLeft size={20} className="text-white" />
                        </button>
                        <button
                          onClick={() => setCurrentSuggestionIdx(idx => (idx + 1) % autoSuggestions.length)}
                          className="absolute right-2 top-1/2 -translate-y-1/2 p-2 bg-black/60 hover:bg-black/80 rounded-full transition-all"
                        >
                          <ChevronRight size={20} className="text-white" />
                        </button>
                      </>
                    )}
                  </div>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Manual Editor Mode */}
        <AnimatePresence mode="wait">
          {mode === 'manual' && (
            <motion.div
              key="manual-mode"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="space-y-6"
            >
              {/* Template Selection */}
              {!selectedTemplate ? (
                <div>
                  <h3 className="font-semibold mb-4">Choose a Template</h3>
                  <TemplateSelector
                    onSelectTemplate={(templateId) => {
                      // Fetch full template data
                      fetch(`/api/memes/templates/${templateId}`)
                        .then(res => res.json())
                        .then(data => {
                          setSelectedTemplate(data);
                          const newFields: TextField[] = data.text_coordinates.map((coord: any, idx: number) => ({
                            id: `text-${idx}`,
                            text: '',
                            color: '#FFFFFF',
                            fontSize: 32,
                            uppercase: false,
                            stroke: true,
                            x: coord.x,
                            y: coord.y,
                          }));
                          setTextFields(newFields);
                        })
                        .catch(err => {
                          console.error('Failed to load template:', err);
                          toast.error('Failed to load template');
                        });
                    }}
                  />
                </div>
              ) : (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Editor Panel */}
                  <div className="space-y-6">
                    <div className="flex items-center justify-between">
                      <h3 className="font-semibold">Edit Text</h3>
                      <button
                        onClick={() => {
                          setSelectedTemplate(null);
                          setTextFields([]);
                        }}
                        className="text-sm text-secondary hover:text-primary transition-colors"
                      >
                        Change Template
                      </button>
                    </div>

                    <MemeEditor
                      texts={textFields}
                      onTextUpdate={handleTextUpdate}
                      onStyleUpdate={handleStyleUpdate}
                    />

                    {/* Generate Button */}
                    <button
                      onClick={handleGenerateMeme}
                      disabled={isGenerating}
                      className="w-full btn-acid justify-center py-3"
                    >
                      {isGenerating ? (
                        <>
                          <Loader2 size={16} className="animate-spin" />
                          Generating...
                        </>
                      ) : (
                        <>
                          <Wand2 size={16} />
                          Generate Meme
                        </>
                      )}
                    </button>
                  </div>

                  {/* Preview Panel */}
                  <div>
                    <h3 className="font-semibold mb-4">Preview</h3>
                    <MemePreview
                      templateImageUrl={selectedTemplate.image_url}
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

        {/* Results Section */}
        {memes.length > 0 && (
          <div className="space-y-6 mt-12">
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-bold">Your Memes</h2>
              <button
                onClick={clearMemes}
                className="px-4 py-2 text-sm bg-surface-2 hover:bg-surface-3 border border-border hover:border-red-500/40 rounded-lg text-secondary hover:text-red-400 transition-all flex items-center gap-2"
              >
                <RefreshCw size={16} />
                Clear
              </button>
            </div>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {memes.map((meme, idx) => (
                <div
                  key={meme.id}
                  className="animate-slide-up"
                  style={{ animationDelay: `${idx * 100}ms` }}
                >
                  <MemeCard meme={meme} priority={idx < 3} showStats={false} />
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Sidebar - Trending Topics */}
      <div className="lg:col-span-1">
        <div className="sticky top-6 space-y-4">
          <h3 className="font-semibold text-sm uppercase tracking-wider text-secondary">
            Trending Now
          </h3>
          <TrendingTopics
            onTopicSelect={handleTrendingTopicSelect}
            maxItems={6}
            variant="sidebar"
          />
        </div>
      </div>
    </div>
  );
}
