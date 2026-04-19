'use client';

import { useState, useEffect } from 'react';
import { TrendingUp, Clock, Flame, ExternalLink } from 'lucide-react';
import { apiClient } from '@/lib/api';
import { TrendingTopic } from '@/lib/types';



export function TrendingTopics() {
  const [topics, setTopics] = useState<TrendingTopic[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchTrendingTopics();
  }, []);

  const fetchTrendingTopics = async () => {
    try {
      const data = await apiClient.getTrendingTopics();
      setTopics(data.topics || []);
    } catch (err) {
      console.error('Error fetching trending topics:', err);
      setError('Failed to load trending topics');
      // Fallback to mock data for development
      setTopics(getMockTopics());
    } finally {
      setLoading(false);
    }
  };

  const handleTopicClick = (topic: TrendingTopic) => {
    // Trigger meme generation with this topic
    const event = new CustomEvent('generateFromTopic', { 
      detail: { topic: topic.title } 
    });
    window.dispatchEvent(event);
  };

  if (loading) {
    return <TrendingTopicsSkeleton />;
  }

  if (error) {
    return (
      <div className="card-dark p-6">
        <div className="flex items-center gap-2 mb-4">
          <TrendingUp size={16} className="text-acid" />
          <h2 className="font-mono text-sm uppercase tracking-wider text-secondary">
            Trending Topics
          </h2>
        </div>
        <p className="text-sm text-muted">Unable to load trending topics</p>
      </div>
    );
  }

  return (
    <div className="card-dark p-6">
      <div className="flex items-center gap-2 mb-4">
        <TrendingUp size={16} className="text-acid" />
        <h2 className="font-mono text-sm uppercase tracking-wider text-secondary">
          Trending Topics
        </h2>
      </div>

      <div className="space-y-3">
        {topics.slice(0, 8).map((topic, index) => (
          <div
            key={topic.id}
            className="group cursor-pointer p-3 rounded-lg hover:bg-surface-2 transition-colors"
            onClick={() => handleTopicClick(topic)}
          >
            <div className="flex items-start gap-3">
              <div className="flex-shrink-0 mt-1">
                {topic.source === 'reddit' ? (
                  <Flame size={14} className="text-orange-400" />
                ) : (
                  <Clock size={14} className="text-blue-400" />
                )}
              </div>
              
              <div className="flex-1 min-w-0">
                <p className="text-sm text-primary group-hover:text-acid transition-colors line-clamp-2">
                  {topic.title}
                </p>
                
                <div className="flex items-center justify-between mt-2">
                  <span className="text-xs text-muted capitalize">
                    {topic.source}
                  </span>
                  
                  <div className="flex items-center gap-2">
                    {topic.score && (
                      <span className="text-xs text-muted">
                        {topic.score > 1000 
                          ? `${(topic.score / 1000).toFixed(1)}k` 
                          : topic.score
                        }
                      </span>
                    )}
                    
                    {topic.url && (
                      <a
                        href={topic.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="text-muted hover:text-primary transition-colors"
                        title="View source"
                      >
                        <ExternalLink size={12} />
                      </a>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 pt-4 border-t border-border">
        <p className="text-xs text-muted text-center">
          Click any topic to generate memes about it
        </p>
      </div>
    </div>
  );
}

function TrendingTopicsSkeleton() {
  return (
    <div className="card-dark p-6">
      <div className="flex items-center gap-2 mb-4">
        <div className="w-4 h-4 bg-surface-2 rounded animate-pulse" />
        <div className="h-4 bg-surface-2 rounded w-32 animate-pulse" />
      </div>
      
      <div className="space-y-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="p-3">
            <div className="flex items-start gap-3">
              <div className="w-3 h-3 bg-surface-2 rounded animate-pulse mt-1" />
              <div className="flex-1 space-y-2">
                <div className="h-4 bg-surface-2 rounded animate-pulse" />
                <div className="h-3 bg-surface-2 rounded w-3/4 animate-pulse" />
                <div className="flex justify-between">
                  <div className="h-3 bg-surface-2 rounded w-16 animate-pulse" />
                  <div className="h-3 bg-surface-2 rounded w-8 animate-pulse" />
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// Mock data for development/fallback
function getMockTopics(): TrendingTopic[] {
  return [
    {
      id: '1',
      title: 'When you realize it\'s Monday morning',
      source: 'reddit',
      score: 15420,
      created_at: new Date().toISOString(),
    },
    {
      id: '2',
      title: 'AI taking over programming jobs',
      source: 'news',
      score: 8930,
      created_at: new Date().toISOString(),
    },
    {
      id: '3',
      title: 'Working from home vs office life',
      source: 'reddit',
      score: 12340,
      created_at: new Date().toISOString(),
    },
    {
      id: '4',
      title: 'Coffee addiction among developers',
      source: 'reddit',
      score: 9876,
      created_at: new Date().toISOString(),
    },
    {
      id: '5',
      title: 'New iPhone release reactions',
      source: 'news',
      score: 7654,
      created_at: new Date().toISOString(),
    },
    {
      id: '6',
      title: 'Debugging at 3 AM',
      source: 'reddit',
      score: 11234,
      created_at: new Date().toISOString(),
    },
  ];
}