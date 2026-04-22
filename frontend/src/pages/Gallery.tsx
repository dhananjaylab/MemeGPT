import { useState, useEffect, useRef, useCallback } from "react";
import { MemeCard } from "../components/MemeCard";
import type { GeneratedMeme } from "../lib/types";
import { Loader2, LayoutGrid, Flame, Clock, Search, Zap } from "lucide-react";
import { apiClient } from "../lib/api";

type SortMode = "recent" | "top" | "trending";

const PAGE_SIZE = 20;

async function fetchMemes(page: number, sort: SortMode): Promise<{ memes: GeneratedMeme[]; total: number }> {
  try {
    const data = await apiClient.getMemes({ page, limit: PAGE_SIZE, sort });
    
    return { 
      memes: data.memes || [], 
      total: data.total || 0
    };
  } catch (err) {
    console.error("Failed to load memes:", err);
    throw err;
  }
}

export function Gallery() {
  const [sort, setSort] = useState<SortMode>("recent");
  const [search, setSearch] = useState("");
  const [memes, setMemes] = useState<GeneratedMeme[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [initialLoad, setInitialLoad] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const loaderRef = useRef<HTMLDivElement>(null);

  const hasMore = memes.length < total || total === 0;

  const loadPage = useCallback(
    async (pageNum: number, reset: boolean) => {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchMemes(pageNum, sort);
        setMemes((prev) => (reset ? data.memes : [...prev, ...data.memes]));
        setTotal(data.total);
        setPage(pageNum);
      } catch (e) {
        setError("Couldn't load memes. Please try again.");
      } finally {
        setLoading(false);
        setInitialLoad(false);
      }
    },
    [sort]
  );

  // Reset on sort change
  useEffect(() => {
    setInitialLoad(true);
    setMemes([]);
    loadPage(1, true);
  }, [sort, loadPage]);

  // Infinite scroll via IntersectionObserver
  useEffect(() => {
    if (!loaderRef.current || !hasMore || loading) return;
    const obs = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) loadPage(page + 1, false);
      },
      { threshold: 0.1 }
    );
    obs.observe(loaderRef.current);
    return () => obs.disconnect();
  }, [hasMore, loading, page, loadPage]);

  // Client-side search filter
  const filtered = search.trim()
    ? memes.filter(
        (m) =>
          m.template_name.toLowerCase().includes(search.toLowerCase()) ||
          m.prompt.toLowerCase().includes(search.toLowerCase()) ||
          m.meme_text?.some((t) => t.toLowerCase().includes(search.toLowerCase()))
      )
    : memes;

  const sortTabs: { id: SortMode; label: string; Icon: React.ElementType }[] = [
    { id: "recent", label: "Recent", Icon: Clock },
    { id: "top", label: "Top", Icon: Flame },
    { id: "trending", label: "Trending", Icon: Zap },
  ];

  return (
    <div className="space-y-6">
      {/* Gallery Header */}
      <div className="space-y-4">
        <div>
          <h1 className="text-4xl font-bold">Meme Gallery</h1>
          <p className="text-secondary mt-2">
            Browse thousands of AI-generated memes from the community
          </p>
        </div>

        {/* ── Controls ─────────────────────────────────────────────────────── */}
        <div className="flex flex-col sm:flex-row gap-3">
          {/* Sort tabs */}
          <div className="flex items-center gap-1 bg-surface border border-border rounded-lg p-1">
            {sortTabs.map(({ id, label, Icon }) => (
              <button
                key={id}
                onClick={() => setSort(id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-mono transition-all ${
                  sort === id
                     ? "bg-acid text-black font-medium"
                     : "text-secondary hover:text-primary"
                }`}
                aria-label={`Sort by ${label}`}
                aria-pressed={sort === id}
              >
                <Icon size={12} />
                {label}
              </button>
            ))}
          </div>

          {/* Search */}
          <div className="relative flex-1 max-w-xs">
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

          <p className="font-mono text-xs text-muted self-center hidden sm:block">
            {total > 0 ? `${total.toLocaleString()} total` : ""}
          </p>
        </div>
      </div>

      {/* Info Stats */}
      <div className="bg-surface/50 border border-border rounded-lg p-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div>
            <p className="text-sm font-medium">Viewing: <span className="text-acid">{sort.toUpperCase()}</span></p>
            <p className="text-xs text-muted mt-1">
              {total > 0 
                ? `${filtered.length.toLocaleString()} of ${total.toLocaleString()} memes`
                : 'Loading memes...'}
            </p>
          </div>
        </div>
        <div className="text-right">
          <p className="text-xs text-muted">💡 Tip: Use search to find specific templates</p>
        </div>
      </div>

      {/* ── Grid ─────────────────────────────────────────────────────────── */}
      <div>
        {initialLoad ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
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
            <div className="w-16 h-16 rounded-full bg-surface-2 border border-border flex items-center justify-center mx-auto">
              <Loader2 size={24} className="text-muted" />
            </div>
            <div>
              <p className="font-mono text-sm text-red-400">{error}</p>
              <button onClick={() => loadPage(1, true)} className="btn-ghost text-xs mt-3">
                Try Again
              </button>
            </div>
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center py-24 text-center">
            <div className="w-20 h-20 rounded-full bg-surface-2 border border-border flex items-center justify-center mx-auto mb-6">
              <Search size={32} className="text-muted" />
            </div>
            <p className="font-display text-2xl font-bold text-white mb-2">No memes found</p>
            <p className="font-mono text-sm text-muted max-w-sm">
              {search ? "Try a different search term or browse by trending" : "Start by generating your first meme!"}
            </p>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
              {filtered.map((meme, i) => (
                <MemeCard
                  key={meme.id}
                  meme={meme}
                  priority={i < 10}
                />
              ))}
            </div>

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
    </div>
  );
}
