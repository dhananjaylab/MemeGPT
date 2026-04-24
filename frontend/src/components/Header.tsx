import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Menu, X, Home, Wand2, LayoutDashboard, Image, LogIn, LogOut, ChevronDown } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export function Header() {
  const [isOpen, setIsOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const location = useLocation();
  const { user, isAuthenticated, logout } = useAuth();

  const navItems = [
    { label: 'Home', path: '/', icon: Home },
    { label: 'Synthesize', path: '/synthesize', icon: Wand2 },
    { label: 'Gallery', path: '/gallery', icon: Image },
    { label: 'Dashboard', path: '/dashboard', icon: LayoutDashboard, protected: true },
  ];

  const filteredItems = navItems.filter(item => !item.protected || isAuthenticated);

  return (
    <header className="sticky top-0 z-50 border-b border-border/50">
      <div className="backdrop-blur-xl bg-background/60" style={{backgroundImage: 'linear-gradient(180deg, rgba(176, 255, 0, 0.02) 0%, transparent 100%)'}}>
        <div className="container mx-auto px-4 h-16 flex items-center justify-between">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 group">
            <div className="w-8 h-8 bg-acid rounded-lg flex items-center justify-center group-hover:rotate-12 group-hover:shadow-acid transition-all duration-300">
              <Wand2 size={18} className="text-black" />
            </div>
            <span className="font-display text-xl font-bold tracking-tight group-hover:text-acid transition-colors duration-300">MemeGPT</span>
          </Link>

          {/* Desktop Nav */}
          <nav className="hidden md:flex items-center gap-6">
            {filteredItems.map(item => (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-2 text-sm font-medium transition-all duration-300 relative group ${
                  location.pathname === item.path ? 'text-acid' : 'text-secondary hover:text-primary'
                }`}
              >
                <item.icon size={16} />
                {item.label}
                {location.pathname === item.path && (
                  <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-acid via-acid to-transparent rounded-full"></div>
                )}
              </Link>
            ))}
          </nav>

          {/* Auth / Profile */}
          <div className="hidden md:flex items-center gap-4 border-l border-border/50 pl-6 ml-6">
            {isAuthenticated ? (
              <div className="relative">
                <button
                  onClick={() => setProfileOpen((prev) => !prev)}
                  className="flex items-center gap-2 px-3 py-1.5 rounded-full glass-button border-border/50 hover:border-border transition-all duration-300"
                >
                  {user?.avatar_url ? (
                    <img src={user.avatar_url} alt={user.name} className="w-6 h-6 rounded-full object-cover" />
                  ) : (
                    <div className="w-6 h-6 rounded-full bg-gradient-to-br from-acid/50 to-acid/30" />
                  )}
                  <span className="text-xs font-medium pr-1">{user?.name || user?.email.split('@')[0]}</span>
                  <ChevronDown size={14} className="text-muted" />
                </button>
                {profileOpen && (
                  <div className="absolute right-0 mt-2 w-44 rounded-lg border border-border bg-surface p-2 z-50">
                    <Link to="/dashboard" className="block px-3 py-2 text-sm rounded hover:bg-surface-2" onClick={() => setProfileOpen(false)}>
                      Dashboard
                    </Link>
                    <button
                      onClick={logout}
                      className="w-full text-left px-3 py-2 text-sm rounded hover:bg-red-500/10 text-red-400"
                    >
                      Sign Out
                    </button>
                  </div>
                )}
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
            className="md:hidden p-2 text-secondary hover:text-primary hover:bg-surface/50 rounded-lg transition-all duration-300"
            onClick={() => setIsOpen(!isOpen)}
        >
          {isOpen ? <X size={24} /> : <Menu size={24} />}
        </button>
      </div>

      {/* Mobile Menu */}
      {isOpen && (
        <div className="md:hidden bg-surface/40 backdrop-blur-lg border-b border-border/50 p-4 space-y-4 animate-slide-up">
          <nav className="flex flex-col gap-2">
            {filteredItems.map((item, idx) => (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setIsOpen(false)}
                className={`flex items-center gap-3 p-3 rounded-lg text-sm font-medium transition-all duration-300 delay-${idx * 50} ${
                  location.pathname === item.path ? 'bg-acid/15 text-acid border border-acid/30' : 'hover:bg-surface/50 hover:border border-border/30'
                }`}
              >
                <item.icon size={18} />
                {item.label}
              </Link>
            ))}
          </nav>
          
          <div className="pt-4 border-t border-border/50">
            {isAuthenticated ? (
              <div className="flex items-center justify-between p-2 glass-button border-border/50">
                <div className="flex items-center gap-3">
                  {user?.avatar_url && (
                    <img src={user.avatar_url} alt="" className="w-8 h-8 rounded-full object-cover" />
                  )}
                  <div className="flex flex-col">
                    <span className="text-sm font-medium">{user?.name}</span>
                    <span className="text-xs text-muted">{user?.email}</span>
                  </div>
                </div>
                <button onClick={logout} className="p-2 text-red-400 hover:bg-red-500/10 rounded-lg transition-all duration-300">
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
      </div>
    </header>
  );
}
