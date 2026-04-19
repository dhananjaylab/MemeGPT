import React from 'react';
import { MemeGenerator } from '../components/MemeGenerator';
import { TrendingTopics } from '../components/TrendingTopics';
import { Sparkles, Zap, Shield, BarChart3 } from 'lucide-react';

export function Home() {
  return (
    <div className="space-y-16 py-8">
      {/* Hero Section */}
      <section className="text-center space-y-6 max-w-4xl mx-auto">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-acid/10 border border-acid/20 text-acid text-xs font-bold uppercase tracking-widest animate-fade-in">
          <Sparkles size={14} />
          AI-Powered Meme Synthesis
        </div>
        <h1 className="font-display text-5xl md:text-7xl font-bold tracking-tight text-white">
          Turn your <span className="text-acid">vibes</span> into memes.
        </h1>
        <p className="text-secondary text-lg md:text-xl max-w-2xl mx-auto leading-relaxed">
          MemeGPT uses state-of-the-art AI to generate trend-aware, hilarious memes from your prompts. 
          Stop trying to be funny. Let the machine do it.
        </p>
      </section>

      {/* Main Generator */}
      <section className="max-w-4xl mx-auto">
        <MemeGenerator />
      </section>

      {/* Topics */}
      <section className="max-w-4xl mx-auto">
        <TrendingTopics />
      </section>

      {/* Features */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-8 pt-16">
        <div className="card-dark space-y-4">
          <div className="w-10 h-10 bg-blue-500/10 rounded-lg flex items-center justify-center text-blue-400">
            <Zap size={20} />
          </div>
          <h3 className="font-display font-bold text-lg">Instant Generation</h3>
          <p className="text-sm text-secondary leading-relaxed">
            Proprietary ARQ-powered task queue ensures your memes are ready in seconds, not minutes.
          </p>
        </div>
        
        <div className="card-dark space-y-4">
          <div className="w-10 h-10 bg-purple-500/10 rounded-lg flex items-center justify-center text-purple-400">
            <Shield size={20} />
          </div>
          <h3 className="font-display font-bold text-lg">Advanced AI Models</h3>
          <p className="text-sm text-secondary leading-relaxed">
            Leveraging specialized visual-humor models trained on millions of viral memes.
          </p>
        </div>

        <div className="card-dark space-y-4">
          <div className="w-10 h-10 bg-acid/10 rounded-lg flex items-center justify-center text-acid">
            <BarChart3 size={20} />
          </div>
          <h3 className="font-display font-bold text-lg">Trend Awareness</h3>
          <p className="text-sm text-secondary leading-relaxed">
            Real-time internet culture analysis keeps your content relevant and shareable.
          </p>
        </div>
      </section>
    </div>
  );
}
