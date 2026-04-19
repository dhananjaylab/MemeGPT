import React from 'react';
import { Link } from 'react-router-dom';
import { Wand2, Github, Twitter, Mail } from 'lucide-react';

export function Footer() {
  return (
    <footer className="bg-background border-t border-border py-12">
      <div className="container mx-auto px-4 max-w-7xl">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-10">
          {/* Brand */}
          <div className="md:col-span-2 space-y-4">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 bg-acid rounded flex items-center justify-center">
                <Wand2 size={14} className="text-black" />
              </div>
              <span className="font-display font-bold text-lg tracking-tight">MemeGPT</span>
            </div>
            <p className="text-secondary text-sm max-w-xs leading-relaxed">
              Synthesizing the internet's humor through advanced AI. Create hilarious, 
              trend-aware memes in seconds.
            </p>
            <div className="flex items-center gap-4 text-muted">
              <a href="#" className="hover:text-primary transition-colors"><Github size={18} /></a>
              <a href="#" className="hover:text-primary transition-colors"><Twitter size={18} /></a>
              <a href="#" className="hover:text-primary transition-colors"><Mail size={18} /></a>
            </div>
          </div>

          {/* Links */}
          <div>
            <h4 className="font-mono text-[10px] uppercase tracking-widest text-secondary mb-4">Platform</h4>
            <ul className="space-y-2 text-sm text-muted">
              <li><Link to="/" className="hover:text-acid transition-colors">Generator</Link></li>
              <li><Link to="/gallery" className="hover:text-acid transition-colors">Gallery</Link></li>
              <li><Link to="/gallery" className="hover:text-acid transition-colors">Trending</Link></li>
              <li><Link to="/dashboard" className="hover:text-acid transition-colors">Dashboard</Link></li>
            </ul>
          </div>

          {/* Legal */}
          <div>
            <h4 className="font-mono text-[10px] uppercase tracking-widest text-secondary mb-4">Integrations</h4>
            <ul className="space-y-2 text-sm text-muted">
              <li><a href="#" className="hover:text-acid transition-colors">Stripe</a></li>
              <li><a href="#" className="hover:text-acid transition-colors">Reddit</a></li>
              <li><a href="#" className="hover:text-acid transition-colors">Discord Bot</a></li>
              <li><a href="#" className="hover:text-acid transition-colors">Slack App</a></li>
            </ul>
          </div>
        </div>
        
        <div className="mt-12 pt-8 border-t border-border flex flex-col md:flex-row justify-between items-center gap-4">
          <p className="text-[10px] font-mono text-muted uppercase tracking-wider">
            © 2024 MemeGPT Research Lab. All humor intended.
          </p>
          <div className="flex gap-6 text-[10px] font-mono text-muted uppercase tracking-wider">
            <a href="#" className="hover:text-secondary">Privacy Policy</a>
            <a href="#" className="hover:text-secondary">Terms of Service</a>
          </div>
        </div>
      </div>
    </footer>
  );
}
