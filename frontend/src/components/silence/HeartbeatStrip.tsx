import React, { useState } from 'react';
import { SilenceReplayTick } from '../../types';

interface HeartbeatStripProps {
  ticks: SilenceReplayTick[];
  onSelectTick?: (tick: SilenceReplayTick) => void;
  selectedTickIndex?: number;
}

export const HeartbeatStrip: React.FC<HeartbeatStripProps> = ({
  ticks,
  onSelectTick,
  selectedTickIndex,
}) => {
  const [hoveredTick, setHoveredTick] = useState<SilenceReplayTick | null>(null);

  // Take the last 40 ticks for the strip if long
  const displayTicks = ticks.slice(-40);

  return (
    <div className="relative bg-white/95 backdrop-blur border border-slate-200/90 rounded-2xl p-3 shadow-sm select-none">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
          </span>
          <span className="text-xs font-bold text-slate-800 tracking-tight">The Heartbeat</span>
          <span className="text-[10px] text-slate-400 font-mono">Live Decider 2B trajectory</span>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-3 text-[10px] font-mono text-slate-500">
          <span className="flex items-center gap-1">
            <span className="inline-block h-2 w-2 rounded-full bg-slate-300" />
            Silent
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block h-2.5 w-2.5 rounded-full border border-amber-500 bg-amber-50" />
            Underline
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block h-2.5 w-2.5 rounded-full bg-blue-600 shadow-2xs" />
            Spoke (R2-4)
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block h-2 w-2 rounded-full bg-purple-500" />
            Breather
          </span>
        </div>
      </div>

      {/* SVG Timeline Canvas */}
      <div className="relative h-14 w-full bg-slate-50/80 rounded-xl border border-slate-200/60 overflow-hidden flex items-end px-3 py-1.5">
        {displayTicks.length === 0 ? (
          <div className="w-full h-full flex items-center justify-center text-[11px] text-slate-400 font-mono">
            Waiting for first keystroke tick (~1s debounce)...
          </div>
        ) : (
          <div className="w-full flex items-end justify-between gap-1 h-full">
            {displayTicks.map((tick, i) => {
              const pStuck = tick.probabilities?.stuck || 0;
              const pStruggle = tick.probabilities?.productive_struggle || 0;
              const isSelected = selectedTickIndex === tick.tick_index;

              // Height proportional to P(stuck) or escalation
              const heightPct = Math.max(16, Math.min(95, Math.round(pStuck * 100)));

              // Dot appearance
              let dotClass = 'bg-slate-300 text-slate-500';
              let ringClass = '';
              if (tick.rung === 'B') {
                dotClass = 'bg-purple-600 ring-2 ring-purple-200';
              } else if (typeof tick.rung === 'number' && tick.rung >= 2) {
                dotClass = 'bg-blue-600 shadow-sm ring-2 ring-blue-200 scale-110';
              } else if (tick.rung === 1) {
                dotClass = 'bg-amber-400 ring-2 ring-amber-100';
              }

              if (isSelected) {
                ringClass = 'ring-2 ring-slate-900 scale-125';
              }

              return (
                <div
                  key={`${tick.tick_index}-${i}`}
                  className="flex-1 flex flex-col items-center justify-end h-full group relative cursor-pointer"
                  onMouseEnter={() => setHoveredTick(tick)}
                  onMouseLeave={() => setHoveredTick(null)}
                  onClick={() => onSelectTick && onSelectTick(tick)}
                >
                  {/* Subtle struggle guide bar */}
                  <div
                    className="w-1 rounded-t-full bg-emerald-200/50 mb-0.5 transition-all"
                    style={{ height: `${Math.round(pStruggle * 40)}%` }}
                    title={`P(productive_struggle) = ${pStruggle.toFixed(2)}`}
                  />

                  {/* Tick Dot */}
                  <div
                    className={`w-2.5 h-2.5 rounded-full transition-transform duration-200 ${dotClass} ${ringClass}`}
                  />

                  {/* Height line for stuck signal */}
                  <div
                    className={`w-0.5 rounded-t transition-all ${
                      tick.spoken ? 'bg-blue-500' : 'bg-slate-300'
                    }`}
                    style={{ height: `${heightPct * 0.4}%` }}
                  />
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Popover on hover showing "Why Silent?" or spoken explanation */}
      {hoveredTick && (
        <div className="absolute bottom-16 left-4 right-4 bg-slate-900 text-white rounded-xl p-3 shadow-xl z-30 text-xs font-mono border border-slate-700 animate-in fade-in duration-150">
          <div className="flex items-center justify-between text-[11px] text-slate-300 border-b border-slate-700/80 pb-1.5 mb-1.5">
            <span className="font-bold text-white">Tick #{hoveredTick.tick_index}</span>
            <span className="text-emerald-400 font-semibold">{hoveredTick.rung_name}</span>
            <span className="text-slate-400">{hoveredTick.decider_ms ? `${hoveredTick.decider_ms}ms` : 'decider'}</span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[10px] text-slate-300 mb-2">
            <div>
              <span className="text-slate-400">P(struggle):</span>{' '}
              <strong className="text-emerald-400">
                {(hoveredTick.probabilities?.productive_struggle ?? 0).toFixed(2)}
              </strong>
            </div>
            <div>
              <span className="text-slate-400">P(stuck):</span>{' '}
              <strong className="text-amber-400">
                {(hoveredTick.probabilities?.stuck ?? 0).toFixed(2)}
              </strong>
            </div>
            <div>
              <span className="text-slate-400">P(frustration):</span>{' '}
              <strong className="text-rose-400">
                {(hoveredTick.probabilities?.frustration ?? 0).toFixed(2)}
              </strong>
            </div>
            <div>
              <span className="text-slate-400">P(help):</span>{' '}
              <strong className="text-blue-400">
                {(hoveredTick.probabilities?.help_request ?? 0).toFixed(2)}
              </strong>
            </div>
          </div>

          <div className="text-[11px] text-slate-200">
            {hoveredTick.held_back_by ? (
              <span className="text-emerald-300">
                <strong>Why stayed silent:</strong> {hoveredTick.held_back_by}
              </span>
            ) : hoveredTick.spoken_text ? (
              <span className="text-blue-300">
                <strong>Spoke:</strong> &ldquo;{hoveredTick.spoken_text}&rdquo;
              </span>
            ) : (
              <span>Rung 1: Ghost underline on suspect line (0 words)</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
