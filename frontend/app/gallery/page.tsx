import { Metadata } from 'next';
import { GalleryClient } from './GalleryClient';
import { ErrorBoundary } from '@/components/ErrorBoundary';

export const metadata: Metadata = {
  title: 'Meme Gallery | MemeGPT',
  description: 'Explore the funniest AI-generated memes from our community.',
};

export default function GalleryPage() {
  return (
    <main className="container mx-auto px-4 py-12 max-w-7xl">
      <div className="mb-10 text-center">
        <h1 className="font-display text-5xl font-bold bg-gradient-to-r from-acid to-white bg-clip-text text-transparent mb-3">
          Community Gallery
        </h1>
        <p className="font-mono text-xs text-muted uppercase tracking-[0.2em]">
          Endless stream of digital consciousness
        </p>
      </div>

      <ErrorBoundary componentName="Gallery">
        <GalleryClient />
      </ErrorBoundary>
    </main>
  );
}
