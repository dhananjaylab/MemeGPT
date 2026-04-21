import { useState, useCallback } from 'react';
import { Wand2, Loader2, Sparkles, RefreshCw } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { MemeCard } from './MemeCard';
import type { GeneratedMeme } from '../lib/types';
import { generateMemes, apiClient } from '../lib/api';

export function MemeGenerator() {
  const [prompt, setPrompt] = useState('');
  const [memes, setMemes] = useState<GeneratedMeme[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);

  const handleGenerate = useCallback(async () => {
    if (!prompt.trim()) {
      toast.error('Please enter a topic or situation');
      return;
    }

    if (prompt.trim().length < 10) {
      toast.error('Please provide more context (at least 10 characters)');
      return;
    }

    setIsGenerating(true);
    setJobId(null);

    try {
      const result = await generateMemes(prompt.trim());
      
      if (result.job_id) {
        setJobId(result.job_id);
        // Start polling for results
        pollJobStatus(result.job_id);
      } else if (result.memes) {
        // Immediate response
        setMemes(prev => [...(result.memes || []), ...prev]);
        toast.success(`Generated ${result.memes.length} memes!`);
      }
    } catch (error: any) {
      console.error('Generation error:', error);
      if (error.isRateLimit) {
        toast.error('Daily limit reached. Upgrade to Pro for unlimited generation!', {
          duration: 5000,
          icon: '🚀'
        });
      } else if (error.message?.includes('fetch')) {
        toast.error('Backend server is not running. Please start the backend first.', {
          duration: 8000,
          icon: '⚠️'
        });
      } else {
        toast.error(error.message || 'Failed to generate memes. Please try again.');
      }
    } finally {
      if (!jobId) {
        setIsGenerating(false);
      }
    }
  }, [prompt, jobId]);

  const pollJobStatus = useCallback(async (id: string) => {
    const maxAttempts = 30; // 30 seconds max
    let attempts = 0;

    const poll = async () => {
      try {
        const data = await apiClient.getJobStatus(id);

        if (data.status === 'completed' && data.result?.memes) {
          setMemes(prev => [...(data.result?.memes || []), ...prev]);
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

        // Continue polling if still processing
        if (data.status === 'processing' && attempts < maxAttempts) {
          attempts++;
          setTimeout(poll, 1000);
        } else if (attempts >= maxAttempts) {
          toast.error('Generation timed out. Please try again.');
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

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      handleGenerate();
    }
  };

  const clearMemes = () => {
    setMemes([]);
    toast.success('Cleared all memes');
  };

  return (
    <div className="space-y-12">
      {/* Input Section - Enhanced Design */}
      <div className="relative">
        {/* Background Glow Effect */}
        <div className="absolute inset-0 bg-gradient-to-r from-acid/5 via-purple-500/5 to-blue-500/5 rounded-3xl blur-xl"></div>
        
        <div className="relative glass-card border-2 border-acid/20 p-8">
          <div className="space-y-6">
            {/* Header */}
            <div className="text-center space-y-2">
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-acid/10 border border-acid/30 text-acid text-sm font-bold">
                <Sparkles size={16} className="animate-pulse" />
                AI Meme Generator
              </div>
              <h2 className="font-display text-2xl font-bold text-white">
                What's your vibe today?
              </h2>
              <p className="text-secondary text-sm">
                Describe any situation, feeling, or random thought - our AI will turn it into hilarious memes
              </p>
            </div>

            {/* Enhanced Input */}
            <div className="space-y-4">
              <div className="relative">
                <textarea
                  id="prompt"
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  onKeyDown={handleKeyPress}
                  placeholder="Try: 'When you finally understand a programming concept' or 'Monday morning energy' or 'That feeling when your code works on the first try'..."
                  aria-label="Meme generation prompt"
                  className="w-full h-40 bg-surface/50 backdrop-blur-sm border-2 border-border hover:border-acid/40 focus:border-acid/60 rounded-2xl px-6 py-4 text-primary placeholder:text-muted/70 focus:outline-none transition-all duration-300 resize-none text-lg leading-relaxed"
                  disabled={isGenerating}
                />
                <div className="absolute bottom-4 right-4 text-xs text-muted">
                  {prompt.length}/1000
                </div>
              </div>

              {/* Quick Suggestions */}
              <div className="flex flex-wrap gap-2">
                <span className="text-xs text-muted font-medium">Quick ideas:</span>
                {['Monday vibes', 'Coding life', 'Weekend plans', 'Coffee addiction'].map((suggestion) => (
                  <button
                    key={suggestion}
                    onClick={() => setPrompt(suggestion)}
                    disabled={isGenerating}
                    className="px-3 py-1 text-xs bg-surface-2 hover:bg-surface-3 border border-border hover:border-acid/40 rounded-full text-secondary hover:text-primary transition-all duration-200"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
            
            {/* Action Bar */}
            <div className="flex items-center justify-between pt-4 border-t border-border/50">
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-2 text-xs text-muted">
                  <Sparkles size={14} className="text-acid" />
                  <span>Pro tip: Be specific and descriptive for better results</span>
                </div>
              </div>
              
              <div className="flex items-center gap-3">
                {memes.length > 0 && (
                  <button
                    onClick={clearMemes}
                    className="px-4 py-2 text-sm bg-surface-2 hover:bg-surface-3 border border-border hover:border-red-500/40 rounded-xl text-secondary hover:text-red-400 transition-all duration-200 flex items-center gap-2"
                    disabled={isGenerating}
                    aria-label="Clear all current results"
                  >
                    <RefreshCw size={16} />
                    Clear All
                  </button>
                )}
                <button
                  onClick={handleGenerate}
                  disabled={isGenerating || !prompt.trim()}
                  className="px-8 py-3 bg-gradient-to-r from-acid to-acid/80 hover:from-acid/90 hover:to-acid/70 text-black font-bold rounded-xl transition-all duration-300 flex items-center gap-3 shadow-lg shadow-acid/20 hover:shadow-acid/30 disabled:opacity-50 disabled:cursor-not-allowed text-lg"
                  aria-busy={isGenerating}
                  aria-label={isGenerating ? "Generating memes" : "Generate memes"}
                >
                  {isGenerating ? (
                    <>
                      <Loader2 size={20} className="animate-spin" />
                      Generating Magic...
                    </>
                  ) : (
                    <>
                      <Wand2 size={20} />
                      Generate Memes
                    </>
                  )}
                </button>
              </div>
            </div>
            
            {/* Enhanced Loading State */}
            {isGenerating && (
              <div className="bg-gradient-to-r from-surface-2/50 to-surface-3/50 backdrop-blur-sm rounded-2xl p-6 border border-acid/20">
                <div className="flex items-center gap-3 text-primary mb-4">
                  <div className="w-8 h-8 bg-acid/20 rounded-full flex items-center justify-center">
                    <Loader2 size={16} className="animate-spin text-acid" />
                  </div>
                  <div>
                    <div className="font-medium">
                      {jobId ? 'AI is crafting your memes...' : 'Starting generation...'}
                    </div>
                    <div className="text-sm text-secondary">
                      This usually takes 10-30 seconds
                    </div>
                  </div>
                </div>
                <div className="relative h-2 bg-surface-3 rounded-full overflow-hidden">
                  <div className="absolute inset-0 bg-gradient-to-r from-acid/60 via-acid to-acid/60 rounded-full animate-pulse"></div>
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent rounded-full animate-shimmer"></div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Results Section - Enhanced */}
      {memes.length > 0 && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <h2 className="font-display text-2xl font-bold text-white">
                Your Memes
              </h2>
              <div className="px-3 py-1 bg-acid/10 border border-acid/30 rounded-full">
                <span className="text-acid font-bold text-sm">{memes.length}</span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="badge-dim">Latest first</span>
            </div>
          </div>
          
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8">
            {memes.map((meme, index) => (
              <div 
                key={meme.id} 
                className="animate-slide-up"
                style={{ animationDelay: `${index * 100}ms` }}
              >
                <MemeCard 
                  meme={meme} 
                  priority={index < 3}
                  showStats={false}
                />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Enhanced Empty State */}
      {memes.length === 0 && !isGenerating && (
        <div className="text-center py-16 space-y-6">
          <div className="relative mx-auto w-24 h-24">
            <div className="absolute inset-0 bg-gradient-to-r from-acid/20 to-purple-500/20 rounded-full blur-xl"></div>
            <div className="relative w-24 h-24 bg-gradient-to-br from-surface-2 to-surface-3 rounded-full flex items-center justify-center border border-border">
              <Wand2 size={32} className="text-acid" />
            </div>
          </div>
          <div className="space-y-3">
            <h3 className="font-display text-2xl font-bold text-white">
              Ready to create some magic?
            </h3>
            <p className="text-secondary max-w-md mx-auto leading-relaxed">
              Describe any situation, feeling, or random thought above. Our AI will transform it into hilarious, shareable memes in seconds.
            </p>
          </div>
          <div className="flex flex-wrap justify-center gap-2 pt-4">
            <div className="text-xs text-muted">Try something like:</div>
            {[
              "When you finally fix that bug",
              "Monday morning energy",
              "Trying to adult",
              "Weekend vs Monday"
            ].map((example, index) => (
              <button
                key={index}
                onClick={() => setPrompt(example)}
                className="px-3 py-1 text-xs bg-surface-2/50 hover:bg-acid/10 border border-border hover:border-acid/40 rounded-full text-secondary hover:text-acid transition-all duration-200"
              >
                "{example}"
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
