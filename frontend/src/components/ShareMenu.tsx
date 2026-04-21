import { useState, useRef, useEffect } from 'react';
import { Share2, MessageCircle, Copy, Check } from 'lucide-react';
import { toast } from 'react-hot-toast';
import type { GeneratedMeme } from '../lib/types';
import { apiClient } from '../lib/api';

interface ShareMenuProps {
  meme: GeneratedMeme;
  className?: string;
}

export function ShareMenu({ meme, className = '' }: ShareMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  const memeUrl = `${window.location.origin}/meme/${meme.id}`;
  const memeText = meme.meme_text.join(' / ');
  
  const shareOptions = [
    {
      name: 'Twitter',
      icon: () => (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
          <path d="M23.953 4.57a10 10 0 01-2.825.775 4.958 4.958 0 002.163-2.723c-.951.555-2.005.959-3.127 1.184a4.92 4.92 0 00-8.384 4.482C7.69 8.095 4.067 6.13 1.64 3.162a4.822 4.822 0 00-.666 2.475c0 1.71.87 3.213 2.188 4.096a4.904 4.904 0 01-2.228-.616v.06a4.923 4.923 0 003.946 4.827 4.996 4.996 0 01-2.212.085 4.936 4.936 0 004.604 3.417 9.867 9.867 0 01-6.102 2.105c-.39 0-.779-.023-1.17-.067a13.995 13.995 0 007.557 2.209c9.053 0 13.998-7.496 13.998-13.985 0-.21 0-.42-.015-.63A9.935 9.935 0 0024 4.59z"/>
        </svg>
      ),
      action: () => {
        const text = `Check out this hilarious meme: "${memeText}" 😂`;
        const url = `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(memeUrl)}&hashtags=meme,AI,funny`;
        window.open(url, '_blank', 'width=550,height=420');
        trackShare('twitter');
      },
    },
    {
      name: 'WhatsApp',
      icon: () => <MessageCircle size={16} />,
      action: () => {
        const text = `Check out this meme: ${memeText} ${memeUrl}`;
        const url = `https://wa.me/?text=${encodeURIComponent(text)}`;
        window.open(url, '_blank');
        trackShare('whatsapp');
      },
    },
    {
      name: 'Copy Link',
      icon: copied ? () => <Check size={16} /> : () => <Copy size={16} />,
      action: async () => {
        try {
          await navigator.clipboard.writeText(memeUrl);
          setCopied(true);
          toast.success('Link copied to clipboard!');
          setTimeout(() => setCopied(false), 2000);
          trackShare('copy');
        } catch (error) {
          console.error('Failed to copy:', error);
          toast.error('Failed to copy link');
        }
      },
    },
  ];

  const trackShare = async (platform: string) => {
    try {
      await apiClient.shareMeme(meme.id, platform as any);
    } catch (error) {
      console.error('Failed to track share:', error);
    }
    setIsOpen(false);
  };

  return (
    <div className={`relative ${className}`} ref={menuRef}>
      <button
        onClick={(e) => {
          e.stopPropagation();
          setIsOpen(!isOpen);
        }}
        className="p-2 rounded-full bg-black/40 text-white hover:bg-black/60 backdrop-blur-sm transition-colors"
        title="Share"
      >
        <Share2 size={16} />
      </button>

      {isOpen && (
        <div className="absolute right-0 top-full mt-2 w-48 bg-surface border border-border rounded-lg shadow-lg z-50 py-2">
          {shareOptions.map((option) => (
            <button
              key={option.name}
              onClick={(e) => {
                e.stopPropagation();
                option.action();
              }}
              className="w-full flex items-center gap-3 px-4 py-2 text-sm text-secondary hover:text-primary hover:bg-surface-2 transition-colors"
            >
              <option.icon />
              <span>{option.name}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
