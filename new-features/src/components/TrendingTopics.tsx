
import { TrendingUp, Flame, MessageSquare, Twitter } from 'lucide-react';
import { motion } from 'motion/react';
import type { TrendingTopic } from '../types';
import { useState, useEffect } from 'react';
import { MemeAPI } from '../lib/api';

export function TrendingTopics() {
  const [topics, setTopics] = useState<TrendingTopic[]>([]);

  useEffect(() => {
    MemeAPI.getTrending().then(setTopics);
  }, []);

  return (
    <div className="glass-card">
      <div className="flex items-center gap-2 mb-6">
        <TrendingUp size={16} className="text-acid" />
        <h2 className="font-mono text-xs uppercase tracking-widest text-muted">Currently Trending</h2>
      </div>

      <div className="space-y-4">
        {topics.map((topic, i) => (
          <motion.div
            key={topic.id}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.1 }}
            className="flex items-start gap-4 p-3 rounded-xl hover:bg-white/5 transition-colors cursor-pointer group"
          >
            <div className="mt-1">
              {topic.source === 'reddit' && <MessageSquare size={14} className="text-orange-400" />}
              {topic.source === 'twitter' && <Twitter size={14} className="text-blue-400" />}
              {topic.source === 'news' && <Flame size={14} className="text-red-400" />}
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium group-hover:text-acid transition-colors">{topic.title}</p>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-[10px] uppercase font-mono text-muted">{topic.source}</span>
                <span className="text-[10px] text-muted">•</span>
                <span className="text-[10px] font-mono text-muted">{(topic.score! / 1000).toFixed(1)}k score</span>
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      <div className="mt-6 pt-6 border-t border-border">
        <p className="text-[10px] text-center font-mono text-muted uppercase tracking-widest">
            Click to auto-generate from topic
        </p>
      </div>
    </div>
  );
}
