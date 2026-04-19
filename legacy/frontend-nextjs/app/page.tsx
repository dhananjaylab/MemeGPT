import { Suspense } from 'react';
import { MemeGenerator } from '@/components/MemeGenerator';
import { TrendingTopics } from '@/components/TrendingTopics';
import { ErrorBoundary } from '@/components/ErrorBoundary';

export default function HomePage() {
  return (
    <div className="min-h-screen bg-background">
      <main className="container mx-auto px-4 py-8 max-w-7xl">
        <div className="grid lg:grid-cols-3 gap-8">
          {/* Main content */}
          <div className="lg:col-span-2">
            <div className="mb-8 text-center lg:text-left">
              <h1 className="font-display text-display-lg text-primary mb-4">
                Generate memes with{' '}
                <span className="text-acid">AI magic</span> ✨
              </h1>
              <p className="text-secondary text-lg max-w-2xl">
                Turn any topic, story, or situation into hilarious memes. 
                Powered by GPT-4o with 50+ popular templates.
              </p>
            </div>
            
            <ErrorBoundary componentName="MemeGenerator">
              <MemeGenerator />
            </ErrorBoundary>
          </div>
          
          {/* Sidebar */}
          <div className="lg:col-span-1">
            <ErrorBoundary componentName="TrendingTopics">
              <Suspense fallback={<TrendingTopicsSkeleton />}>
                <TrendingTopics />
              </Suspense>
            </ErrorBoundary>
          </div>
        </div>
    </div>
  );
}

function TrendingTopicsSkeleton() {
  return (
    <div className="card-dark p-6">
      <div className="h-6 bg-surface-2 rounded mb-4 animate-pulse" />
      <div className="space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-4 bg-surface-2 rounded animate-pulse" />
        ))}
      </div>
    </div>
  );
}