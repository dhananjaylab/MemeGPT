import React, { useState } from 'react';
import { Share2, Twitter, MessageCircle, Reddit, Copy, Check } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export interface ShareMenuProps {
  memeUrl: string;
  memeTitle?: string;
  onShare?: (platform: string) => void;
}

export function ShareMenu({
  memeUrl,
  memeTitle = 'Check out this awesome meme!',
  onShare,
}: ShareMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const shareOptions = [
    {
      name: 'Twitter',
      icon: Twitter,
      color: 'hover:text-blue-400',
      action: () => {
        const text = encodeURIComponent(`${memeTitle} ${memeUrl}`);
        window.open(
          `https://twitter.com/intent/tweet?text=${text}`,
          '_blank',
          'width=550,height=420'
        );
        onShare?.('twitter');
      },
    },
    {
      name: 'WhatsApp',
      icon: MessageCircle,
      color: 'hover:text-green-400',
      action: () => {
        const text = encodeURIComponent(`${memeTitle}\n${memeUrl}`);
        window.open(
          `https://wa.me/?text=${text}`,
          '_blank'
        );
        onShare?.('whatsapp');
      },
    },
    {
      name: 'Reddit',
      icon: Reddit,
      color: 'hover:text-orange-500',
      action: () => {
        const text = encodeURIComponent(`${memeTitle}\n${memeUrl}`);
        window.open(
          `https://www.reddit.com/submit?title=${encodeURIComponent(memeTitle)}&url=${memeUrl}`,
          '_blank'
        );
        onShare?.('reddit');
      },
    },
  ];

  const handleCopyLink = async () => {
    try {
      await navigator.clipboard.writeText(memeUrl);
      setCopied(true);
      onShare?.('copy');
      setTimeout(() => setCopied(false), 2000);
    } catch {
      console.error('Failed to copy link');
    }
  };

  return (
    <div className="relative inline-block">
      {/* Share Button */}
      <motion.button
        onClick={() => setIsOpen(!isOpen)}
        className="btn-acid gap-2"
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
      >
        <Share2 size={16} />
        Share
      </motion.button>

      {/* Share Menu Dropdown */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: -10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: -10 }}
            transition={{ duration: 0.15 }}
            className="absolute top-full right-0 mt-2 bg-surface border border-border rounded-xl shadow-xl z-50 overflow-hidden"
          >
            <div className="p-2">
              {/* Social Share Options */}
              {shareOptions.map((option, idx) => {
                const Icon = option.icon;
                return (
                  <motion.button
                    key={option.name}
                    onClick={() => {
                      option.action();
                      setIsOpen(false);
                    }}
                    className={`w-full px-4 py-2 rounded-lg flex items-center gap-2 text-sm hover:bg-surface-2 transition-colors ${option.color}`}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.05 }}
                  >
                    <Icon size={16} />
                    {option.name}
                  </motion.button>
                );
              })}

              {/* Divider */}
              <div className="h-px bg-border my-2" />

              {/* Copy Link Option */}
              <motion.button
                onClick={handleCopyLink}
                className="w-full px-4 py-2 rounded-lg flex items-center gap-2 text-sm hover:bg-surface-2 transition-colors text-secondary"
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: shareOptions.length * 0.05 }}
              >
                {copied ? (
                  <>
                    <Check size={16} className="text-green-400" />
                    <span>Copied!</span>
                  </>
                ) : (
                  <>
                    <Copy size={16} />
                    <span>Copy Link</span>
                  </>
                )}
              </motion.button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Backdrop to close menu */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setIsOpen(false)}
            className="fixed inset-0 z-40"
          />
        )}
      </AnimatePresence>
    </div>
  );
}
