
import { MemeGenerator } from '../components/MemeGenerator';
import { TrendingTopics } from '../components/TrendingTopics';
import { Sparkles, Zap, Shield, BarChart3 } from 'lucide-react';

export function Home() {
  return (
    <div className="space-y-20 py-12">
      {/* Hero Section - Enhanced */}
      <section className="text-center space-y-8 max-w-5xl mx-auto relative">
        {/* Background Effects */}
        <div className="absolute inset-0 bg-gradient-to-r from-acid/5 via-purple-500/5 to-blue-500/5 rounded-3xl blur-3xl -z-10"></div>
        
        <div className="space-y-6">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-acid/10 border border-acid/20 text-acid text-sm font-bold uppercase tracking-widest animate-fade-in">
            <Sparkles size={16} className="animate-pulse" />
            AI-Powered Meme Synthesis
          </div>
          
          <h1 className="font-display text-6xl md:text-8xl font-bold tracking-tight text-white leading-tight">
            Turn your{' '}
            <span className="relative">
              <span className="bg-gradient-to-r from-acid via-acid to-green-400 bg-clip-text text-transparent animate-glow">
                vibes
              </span>
              <div className="absolute inset-0 bg-gradient-to-r from-acid/20 to-green-400/20 blur-xl -z-10"></div>
            </span>
            {' '}into memes.
          </h1>
          
          <p className="text-secondary text-xl md:text-2xl max-w-3xl mx-auto leading-relaxed">
            MemeGPT uses state-of-the-art AI to generate trend-aware, hilarious memes from your prompts. 
            <br />
            <span className="text-acid font-medium">Stop trying to be funny. Let the machine do it.</span>
          </p>
          
          {/* Quick Stats */}
          <div className="flex flex-wrap justify-center gap-8 pt-6">
            <div className="text-center">
              <div className="text-2xl font-bold text-acid">10K+</div>
              <div className="text-xs text-muted uppercase tracking-wider">Memes Generated</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-acid">11</div>
              <div className="text-xs text-muted uppercase tracking-wider">Template Types</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-acid">~15s</div>
              <div className="text-xs text-muted uppercase tracking-wider">Avg Generation</div>
            </div>
          </div>
        </div>
      </section>

      {/* Main Generator */}
      <section className="max-w-4xl mx-auto">
        <MemeGenerator />
      </section>

      {/* Topics */}
      <section className="max-w-4xl mx-auto">
        <TrendingTopics />
      </section>

      {/* Features - Enhanced */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-8 pt-20">
        <div className="group card-dark hover:border-blue-500/30 transition-all duration-300 space-y-4 relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
          <div className="relative">
            <div className="w-12 h-12 bg-blue-500/10 rounded-xl flex items-center justify-center text-blue-400 group-hover:scale-110 transition-transform duration-300">
              <Zap size={24} />
            </div>
            <h3 className="font-display font-bold text-xl mt-4">Lightning Fast</h3>
            <p className="text-sm text-secondary leading-relaxed">
              Proprietary ARQ-powered task queue ensures your memes are ready in seconds, not minutes. 
              <span className="text-blue-400">Built for speed.</span>
            </p>
          </div>
        </div>
        
        <div className="group card-dark hover:border-purple-500/30 transition-all duration-300 space-y-4 relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-purple-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
          <div className="relative">
            <div className="w-12 h-12 bg-purple-500/10 rounded-xl flex items-center justify-center text-purple-400 group-hover:scale-110 transition-transform duration-300">
              <Shield size={24} />
            </div>
            <h3 className="font-display font-bold text-xl mt-4">Advanced AI</h3>
            <p className="text-sm text-secondary leading-relaxed">
              Leveraging GPT-4o with specialized visual-humor models trained on millions of viral memes.
              <span className="text-purple-400">Pure intelligence.</span>
            </p>
          </div>
        </div>

        <div className="group card-dark hover:border-acid/30 transition-all duration-300 space-y-4 relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-acid/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
          <div className="relative">
            <div className="w-12 h-12 bg-acid/10 rounded-xl flex items-center justify-center text-acid group-hover:scale-110 transition-transform duration-300">
              <BarChart3 size={24} />
            </div>
            <h3 className="font-display font-bold text-xl mt-4">Trend Aware</h3>
            <p className="text-sm text-secondary leading-relaxed">
              Real-time internet culture analysis keeps your content relevant and shareable.
              <span className="text-acid">Always current.</span>
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
