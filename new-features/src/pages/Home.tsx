
import { MemeGenerator } from '../components/MemeGenerator';
import { TrendingTopics } from '../components/TrendingTopics';
import { motion } from 'motion/react';
import { Rocket, Shield, Globe } from 'lucide-react';

export function Home() {
  return (
    <div className="space-y-24 py-12">
      {/* Hero */}
      <section className="text-center space-y-8 max-w-4xl mx-auto relative">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-acid/20 rounded-full blur-[128px] -z-10" />
        
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-6"
        >
          <h1 className="font-display text-6xl md:text-8xl font-bold tracking-tight text-white leading-[0.9]">
            The <span className="text-acid">Memery</span> <br />
            of the Future.
          </h1>
          <p className="text-xl text-secondary max-w-2xl mx-auto leading-relaxed">
            MemeGPT synthesizes internet culture through semantic AI. 
            Stop crafting memes. Start <span className="text-white italic">synthesizing</span> them.
          </p>
        </motion.div>
      </section>

      {/* Generator Section */}
      <section id="generate">
        <MemeGenerator />
      </section>

      {/* Topics & Features */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-1">
          <TrendingTopics />
        </div>
        
        <div className="lg:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-8">
          <FeatureCard
            icon={Rocket}
            title="Fast Synthesis"
            description="Our optimized queue processing means your humor is served fresh in under 15 seconds."
          />
          <FeatureCard
            icon={Shield}
            title="Brand Safe"
            description="Built-in toxicity filters ensure your memes stay funny, not offensive."
          />
          <FeatureCard
            icon={Globe}
            title="Trend Sync"
            description="Real-time web scraping keeps our AI updated on the latest viral phenomena."
          />
          <div className="glass-card border-acid/20 bg-acid/5 flex flex-col items-center justify-center text-center p-8 gap-4">
            <h3 className="font-display text-2xl font-bold text-acid">Ready for Pro?</h3>
            <p className="text-sm text-secondary">Unlimited generations, 4K export, and API access.</p>
            <button className="btn-primary w-full mt-2">Go Pro Now</button>
          </div>
        </div>
      </section>
    </div>
  );
}

function FeatureCard({ icon: Icon, title, description }: { icon: any, title: string, description: string }) {
  return (
    <div className="glass-card hover:border-acid/30 group">
      <div className="w-12 h-12 bg-white/5 rounded-xl flex items-center justify-center text-secondary group-hover:text-acid group-hover:bg-acid/10 transition-all duration-300">
        <Icon size={24} />
      </div>
      <h3 className="font-display text-xl font-bold mt-6 mb-2">{title}</h3>
      <p className="text-sm text-secondary leading-relaxed">{description}</p>
    </div>
  );
}
