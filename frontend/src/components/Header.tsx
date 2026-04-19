import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Menu, X, Wand2, LayoutDashboard, Image, LogIn, LogOut, ChevronDown } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export function Header() {
  const [isOpen, setIsOpen] = useState(false);
  const location = useLocation();
  const { user, isAuthenticated, logout } = useAuth();

  const navItems = [
    { label: 'Generate', path: '/', icon: Wand2 },
    { label: 'Gallery', path: '/gallery', icon: Image },
    { label: 'Dashboard', path: '/dashboard', icon: LayoutDashboard, protected: true },
  ];

  const filteredItems = navItems.filter(item => !item.protected || isAuthenticated);

  return (
    <header className="sticky top-0 z-50 bg-background/80 backdrop-blur-md border-b border-border">
      <div className="container mx-auto px-4 h-16 flex items-center justify-between">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2 group">
          <div className="w-8 h-8 bg-acid rounded-lg flex items-center justify-center group-hover:rotate-12 transition-transform">
            <Wand2 size={18} className="text-black" />
          </div>
          <span className="font-display text-xl font-bold tracking-tight">MemeGPT</span>
        </Link>

        {/* Desktop Nav */}
        <nav className="hidden md:flex items-center gap-6">
          {filteredItems.map(item => (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-2 text-sm font-medium transition-colors ${
                location.pathname === item.path ? 'text-acid' : 'text-secondary hover:text-primary'
              }`}
            >
              <item.icon size={16} />
              {item.label}
            </Link>
          ))}
        </nav>

        {/* Auth / Profile */}
        <div className="hidden md:flex items-center gap-4 border-l border-border pl-6 ml-6">
          {isAuthenticated ? (
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 px-2 py-1 rounded-full bg-surface-2 border border-border">
                {user?.avatar_url ? (
                  <img src={user.avatar_url} alt={user.name} className="w-6 h-6 rounded-full" />
                ) : (
                  <div className="w-6 h-6 rounded-full bg-surface-3" />
                )}
                <span className="text-xs font-medium pr-1">{user?.name || user?.email.split('@')[0]}</span>
              </div>
              <button 
                onClick={logout}
                className="p-2 text-muted hover:text-red-400 transition-colors"
                title="Sign Out"
              >
                <LogOut size={18} />
              </button>
            </div>
          ) : (
            <button 
              onClick={() => window.location.href = `${import.meta.env.VITE_API_URL}/auth/login/google`}
              className="btn-acid text-xs py-1.5"
            >
              <LogIn size={14} />
              Sign In
            </button>
          )}
        </div>

        {/* Mobile Menu Button */}
        <button 
          className="md:hidden p-2 text-secondary hover:text-primary"
          onClick={() => setIsOpen(!isOpen)}
        >
          {isOpen ? <X size={24} /> : <Menu size={24} />}
        </button>
      </div>

      {/* Mobile Menu */}
      {isOpen && (
        <div className="md:hidden bg-surface border-b border-border p-4 space-y-4">
          <nav className="flex flex-col gap-2">
            {filteredItems.map(item => (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setIsOpen(false)}
                className={`flex items-center gap-3 p-3 rounded-lg text-sm font-medium transition-colors ${
                  location.pathname === item.path ? 'bg-acid/10 text-acid' : 'hover:bg-surface-2'
                }`}
              >
                <item.icon size={18} />
                {item.label}
              </Link>
            ))}
          </nav>
          
          <div className="pt-4 border-t border-border">
            {isAuthenticated ? (
              <div className="flex items-center justify-between p-2">
                <div className="flex items-center gap-3">
                  {user?.avatar_url && (
                    <img src={user.avatar_url} alt="" className="w-8 h-8 rounded-full" />
                  )}
                  <div className="flex flex-col">
                    <span className="text-sm font-medium">{user?.name}</span>
                    <span className="text-xs text-muted">{user?.email}</span>
                  </div>
                </div>
                <button onClick={logout} className="p-2 text-red-400">
                  <LogOut size={20} />
                </button>
              </div>
            ) : (
              <button 
                onClick={() => window.location.href = `${import.meta.env.VITE_API_URL}/auth/login/google`}
                className="btn-acid w-full justify-center"
              >
                <LogIn size={18} />
                Sign In with Google
              </button>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
