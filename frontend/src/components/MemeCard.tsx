import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Heart, Share2, Download, ExternalLink, Eye } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { ShareMenu } from './ShareMenu';
import type { GeneratedMeme } from '../lib/types';
import { apiClient } from '../lib/api';

interface MemeCardProps {
  meme: GeneratedMeme;
  priority?: boolean;
  showStats?: boolean;
  className?: string;
}

export function MemeCard({ meme, showStats = false, className = '' }: MemeCardProps) {
  const [imageLoading, setImageLoading] = useState(true);
  const [liked, setLiked] = useState(false);

  const handleDownload = async () => {
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
      toast.success('Meme downloaded!');
    } catch (error) {
      console.error('Download error:', error);
      toast.error('Failed to download meme');
    }
  };

  const handleLike = async () => {
    try {
      // Optimistic update
      setLiked(!liked);
      
      const res = await apiClient.likeMeme(meme.id);
      
      if (!res.liked && !res.like_count) {
        // Revert on error-like response (though liked bool being false isn't always error)
        // For now, if it throws it's handled below
      }
      
      toast.success(liked ? 'Removed like' : 'Liked!');
    } catch (error) {
      console.error('Like error:', error);
      toast.error('Failed to update like');
    }
  };

  return (
    <article className={`group glass-card flex flex-col overflow-hidden hover:border-acid/40 hover:shadow-acid transition-all duration-300 ${className}`}>
      {/* Image */}
      <div className="relative aspect-square overflow-hidden bg-background rounded-lg">
        {imageLoading && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="w-8 h-8 border-2 border-acid border-t-transparent rounded-full animate-spin" />
          </div>
        )}
        
        <img
          src={meme.image_url}
          alt={meme.meme_text.join(' / ')}
          className={`w-full h-full object-contain transition-all duration-300 group-hover:scale-[1.02] ${
            imageLoading ? 'opacity-0' : 'opacity-100'
          }`}
          onLoad={() => setImageLoading(false)}
        />
        
        {/* Overlay on hover */}
        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-all duration-300" />
        
        {/* Quick actions overlay */}
        <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-300">
          <div className="flex items-center gap-2">
            <button
              onClick={handleLike}
              className={`p-2 rounded-full backdrop-blur-sm transition-all duration-200 ${
                liked 
                  ? 'bg-red-500/30 text-red-400 shadow-[0_0_12px_rgba(248,113,113,0.4)]' 
                  : 'bg-black/40 text-white hover:bg-acid/20 hover:text-acid'
              }`}
              title={liked ? 'Unlike' : 'Like'}
              aria-label={liked ? 'Unlike meme' : 'Like meme'}
            >
              <Heart size={16} fill={liked ? 'currentColor' : 'none'} />
            </button>
            
            <ShareMenu meme={meme} />
            
            <button
              onClick={handleDownload}
              className="p-2 rounded-full bg-black/40 text-white hover:bg-acid/20 hover:text-acid backdrop-blur-sm transition-all duration-200"
              title="Download"
              aria-label="Download meme image"
            >
              <Download size={16} />
            </button>
            
            <Link
              to={`/meme/${meme.id}`}
              className="p-2 rounded-full bg-black/40 text-white hover:bg-acid/20 hover:text-acid backdrop-blur-sm transition-all duration-200"
              title="View details"
              aria-label="View meme details"
            >
              <ExternalLink size={16} />
            </Link>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="p-4 flex-1 flex flex-col">
        {/* Template name */}
        <div className="flex items-center justify-between mb-2">
          <span className="badge-dim text-xs">
            {meme.template_name}
          </span>
          {showStats && (
            <div className="flex items-center gap-3 text-xs text-muted">
              <span className="flex items-center gap-1">
                <Eye size={12} />
                {meme.view_count || 0}
              </span>
              <span className="flex items-center gap-1">
                <Heart size={12} />
                {meme.like_count || 0}
              </span>
              <span className="flex items-center gap-1">
                <Share2 size={12} />
                {meme.share_count || 0}
              </span>
            </div>
          )}
        </div>

        {/* Meme text preview */}
        <div className="flex-1 mb-3">
          <div className="space-y-1">
            {meme.meme_text.slice(0, 2).map((text, index) => (
              <p key={index} className="text-sm text-secondary line-clamp-2">
                "{text}"
              </p>
            ))}
            {meme.meme_text.length > 2 && (
              <p className="text-xs text-muted">
                +{meme.meme_text.length - 2} more
              </p>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between text-xs text-muted">
          <time dateTime={meme.created_at}>
            {new Date(meme.created_at).toLocaleDateString()}
          </time>
          
          <div className="flex items-center gap-2">
            <button
              onClick={handleLike}
              className={`flex items-center gap-1 transition-all duration-200 ${
                liked ? 'text-red-400' : 'text-muted hover:text-acid'
              }`}
              aria-label={`${liked ? 'Remove like' : 'Like'} meme`}
            >
              <Heart size={12} fill={liked ? 'currentColor' : 'none'} />
              <span>{(meme.like_count || 0) + (liked ? 1 : 0)}</span>
            </button>
            
            <ShareMenu meme={meme} />
          </div>
        </div>
      </div>
    </article>
  );
}
