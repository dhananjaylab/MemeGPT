
import { useState, useEffect } from 'react';
import { MemeAPI } from '../lib/api';
import { useAuth } from '../context/AuthContext';
import { User, Key, Zap, Shield, BarChart3, Clock, LayoutGrid } from 'lucide-react';
import type { GeneratedMeme } from '../types';
import { MemeCard } from '../components/MemeCard';

export function Dashboard() {
  const { user } = useAuth();
  const [memes, setMemes] = useState<GeneratedMeme[]>([]);

  useEffect(() => {
    if (user) {
      MemeAPI.getMyMemes().then(setMemes);
    }
  }, [user]);

  if (!user) return null;

  return (
    <div className="py-12 space-y-12">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 bg-acid rounded-2xl flex items-center justify-center text-black">
            <User size={32} />
          </div>
          <div>
            <h1 className="font-display text-4xl font-bold">{user.name}</h1>
            <p className="text-muted">{user.email} • {user.plan.toUpperCase()} Plan</p>
          </div>
        </div>
        <button className="btn-primary">Upgrade Plan</button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatCard icon={Zap} label="Daily Limit" value={`${user.daily_used} / ${user.daily_limit}`} />
        <StatCard icon={BarChart3} label="Total Generated" value={memes.length.toString()} />
        <StatCard icon={Shield} label="Safety Status" value="Healthy" />
      </div>

      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock size={16} className="text-acid" />
            <h2 className="font-mono text-xs uppercase tracking-widest text-muted">Recent Activity</h2>
          </div>
        </div>

        {memes.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {memes.slice(0, 4).map((meme) => (
              <MemeCard key={meme.id} meme={meme} />
            ))}
          </div>
        ) : (
          <div className="glass-card text-center py-20 opacity-40">
             <LayoutGrid size={32} className="mx-auto mb-4" />
             <p className="text-sm font-mono uppercase tracking-widest">No activity logged yet</p>
          </div>
        )}
      </div>

      <div className="glass-card space-y-6">
        <div className="flex items-center gap-2">
          <Key size={16} className="text-acid" />
          <h2 className="font-mono text-xs uppercase tracking-widest text-muted">API Credentials</h2>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex-1 bg-black/40 border border-border p-4 rounded-xl font-mono text-sm text-secondary overflow-hidden">
            mgpt_sk_live_••••••••••••••••••••••••
          </div>
          <button className="btn-ghost px-4">Reveal</button>
        </div>
      </div>
    </div>
  );
}

function StatCard({ icon: Icon, label, value }: { icon: any, label: string, value: string }) {
  return (
    <div className="glass-card">
      <div className="flex items-center gap-2 mb-4">
        <Icon size={14} className="text-muted" />
        <span className="font-mono text-[10px] uppercase tracking-widest text-muted">{label}</span>
      </div>
      <div className="text-3xl font-display font-bold text-white">{value}</div>
    </div>
  );
}
