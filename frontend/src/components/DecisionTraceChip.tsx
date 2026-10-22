import React, { useState } from 'react';
import { Cpu, ThumbsUp, ThumbsDown, ChevronDown, ChevronUp, Zap, AlertTriangle } from 'lucide-react';
import { DecisionTrace, DecisionItem } from '../types';
import { api } from '../services/api';

const ACTION_STYLE: Record<string, { label: string; cls: string }> = {
  answer: { label: 'Grounded answer', cls: 'bg-blue-50 text-blue-700 border-blue-200' },
  quiz: { label: 'Quiz mode', cls: 'bg-violet-50 text-violet-700 border-violet-200' },
  socratic: { label: 'Guided discovery (no answer dump)', cls: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  clarify: { label: 'Asked to clarify', cls: 'bg-amber-50 text-amber-800 border-amber-200' },
  support: { label: 'Study-stress support', cls: 'bg-rose-50 text-rose-700 border-rose-200' },
  redirect: { label: 'Redirected to course', cls: 'bg-slate-100 text-slate-700 border-slate-300' },
};

export const DecisionBar: React.FC<{ d: DecisionItem }> = ({ d }) => {
  const pct = Math.round(d.measure * 100);
  const thr = Math.round(d.threshold * 100);
  const title = d.kind === 'choice' ? `${d.key}: ${d.label}` : d.key;
  return (
    <div className="space-y-0.5">
      <div className="flex justify-between text-[10px] font-mono text-slate-600">
        <span className="font-bold text-slate-800">{title}</span>
        <span>
          {d.kind === 'choice' ? 'confidence' : 'P(yes)'} {pct}% · threshold {thr}%{' '}
          {d.triggered ? <span className="text-blue-700 font-bold">→ triggered</span> : <span className="text-slate-400">→ not triggered</span>}
          {d.fallback && <span className="text-amber-600 font-bold"> · heuristic fallback</span>}
        </span>
      </div>
      <div className="relative h-2 rounded-full bg-slate-100 overflow-hidden">
        <div className={`h-full ${d.fallback ? 'bg-amber-400' : 'bg-blue-500'}`} style={{ width: `${pct}%` }} />
        <div className="absolute top-0 h-full w-0.5 bg-slate-800" style={{ left: `${thr}%` }} title={`threshold ${thr}%`} />
      </div>
      {d.kind === 'choice' && (
        <div className="flex flex-wrap gap-1 pt-0.5">
          {Object.entries(d.probabilities)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 4)
            .map(([k, v]) => (
              <span key={k} className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-slate-50 border border-slate-200 text-slate-600">
                {k} {Math.round(v * 100)}%
              </span>
            ))}
        </div>
      )}
    </div>
  );
};

export const DecisionTraceChip: React.FC<{ trace: DecisionTrace }> = ({ trace }) => {
  const [open, setOpen] = useState(false);
  const [vote, setVote] = useState<'up' | 'down' | null>(null);
  const [note, setNote] = useState<string>('');
  const style = ACTION_STYLE[trace.action] || ACTION_STYLE.answer;
  const skipped = trace.decider_mode === 'skipped';
  const fallback = trace.decider_mode === 'fallback';

  const sendFeedback = async (helpful: boolean) => {
    if (!trace.trace_id || vote) return;
    setVote(helpful ? 'up' : 'down');
    try {
      const res = await api.post('/decider/feedback', { trace_id: trace.trace_id, helpful });
      const ch = (res.threshold_changes || []) as { key: string; from: number; to: number }[];
      setNote(ch.length ? `Thresholds adapted: ${ch.map(c => `${c.key} ${c.from.toFixed(2)}→${c.to.toFixed(2)}`).join(', ')}` : 'Thanks — no threshold change needed.');
    } catch {
      setNote('Could not record feedback.');
    }
  };

  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-2.5 space-y-2">
      <div className="flex flex-wrap items-center gap-1.5 text-[10px] font-mono">
        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-slate-900 text-white font-bold">
          <Cpu className="h-3 w-3" /> Decider 2B
        </span>
        <span className={`px-2 py-0.5 rounded-full border font-bold ${style.cls}`}>{style.label}</span>
        {!skipped && <span className="text-slate-500">{Math.round(trace.decider_ms)} ms</span>}
        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-white border border-slate-200 text-slate-600">
          <Zap className="h-3 w-3" /> {trace.route.tier === 'deep' ? 'deep model' : 'fast model'}
        </span>
        {fallback && (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-amber-50 border border-amber-200 text-amber-700 font-bold">
            <AlertTriangle className="h-3 w-3" /> model offline — heuristic fallback
          </span>
        )}
        {skipped && <span className="text-slate-400">skipped: {trace.skipped_reason}</span>}
        <div className="ml-auto flex items-center gap-1">
          {trace.trace_id && !skipped && (
            <>
              <button type="button" disabled={!!vote} onClick={() => sendFeedback(true)} aria-label="Helpful"
                className={`p-1 rounded hover:bg-white ${vote === 'up' ? 'text-emerald-600' : 'text-slate-400'}`}>
                <ThumbsUp className="h-3.5 w-3.5" />
              </button>
              <button type="button" disabled={!!vote} onClick={() => sendFeedback(false)} aria-label="Not helpful"
                className={`p-1 rounded hover:bg-white ${vote === 'down' ? 'text-rose-600' : 'text-slate-400'}`}>
                <ThumbsDown className="h-3.5 w-3.5" />
              </button>
            </>
          )}
          <button type="button" onClick={() => setOpen(o => !o)} className="p-1 rounded hover:bg-white text-slate-500" aria-label="Toggle decision details">
            {open ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
          </button>
        </div>
      </div>
      {note && <div className="text-[10px] text-slate-500">{note}</div>}
      {open && (
        <div className="space-y-2.5 pt-1">
          {trace.decisions.map(d => <DecisionBar key={d.key} d={d} />)}
          <div className="text-[10px] text-slate-500 font-mono">
            route → {trace.route.model_id || 'default model'} ({trace.route.reason})
            {trace.generated_by?.model_id && <> · written by {trace.generated_by.model_id}</>}
          </div>
          {trace.learner_hint && <div className="text-[10px] text-blue-700">Prerequisite nudge added: {trace.learner_hint}</div>}
          {trace.context?.scores && trace.context.scores.length > 0 && (
            <div className="text-[10px] text-slate-600 font-mono">
              context scored by Decider: {trace.context.scores.map(s => `${Math.round((s.relevance || 0) * 100)}%`).join(' · ')}
              {trace.context.dropped ? ` (dropped ${trace.context.dropped})` : ''}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
