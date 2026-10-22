import React from 'react';
import { Eye, ShieldCheck, Zap, Activity } from 'lucide-react';
import { SilenceSessionStats } from '../../types';

interface SilenceMeterProps {
  stats: SilenceSessionStats | null;
  isTyping: boolean;
  deciderMode?: string;
  avgLatencyMs?: number;
  lastHeldBackBy?: string | null;
}

export const SilenceMeter: React.FC<SilenceMeterProps> = ({
  stats,
  isTyping,
  deciderMode = 'model',
  avgLatencyMs = 115,
  lastHeldBackBy,
}) => {
  const totalTicks = stats?.total_ticks || 0;
  const spoken = stats?.spoken_interventions || 0;
  const silent = Math.max(0, totalTicks - spoken);
  const tokens = stats?.tokens_used || 0;
  const latency = stats?.avg_decider_ms || avgLatencyMs;
  const mode = stats?.decider_mode || deciderMode;

  const isModel = mode === 'model';
  const isFallback = mode === 'fallback';

  return (
    <div className="bg-white/90 backdrop-blur-md border border-slate-200/80 rounded-2xl p-4 shadow-sm space-y-3">
      {/* Top Bar: Eye animation + Mode badge */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div
            className={`relative flex items-center justify-center h-8 w-8 rounded-full border transition-all duration-300 ${
              isTyping
                ? 'bg-slate-100 border-slate-300 text-slate-400 scale-95'
                : 'bg-emerald-50 border-emerald-300 text-emerald-600 scale-100 shadow-2xs'
            }`}
            title={isTyping ? 'Resting eye during fast typing burst' : 'Calm eye watching locally'}
          >
            <Eye
              className={`h-4 w-4 transition-transform duration-300 ${
                isTyping ? 'scale-y-20 opacity-40' : 'scale-y-100 opacity-100 animate-pulse'
              }`}
            />
            {!isTyping && (
              <span className="absolute -top-0.5 -right-0.5 h-2 w-2 rounded-full bg-emerald-500 animate-ping opacity-75" />
            )}
          </div>
          <div>
            <div className="text-[11px] font-mono font-bold tracking-wider uppercase text-slate-400">
              Silence Engine
            </div>
            <div className="text-xs font-semibold text-slate-800">
              {isTyping ? 'Typing burst...' : 'Observing quietly'}
            </div>
          </div>
        </div>

        {/* Mode & Latency badge */}
        <div className="flex items-center gap-1.5 font-mono text-[10px]">
          <span
            className={`px-2 py-0.5 rounded-full font-bold uppercase tracking-wider border ${
              isModel
                ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                : isFallback
                ? 'bg-amber-50 text-amber-700 border-amber-200'
                : 'bg-rose-50 text-rose-700 border-rose-200'
            }`}
          >
            {isModel ? 'DECIDER 2B' : isFallback ? 'FALLBACK (heuristic)' : 'UNAVAILABLE'}
          </span>
          <span className="px-1.5 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200 flex items-center gap-1 font-semibold">
            <Zap className="h-2.5 w-2.5 text-amber-500" />
            {latency > 0 ? `${latency}ms` : '~115ms'}
          </span>
        </div>
      </div>

      {/* Main Meter Counter */}
      <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200/60">
        <div className="text-xs font-medium text-slate-700 flex items-center justify-between">
          <span>Watched <strong className="font-mono text-slate-900">{totalTicks}</strong> ticks</span>
          <span>Spoke <strong className="font-mono text-blue-700">{spoken}</strong> times</span>
        </div>
        <div className="mt-1 text-[11px] text-emerald-700 font-medium flex items-center gap-1">
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-500" />
          <span><strong>0 tokens</strong> spent on the other <strong>{silent}</strong> ticks</span>
        </div>
        {tokens > 0 && (
          <div className="mt-1 text-[10px] font-mono text-slate-500">
            Total tokens spent: {tokens} (tiny Socratic margin notes only)
          </div>
        )}
      </div>

      {/* Local-First Privacy Chip */}
      <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1 border-t border-slate-100">
        <div className="flex items-center gap-1.5">
          <ShieldCheck className="h-3.5 w-3.5 text-blue-600" />
          <span>Watching locally – cloud only when the tutor speaks</span>
        </div>
      </div>

      {/* Current holding rule badge if available */}
      {lastHeldBackBy && (
        <div className="text-[10px] font-mono text-slate-500 bg-slate-100/70 px-2 py-1 rounded-lg truncate" title={lastHeldBackBy}>
          Held by: <span className="font-medium text-slate-700">{lastHeldBackBy}</span>
        </div>
      )}
    </div>
  );
};
