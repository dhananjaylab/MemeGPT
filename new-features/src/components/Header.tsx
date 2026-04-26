
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Wand2, Image, LayoutDashboard, Menu, X, LogOut, User as UserIcon } from 'lucide-react';
import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { useAuth } from '../context/AuthContext';

export function Header() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const { user, isAuthenticated, logout, loginWithGoogle } = useAuth();

  const navItems = [
    { name: 'Synthesize', path: '/', icon: Wand2 },
    { name: 'Gallery', path: '/gallery', icon: Image },
  ];

  const filteredItems = navItems;

  return (
    <header className="sticky top-0 z-50 bg-background/80 backdrop-blur-md border-b border-border">
      <div className="container mx-auto px-4 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2 group">
          <div className="w-8 h-8 bg-acid rounded-lg flex items-center justify-center group-hover:rotate-12 transition-transform duration-300">
            <Wand2 size={18} className="text-black" />
          </div>
          <span className="font-display text-xl font-bold tracking-tight text-white">MemeGPT</span>
        </Link>

        {/* Desktop Nav */}
        <nav className="hidden md:flex items-center gap-8">
          {filteredItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`text-xs font-mono uppercase tracking-widest transition-colors duration-200 ${
                location.pathname === item.path ? 'text-acid font-bold' : 'text-muted hover:text-white'
              }`}
            >
              {item.name}
            </Link>
          ))}
        </nav>

        <div className="hidden md:flex items-center gap-4">
           <div className="text-[10px] font-mono text-muted uppercase tracking-widest flex items-center gap-2">
             <div className="w-2 h-2 bg-acid rounded-full animate-pulse" />
             Anon Agent Active
           </div>
        </div>

        {/* Mobile Menu Button */}
        <button
          className="md:hidden p-2 text-muted hover:text-white"
          onClick={() => setIsMenuOpen(!isMenuOpen)}
        >
          {isMenuOpen ? <X size={24} /> : <Menu size={24} />}
        </button>
      </div>

      {/* Mobile Nav */}
      <AnimatePresence>
        {isMenuOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="md:hidden bg-surface border-b border-border overflow-hidden"
          >
            <div className="container mx-auto px-4 py-4 flex flex-col gap-4">
              {filteredItems.map((item) => (
                <Link
                  key={item.path}
                  to={item.path}
                  onClick={() => setIsMenuOpen(false)}
                  className={`flex items-center gap-3 p-3 rounded-xl transition-colors ${
                    location.pathname === item.path ? 'bg-acid/10 text-acid' : 'hover:bg-white/5'
                  }`}
                >
                  <item.icon size={18} />
                  <span className="font-medium">{item.name}</span>
                </Link>
              ))}
              <div className="pt-4 border-t border-border">
                <div className="flex flex-col gap-2 p-3 text-[10px] font-mono text-muted uppercase tracking-widest text-center">
                   Anonymous Mode Active
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}
