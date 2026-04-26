import { motion } from 'framer-motion';
import { Sparkles, Zap, Edit3, Radio, ArrowRight, Wand2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import { MemeGenerator } from '../components/MemeGenerator';
import { TrendingTopics } from '../components/TrendingTopics';
import { PageTransition, staggerChild } from '../components/PageTransition';

const features = [
  {
    icon: Zap,
    label: 'Fast Synthesis',
    desc: 'Generate multiple AI-ready meme options in seconds.',
    color: 'text-blue-400',
    bg: 'bg-blue-500/10',
    border: 'border-blue-500/20',
  },
  {
    icon: Edit3,
    label: 'Manual Editor',
    desc: 'Fine-tune captions, style, and text placement with live preview.',
    color: 'text-purple-400',
    bg: 'bg-purple-500/10',
    border: 'border-purple-500/20',
  },
  {
    icon: Radio,
    label: 'Trending Sync',
    desc: 'Turn current trending topics into instant meme prompts.',
    color: 'text-acid',
    bg: 'bg-acid/10',
    border: 'border-acid/20',
  },
];

export function Home() {
  return (
    <PageTransition>
      <div className="space-y-16 pb-16">

        {/* ── Hero ─────────────────────────────────────────────────────── */}
        <motion.section
          variants={staggerChild}
          className="text-center space-y-8 max-w-5xl mx-auto relative pt-6 md:pt-10"
        >
          {/* ambient glow */}
          <div
            className="absolute inset-0 -z-10 rounded-3xl blur-3xl"
            style={{
              background:
                'radial-gradient(ellipse 80% 60% at 50% 30%, rgba(176,255,0,0.07) 0%, rgba(139,92,246,0.04) 50%, transparent 100%)',
            }}
          />

          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-acid/10 border border-acid/20 text-acid text-xs md:text-sm font-bold uppercase tracking-widest"
          >
            <Sparkles size={14} className="animate-pulse" />
            AI-Powered Meme Synthesis
          </motion.div>

          <h1 className="font-display text-5xl sm:text-6xl md:text-7xl lg:text-8xl font-bold tracking-tight text-white leading-tight px-2">
            Turn your{' '}
            <span
              className="bg-gradient-to-r from-acid via-green-300 to-acid bg-clip-text text-transparent animate-text-shimmer"
              style={{ backgroundSize: '200% auto' }}
            >
              vibes
            </span>{' '}
            into memes.
          </h1>

          <p className="text-secondary text-lg md:text-xl max-w-2xl mx-auto leading-relaxed px-4">
            MemeGPT generates trend-aware meme options and lets you refine them
            with full manual controls.
          </p>

          <div className="flex flex-col sm:flex-row gap-3 justify-center px-4">
            <Link to="/synthesize" className="btn-acid text-sm px-8 py-3">
              <Wand2 size={16} />
              Start Creating
            </Link>
            <Link to="/gallery" className="btn-ghost text-sm px-8 py-3">
              Browse Gallery
              <ArrowRight size={14} />
            </Link>
          </div>
        </motion.section>

        {/* ── Feature cards ────────────────────────────────────────────── */}
        <motion.section variants={staggerChild} className="space-y-5">
          <h2 className="text-2xl md:text-3xl font-bold text-center">Why MemeGPT?</h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 md:gap-6">
            {features.map(({ icon: Icon, label, desc, color, bg, border }, i) => (
              <motion.div
                key={label}
                className={`glass-card border ${border} hover:scale-[1.02]`}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
              >
                <div className={`w-11 h-11 ${bg} rounded-xl flex items-center justify-center ${color} mb-4`}>
                  <Icon size={22} />
                </div>
                <h3 className="font-display font-bold text-lg mb-2">{label}</h3>
                <p className="text-sm text-secondary leading-relaxed">{desc}</p>
              </motion.div>
            ))}
          </div>
        </motion.section>

        {/* ── Generator + Trending ─────────────────────────────────────── */}
        <motion.section
          variants={staggerChild}
          className="grid grid-cols-1 lg:grid-cols-4 gap-6 lg:gap-8 items-start"
        >
          <div className="lg:col-span-3 space-y-4">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <h2 className="text-2xl md:text-3xl font-bold">Synthesize A Meme</h2>
              <Link to="/synthesize" className="btn-ghost text-xs">
                Full Page
                <ArrowRight size={12} />
              </Link>
            </div>
            <MemeGenerator />
          </div>

          <div className="lg:col-span-1 lg:sticky lg:top-6">
            <TrendingTopics maxItems={6} variant="sidebar" />
          </div>
        </motion.section>

      </div>
    </PageTransition>
  );
}
