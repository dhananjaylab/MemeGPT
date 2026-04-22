
import { Link } from 'react-router-dom';
import { Wand2, Mail } from 'lucide-react';

export function Footer() {
  return (
    <footer className="border-t border-border/50 backdrop-blur-xl bg-background/60" style={{backgroundImage: 'linear-gradient(180deg, transparent 0%, rgba(176, 255, 0, 0.02) 100%)'}}>
      <div className="container mx-auto px-4 max-w-7xl">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-10 py-12">
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
              <a href="#" className="hover:text-primary transition-colors">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                </svg>
              </a>
              <a href="#" className="hover:text-primary transition-colors">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M23.953 4.57a10 10 0 01-2.825.775 4.958 4.958 0 002.163-2.723c-.951.555-2.005.959-3.127 1.184a4.92 4.92 0 00-8.384 4.482C7.69 8.095 4.067 6.13 1.64 3.162a4.822 4.822 0 00-.666 2.475c0 1.71.87 3.213 2.188 4.096a4.904 4.904 0 01-2.228-.616v.06a4.923 4.923 0 003.946 4.827 4.996 4.996 0 01-2.212.085 4.936 4.936 0 004.604 3.417 9.867 9.867 0 01-6.102 2.105c-.39 0-.779-.023-1.17-.067a13.995 13.995 0 007.557 2.209c9.053 0 13.998-7.496 13.998-13.985 0-.21 0-.42-.015-.63A9.935 9.935 0 0024 4.59z"/>
                </svg>
              </a>
              <Mail size={18} />
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
