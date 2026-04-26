
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { LayoutGrid, Type, Wand2, ArrowLeft, Loader2, Sparkles, CheckCircle2, Zap, BrainCircuit, Plus, Minus, RotateCcw } from 'lucide-react';
import { TemplateSelector } from './TemplateSelector';
import { MemeEditor } from './MemeEditor';
import { MemePreview } from './MemePreview';
import { MemeAPI } from '../lib/api';
import { synthesizeMeme } from '../lib/canvas';
import { synthesizeMemeCaptions } from '../lib/gemini';
import type { MemeTemplate, MemeSettings, GeneratedMeme } from '../types';
import { toast } from 'react-hot-toast';
import { MemeCard } from './MemeCard';
import confetti from 'canvas-confetti';

type Step = 'template' | 'editor' | 'auto';

export function MemeGenerator() {
  const [step, setStep] = useState<Step>('auto');
  const [templates, setTemplates] = useState<MemeTemplate[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<MemeTemplate | null>(null);
  const [texts, setTexts] = useState<string[]>([]);
  const [settings, setSettings] = useState<MemeSettings>({
    fontSize: 40,
    color: '#FFFFFF',
    uppercase: true,
    manualLayout: false,
    autoResize: true,
  });
  const [isSynthesizing, setIsSynthesizing] = useState(false);
  const [lastGenerated, setLastGenerated] = useState<GeneratedMeme | null>(null);
  const [autoPrompt, setAutoPrompt] = useState('');
  const [aiSuggestions, setAiSuggestions] = useState<{ templateId: string; captions: string[]; reasoning: string }[]>([]);
  const [currentAiIndex, setCurrentAiIndex] = useState(0);

  useEffect(() => {
    MemeAPI.getTemplates().then(setTemplates);
  }, []);

  const applyAiSuggestion = (index: number, suggestions: any[]) => {
    const suggestion = suggestions[index];
    const template = templates.find(t => t.id === suggestion.templateId);
    if (template) {
      setSelectedTemplate(template);
      setTexts(suggestion.captions);
      setCurrentAiIndex(index);
      setSettings(prev => ({ ...prev, positions: undefined, manualLayout: false }));
    }
  };

  const handleTemplateSelect = (t: MemeTemplate) => {
    setSelectedTemplate(t);
    setTexts(new Array(t.textFields).fill(''));
    setAiSuggestions([]); // Clear suggestions if manually selecting
    setSettings(prev => ({ ...prev, positions: undefined, manualLayout: false }));
    setStep('editor');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleCustomUpload = (url: string) => {
    const customTemplate: MemeTemplate = {
      id: 'custom-' + Date.now(),
      name: 'Custom Laboratory Asset',
      url: url,
      description: 'User-provided synthesis base.',
      textFields: 2, 
    };
    setSelectedTemplate(customTemplate);
    setTexts(new Array(customTemplate.textFields).fill(''));
    setAiSuggestions([]);
    setSettings(prev => ({ ...prev, positions: undefined, manualLayout: false }));
    setStep('editor');
    toast.success('Custom Asset Loaded!');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleAddField = () => {
    if (selectedTemplate?.id.startsWith('custom-')) {
      const updated = { ...selectedTemplate, textFields: selectedTemplate.textFields + 1 };
      setSelectedTemplate(updated);
      setTexts([...texts, '']);
    }
  };

  const handleRemoveField = () => {
    if (selectedTemplate?.id.startsWith('custom-') && selectedTemplate.textFields > 1) {
      const updated = { ...selectedTemplate, textFields: selectedTemplate.textFields - 1 };
      setSelectedTemplate(updated);
      setTexts(texts.slice(0, -1));
    }
  };

  const handleAutoSynthesize = async () => {
    if (!autoPrompt.trim()) return;
    
    setIsSynthesizing(true);
    setLastGenerated(null);
    try {
      // 1. Ask Gemini to pick 3 diverse template and captions
      const options = await synthesizeMemeCaptions(autoPrompt, templates);
      
      if (options.length === 0) throw new Error("Synthesis failed to generate viable options.");

      setAiSuggestions(options);
      
      // 2. Apply first suggestion initially
      applyAiSuggestion(0, options);
      
      // 3. Navigate to editor for manual refinement
      setStep('editor');
      toast.success('AI Drafts Ready! Swipe to choose.');
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (error: any) {
      toast.error(error.message || 'Synthesis failed.');
    } finally {
      setIsSynthesizing(false);
    }
  };

  const handleRemix = (meme: GeneratedMeme) => {
    const template = templates.find(t => t.id === meme.template_id);
    const activeTemplate = template || {
      id: meme.template_id,
      name: meme.template_name,
      url: meme.image_url,
      description: 'Synthesized Asset Remix',
      textFields: meme.meme_text.length
    };

    setSelectedTemplate(activeTemplate);
    setTexts(meme.meme_text);
    if (meme.settings) {
      setSettings(meme.settings);
    }
    setLastGenerated(null);
    setStep('editor');
    window.scrollTo({ top: 0, behavior: 'smooth' });
    toast.success('Ready for Synthesis Remix!');
  };

  const handleSynthesize = async () => {
    if (!selectedTemplate) return;
    
    setIsSynthesizing(true);
    setLastGenerated(null);
    try {
      const synthesizedUrl = await synthesizeMeme(selectedTemplate, texts, settings);
      
      console.log(`Neural Asset Size: ${(synthesizedUrl.length / 1024).toFixed(2)} KB`);

      const meme = await MemeAPI.generate(
        `Meme about ${selectedTemplate.name}`,
        selectedTemplate.id,
        texts,
        { ...settings, templateName: selectedTemplate.name, imageUrl: synthesizedUrl }
      );
      
      meme.image_url = synthesizedUrl;
      setLastGenerated(meme);
      confetti({
        particleCount: 150,
        spread: 100,
        origin: { y: 0.6 },
        colors: ['#B0FF00', '#ffffff', '#1F1F1F'],
      });
      toast.success('Meme successfully synthesized!');
    } catch (error) {
      toast.error('Synthesis failed. Please try again.');
    } finally {
      setIsSynthesizing(false);
    }
  };

  const handlePositionChange = (index: number, pos: { x: number, y: number }) => {
    const newPositions = settings.positions ? [...settings.positions] : [];
    // Ensure array is filled up to index
    if (newPositions.length <= index) {
      for (let i = newPositions.length; i <= index; i++) {
        if (!newPositions[i]) newPositions[i] = { x: 50, y: i === 0 ? 15 : i === 1 ? 85 : 50 };
      }
    }
    newPositions[index] = pos;
    setSettings({ ...settings, positions: newPositions });
  };

  return (
    <div className="max-w-6xl mx-auto w-full space-y-8 py-8 px-4">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border pb-6">
        <div className="space-y-1">
          <h1 className="font-display text-4xl font-bold tracking-tight">Memery Lab</h1>
          <p className="text-muted text-sm">Follow the synthesis steps to create viral assets.</p>
        </div>

        <div className="flex items-center gap-2 bg-white/5 p-1 rounded-xl border border-border self-start">
           <button 
            onClick={() => setStep('auto')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-mono uppercase tracking-wider transition-all ${
              step === 'auto' ? 'bg-acid text-black font-bold shadow-lg shadow-acid/20' : 'text-muted hover:text-white'
            }`}
          >
            <Sparkles size={14} />
            Auto Gen
          </button>
          <button 
            onClick={() => setStep('template')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-mono uppercase tracking-wider transition-all ${
              step === 'template' ? 'bg-acid text-black font-bold' : 'text-muted hover:text-white'
            }`}
          >
            <LayoutGrid size={14} />
            Designer
          </button>
          {selectedTemplate && (
             <button 
              onClick={() => setStep('editor')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-mono uppercase tracking-wider transition-all ${
                step === 'editor' ? 'bg-acid text-black font-bold' : 'text-muted hover:text-white'
              }`}
            >
              <Type size={14} />
              Editor
            </button>
          )}
        </div>
      </div>

      <AnimatePresence mode="wait">
        {step === 'auto' && (
          <motion.div
            key="auto-step"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="max-w-2xl mx-auto space-y-8"
          >
            <div className="text-center space-y-4 py-12">
               <div className="w-20 h-20 bg-acid/10 rounded-3xl flex items-center justify-center text-acid mx-auto border border-acid/20 animate-pulse">
                  <BrainCircuit size={40} />
               </div>
               <h2 className="text-3xl font-display font-bold">Neural Auto-Synthesis</h2>
               <p className="text-muted">Describe a situation, feeling, or story. MemeGPT will select the perfect base and synthesize captions.</p>
            </div>

            <div className="space-y-4">
              <textarea
                value={autoPrompt}
                onChange={(e) => setAutoPrompt(e.target.value)}
                placeholder="Ex: When I show my project to my boss and he finds a bug immediately..."
                className="w-full bg-black/40 border-2 border-border rounded-2xl p-6 min-h-[160px] focus:border-acid outline-none transition-all resize-none text-lg placeholder:text-muted/50"
              />
              <button
                onClick={handleAutoSynthesize}
                disabled={isSynthesizing || !autoPrompt.trim()}
                className="btn-primary w-full py-5 text-xl flex items-center justify-center gap-3"
              >
                {isSynthesizing ? (
                  <>
                    <Loader2 size={24} className="animate-spin" />
                    Connecting to Brain...
                  </>
                ) : (
                  <>
                    <Zap size={24} />
                    Synthesize Now
                  </>
                )}
              </button>
            </div>
          </motion.div>
        )}

        {step === 'template' && (
          <motion.div
            key="template-step"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
          >
            <div className="space-y-8">
              <div className="flex items-center gap-4 border-l-2 border-acid pl-6">
                 <h2 className="text-2xl font-display font-bold">Pick Your Base Asset</h2>
              </div>
              <TemplateSelector 
                templates={templates} 
                onSelect={handleTemplateSelect} 
                onCustomUpload={handleCustomUpload}
                selectedId={selectedTemplate?.id}
              />
            </div>
          </motion.div>
        )}

        {step === 'editor' && (
          <motion.div
            key="editor-step"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="grid grid-cols-1 lg:grid-cols-2 gap-12"
          >
            <div className="space-y-10">
              <div className="flex flex-col gap-4">
                <button 
                  onClick={() => setStep('auto')}
                  className="flex items-center gap-2 text-muted hover:text-acid transition-colors text-xs font-mono uppercase tracking-widest w-fit"
                >
                  <ArrowLeft size={14} />
                  Back to Neural Prompt
                </button>

                {aiSuggestions.length > 0 && (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <h3 className="text-[10px] font-mono text-muted uppercase tracking-[0.2em] flex items-center gap-2">
                        <Sparkles size={12} className="text-acid" /> Batch Neural Ideas ({aiSuggestions.length})
                      </h3>
                      <div className="flex gap-1.5">
                         {aiSuggestions.map((_, i) => (
                           <div 
                             key={i}
                             className={`h-1 rounded-full transition-all duration-300 ${
                               currentAiIndex === i ? 'bg-acid w-6' : 'bg-white/10 w-2'
                             }`}
                           />
                         ))}
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-5 gap-3 h-24 overflow-hidden">
                      {aiSuggestions.map((suggestion, i) => {
                        const template = templates.find(t => t.id === suggestion.templateId);
                        return (
                          <button
                            key={i}
                            onClick={() => applyAiSuggestion(i, aiSuggestions)}
                            className={`relative rounded-lg overflow-hidden border-2 transition-all duration-300 group ${
                              currentAiIndex === i 
                                ? 'border-acid scale-105 shadow-[0_0_15px_rgba(176,255,0,0.4)]' 
                                : 'border-border grayscale hover:grayscale-0 hover:border-white/30'
                            }`}
                          >
                            {template && (
                              <>
                                <img 
                                  src={template.url} 
                                  className="w-full h-full object-cover" 
                                  alt="Draft" 
                                />
                                <div className="absolute inset-0 bg-black/40 group-hover:bg-transparent transition-colors" />
                                <div className="absolute top-1 left-1.5 text-[8px] font-bold text-acid bg-black/80 px-1 rounded">
                                  #{i+1}
                                </div>
                              </>
                            )}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>

              <div className="space-y-2">
                 <div className="flex items-center gap-2">
                   <h2 className="text-3xl font-display font-bold">{selectedTemplate?.name}</h2>
                   {aiSuggestions.length > 0 && (
                     <div className="text-[10px] font-mono bg-acid/10 text-acid border border-acid/20 px-2 py-0.5 rounded uppercase tracking-widest">
                       AI Optimized
                     </div>
                   )}
                 </div>
                <p className="text-muted text-sm">{selectedTemplate?.description}</p>
                {aiSuggestions.length > 0 && (
                   <motion.p 
                    key={currentAiIndex}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="text-[10px] text-muted-foreground italic font-mono mt-2"
                   >
                     Rationale: {aiSuggestions[currentAiIndex].reasoning}
                   </motion.p>
                )}
              </div>

              {selectedTemplate?.id.startsWith('custom-') && (
                <div className="flex items-center gap-4 bg-white/5 p-4 rounded-2xl border border-border">
                  <div className="flex-1">
                    <h4 className="text-xs font-mono uppercase tracking-widest text-muted mb-1">Custom Asset Controls</h4>
                    <p className="text-[10px] text-muted-foreground italic">Add or remove text nodes for your custom base.</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button 
                      onClick={handleRemoveField}
                      className="p-2 bg-white/5 hover:bg-white/10 rounded-lg transition-colors border border-border"
                      title="Remove Field"
                    >
                      <Minus size={14} />
                    </button>
                    <span className="font-mono text-sm w-8 text-center">{selectedTemplate.textFields}</span>
                    <button 
                      onClick={handleAddField}
                      className="p-2 bg-acid/20 hover:bg-acid/30 rounded-lg transition-colors border border-acid/20 text-acid"
                      title="Add Field"
                    >
                      <Plus size={14} />
                    </button>
                  </div>
                </div>
              )}

              <MemeEditor 
                numFields={selectedTemplate?.textFields || 1}
                initialTexts={texts}
                settings={settings}
                onTextChange={setTexts}
                onSettingsChange={setSettings}
              />

              <div className="pt-8 border-t border-border">
                <button
                  onClick={handleSynthesize}
                  disabled={isSynthesizing || texts.every(t => !t.trim())}
                  className="btn-primary w-full py-5 text-xl flex items-center justify-center gap-3 disabled:opacity-50 disabled:scale-100"
                >
                  {isSynthesizing ? (
                    <>
                      <Loader2 size={24} className="animate-spin" />
                      Processing Nodes...
                    </>
                  ) : (
                    <>
                      <Wand2 size={24} />
                      Synthesize Meme
                    </>
                  )}
                </button>
              </div>
            </div>

            <div className="space-y-6 lg:sticky lg:top-24 h-fit">
              <div className="flex items-center justify-between font-mono text-[10px] text-muted uppercase tracking-[0.2em] px-2">
                <span>Viewport Preview</span>
                <span className="flex items-center gap-1"><Sparkles size={8} /> AI Render active</span>
              </div>
              <div className="relative">
                <MemePreview 
                  template={selectedTemplate}
                  texts={texts}
                  settings={settings}
                  onPositionChange={handlePositionChange}
                />
                <AnimatePresence>
                  {isSynthesizing && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="absolute inset-0 bg-acid/20 backdrop-blur-sm flex flex-col items-center justify-center rounded-2xl z-20 border-2 border-acid"
                    >
                      <div className="w-16 h-16 border-4 border-white/30 border-t-white rounded-full animate-spin mb-4" />
                      <div className="font-mono text-xs text-white uppercase tracking-[0.3em] font-bold animate-pulse">
                        Neural Synthesis in Progress
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Synthesis Success Panel */}
      <AnimatePresence>
        {lastGenerated && !isSynthesizing && (
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            className="pt-20 border-t border-border space-y-8"
          >
            <div className="text-center space-y-2">
              <div className="w-16 h-16 bg-acid rounded-full flex items-center justify-center text-black mx-auto mb-4 animate-bounce">
                <Wand2 size={32} />
              </div>
              <h2 className="text-4xl font-display font-bold">Synthesis Complete</h2>
              <p className="text-muted">Your hilarious artifact is ready for distribution.</p>
            </div>

            <div className="max-w-sm mx-auto">
              <MemeCard meme={lastGenerated} onRemix={handleRemix} />
            </div>

            <div className="flex flex-wrap justify-center gap-4">
               <button onClick={() => setLastGenerated(null)} className="btn-ghost">
                  Dismiss
               </button>
               <button 
                onClick={() => {
                  setLastGenerated(null);
                  setStep('editor');
                }} 
                className="px-6 py-2 rounded-xl border border-white/10 hover:bg-white/5 transition-all text-sm font-mono uppercase tracking-widest flex items-center gap-2"
               >
                  <RotateCcw size={16} />
                  Keep Editing
               </button>
               <button onClick={() => { setStep('auto'); setLastGenerated(null); setSelectedTemplate(null); setAutoPrompt(''); }} className="btn-primary">
                  Synthesize Another
               </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
