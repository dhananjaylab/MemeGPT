import { Metadata } from 'next';
import { notFound } from 'next/navigation';
import Image from 'next/image';
import Link from 'next/link';
import { ArrowLeft, Calendar, Eye, Heart, Share2, Download } from 'lucide-react';
import { ShareMenu } from '@/components/ShareMenu';
import { getMeme } from '@/lib/api';

interface MemePageProps {
  params: {
    id: string;
  };
}

export async function generateMetadata({ params }: MemePageProps): Promise<Metadata> {
  try {
    const meme = await getMeme(params.id);
    const memeText = meme.meme_text.join(' / ');
    
    return {
      title: `${meme.template_name} Meme - MemeGPT`,
      description: `"${memeText}" - Generated with AI on MemeGPT`,
      openGraph: {
        title: `${meme.template_name} Meme`,
        description: `"${memeText}"`,
        images: [
          {
            url: meme.image_url,
            width: 800,
            height: 800,
            alt: memeText,
          },
        ],
        type: 'website',
      },
      twitter: {
        card: 'summary_large_image',
        title: `${meme.template_name} Meme`,
        description: `"${memeText}"`,
        images: [meme.image_url],
      },
    };
  } catch {
    return {
      title: 'Meme Not Found - MemeGPT',
      description: 'This meme could not be found.',
    };
  }
}

export default async function MemePage({ params }: MemePageProps) {
  let meme;
  
  try {
    meme = await getMeme(params.id);
  } catch {
    notFound();
  }

  const handleDownload = async () => {
    'use client';
    try {
      const response = await fetch(meme.image_url);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `memegpt-${meme.id}.png`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Download failed:', error);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        {/* Header */}
        <div className="flex items-center gap-4 mb-8">
          <Link 
            href="/" 
            className="flex items-center gap-2 text-secondary hover:text-primary transition-colors"
          >
            <ArrowLeft size={20} />
            <span>Back to Generator</span>
          </Link>
        </div>

        <div className="grid lg:grid-cols-2 gap-8">
          {/* Meme Image */}
          <div className="space-y-4">
            <div className="relative aspect-square bg-surface rounded-xl overflow-hidden">
              <Image
                src={meme.image_url}
                alt={meme.meme_text.join(' / ')}
                fill
                className="object-contain"
                priority
                sizes="(max-width: 1024px) 100vw, 50vw"
              />
            </div>

            {/* Action Buttons */}
            <div className="flex items-center justify-center gap-3">
              <button
                onClick={handleDownload}
                className="btn-acid flex items-center gap-2"
              >
                <Download size={16} />
                Download
              </button>
              
              <ShareMenu meme={meme} className="btn-ghost" />
            </div>
          </div>

          {/* Meme Details */}
          <div className="space-y-6">
            <div>
              <h1 className="font-display text-display-md text-primary mb-2">
                {meme.template_name}
              </h1>
              <p className="text-secondary">
                Generated with AI from: "{meme.prompt}"
              </p>
            </div>

            {/* Meme Text */}
            <div className="card-dark p-6">
              <h2 className="font-medium text-primary mb-4">Meme Text</h2>
              <div className="space-y-3">
                {meme.meme_text.map((text, index) => (
                  <div key={index} className="flex items-start gap-3">
                    <span className="badge-dim text-xs mt-1">
                      {index + 1}
                    </span>
                    <p className="text-secondary flex-1">"{text}"</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-3 gap-4">
              <div className="card-dark p-4 text-center">
                <div className="flex items-center justify-center gap-2 text-secondary mb-1">
                  <Eye size={16} />
                  <span className="font-mono text-sm">Views</span>
                </div>
                <p className="font-display text-xl text-primary">
                  {meme.view_count.toLocaleString()}
                </p>
              </div>
              
              <div className="card-dark p-4 text-center">
                <div className="flex items-center justify-center gap-2 text-secondary mb-1">
                  <Heart size={16} />
                  <span className="font-mono text-sm">Likes</span>
                </div>
                <p className="font-display text-xl text-primary">
                  {meme.like_count.toLocaleString()}
                </p>
              </div>
              
              <div className="card-dark p-4 text-center">
                <div className="flex items-center justify-center gap-2 text-secondary mb-1">
                  <Share2 size={16} />
                  <span className="font-mono text-sm">Shares</span>
                </div>
                <p className="font-display text-xl text-primary">
                  {meme.share_count.toLocaleString()}
                </p>
              </div>
            </div>

            {/* Metadata */}
            <div className="card-dark p-6">
              <h2 className="font-medium text-primary mb-4">Details</h2>
              <div className="space-y-3 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-secondary">Created</span>
                  <div className="flex items-center gap-2 text-primary">
                    <Calendar size={14} />
                    <time dateTime={meme.created_at}>
                      {new Date(meme.created_at).toLocaleDateString('en-US', {
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric',
                      })}
                    </time>
                  </div>
                </div>
                
                <div className="flex items-center justify-between">
                  <span className="text-secondary">Template</span>
                  <span className="text-primary">{meme.template_name}</span>
                </div>
                
                <div className="flex items-center justify-between">
                  <span className="text-secondary">Text Fields</span>
                  <span className="text-primary">{meme.meme_text.length}</span>
                </div>
                
                {meme.metadata?.generation_time_ms && (
                  <div className="flex items-center justify-between">
                    <span className="text-secondary">Generation Time</span>
                    <span className="text-primary">
                      {(meme.metadata.generation_time_ms / 1000).toFixed(1)}s
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Call to Action */}
            <div className="card-dark p-6 text-center">
              <h3 className="font-display text-lg text-primary mb-2">
                Create Your Own Memes
              </h3>
              <p className="text-secondary text-sm mb-4">
                Generate unlimited memes with AI. It's free to get started!
              </p>
              <Link href="/" className="btn-acid">
                Try MemeGPT Now
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}