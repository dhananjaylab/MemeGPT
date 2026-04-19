import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  Key, Copy, Check, Eye, EyeOff, ExternalLink,
  Zap, Trash2, BarChart2,
} from "lucide-react";
import { toast } from "react-hot-toast";
import { useAuth } from "../context/AuthContext";
import { ShareMenu } from "../components/ShareMenu";
import type { GeneratedMeme, User } from "../lib/types";
import { apiClient } from "../lib/api";


interface DashboardClientProps {}


async function fetchUserData(token?: string) {
  try {
    const [user, memesResponse] = await Promise.all([
      apiClient.getCurrentUser(token),
      apiClient.getMemes({ user: "me", page: 1, limit: 40 }, token),
    ]);

    return { 
      user, 
      memes: memesResponse.memes || [], 
      total: memesResponse.total || 0
    };
  } catch (err) {
    console.error("Failed to fetch dashboard data:", err);
    return { user: null, memes: [], total: 0 };
  }
}

export function Dashboard() {
  const [user, setUser] = useState<User | null>(null);
  const [memes, setMemes] = useState<GeneratedMeme[]>([]);
  const [totalMemes, setTotalMemes] = useState(0);
  const [loading, setLoading] = useState(true);
  const [keyVisible, setKeyVisible] = useState(false);
  const [copied, setCopied] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const { token: backendToken, isAuthenticated, isLoading: authLoading } = useAuth();

  useEffect(() => {
    const loadData = async () => {
      if (authLoading) return;
      
      if (!isAuthenticated) {
        setLoading(false);
        return;
      }

      try {
        const { user, memes, total } = await fetchUserData(backendToken || undefined);
        setUser(user);
        setMemes(memes);
        setTotalMemes(total);
      } catch (err) {
        console.error("Failed to fetch dashboard data:", err);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [backendToken, isAuthenticated, authLoading]);

  const handleDelete = async (id: string) => {
    setDeletingId(id);
    try {
      const res = await apiClient.deleteMeme(id, backendToken);
      if (res.success) {
        setMemes((prev) => prev.filter((m) => m.id !== id));
        setTotalMemes((t) => Math.max(0, t - 1));
      }
    } catch (err) {
      console.error("Delete error:", err);
    } finally {
      setDeletingId(null);
    }
  };

  const copyKey = async () => {
    if (!user?.api_key) return;
    await navigator.clipboard.writeText(user.api_key);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const startCheckout = async (plan: "pro" | "api") => {
    try {
      const res = await apiClient.createCheckoutSession(plan, {
        success_url: `${window.location.origin}/dashboard`,
        cancel_url: `${window.location.origin}/dashboard`,
      }, backendToken);
      
      if (res.checkout_url) {
        window.location.href = res.checkout_url;
      }
    } catch (err) {
      console.error("Checkout error:", err);
    }
  };

  const handleRotateKey = async () => {
    if (!confirm("Are you sure? Your existing key will stop working immediately.")) return;
    try {
      const res = await apiClient.rotateApiKey(backendToken);
      if (res.api_key && user) {
        setUser({ ...user, api_key: res.api_key });
        toast.success("API key rotated successfully!");
      }
    } catch (err: any) {
      console.error("Rotate error:", err);
      toast.error(err.message || "Failed to rotate key");
    }
  };

  if (loading) return <DashboardSkeleton />;

  const used = user?.daily_used ?? 0;
  const limit = user?.daily_limit ?? 5;
  const pct = Math.min(100, Math.round((used / limit) * 100));
  const plan = user?.plan ?? "free";

  return (
    <div className="space-y-10">
      {/* ── Overview stats ─────────────────────────────────────────────────── */}
      <section id="overview">
        <SectionHeading icon={BarChart2} label="Overview" />
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: "Plan",       value: plan.toUpperCase(),        accent: plan !== "free" },
            { label: "Generated",  value: totalMemes.toLocaleString() },
            { label: "Used today", value: `${used} / ${limit}` },
            { label: "Shares",     value: memes.reduce((a, m) => a + (m.share_count || 0), 0).toLocaleString() },
          ].map((s) => (
            <div key={s.label} className="card-dark p-4 text-center">
              <p className={`font-display text-2xl ${s.accent ? "text-acid" : "text-primary"}`}>
                {s.value}
              </p>
              <p className="font-mono text-[10px] uppercase tracking-wider text-muted mt-0.5">
                {s.label}
              </p>
            </div>
          ))}
        </div>

        {/* Daily usage bar */}
        <div className="mt-4 card-dark p-4">
          <div className="flex justify-between items-center mb-2">
            <span className="font-mono text-xs text-secondary">Daily generations</span>
            <span className="font-mono text-xs text-muted">{used} / {limit}</span>
          </div>
          <div className="h-1.5 bg-surface-3 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-700 ${
                pct >= 90 ? "bg-red-400" : pct >= 70 ? "bg-amber-400" : "bg-acid"
              }`}
              style={{ width: `${pct}%` }}
            />
          </div>
          {pct >= 80 && plan === "free" && (
            <p className="font-mono text-xs text-amber-400 mt-2">
              Running low —{" "}
              <button
                onClick={() => startCheckout("pro")}
                className="underline hover:text-acid transition-colors"
              >
                upgrade to Pro
              </button>{" "}
              for 500/day.
            </p>
          )}
        </div>
      </section>

      {/* ── Meme history ───────────────────────────────────────────────────── */}
      <section id="my-memes">
        <div className="flex items-center justify-between mb-4">
          <SectionHeading icon={Zap} label="My memes" />
          {totalMemes > 0 && (
            <span className="badge-dim">{totalMemes} total</span>
          )}
        </div>

        {memes.length === 0 ? (
          <div className="card-dark p-10 text-center">
            <p className="font-display text-display-md text-muted mb-3">No memes yet</p>
            <Link to="/" className="btn-acid text-xs">
              Generate your first meme →
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            {memes.map((meme, i) => (
              <HistoryCard
                key={meme.id}
                meme={meme}
                priority={i < 4}
                deleting={deletingId === meme.id}
                onDelete={() => handleDelete(meme.id)}
              />
            ))}
          </div>
        )}

        {totalMemes > 40 && (
          <div className="mt-4 text-center">
            <Link to="/gallery" className="btn-ghost text-xs" title="View all">
              View all in gallery →
            </Link>
          </div>
        )}
      </section>

      {/* ── API key ────────────────────────────────────────────────────────── */}
      <section id="api">
        <SectionHeading icon={Key} label="API access" />
        <div className="card-dark p-5">
          {plan === "api" && user?.api_key ? (
            <>
              <p className="font-mono text-xs text-secondary mb-3 leading-relaxed">
                Include this key in every request as{" "}
                <code className="text-acid">X-API-Key: your_key</code>
              </p>
              <div className="flex items-center gap-2">
                <div className="flex-1 bg-black border border-border rounded-lg px-3 py-2 font-mono text-xs text-secondary overflow-hidden">
                  {keyVisible
                    ? user.api_key
                    : "mgpt_" + "•".repeat(Math.max(0, user.api_key.length - 5))}
                </div>
                <button
                  onClick={() => setKeyVisible((v) => !v)}
                  className="btn-ghost p-2"
                  title={keyVisible ? "Hide" : "Reveal"}
                  aria-label={keyVisible ? "Hide API key" : "Reveal API key"}
                >
                  {keyVisible ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
                <button
                  onClick={copyKey}
                  className="btn-ghost p-2"
                  title="Copy"
                  aria-label="Copy API key to clipboard"
                >
                  {copied ? (
                    <Check size={14} className="text-acid" />
                  ) : (
                    <Copy size={14} />
                  )}
                </button>
              </div>
              <p className="font-mono text-[10px] text-muted mt-3">
                Keep this secret. Rotate it anytime if compromised.
              </p>
              <div className="mt-4 pt-4 border-t border-border flex items-center justify-between">
                <Link to="/api-docs" className="btn-ghost text-xs gap-1.5">
                  <ExternalLink size={12} />
                  View API documentation
                </Link>
                <button 
                  onClick={handleRotateKey}
                  className="text-[10px] font-mono text-muted hover:text-red-400 transition-colors uppercase"
                >
                  Rotate Key
                </button>
              </div>
            </>
          ) : (
            <div className="text-center py-4">
              <div className="w-10 h-10 rounded-xl bg-surface-2 border border-border flex items-center justify-center mx-auto mb-3">
                <Key size={18} className="text-muted" />
              </div>
              <p className="font-mono text-sm text-secondary mb-1">
                API access requires the API plan
              </p>
              <p className="font-mono text-xs text-muted mb-4">
                $29/mo · 500 generations/day · full REST API
              </p>
              <button
                onClick={() => startCheckout("api")}
                className="btn-acid text-xs"
              >
                Upgrade to API Plan
              </button>
            </div>
          )}
        </div>
      </section>

      {/* ── Upgrade CTA ────────────────────────────────────────────────────── */}
      {plan === "free" && (
        <section id="upgrade">
          <SectionHeading icon={Zap} label="Upgrade" />
          <div className="grid sm:grid-cols-2 gap-4">
            <PlanCard
              name="Pro"
              price="$9"
              features={[
                "500 generations / day",
                "No watermark",
                "Priority queue",
                "Meme history forever",
              ]}
              cta="Upgrade to Pro"
              accent={true}
              onClick={() => startCheckout("pro")}
            />
            <PlanCard
              name="API"
              price="$29"
              features={[
                "Everything in Pro",
                "REST API access",
                "API key management",
                "Developer portal",
              ]}
              cta="Get API Access"
              onClick={() => startCheckout("api")}
            />
          </div>
        </section>
      )}
    </div>
  );
}

// ── Sub-components ─────────────────────────────────────────────────────────

function SectionHeading({
  icon: Icon,
  label,
}: {
  icon: React.ElementType;
  label: string;
}) {
  return (
    <div className="flex items-center gap-2 mb-4">
      <Icon size={14} className="text-acid" />
      <h2 className="font-mono text-xs uppercase tracking-widest text-secondary">
        {label}
      </h2>
    </div>
  );
}

function HistoryCard({
  meme,
  priority,
  deleting,
  onDelete,
}: {
  meme: GeneratedMeme;
  priority: boolean;
  deleting: boolean;
  onDelete: () => void;
}) {
  return (
    <article className="group card-dark flex flex-col hover:border-border-light transition-colors duration-200">
      <div className="relative aspect-square overflow-hidden bg-surface-2">
        <img
          src={meme.image_url}
          alt={meme.meme_text?.join(" / ") || "Meme"}
          className="w-full h-full object-contain transition-transform duration-300 group-hover:scale-[1.02]"
          loading={priority ? "eager" : "lazy"}
        />
        {deleting && (
          <div className="absolute inset-0 bg-black/60 flex items-center justify-center">
            <div className="w-5 h-5 border-2 border-acid border-t-transparent rounded-full animate-spin" />
          </div>
        )}
        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-all duration-200" />
      </div>
      <div className="px-3 py-2 flex items-center justify-between gap-1">
        <p className="font-mono text-[10px] text-muted truncate">
          {meme.template_name}
        </p>
        <div className="flex items-center gap-0.5 shrink-0">
          <Link
            to={`/meme/${meme.id}`}
            className="p-1.5 rounded text-muted hover:text-primary transition-colors"
            title="View"
          >
            <ExternalLink size={11} />
          </Link>
          <ShareMenu meme={meme} />
          <button
            onClick={onDelete}
            disabled={deleting}
            className="p-1.5 rounded text-muted hover:text-red-400 hover:bg-red-400/10 transition-colors"
            title="Delete"
            aria-label="Delete meme"
          >
            <Trash2 size={11} />
          </button>
        </div>
      </div>
    </article>
  );
}

function PlanCard({
  name,
  price,
  features,
  cta,
  accent = false,
  onClick,
}: {
  name: string;
  price: string;
  features: string[];
  cta: string;
  accent?: boolean;
  onClick: () => void;
}) {
  return (
    <div
      className={`card-dark p-6 flex flex-col gap-5 ${
        accent ? "border-acid/40" : ""
      }`}
    >
      {accent && (
        <div className="badge-acid self-start">Most popular</div>
      )}
      <div>
        <p className="font-display text-3xl text-primary">
          {price}
          <span className="font-mono text-sm text-muted">/mo</span>
        </p>
        <p className="font-mono text-xs text-muted mt-0.5">{name} plan</p>
      </div>
      <ul className="space-y-2 flex-1">
        {features.map((f) => (
          <li key={f} className="flex items-start gap-2 font-mono text-xs text-secondary">
            <span className="text-acid mt-0.5 shrink-0">✓</span>
            {f}
          </li>
        ))}
      </ul>
      <button
        onClick={onClick}
        className={accent ? "btn-acid w-full justify-center" : "btn-ghost w-full justify-center"}
      >
        {cta}
      </button>
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-10">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="h-20 rounded-xl bg-surface animate-pulse" />
        ))}
      </div>
      <div className="h-16 rounded-xl bg-surface animate-pulse" />
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="aspect-square rounded-xl bg-surface animate-pulse" />
        ))}
      </div>
    </div>
  );
}
