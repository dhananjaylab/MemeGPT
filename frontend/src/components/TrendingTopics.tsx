import React, { useEffect, useState } from 'react';
import { TrendingUp, TrendingDown, ChevronRight } from 'lucide-react';
import { motion } from 'framer-motion';

export interface TrendingTopic {
  name: string;
  source: string;
  count: number;
  trend_direction: 'up' | 'down' | 'steady';
}

export interface TrendingTopicsProps {
  onTopicSelect?: (topic: string) => void;
  maxItems?: number;
  variant?: 'sidebar' | 'inline';
}

export function TrendingTopics({
  onTopicSelect,
  maxItems = 8,
  variant = 'sidebar',
}: TrendingTopicsProps) {
  const [topics, setTopics] = useState<TrendingTopic[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch trending topics from backend
  useEffect(() => {
    const fetchTopics = async () => {
      try {
        setIsLoading(true);
        const response = await fetch(`/api/trending/topics?limit=${maxItems}`);
        if (!response.ok) {
          throw new Error(`Failed to fetch trending topics: ${response.statusText}`);
        }
        const data = await response.json();
        setTopics(data.topics || []);
      } catch (err) {
        console.error('Error fetching trending topics:', err);
        setError(err instanceof Error ? err.message : 'Failed to load trending topics');
      } finally {
        setIsLoading(false);
      }
    };

    fetchTopics();
    
    // Refresh topics every 5 minutes
    const interval = setInterval(fetchTopics, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [maxItems]);

  const getTrendIcon = (direction: 'up' | 'down' | 'steady') => {
    switch (direction) {
      case 'up':
        return <TrendingUp size={14} className="text-green-400" />;
      case 'down':
        return <TrendingDown size={14} className="text-red-400" />;
      case 'steady':
        return <div className="w-0.5 h-3.5 bg-gray-400" />;
    }
  };

  const handleTopicClick = (topicName: string) => {
    onTopicSelect?.(topicName);
  };

  if (isLoading) {
    return (
      <div className={`card-dark ${variant === 'inline' ? 'w-full' : ''}`}>
        <div className="flex items-center justify-center py-8">
          <div className="w-6 h-6 border-2 border-acid border-t-transparent rounded-full animate-spin" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`card-dark ${variant === 'inline' ? 'w-full' : ''}`}>
        <p className="text-red-500 text-sm">{error}</p>
      </div>
    );
  }

  if (topics.length === 0) {
    return (
      <div className={`card-dark ${variant === 'inline' ? 'w-full' : ''}`}>
        <p className="text-secondary text-sm text-center py-8">No trending topics</p>
      </div>
    );
  }

  return (
    <div className={`card-dark ${variant === 'inline' ? 'w-full' : ''}`}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold flex items-center gap-2">
          <TrendingUp size={18} className="text-acid" />
          Trending Now
        </h3>
      </div>

      <div className={variant === 'inline' ? 'grid grid-cols-2 gap-2' : 'space-y-2'}>
        {topics.map((topic, idx) => (
          <motion.button
            key={`${topic.name}-${idx}`}
            onClick={() => handleTopicClick(topic.name)}
            className="group text-left p-3 rounded-lg border border-border hover:border-acid/50 transition-all hover:bg-surface-2"
            whileHover={{ x: 4 }}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: idx * 0.05 }}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-primary truncate group-hover:text-acid transition-colors">
                  {topic.name}
                </p>
                <div className="flex items-center gap-1 mt-1">
                  <span className="text-xs text-muted bg-surface-3 px-1.5 py-0.5 rounded">
                    {topic.source}
                  </span>
                  <span className="text-xs text-secondary">
                    {topic.count.toLocaleString()}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-1">
                {getTrendIcon(topic.trend_direction)}
                <ChevronRight size={14} className="text-secondary group-hover:text-acid transition-colors" />
              </div>
            </div>
          </motion.button>
        ))}
      </div>

      {/* Refresh hint */}
      <p className="text-xs text-muted text-center mt-4 pt-3 border-t border-border">
        Refreshes every 5 minutes
      </p>
    </div>
  );
}
      source: 'reddit',
      score: 11234,
      created_at: new Date().toISOString(),
    },
  ];
}
