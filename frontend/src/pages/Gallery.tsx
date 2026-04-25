import { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { MemeCard } from '../components/MemeCard';
import { PageTransition } from '../components/PageTransition';
import type { GeneratedMeme } from '../lib/types';
import { Loader2, Flame, Clock, Search, Zap, User, Globe } from 'lucide-react';
import { apiClient } from '../lib/api';
import { useAuth } from '../context/AuthContext';

type SortMode = 'recent' | 'top' | 'trending';
type ViewMode = 'all' | 'my';

const PAGE_SIZE = 20;

async function fetchMemes(
  page: number,
  sort: SortMode,
  userOnly = false,
): Promise<{ memes: GeneratedMeme[]; total: number; hasMore: boolean }> {
  try {
    if (userOnly) {
      const response = await fetch(`/api/memes/my?page=${page}&limit=${PAGE_SIZE}`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('auth_token') || ''}` },
      });
      if (!response.ok) throw new Error('Failed to fetch user memes');
      const myMemes = (await response.json()) as GeneratedMeme[];
      return {
        memes: myMemes,
        total: page * PAGE_SIZE + myMemes.length,
        hasMore: myMemes.length === PAGE_SIZE,
      };
    }
    const data = await apiClient.getMemes({ page, limit: PAGE_SIZE, sort });
    return {
      memes: data.memes || [],
      total: data.total || 0,
      hasMore: Boolean(data.has_more),
    };
  } catch (err) {
    console.error('Failed to load memes:', err);
    throw err;
  }
}

export function Gallery() {
  const [sort, setSort] = useState<SortMode>('recent');
  const [viewMode, setViewMode] = useState<ViewMode>('all');
  const [search, setSearch] = useState('');
  const [memes, setMemes] = useState<GeneratedMeme[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [initialLoad, setInitialLoad] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(true);
  const loaderRef = useRef<HTMLDivElement>(null);
  const { isAuthenticated } = useAuth();

  const loadPage = useCallback(
    async (pageNum: number, reset: boolean) => {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchMemes(pageNum, sort, viewMode === 'my');
        setMemes((prev) => (reset ? data.memes : [...prev, ...data.memes]));
        setTotal(data.total);
        setHasMore(data.hasMore);
        setPage(pageNum);
      } catch {
        setError("Couldn't load memes. Please try again.");
      } finally {
        setLoading(false);
        setInitialLoad(false);
      }
    },
    [sort, viewMode],
  );

  useEffect(() => {
    setInitialLoad(true);
    setMemes([]);
    loadPage(1, true);
  }, [sort, viewMode, loadPage]);

  useEffect(() => {
    if (!loaderRef.current || !hasMore || loading) return;
    const obs = new IntersectionObserver(
      (entries) => { if (entries[0].isIntersecting) loadPage(page + 1, false); },
      { threshold: 0.1 },
    );
    obs.observe(loaderRef.current);
    return () => obs.disconnect();
  }, [hasMore, loading, page, loadPage]);

  const filtered = search.trim()
    ? memes.filter(
        (m) =>
          m.template_name.toLowerCase().includes(search.toLowerCase()) ||
          m.prompt.toLowerCase().includes(search.toLowerCase()) ||
          m.meme_text?.some((t) => t.toLowerCase().includes(search.toLowerCase())),
      )
    : memes;

  const sortTabs: { id: SortMode; label: string; Icon: React.ElementType }[] = [
    { id: 'recent',   label: 'Recent',   Icon: Clock },
    { id: 'top',      label: 'Top',      Icon: Flame },
    { id: 'trending', label: 'Trending', Icon: Zap },
  ];

  return (
    <PageTransition>
      <div className="space-y-6">

        {/* Header */}
        <div className="space-y-1">
          <h1 className="text-3xl md:text-4xl font-bold">Meme Gallery</h1>
          <p className="text-secondary text-sm md:text-base">
            Browse thousands of AI-generated memes from the community
          </p>
        </div>

        {/* Controls — stack on mobile, row on sm+ */}
        <div className="flex flex-col sm:flex-row flex-wrap gap-3">
          {/* View mode */}
          <div className="flex items-center gap-1 bg-surface border border-border rounded-lg p-1">
            {([
              { id: 'all', label: 'All', Icon: Globe },
              { id: 'my',  label: 'Mine', Icon: User },
            ] as const).map(({ id, label, Icon }) => (
              <button
                key={id}
                onClick={() => setViewMode(id)}
                disabled={id === 'my' && !isAuthenticated}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-mono transition-all ${
                  viewMode === id
                    ? 'bg-acid text-black font-semibold shadow-glow-sm'
                    : 'text-secondary hover:text-acid'
                } disabled:opacity-40`}
              >
                <Icon size={12} />
                {label}
              </button>
            ))}
          </div>

          {/* Sort tabs */}
          <div className="flex items-center gap-1 bg-surface border border-border rounded-lg p-1">
            {sortTabs.map(({ id, label, Icon }) => (
              <button
                key={id}
                onClick={() => setSort(id)}
                aria-pressed={sort === id}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-mono transition-all ${
                  sort === id
                    ? 'bg-acid text-black font-semibold shadow-glow-sm'
                    : 'text-secondary hover:text-acid hover:bg-acid/10'
                }`}
              >
                <Icon size={12} />
                {label}
              </button>
            ))}
          </div>

          {/* Search — full width on mobile */}
          <div className="relative flex-1 min-w-[180px]">
            <Search
              size={13}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-muted pointer-events-none"
            />
            <input
              type="text"
              placeholder="Search templates or topics…"
              aria-label="Search memes"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input-dark pl-8 py-2 text-xs h-9 w-full"
            />
          </div>

          {total > 0 && (
            <p className="font-mono text-xs text-muted self-center hidden sm:block whitespace-nowrap">
              {total.toLocaleString()} total
            </p>
          )}
        </div>

        {/* Status bar */}
        <div className="glass-card !p-3 !rounded-xl flex items-center justify-between gap-4">
          <p className="text-xs text-secondary font-mono">
            Viewing <span className="text-acid">{sort.toUpperCase()}</span>
            {total > 0 && ` · ${filtered.length.toLocaleString()} of ${total.toLocaleString()} memes`}
          </p>
          <p className="text-[10px] text-muted hidden sm:block">
            💡 Search to filter by template name or topic
          </p>
        </div>

        {/* Grid */}
        {initialLoad ? (
          <div className="grid-gallery">
            {Array.from({ length: PAGE_SIZE }).map((_, i) => (
              <div
                key={i}
                className="aspect-square rounded-xl bg-surface animate-pulse"
                style={{ animationDelay: `${i * 30}ms` }}
              />
            ))}
          </div>
        ) : error ? (
          <div className="flex flex-col items-center py-20 gap-4 text-center">
            <div className="w-16 h-16 rounded-full bg-surface-2 border border-border flex items-center justify-center">
              <Loader2 size={24} className="text-muted" />
            </div>
            <p className="font-mono text-sm text-red-400">{error}</p>
            <button onClick={() => loadPage(1, true)} className="btn-ghost text-xs">
              Try Again
            </button>
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center py-24 text-center">
            <div className="w-20 h-20 rounded-full bg-surface-2 border border-border flex items-center justify-center mb-6">
              <Search size={32} className="text-muted" />
            </div>
            <p className="font-display text-2xl font-bold mb-2">No memes found</p>
            <p className="font-mono text-sm text-muted max-w-xs">
              {search
                ? 'Try a different search term or browse by trending'
                : 'Start by generating your first meme!'}
            </p>
          </div>
        ) : (
          <>
            <AnimatePresence>
              <div className="grid-gallery">
                {filtered.map((meme, i) => (
                  <motion.div
                    key={meme.id}
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: Math.min(i * 0.03, 0.5), duration: 0.35 }}
                  >
                    <MemeCard meme={meme} priority={i < 10} />
                  </motion.div>
                ))}
              </div>
            </AnimatePresence>

            {/* Infinite scroll sentinel */}
            <div ref={loaderRef} className="flex justify-center py-10">
              {loading && !initialLoad && (
                <Loader2 size={20} className="text-muted animate-spin" />
              )}
              {!hasMore && filtered.length > 0 && (
                <p className="font-mono text-xs text-muted">You've seen them all ✓</p>
              )}
            </div>
          </>
        )}
      </div>
    </PageTransition>
  );
}
