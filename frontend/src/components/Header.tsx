import { useState, useRef, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Home, Wand2, LayoutDashboard, Image, LogIn, LogOut, ChevronDown } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from '../context/AuthContext';

const NAV_ITEMS = [
  { label: 'Home',      path: '/',          icon: Home },
  { label: 'Synthesize',path: '/synthesize', icon: Wand2 },
  { label: 'Gallery',   path: '/gallery',    icon: Image },
  { label: 'Dashboard', path: '/dashboard',  icon: LayoutDashboard, protected: true },
];

/** Animated hamburger → X icon */
function HamburgerIcon({ open }: { open: boolean }) {
  return (
    <div className="w-5 h-4 flex flex-col justify-between" aria-hidden>
      <motion.span
        className="block h-0.5 bg-current rounded-full origin-center"
        animate={open ? { rotate: 45, y: 7.5 } : { rotate: 0, y: 0 }}
        transition={{ duration: 0.25 }}
      />
      <motion.span
        className="block h-0.5 bg-current rounded-full"
        animate={open ? { opacity: 0, scaleX: 0 } : { opacity: 1, scaleX: 1 }}
        transition={{ duration: 0.2 }}
      />
      <motion.span
        className="block h-0.5 bg-current rounded-full origin-center"
        animate={open ? { rotate: -45, y: -7.5 } : { rotate: 0, y: 0 }}
        transition={{ duration: 0.25 }}
      />
    </div>
  );
}

export function Header() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const location = useLocation();
  const { user, isAuthenticated, logout } = useAuth();
  const profileRef = useRef<HTMLDivElement>(null);

  // Close profile dropdown on outside click
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (profileRef.current && !profileRef.current.contains(e.target as Node)) {
        setProfileOpen(false);
      }
    }
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // Close mobile menu on route change
  useEffect(() => { setMenuOpen(false); }, [location.pathname]);

  const filteredItems = NAV_ITEMS.filter((item) => !item.protected || isAuthenticated);

  return (
    <header className="sticky top-0 z-50 border-b border-border/50">
      <div
        className="backdrop-blur-xl bg-background/70"
        style={{ backgroundImage: 'linear-gradient(180deg, rgba(176,255,0,0.02) 0%, transparent 100%)' }}
      >
        <div className="page-container h-16 flex items-center justify-between gap-4">

          {/* ── Logo ───────────────────────────────────────────────── */}
          <Link to="/" className="flex items-center gap-2 group shrink-0">
            <motion.div
              whileHover={{ rotate: 12, scale: 1.1 }}
              transition={{ type: 'spring', stiffness: 400 }}
              className="w-8 h-8 bg-acid rounded-lg flex items-center justify-center shadow-glow-sm"
            >
              <Wand2 size={16} className="text-black" />
            </motion.div>
            <span className="font-display text-xl font-bold tracking-tight group-hover:text-acid transition-colors duration-300">
              MemeGPT
            </span>
          </Link>

          {/* ── Desktop Nav ─────────────────────────────────────────── */}
          <nav className="hidden md:flex items-center gap-6">
            {filteredItems.map((item) => {
              const active = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center gap-1.5 text-sm font-medium transition-colors duration-200 relative py-1 ${
                    active ? 'text-acid' : 'text-secondary hover:text-primary'
                  }`}
                >
                  <item.icon size={15} />
                  {item.label}
                  {active && (
                    <motion.div
                      layoutId="nav-indicator"
                      className="absolute -bottom-px left-0 right-0 h-0.5 bg-acid rounded-full"
                      transition={{ type: 'spring', stiffness: 500, damping: 35 }}
                    />
                  )}
                </Link>
              );
            })}
          </nav>

          {/* ── Auth / Profile (desktop) ────────────────────────────── */}
          <div className="hidden md:flex items-center gap-3 border-l border-border/50 pl-5 ml-2 shrink-0">
            {isAuthenticated ? (
              <div className="relative" ref={profileRef}>
                <button
                  id="profile-menu-btn"
                  onClick={() => setProfileOpen((p) => !p)}
                  className="flex items-center gap-2 px-3 py-1.5 rounded-full glass-button border-border/50 hover:border-acid/30 transition-all"
                >
                  {user?.avatar_url ? (
                    <img src={user.avatar_url} alt={user.name} className="w-6 h-6 rounded-full object-cover" />
                  ) : (
                    <div className="w-6 h-6 rounded-full bg-gradient-to-br from-acid/50 to-acid/30" />
                  )}
                  <span className="text-xs font-medium max-w-[80px] truncate">
                    {user?.name || user?.email.split('@')[0]}
                  </span>
                  <motion.div animate={{ rotate: profileOpen ? 180 : 0 }} transition={{ duration: 0.2 }}>
                    <ChevronDown size={13} className="text-muted" />
                  </motion.div>
                </button>

                <AnimatePresence>
                  {profileOpen && (
                    <motion.div
                      initial={{ opacity: 0, y: 6, scale: 0.95 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      exit={{ opacity: 0, y: 4, scale: 0.95 }}
                      transition={{ duration: 0.18 }}
                      className="absolute right-0 mt-2 w-44 rounded-xl border border-border bg-surface shadow-glass-lg p-1.5 z-50"
                    >
                      <Link
                        to="/dashboard"
                        className="flex items-center gap-2 px-3 py-2 text-sm rounded-lg hover:bg-surface-2 transition-colors"
                        onClick={() => setProfileOpen(false)}
                      >
                        <LayoutDashboard size={14} className="text-acid" />
                        Dashboard
                      </Link>
                      <button
                        onClick={logout}
                        className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded-lg hover:bg-red-500/10 text-red-400 transition-colors"
                      >
                        <LogOut size={14} />
                        Sign Out
                      </button>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            ) : (
              <button
                id="header-signin-btn"
                onClick={() => window.location.href = `${import.meta.env.VITE_API_URL}/auth/login/google`}
                className="btn-acid text-xs py-2"
              >
                <LogIn size={13} />
                Sign In
              </button>
            )}
          </div>

          {/* ── Hamburger (mobile) ──────────────────────────────────── */}
          <button
            id="mobile-menu-btn"
            className="md:hidden p-2 text-secondary hover:text-primary hover:bg-surface/50 rounded-lg transition-all"
            onClick={() => setMenuOpen((o) => !o)}
            aria-label={menuOpen ? 'Close menu' : 'Open menu'}
            aria-expanded={menuOpen}
          >
            <HamburgerIcon open={menuOpen} />
          </button>
        </div>

        {/* ── Mobile Menu ─────────────────────────────────────────────── */}
        <AnimatePresence>
          {menuOpen && (
            <motion.div
              key="mobile-menu"
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
              className="md:hidden overflow-hidden border-t border-border/30 bg-surface/60 backdrop-blur-xl"
            >
              <div className="page-container py-4 space-y-1">
                <nav className="flex flex-col gap-1">
                  {filteredItems.map((item, idx) => (
                    <motion.div
                      key={item.path}
                      initial={{ opacity: 0, x: -12 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: idx * 0.06, duration: 0.25 }}
                    >
                      <Link
                        to={item.path}
                        className={`flex items-center gap-3 px-3 py-3 rounded-xl text-sm font-medium transition-all ${
                          location.pathname === item.path
                            ? 'bg-acid/15 text-acid border border-acid/25'
                            : 'text-secondary hover:bg-surface-2 hover:text-primary'
                        }`}
                      >
                        <item.icon size={17} />
                        {item.label}
                      </Link>
                    </motion.div>
                  ))}
                </nav>

                <div className="pt-3 border-t border-border/40 mt-3">
                  {isAuthenticated ? (
                    <div className="flex items-center justify-between p-2.5 rounded-xl glass border-border/40">
                      <div className="flex items-center gap-3 min-w-0">
                        {user?.avatar_url && (
                          <img src={user.avatar_url} alt="" className="w-8 h-8 rounded-full object-cover shrink-0" />
                        )}
                        <div className="flex flex-col min-w-0">
                          <span className="text-sm font-medium truncate">{user?.name}</span>
                          <span className="text-xs text-muted truncate">{user?.email}</span>
                        </div>
                      </div>
                      <button
                        onClick={logout}
                        className="p-2 text-red-400 hover:bg-red-500/10 rounded-lg transition-all ml-2 shrink-0"
                        aria-label="Sign out"
                      >
                        <LogOut size={18} />
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => window.location.href = `${import.meta.env.VITE_API_URL}/auth/login/google`}
                      className="btn-acid w-full justify-center"
                    >
                      <LogIn size={16} />
                      Sign In with Google
                    </button>
                  )}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </header>
  );
}
