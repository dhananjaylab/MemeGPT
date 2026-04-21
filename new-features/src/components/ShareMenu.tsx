
import React, { useState, useRef, useEffect, MouseEvent } from 'react';
import { Share2, MessageCircle, Copy, Check, Twitter, Send } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { motion, AnimatePresence } from 'motion/react';
import type { GeneratedMeme } from '../types';

interface ShareMenuProps {
  meme: GeneratedMeme;
}

export function ShareMenu({ meme }: ShareMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: any) {
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

  const memeUrl = meme.image_url; // In a real app, this would be the detail page URL
  const shareText = `Check out this meme I synthesized with MemeGPT! 🤖✨`;

  const handleCopy = async (e: MouseEvent) => {
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(memeUrl);
      setCopied(true);
      toast.success('Link copied to clipboard!');
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      toast.error('Failed to copy link');
    }
  };

  const shareOptions = [
    {
      name: 'Twitter',
      icon: Twitter,
      color: 'hover:text-[#1DA1F2]',
      action: () => {
        window.open(`https://twitter.com/intent/tweet?text=${encodeURIComponent(shareText)}&url=${encodeURIComponent(memeUrl)}`, '_blank');
      }
    },
    {
      name: 'WhatsApp',
      icon: MessageCircle,
      color: 'hover:text-[#25D366]',
      action: () => {
        window.open(`https://wa.me/?text=${encodeURIComponent(shareText + ' ' + memeUrl)}`, '_blank');
      }
    },
    {
      name: 'Reddit',
      icon: Send,
      color: 'hover:text-[#FF4500]',
      action: () => {
        window.open(`https://www.reddit.com/submit?title=${encodeURIComponent(shareText)}&url=${encodeURIComponent(memeUrl)}`, '_blank');
      }
    }
  ];

  return (
    <div className="relative" ref={menuRef}>
      <button
        onClick={(e) => {
          e.stopPropagation();
          setIsOpen(!isOpen);
        }}
        className="p-3 bg-white/10 hover:bg-white/20 rounded-full backdrop-blur-md transition-colors"
        title="Share Meme"
      >
        <Share2 size={20} className="text-white" />
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 10 }}
            className="absolute bottom-full right-0 mb-3 w-48 bg-surface border border-border rounded-xl shadow-2xl p-2 z-50 overflow-hidden"
          >
            <div className="space-y-1">
              {shareOptions.map((option) => (
                <button
                  key={option.name}
                  onClick={(e) => {
                    e.stopPropagation();
                    option.action();
                    setIsOpen(false);
                  }}
                  className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-muted transition-colors hover:bg-white/5 ${option.color}`}
                >
                  <option.icon size={16} />
                  <span>{option.name}</span>
                </button>
              ))}
              <div className="h-px bg-border my-1" />
              <button
                onClick={handleCopy}
                className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-muted hover:bg-white/5 hover:text-acid transition-colors"
              >
                {copied ? <Check size={16} className="text-acid" /> : <Copy size={16} />}
                <span>{copied ? 'Copied!' : 'Copy Link'}</span>
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
