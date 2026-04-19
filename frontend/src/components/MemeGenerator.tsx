import { useState, useCallback } from 'react';
import { Wand2, Loader2, Sparkles, RefreshCw } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { MemeCard } from './MemeCard';
import { GeneratedMeme } from '../lib/types';
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
        setMemes(prev => [...result.memes, ...prev]);
        toast.success(`Generated ${result.memes.length} memes!`);
      }
    } catch (error: any) {
      console.error('Generation error:', error);
      if (error.isRateLimit) {
        toast.error('Daily limit reached. Upgrade to Pro for unlimited generation!', {
          duration: 5000,
          icon: '🚀'
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
          setMemes(prev => [...data.result.memes, ...prev]);
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
    <div className="space-y-8">
      {/* Input Section */}
      <div className="card-dark p-6">
        <div className="space-y-4">
          <div>
            <label htmlFor="prompt" className="block text-sm font-medium text-primary mb-2">
              What's on your mind? 🤔
            </label>
            <textarea
              id="prompt"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={handleKeyPress}
              placeholder="Enter a topic, situation, or story... (e.g., 'When you realize it's Monday morning')"
              aria-label="Meme generation prompt"
              className="input-dark w-full h-32 resize-none"
              disabled={isGenerating}
            />
          </div>
          
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs text-muted">
              <Sparkles size={12} />
              <span>Tip: Be specific for better results</span>
            </div>
            
            <div className="flex items-center gap-2">
              {memes.length > 0 && (
                <button
                  onClick={clearMemes}
                  className="btn-ghost text-xs"
                  disabled={isGenerating}
                  aria-label="Clear all current results"
                >
                  <RefreshCw size={14} />
                  Clear
                </button>
              )}
              <button
                onClick={handleGenerate}
                disabled={isGenerating || !prompt.trim()}
                className="btn-acid"
                aria-busy={isGenerating}
                aria-label={isGenerating ? "Generating memes" : "Generate memes"}
              >
                {isGenerating ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Wand2 size={16} />
                    Generate Memes
                  </>
                )}
              </button>
            </div>
          </div>
          
          {isGenerating && (
            <div className="bg-surface-2 rounded-lg p-3">
              <div className="flex items-center gap-2 text-sm text-secondary">
                <Loader2 size={14} className="animate-spin" />
                <span>
                  {jobId 
                    ? 'AI is crafting your memes... This may take 10-30 seconds'
                    : 'Starting generation...'
                  }
                </span>
              </div>
              <div className="mt-2 h-1 bg-surface-3 rounded-full overflow-hidden">
                <div className="h-full bg-acid rounded-full animate-pulse" style={{ width: '60%' }} />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Results Section */}
      {memes.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-display text-xl text-primary">
              Your Memes ({memes.length})
            </h2>
            <span className="badge-dim">
              Latest first
            </span>
          </div>
          
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {memes.map((meme, index) => (
              <MemeCard 
                key={meme.id} 
                meme={meme} 
                priority={index < 3}
                showStats={false}
              />
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {memes.length === 0 && !isGenerating && (
        <div className="text-center py-12">
          <div className="w-16 h-16 bg-surface-2 rounded-full flex items-center justify-center mx-auto mb-4">
            <Wand2 size={24} className="text-muted" />
          </div>
          <h3 className="font-display text-lg text-primary mb-2">
            Ready to create some memes?
          </h3>
          <p className="text-secondary text-sm max-w-md mx-auto">
            Enter any topic, situation, or story above and let our AI generate hilarious memes for you.
          </p>
        </div>
      )}
    </div>
  );
}
