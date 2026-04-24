import { MemeGenerator } from '../components/MemeGenerator';
import { TrendingTopics } from '../components/TrendingTopics';
import { Sparkles, Zap, Edit3, Radio } from 'lucide-react';
import { Link } from 'react-router-dom';

export function Home() {
  return (
    <div className="space-y-14 py-10">
      <section className="text-center space-y-8 max-w-5xl mx-auto relative">
        <div className="absolute inset-0 bg-gradient-to-r from-acid/5 via-purple-500/5 to-blue-500/5 rounded-3xl blur-3xl -z-10"></div>
        <div className="space-y-6">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-acid/10 border border-acid/20 text-acid text-sm font-bold uppercase tracking-widest animate-fade-in">
            <Sparkles size={16} className="animate-pulse" />
            AI-Powered Meme Synthesis
          </div>
          <h1 className="font-display text-6xl md:text-8xl font-bold tracking-tight text-white leading-tight">
            Turn your <span className="bg-gradient-to-r from-acid via-acid to-green-400 bg-clip-text text-transparent animate-glow">vibes</span> into memes.
          </h1>
          <p className="text-secondary text-xl md:text-2xl max-w-3xl mx-auto leading-relaxed">
            MemeGPT generates trend-aware meme options and lets you refine them with full manual controls.
          </p>
        </div>
      </section>

      <section className="space-y-6">
        <h2 className="text-3xl font-bold text-center">Features</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="card-dark">
            <div className="w-12 h-12 bg-blue-500/10 rounded-xl flex items-center justify-center text-blue-400"><Zap size={24} /></div>
            <h3 className="font-display font-bold text-xl mt-4">Fast Synthesis</h3>
            <p className="text-sm text-secondary mt-2">Generate multiple AI-ready meme options in seconds.</p>
          </div>
          <div className="card-dark">
            <div className="w-12 h-12 bg-purple-500/10 rounded-xl flex items-center justify-center text-purple-400"><Edit3 size={24} /></div>
            <h3 className="font-display font-bold text-xl mt-4">Manual Editor</h3>
            <p className="text-sm text-secondary mt-2">Fine-tune captions, style, and text placement with live preview.</p>
          </div>
          <div className="card-dark">
            <div className="w-12 h-12 bg-acid/10 rounded-xl flex items-center justify-center text-acid"><Radio size={24} /></div>
            <h3 className="font-display font-bold text-xl mt-4">Trending Sync</h3>
            <p className="text-sm text-secondary mt-2">Turn current trending topics into instant meme prompts.</p>
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 lg:grid-cols-4 gap-8 items-start">
        <div className="lg:col-span-3 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-3xl font-bold">Synthesize A Meme</h2>
            <Link to="/synthesize" className="btn-ghost text-xs">Open Full Synthesize Page</Link>
          </div>
          <MemeGenerator />
        </div>
        <div className="lg:col-span-1 sticky top-6">
          <TrendingTopics maxItems={6} variant="sidebar" />
        </div>
      </section>
    </div>
  );
}
