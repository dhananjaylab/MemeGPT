import { motion } from 'framer-motion';
import { Wand2 } from 'lucide-react';
import { MemeGenerator } from '../components/MemeGenerator';
import { PageTransition, staggerChild } from '../components/PageTransition';

export function Synthesize() {
  return (
    <PageTransition>
      <div className="space-y-6 pb-10">
        <motion.div variants={staggerChild}>
          <div className="flex items-center gap-3 mb-1">
            <div className="w-9 h-9 bg-acid/10 border border-acid/20 rounded-xl flex items-center justify-center">
              <Wand2 size={18} className="text-acid" />
            </div>
            <h1 className="text-3xl md:text-4xl font-bold">Synthesize</h1>
          </div>
          <p className="text-secondary text-sm md:text-base pl-12">
            Generate memes with AI suggestions or manual editing.
          </p>
        </motion.div>

        <motion.div variants={staggerChild}>
          <MemeGenerator />
        </motion.div>
      </div>
    </PageTransition>
  );
}
