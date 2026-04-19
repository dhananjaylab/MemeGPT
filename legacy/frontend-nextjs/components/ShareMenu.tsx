'use client';

import { useState, useRef, useEffect } from 'react';
import { Share2, Twitter, MessageCircle, Copy, Check } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { GeneratedMeme } from '@/lib/types';
import { apiClient } from '@/lib/api';

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
      icon: Twitter,
      action: () => {
        const text = `Check out this hilarious meme: "${memeText}" 😂`;
        const url = `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(memeUrl)}&hashtags=meme,AI,funny`;
        window.open(url, '_blank', 'width=550,height=420');
        trackShare('twitter');
      },
    },
    {
      name: 'WhatsApp',
      icon: MessageCircle,
      action: () => {
        const text = `Check out this meme: ${memeText} ${memeUrl}`;
        const url = `https://wa.me/?text=${encodeURIComponent(text)}`;
        window.open(url, '_blank');
        trackShare('whatsapp');
      },
    },
    {
      name: 'Copy Link',
      icon: copied ? Check : Copy,
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
              <option.icon size={16} />
              <span>{option.name}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}