import Link from 'next/link';
import { Github, Twitter, Heart } from 'lucide-react';

export function Footer() {
  return (
    <footer className="border-t border-border bg-background">
      <div className="container mx-auto px-4 py-12 max-w-7xl">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Brand */}
          <div className="md:col-span-1">
            <div className="flex items-center gap-2 font-display font-semibold text-lg mb-4">
              <div className="w-6 h-6 bg-acid rounded-md flex items-center justify-center">
                <span className="text-black text-sm">🧙</span>
              </div>
              <span className="text-primary">MemeGPT</span>
            </div>
            <p className="text-secondary text-sm leading-relaxed">
              AI-powered meme generation platform. Turn any topic into viral content with GPT-4o.
            </p>
          </div>

          {/* Product */}
          <div>
            <h3 className="font-medium text-primary mb-4">Product</h3>
            <ul className="space-y-2">
              <li>
                <Link href="/gallery" className="text-secondary hover:text-primary transition-colors text-sm">
                  Gallery
                </Link>
              </li>
              <li>
                <Link href="/api-docs" className="text-secondary hover:text-primary transition-colors text-sm">
                  API Documentation
                </Link>
              </li>
              <li>
                <Link href="/templates" className="text-secondary hover:text-primary transition-colors text-sm">
                  Templates
                </Link>
              </li>
              <li>
                <Link href="/pricing" className="text-secondary hover:text-primary transition-colors text-sm">
                  Pricing
                </Link>
              </li>
            </ul>
          </div>

          {/* Company */}
          <div>
            <h3 className="font-medium text-primary mb-4">Company</h3>
            <ul className="space-y-2">
              <li>
                <Link href="/about" className="text-secondary hover:text-primary transition-colors text-sm">
                  About
                </Link>
              </li>
              <li>
                <Link href="/blog" className="text-secondary hover:text-primary transition-colors text-sm">
                  Blog
                </Link>
              </li>
              <li>
                <Link href="/contact" className="text-secondary hover:text-primary transition-colors text-sm">
                  Contact
                </Link>
              </li>
              <li>
                <Link href="/careers" className="text-secondary hover:text-primary transition-colors text-sm">
                  Careers
                </Link>
              </li>
            </ul>
          </div>

          {/* Legal */}
          <div>
            <h3 className="font-medium text-primary mb-4">Legal</h3>
            <ul className="space-y-2">
              <li>
                <Link href="/privacy" className="text-secondary hover:text-primary transition-colors text-sm">
                  Privacy Policy
                </Link>
              </li>
              <li>
                <Link href="/terms" className="text-secondary hover:text-primary transition-colors text-sm">
                  Terms of Service
                </Link>
              </li>
              <li>
                <Link href="/cookies" className="text-secondary hover:text-primary transition-colors text-sm">
                  Cookie Policy
                </Link>
              </li>
              <li>
                <Link href="/dmca" className="text-secondary hover:text-primary transition-colors text-sm">
                  DMCA
                </Link>
              </li>
            </ul>
          </div>
        </div>

        <div className="border-t border-border mt-8 pt-8 flex flex-col md:flex-row justify-between items-center gap-4">
          <div className="flex items-center gap-4">
            <p className="text-secondary text-sm">
              © 2024 MemeGPT. All rights reserved.
            </p>
            <div className="flex items-center gap-1 text-secondary text-sm">
              Made with <Heart size={14} className="text-red-400 mx-1" /> by the MemeGPT team
            </div>
          </div>

          <div className="flex items-center gap-4">
            <Link
              href="https://github.com/Dhananjay-97/MemeGPT"
              target="_blank"
              rel="noopener noreferrer"
              className="text-secondary hover:text-primary transition-colors"
              title="GitHub"
            >
              <Github size={18} />
            </Link>
            <Link
              href="https://twitter.com/memegpt"
              target="_blank"
              rel="noopener noreferrer"
              className="text-secondary hover:text-primary transition-colors"
              title="Twitter"
            >
              <Twitter size={18} />
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}