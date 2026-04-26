
import { Wand2 } from 'lucide-react';
import { Link } from 'react-router-dom';

export function Footer() {
  return (
    <footer className="py-20 border-t border-border mt-20 bg-black/20">
      <div className="container mx-auto px-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-12">
          <div className="space-y-4">
            <Link to="/" className="flex items-center gap-2">
              <Wand2 size={24} className="text-acid" />
              <span className="font-display text-xl font-bold tracking-tight">MemeGPT</span>
            </Link>
            <p className="text-muted text-sm leading-relaxed">
              Synthesizing the internet's humor through advanced AI. 
              Built for developers, by developers.
            </p>
          </div>
          
          <div>
            <h4 className="font-mono text-xs uppercase tracking-widest text-white mb-6">Platform</h4>
            <ul className="space-y-4 text-sm text-muted">
              <li><Link to="/" className="hover:text-acid transition-colors">Generator</Link></li>
              <li><Link to="/gallery" className="hover:text-acid transition-colors">Gallery</Link></li>
              <li><Link to="/trending" className="hover:text-acid transition-colors">Trending</Link></li>
            </ul>
          </div>

          <div>
            <h4 className="font-mono text-xs uppercase tracking-widest text-white mb-6">Company</h4>
            <ul className="space-y-4 text-sm text-muted">
              <li><a href="#" className="hover:text-acid transition-colors">About</a></li>
              <li><a href="#" className="hover:text-acid transition-colors">Privacy</a></li>
              <li><a href="#" className="hover:text-acid transition-colors">Terms</a></li>
            </ul>
          </div>

          <div>
            <h4 className="font-mono text-xs uppercase tracking-widest text-white mb-6">Connect</h4>
            <ul className="space-y-4 text-sm text-muted">
              <li><a href="#" className="hover:text-acid transition-colors">Twitter</a></li>
              <li><a href="#" className="hover:text-acid transition-colors">Discord</a></li>
              <li><a href="#" className="hover:text-acid transition-colors">GitHub</a></li>
            </ul>
          </div>
        </div>
        
        <div className="mt-20 pt-8 border-t border-border flex flex-col md:flex-row justify-between items-center gap-4">
          <p className="text-muted text-xs font-mono uppercase tracking-widest">
            © 2024 MemeGPT Research Lab.
          </p>
          <div className="flex gap-6 text-xs font-mono text-muted uppercase tracking-widest">
            <span>Server Status: <span className="text-acid">Optimal</span></span>
            <span>Uptime: 99.9%</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
