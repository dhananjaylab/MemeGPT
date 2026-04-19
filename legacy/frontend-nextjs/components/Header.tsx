'use client';

import Link from 'next/link';
import { useState } from 'react';
import { Menu, X, Zap, Github, Twitter, LogOut, User as UserIcon } from 'lucide-react';
import { useSession, signIn, signOut } from 'next-auth/react';

export function Header() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { data: session, status } = useSession();
  const isLoading = status === 'loading';

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
            {session ? (
              <div className="flex items-center gap-3">
                <Link href="/dashboard" className="flex items-center gap-2 px-3 py-1.5 rounded-full border border-border hover:bg-surface-2 transition-colors">
                  {session.user?.image ? (
                    <img src={session.user.image} alt="" className="w-5 h-5 rounded-full" />
                  ) : (
                    <UserIcon size={14} className="text-secondary" />
                  )}
                  <span className="text-xs font-medium text-primary max-w-[100px] truncate">
                    {session.user?.name || 'User'}
                  </span>
                </Link>
                <button
                  onClick={() => signOut()}
                  className="p-2 text-secondary hover:text-acid transition-colors"
                  title="Sign Out"
                >
                  <LogOut size={18} />
                </button>
              </div>
            ) : (
              <button 
                onClick={() => signIn()}
                className="btn-acid text-sm"
                disabled={isLoading}
              >
                {isLoading ? 'Connecting...' : 'Sign In'}
              </button>
            )}
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
                {session ? (
                  <div className="flex flex-col gap-4">
                    <Link 
                      href="/dashboard" 
                      className="text-secondary hover:text-primary transition-colors text-sm font-medium"
                      onClick={() => setMobileMenuOpen(false)}
                    >
                      Dashboard
                    </Link>
                    <button 
                      onClick={() => signOut()}
                      className="text-left text-secondary hover:text-acid transition-colors text-sm font-medium"
                    >
                      Sign Out
                    </button>
                  </div>
                ) : (
                  <button 
                    onClick={() => signIn()}
                    className="btn-acid text-sm w-full"
                    disabled={isLoading}
                  >
                    {isLoading ? 'Connecting...' : 'Sign In'}
                  </button>
                )}
              </div>
            </nav>
          </div>
        )}
      </div>
    </header>
  );
}