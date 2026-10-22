import React, { useState } from 'react';
import { History, Swords, Sparkles, CheckCircle2, AlertCircle, ArrowRight } from 'lucide-react';
import { SilenceDuelResult, SilenceReplaySession, SilenceReplayTick } from '../../types';
import { api } from '../../services/api';

interface TimeMachineScrubberProps {
  session: SilenceReplaySession | null;
  onScrubTick: (tick: SilenceReplayTick) => void;
}

export const TimeMachineScrubber: React.FC<TimeMachineScrubberProps> = ({
  session,
  onScrubTick,
}) => {
  const [scrubIndex, setScrubIndex] = useState<number>(0);
  const [duelResult, setDuelResult] = useState<SilenceDuelResult | null>(null);
  const [duelLoading, setDuelLoading] = useState<boolean>(false);
  const [duelError, setDuelError] = useState<string | null>(null);

  const ticks = session?.ticks || [];
  const currentTick = ticks[scrubIndex] || ticks[ticks.length - 1];

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const idx = parseInt(e.target.value, 10);
    setScrubIndex(idx);
    if (ticks[idx]) {
      onScrubTick(ticks[idx]);
    }
  };

  const handleRunDuel = async () => {
    if (!session?.session_id) return;
    setDuelLoading(true);
    setDuelError(null);
    try {
      const res = await api.getSilenceBaseline(session.session_id);
      setDuelResult(res);
    } catch (err: any) {
      setDuelError(err.message || 'Failed to replay baseline');
    } finally {
      setDuelLoading(false);
    }
  };

  if (!session || ticks.length === 0) {
    return (
      <div className="p-8 text-center text-slate-400 bg-white rounded-2xl border border-slate-200">
        <History className="h-8 w-8 mx-auto mb-2 text-slate-300" />
        <p className="text-sm font-medium">No recorded session history yet.</p>
        <p className="text-xs text-slate-400 mt-1">Start typing in the scratchpad to record ticks.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Scrubber Controls */}
      <div className="p-5 bg-white border border-slate-200/90 rounded-2xl shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <History className="h-4 w-4 text-blue-600" />
            <h3 className="text-sm font-bold text-slate-800">Session Time Machine</h3>
          </div>
          <span className="text-xs font-mono font-medium text-slate-500">
            Tick <strong className="text-blue-600 font-bold">{scrubIndex + 1}</strong> of{' '}
            <strong className="text-slate-700">{ticks.length}</strong>
          </span>
        </div>

        {/* Range slider */}
        <div className="space-y-1">
          <input
            type="range"
            min={0}
            max={ticks.length - 1}
            value={scrubIndex}
            onChange={handleSliderChange}
            className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
          />
          <div className="flex justify-between text-[10px] font-mono text-slate-400">
            <span>Problem Start</span>
            <span>Current</span>
          </div>
        </div>

        {/* Inspected Tick Snapshot */}
        {currentTick && (
          <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs font-mono space-y-2">
            <div className="flex items-center justify-between text-[11px] pb-1 border-b border-slate-200/80">
              <span className="font-bold text-slate-800">Decision: {currentTick.rung_name}</span>
              <span className="text-slate-500">{currentTick.decider_ms ? `${currentTick.decider_ms}ms` : 'decider'}</span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[10px] text-slate-600">
              <div>
                <span>P(struggle): </span>
                <strong className="text-emerald-700">
                  {(currentTick.probabilities?.productive_struggle ?? 0).toFixed(2)}
                </strong>
              </div>
              <div>
                <span>P(stuck): </span>
                <strong className="text-amber-700">
                  {(currentTick.probabilities?.stuck ?? 0).toFixed(2)}
                </strong>
              </div>
              <div>
                <span>P(frustration): </span>
                <strong className="text-rose-700">
                  {(currentTick.probabilities?.frustration ?? 0).toFixed(2)}
                </strong>
              </div>
              <div>
                <span>P(help): </span>
                <strong className="text-blue-700">
                  {(currentTick.probabilities?.help_request ?? 0).toFixed(2)}
                </strong>
              </div>
            </div>

            <div className="text-[11px] pt-1">
              {currentTick.held_back_by ? (
                <div className="text-emerald-800 font-sans">
                  <strong>Why stayed silent:</strong> &ldquo;{currentTick.held_back_by}&rdquo;
                </div>
              ) : currentTick.spoken_text ? (
                <div className="text-blue-800 font-sans">
                  <strong>Tutor spoke:</strong> &ldquo;{currentTick.spoken_text}&rdquo;
                </div>
              ) : (
                <div className="text-slate-500 font-sans">
                  Ghost underline rendered softly on suspect line (0 words).
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Duel Section */}
      <div className="p-6 bg-gradient-to-br from-slate-900 to-slate-950 text-white rounded-2xl shadow-md space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 text-amber-400 text-xs font-mono font-bold uppercase tracking-wider">
              <Swords className="h-4 w-4" />
              Empirical Head-to-Head Duel
            </div>
            <h3 className="text-base font-bold text-white mt-0.5">
              Silence Engine vs Conventional Always-Talk Baseline
            </h3>
            <p className="text-xs text-slate-400 mt-1">
              Replays the exact recorded scratchpad timeline through both tutor policies.
            </p>
          </div>

          <button
            onClick={handleRunDuel}
            disabled={duelLoading}
            className="px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-medium text-xs flex items-center gap-2 transition shadow-sm cursor-pointer disabled:opacity-50 shrink-0"
          >
            {duelLoading ? (
              <span>Replaying timeline...</span>
            ) : (
              <>
                <Sparkles className="h-4 w-4 text-amber-300" />
                <span>Run Duel Comparison</span>
              </>
            )}
          </button>
        </div>

        {duelError && (
          <div className="p-3 rounded-xl bg-rose-950/50 border border-rose-800 text-rose-300 text-xs">
            {duelError}
          </div>
        )}

        {/* Duel Result Cards */}
        {duelResult && (
          <div className="space-y-4 animate-in fade-in duration-300">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Silence Engine Card */}
              <div className="p-4 rounded-xl bg-slate-800/80 border border-emerald-500/40 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider font-mono">
                    Silence Engine
                  </span>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-300 border border-emerald-700 font-mono">
                    Decider 2B + Bedrock
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-3 text-xs font-mono pt-1">
                  <div>
                    <div className="text-slate-400 text-[10px]">LLM Calls</div>
                    <div className="text-xl font-bold text-white">
                      {duelResult.silence_engine.llm_calls}
                    </div>
                  </div>
                  <div>
                    <div className="text-slate-400 text-[10px]">Tokens Used</div>
                    <div className="text-xl font-bold text-emerald-400">
                      {duelResult.silence_engine.total_tokens.toLocaleString()}
                    </div>
                  </div>
                  <div>
                    <div className="text-slate-400 text-[10px]">Interruptions</div>
                    <div className="text-lg font-bold text-white">
                      {duelResult.silence_engine.interruptions}
                    </div>
                  </div>
                  <div>
                    <div className="text-slate-400 text-[10px]">False Interruption Rate</div>
                    <div className="text-lg font-bold text-emerald-400">
                      {duelResult.silence_engine.false_interruption_rate_pct}%
                    </div>
                  </div>
                </div>

                <div className="text-[11px] text-slate-300 pt-2 border-t border-slate-700/60 flex items-center justify-between">
                  <span>Estimated Cost:</span>
                  <strong className="font-mono text-emerald-300">
                    ${duelResult.silence_engine.estimated_cost_usd.toFixed(5)}
                  </strong>
                </div>
              </div>

              {/* Always-Talk Baseline Card */}
              <div className="p-4 rounded-xl bg-slate-800/80 border border-slate-700 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-amber-400 uppercase tracking-wider font-mono">
                    Always-Talk Baseline
                  </span>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-950 text-amber-300 border border-amber-700 font-mono">
                    Chat LLM on every pause
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-3 text-xs font-mono pt-1">
                  <div>
                    <div className="text-slate-400 text-[10px]">LLM Calls</div>
                    <div className="text-xl font-bold text-white">
                      {duelResult.always_talk_baseline.llm_calls}
                    </div>
                  </div>
                  <div>
                    <div className="text-slate-400 text-[10px]">Tokens Used</div>
                    <div className="text-xl font-bold text-rose-400">
                      {duelResult.always_talk_baseline.total_tokens.toLocaleString()}
                    </div>
                  </div>
                  <div>
                    <div className="text-slate-400 text-[10px]">Interruptions</div>
                    <div className="text-lg font-bold text-white">
                      {duelResult.always_talk_baseline.interruptions}
                    </div>
                  </div>
                  <div>
                    <div className="text-slate-400 text-[10px]">False Interruption Rate</div>
                    <div className="text-lg font-bold text-rose-400">
                      {duelResult.always_talk_baseline.false_interruption_rate_pct}%
                    </div>
                  </div>
                </div>

                <div className="text-[11px] text-slate-300 pt-2 border-t border-slate-700/60 flex items-center justify-between">
                  <span>Estimated Cost:</span>
                  <strong className="font-mono text-rose-300">
                    ${duelResult.always_talk_baseline.estimated_cost_usd.toFixed(5)}
                  </strong>
                </div>
              </div>
            </div>

            {/* Savings summary */}
            <div className="p-3.5 rounded-xl bg-emerald-950/40 border border-emerald-600/40 text-xs font-mono text-emerald-300 flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                <span>
                  <strong>{duelResult.comparison.token_reduction_pct}%</strong> token reduction ·{' '}
                  <strong>{duelResult.comparison.unwanted_interruption_prevention}</strong> fewer unwanted interruptions of reasoned flow
                </span>
              </div>
              <span className="text-[10px] text-slate-400">
                Exact replay of same recorded scratchpad timeline
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
