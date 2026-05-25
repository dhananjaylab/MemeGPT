import { useEffect, useState } from 'react';
import { TrendingUp, TrendingDown, ChevronRight, ChevronUp, ChevronDown } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

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
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    const fetchTopics = async () => {
      const endpoint = `/api/trending/topics?limit=${maxItems}`;
      try {
        // #region agent log
        fetch('http://127.0.0.1:7248/ingest/4bc30d7b-be40-43cb-a209-7c4afed73eca', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': 'e70ed4' }, body: JSON.stringify({ sessionId: 'e70ed4', runId: 'initial', hypothesisId: 'H3', location: 'frontend/src/components/TrendingTopics.tsx:33', message: 'Trending topics request start', data: { endpoint, maxItems, origin: window.location.origin, pathname: window.location.pathname }, timestamp: Date.now() }) }).catch(() => { });
        // #endregion
        setIsLoading(true);
        const response = await fetch(endpoint);
        // #region agent log
        fetch('http://127.0.0.1:7248/ingest/4bc30d7b-be40-43cb-a209-7c4afed73eca', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': 'e70ed4' }, body: JSON.stringify({ sessionId: 'e70ed4', runId: 'initial', hypothesisId: 'H4', location: 'frontend/src/components/TrendingTopics.tsx:37', message: 'Trending topics response received', data: { endpoint, status: response.status, ok: response.ok, statusText: response.statusText }, timestamp: Date.now() }) }).catch(() => { });
        // #endregion
        if (!response.ok) {
          throw new Error(`Failed to fetch trending topics: ${response.statusText}`);
        }
        const data = await response.json();
        setTopics(data.topics || []);
      } catch (err) {
        const normalizedError = err instanceof Error ? { name: err.name, message: err.message } : { value: String(err) };
        // #region agent log
        fetch('http://127.0.0.1:7248/ingest/4bc30d7b-be40-43cb-a209-7c4afed73eca', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': 'e70ed4' }, body: JSON.stringify({ sessionId: 'e70ed4', runId: 'initial', hypothesisId: 'H5', location: 'frontend/src/components/TrendingTopics.tsx:45', message: 'Trending topics request failed', data: { endpoint, error: normalizedError }, timestamp: Date.now() }) }).catch(() => { });
        // #endregion
        console.error('Error fetching trending topics:', err);
        setError(err instanceof Error ? err.message : 'Failed to load trending topics');
      } finally {
        setIsLoading(false);
      }
    };

    fetchTopics();
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

  if (isLoading) {
    return (
      <div className={`glass-card border border-border p-4 ${variant === 'inline' ? 'w-full' : ''}`}>
        <div className="flex items-center justify-center py-8">
          <div className="w-6 h-6 border-2 border-acid border-t-transparent rounded-full animate-spin" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`glass-card border border-border p-4 ${variant === 'inline' ? 'w-full' : ''}`}>
        <p className="text-red-500 text-sm">{error}</p>
      </div>
    );
  }

  if (topics.length === 0) {
    return (
      <div className={`glass-card border border-border p-4 ${variant === 'inline' ? 'w-full' : ''}`}>
        <p className="text-secondary text-sm text-center py-8">No trending topics</p>
      </div>
    );
  }

  const showSingle = variant === 'sidebar';
  const currentTopic = topics[currentIndex];

  return (
    <div className={`glass-card border border-border p-4 ${variant === 'inline' ? 'w-full' : ''}`}>
      {variant !== 'sidebar' && (
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold flex items-center gap-2">
            <TrendingUp size={18} className="text-acid" />
            Trending Now
          </h3>
        </div>
      )}

      <div className={`grid ${variant === 'sidebar' ? 'grid-cols-1' : 'grid-cols-1 md:grid-cols-2'} gap-2`}>
        {topics.map((topic, idx) => (
          <motion.button
            key={`${topic.name}-${idx}`}
            onClick={() => onTopicSelect?.(topic.name)}
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
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-[10px] uppercase font-bold text-muted bg-surface-3 px-1.5 py-0.5 rounded tracking-tighter">
                    {topic.source}
                  </span>
                  <span className="text-[10px] text-secondary font-mono">
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

      <p className="text-xs text-muted text-center mt-4 pt-3 border-t border-border">
        Refreshes every 5 minutes
      </p>
    </div>
  );
}
