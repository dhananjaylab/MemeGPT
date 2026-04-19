'use client';

import Link from 'next/link';
import { useState } from 'react';
import { Menu, X, Zap, Github, Twitter } from 'lucide-react';

export function Header() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container mx-auto px-4 max-w-7xl">
        <div className="flex h-16 items-center justify-between">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2 font-display font-semibold text-xl">
            <div className="w-8 h-8 bg-acid rounded-lg flex items-center justify-center">
              <Zap size={18} className="text-black" />
            </div>
            <span className="text-primary">MemeGPT</span>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-6">
            <Link 
              href="/gallery" 
              className="text-secondary hover:text-primary transition-colors text-sm font-medium"
            >
              Gallery
            </Link>
            <Link 
              href="/api-docs" 
              className="text-secondary hover:text-primary transition-colors text-sm font-medium"
            >
              API
            </Link>
            <Link 
              href="/about" 
              className="text-secondary hover:text-primary transition-colors text-sm font-medium"
            >
              About
            </Link>
          </nav>

          {/* Desktop Actions */}
          <div className="hidden md:flex items-center gap-3">
            <Link
              href="https://github.com/Dhananjay-97/MemeGPT"
              target="_blank"
              rel="noopener noreferrer"
              className="p-2 text-secondary hover:text-primary transition-colors"
              title="GitHub"
            >
              <Github size={18} />
            </Link>
            <Link
              href="https://twitter.com/memegpt"
              target="_blank"
              rel="noopener noreferrer"
              className="p-2 text-secondary hover:text-primary transition-colors"
              title="Twitter"
            >
              <Twitter size={18} />
            </Link>
            <Link href="/dashboard" className="btn-acid text-sm">
              Dashboard
            </Link>
          </div>

          {/* Mobile menu button */}
          <button
            className="md:hidden p-2 text-secondary hover:text-primary"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label="Toggle menu"
          >
            {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>

        {/* Mobile Navigation */}
        {mobileMenuOpen && (
          <div className="md:hidden border-t border-border py-4">
            <nav className="flex flex-col gap-4">
              <Link 
                href="/gallery" 
                className="text-secondary hover:text-primary transition-colors text-sm font-medium"
                onClick={() => setMobileMenuOpen(false)}
              >
                Gallery
              </Link>
              <Link 
                href="/api-docs" 
                className="text-secondary hover:text-primary transition-colors text-sm font-medium"
                onClick={() => setMobileMenuOpen(false)}
              >
                API
              </Link>
              <Link 
                href="/about" 
                className="text-secondary hover:text-primary transition-colors text-sm font-medium"
                onClick={() => setMobileMenuOpen(false)}
              >
                About
              </Link>
              <div className="flex items-center gap-3 pt-2">
                <Link
                  href="https://github.com/Dhananjay-97/MemeGPT"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-2 text-secondary hover:text-primary transition-colors"
                  title="GitHub"
                >
                  <Github size={18} />
                </Link>
                <Link
                  href="https://twitter.com/memegpt"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-2 text-secondary hover:text-primary transition-colors"
                  title="Twitter"
                >
                  <Twitter size={18} />
                </Link>
                <Link 
                  href="/dashboard" 
                  className="btn-acid text-sm"
                  onClick={() => setMobileMenuOpen(false)}
                >
                  Dashboard
                </Link>
              </div>
            </nav>
          </div>
        )}
      </div>
    </header>
  );
}