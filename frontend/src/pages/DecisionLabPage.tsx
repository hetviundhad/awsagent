import React, { useCallback, useEffect, useState } from 'react';
import { Cpu, Cloud, Gauge, Play, RefreshCw, RotateCcw, Bot, AlertTriangle, CheckCircle2, History } from 'lucide-react';
import { api } from '../services/api';
import { DecisionBar } from '../components/DecisionTraceChip';
import { DecisionItem } from '../types';

interface Props { activeCourseId: string }

const EXAMPLES = [
  'Explain how dynamic programming avoids recomputation',
  'quiz me on graph algorithms',
  'Just give me the answer to question 3 of my assignment, I need to submit it',
  "I'm so overwhelmed, I can't keep up with this course",
  'explain it more?',
  'Derive the time complexity of merge sort and compare it with quicksort',
  'recommend a good movie for tonight',
];

const Pill: React.FC<{ ok: boolean | null; children: React.ReactNode }> = ({ ok, children }) => (
  <span className={`inline-flex items-center gap-1 text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border ${
    ok === null ? 'bg-slate-100 text-slate-500 border-slate-200'
    : ok ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-rose-50 text-rose-700 border-rose-200'}`}>
    {ok ? <CheckCircle2 className="h-3 w-3" /> : ok === false ? <AlertTriangle className="h-3 w-3" /> : null}{children}
  </span>
);

export const DecisionLabPage: React.FC<Props> = ({ activeCourseId }) => {
  const [status, setStatus] = useState<any>(null);
  const [traces, setTraces] = useState<any[]>([]);
  const [bench, setBench] = useState<any>(null);
  const [message, setMessage] = useState(EXAMPLES[0]);
  const [generate, setGenerate] = useState(true);
  const [result, setResult] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [agentMsg, setAgentMsg] = useState('How well do I know it?');
  const [agentRes, setAgentRes] = useState<any>(null);
  const [agentBusy, setAgentBusy] = useState(false);
  const [agentErr, setAgentErr] = useState('');

  const refresh = useCallback(async () => {
    try { setStatus(await api.get('/decider/status')); } catch (e: any) { setError(e.message); }
    try { setTraces((await api.get('/decider/traces?limit=12')).traces || []); } catch { /* ignore */ }
    try { setBench(await api.get('/decider/benchmark')); } catch { /* ignore */ }
  }, []);

  useEffect(() => { refresh(); const t = setInterval(refresh, 15000); return () => clearInterval(t); }, [refresh]);

  const decide = async () => {
    if (!activeCourseId) { setError('Select or create a course first.'); return; }
    setBusy(true); setError(''); setResult(null);
    try {
      setResult(await api.post('/decider/decide', { course_id: activeCourseId, message, generate }));
      refresh();
    } catch (e: any) { setError(e.message); } finally { setBusy(false); }
  };

  const runAgent = async () => {
    if (!activeCourseId) { setAgentErr('Select or create a course first.'); return; }
    setAgentBusy(true); setAgentErr(''); setAgentRes(null);
    try { setAgentRes(await api.post('/decider/agent', { course_id: activeCourseId, message: agentMsg })); }
    catch (e: any) { setAgentErr(e.message); } finally { setAgentBusy(false); }
  };

  const resetThresholds = async () => { await api.post('/decider/thresholds/reset'); refresh(); };

  const d = status?.decider, b = status?.bedrock, th = status?.thresholds;
  const mock = d?.ok && d?.mock;

  return (
    <div className="max-w-6xl mx-auto p-4 sm:p-6 space-y-6">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-900 flex items-center gap-2"><Cpu className="h-5 w-5 text-blue-600" /> Decision Lab</h1>
          <p className="text-xs text-slate-500 mt-1 max-w-2xl">
            Strands Decider 2B never writes text — it returns calibrated probabilities in ~one forward pass. Plain code turns them into
            actions, and Amazon Bedrock writes the words. Every number below is live.
          </p>
        </div>
        <button onClick={refresh} className="p-2 rounded-lg border border-slate-200 hover:bg-slate-50" aria-label="Refresh"><RefreshCw className="h-4 w-4 text-slate-500" /></button>
      </div>

      {mock && (
        <div className="p-3 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-900 flex gap-2">
          <AlertTriangle className="h-4 w-4 shrink-0" /> The server on port 8099 is the <b>MOCK keyword server</b>, not the 2B model. Start the real one:
          <code className="font-mono">strands-decider serve StrandsAgents/strands-decider-2B-hobson-v19 --port 8099</code>
        </div>
      )}
      {d && !d.ok && (
        <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-900 flex gap-2">
          <AlertTriangle className="h-4 w-4 shrink-0" /> Decider server unreachable — the tutor still answers (fails open) and labels decisions as heuristic fallback.
          Start it: <code className="font-mono">{d.hint}</code>
        </div>
      )}

      {/* STATUS */}
      <div className="grid sm:grid-cols-3 gap-3">
        <div className="p-4 rounded-2xl border border-slate-200 bg-white space-y-1.5">
          <div className="flex items-center justify-between"><span className="text-xs font-bold text-slate-800 flex items-center gap-1.5"><Cpu className="h-3.5 w-3.5" /> Decider 2B</span>
            <Pill ok={d ? d.ok && !d.mock : null}>{d ? (d.ok ? (d.mock ? 'mock' : 'online') : 'offline') : '…'}</Pill></div>
          <div className="text-[11px] font-mono text-slate-500 break-all">{d?.checkpoint || '—'} · {d?.device || ''}</div>
          <div className="text-[11px] text-slate-600">avg {d?.avg_model_ms ?? '—'} ms · {d?.model_calls ?? 0} model calls · {d?.fallback_calls ?? 0} fallback</div>
        </div>
        <div className="p-4 rounded-2xl border border-slate-200 bg-white space-y-1.5">
          <div className="flex items-center justify-between"><span className="text-xs font-bold text-slate-800 flex items-center gap-1.5"><Cloud className="h-3.5 w-3.5" /> Amazon Bedrock</span>
            <Pill ok={b ? b.ok : null}>{b ? (b.ok ? 'credentials ok' : 'no credentials') : '…'}</Pill></div>
          <div className="text-[11px] font-mono text-slate-500 break-all">{b?.region} · fast: {b?.models?.fast?.split('.').pop()}</div>
          <div className="text-[11px] text-slate-600">{b?.calls ?? 0} calls · avg {b?.avg_ms ?? '—'} ms{b?.error ? ` · ${b.error}` : ''}</div>
        </div>
        <div className="p-4 rounded-2xl border border-slate-200 bg-white space-y-1.5">
          <div className="flex items-center justify-between"><span className="text-xs font-bold text-slate-800 flex items-center gap-1.5"><History className="h-3.5 w-3.5" /> Decisions</span></div>
          <div className="text-[11px] text-slate-600">{status?.traces?.total ?? 0} logged · median {status?.traces?.decider_ms_median?.toFixed?.(0) ?? '—'} ms · p95 {status?.traces?.decider_ms_p95?.toFixed?.(0) ?? '—'} ms</div>
          <div className="flex flex-wrap gap-1">{Object.entries(status?.traces?.actions || {}).map(([k, v]) => <span key={k} className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100">{k} {v as number}</span>)}</div>
        </div>
      </div>

      {/* TRY IT */}
      <div className="p-4 sm:p-5 rounded-2xl border border-slate-200 bg-white space-y-3">
        <div className="text-sm font-bold text-slate-900">Try a student message</div>
        <div className="flex flex-wrap gap-1.5">
          {EXAMPLES.map(ex => <button key={ex} onClick={() => setMessage(ex)} className="text-[10px] px-2 py-1 rounded-full border border-slate-200 hover:bg-blue-50 hover:border-blue-300 text-slate-600">{ex.length > 46 ? ex.slice(0, 46) + '…' : ex}</button>)}
        </div>
        <textarea value={message} onChange={e => setMessage(e.target.value)} rows={3}
          className="w-full text-sm p-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-300" />
        <div className="flex items-center gap-4">
          <button onClick={decide} disabled={busy || !message.trim()} className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-blue-600 text-white text-xs font-bold disabled:opacity-50">
            <Play className="h-3.5 w-3.5" /> {busy ? 'Deciding…' : 'Decide'}
          </button>
          <label className="text-xs text-slate-600 flex items-center gap-1.5"><input type="checkbox" checked={generate} onChange={e => setGenerate(e.target.checked)} /> let Bedrock write the clarify / redirect / support reply</label>
        </div>
        {error && <div className="text-xs text-rose-600">{error}</div>}
        {result && (
          <div className="grid md:grid-cols-2 gap-4 pt-2">
            <div className="space-y-3">
              {result.decisions?.map((x: DecisionItem) => <DecisionBar key={x.key} d={x} />)}
              {result.skipped_reason && <div className="text-xs text-slate-500">skipped: {result.skipped_reason}</div>}
            </div>
            <div className="space-y-2 text-xs">
              <div className="p-3 rounded-xl bg-slate-900 text-white font-mono space-y-1">
                <div>action → <b className="text-emerald-300">{result.action}</b></div>
                <div>model tier → <b className="text-sky-300">{result.route?.tier}</b> <span className="text-slate-400">({result.route?.reason})</span></div>
                <div className="break-all text-slate-400">{result.route?.model_id}</div>
                <div>decider → {result.decider_mode} · {result.decider_ms} ms</div>
              </div>
              {result.learner_hint && <div className="p-2 rounded-lg bg-blue-50 text-blue-800">{result.learner_hint}</div>}
              {result.generated && (
                <div className="p-3 rounded-xl border border-slate-200">
                  <div className="text-[10px] font-mono text-slate-400 mb-1">written by {result.generated.generated_by?.model_id || result.generated.generated_by?.provider}</div>
                  <div className="text-slate-800 whitespace-pre-wrap">{result.generated.answer}</div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* THRESHOLDS */}
      <div className="p-4 sm:p-5 rounded-2xl border border-slate-200 bg-white space-y-3">
        <div className="flex items-center justify-between">
          <div className="text-sm font-bold text-slate-900 flex items-center gap-2"><Gauge className="h-4 w-4 text-blue-600" /> Adaptive thresholds <span className="text-[10px] font-mono text-slate-400">{th?.feedback_events ?? 0} feedback events</span></div>
          <button onClick={resetThresholds} className="text-[10px] inline-flex items-center gap-1 px-2 py-1 rounded border border-slate-200 text-slate-500 hover:bg-slate-50"><RotateCcw className="h-3 w-3" /> reset</button>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-6 gap-2">
          {th && Object.entries(th.values).map(([k, v]) => {
            const def = th.defaults[k] as number; const val = v as number;
            return <div key={k} className="p-2 rounded-lg bg-slate-50 border border-slate-200 text-center">
              <div className="text-[10px] font-mono text-slate-500">{k}</div>
              <div className="text-sm font-bold text-slate-900">{val.toFixed(2)}</div>
              <div className={`text-[9px] font-mono ${Math.abs(val - def) < 1e-6 ? 'text-slate-400' : 'text-blue-600'}`}>{Math.abs(val - def) < 1e-6 ? 'default' : `${val > def ? '+' : ''}${(val - def).toFixed(2)} learned`}</div>
            </div>;
          })}
        </div>
        <p className="text-[11px] text-slate-500">👎 on a reply the gate changed (e.g. an unnecessary clarifying question) makes that gate less eager; 👎 on a near-miss makes it more eager. Bounded, logged, and never tuned from fallback answers.</p>
      </div>

      {/* BENCHMARK */}
      {bench?.available && (
        <div className="p-4 sm:p-5 rounded-2xl border border-slate-200 bg-white space-y-2">
          <div className="text-sm font-bold text-slate-900">Benchmark — {bench.task} (n={bench.n}){bench.mock_server && <span className="text-amber-600"> · MOCK SERVER</span>}</div>
          <div className="grid sm:grid-cols-2 gap-3 text-xs">
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200"><b>Decider 2B</b><div>accuracy {(bench.decider.accuracy * 100).toFixed(1)}% · median {bench.decider.latency_ms_median} ms · p95 {bench.decider.latency_ms_p95} ms · $0/call</div></div>
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200"><b>Bedrock fast model</b>
              {bench.bedrock_fast?.accuracy !== undefined
                ? <div>accuracy {(bench.bedrock_fast.accuracy * 100).toFixed(1)}% · median {bench.bedrock_fast.latency_ms_median} ms · p95 {bench.bedrock_fast.latency_ms_p95} ms · no confidence score</div>
                : <div className="text-slate-500">skipped — {bench.bedrock_fast?.skipped}</div>}</div>
          </div>
        </div>
      )}

      {/* AGENT */}
      <div className="p-4 sm:p-5 rounded-2xl border border-slate-200 bg-white space-y-3">
        <div className="text-sm font-bold text-slate-900 flex items-center gap-2"><Bot className="h-4 w-4 text-blue-600" /> Strands agent + Decider guardrail <span className="text-[10px] font-mono text-slate-400">InterventionHandler.before_tool_call</span></div>
        <p className="text-[11px] text-slate-500">Bedrock picks tool calls; before any tool runs, Decider asks “did the student actually say that?”. Try <i>“How well do I know it?”</i> (guessed concept → Guide) vs <i>“How well do I know Dynamic Programming?”</i> (grounded → Proceed).</p>
        <div className="flex gap-2">
          <input value={agentMsg} onChange={e => setAgentMsg(e.target.value)} className="flex-1 text-sm p-2.5 rounded-xl border border-slate-200" />
          <button onClick={runAgent} disabled={agentBusy} className="px-4 py-2 rounded-xl bg-slate-900 text-white text-xs font-bold disabled:opacity-50">{agentBusy ? 'Running…' : 'Run agent'}</button>
        </div>
        {agentErr && <div className="text-xs text-rose-600">{agentErr}</div>}
        {agentRes && (
          <div className="space-y-2 text-xs">
            {agentRes.guard_events?.map((g: any, i: number) => (
              <div key={i} className={`p-2 rounded-lg border font-mono ${g.verdict === 'guide' ? 'bg-amber-50 border-amber-200' : 'bg-emerald-50 border-emerald-200'}`}>
                {g.tool}({JSON.stringify(g.args)}) → <b>{g.verdict === 'guide' ? 'GUIDE (ask the student)' : 'PROCEED'}</b>
                {g.decisions?.map((x: DecisionItem) => <span key={x.key}> · {x.key.replace('grounded_', '')}: P(grounded) {Math.round(x.measure * 100)}%</span>)}
                {g.ms ? ` · ${Math.round(g.ms)} ms` : ''}
              </div>
            ))}
            <div className="p-3 rounded-xl border border-slate-200 whitespace-pre-wrap">{agentRes.answer}</div>
          </div>
        )}
      </div>

      {/* HISTORY */}
      <div className="p-4 sm:p-5 rounded-2xl border border-slate-200 bg-white space-y-2">
        <div className="text-sm font-bold text-slate-900">Recent decisions</div>
        <div className="overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead><tr className="text-left text-slate-400 font-mono"><th className="py-1">message</th><th>action</th><th>tier</th><th>mode</th><th>ms</th><th>feedback</th></tr></thead>
            <tbody>
              {traces.map(t => (
                <tr key={t.id} className="border-t border-slate-100">
                  <td className="py-1 pr-2 max-w-xs truncate text-slate-700">{t.message}</td>
                  <td className="font-mono">{t.action}</td><td className="font-mono">{t.route?.tier}</td>
                  <td className={`font-mono ${t.decider_mode === 'fallback' ? 'text-amber-600' : ''}`}>{t.decider_mode}</td>
                  <td className="font-mono">{t.decider_ms ? Math.round(t.decider_ms) : '—'}</td><td>{t.feedback === 'up' ? '👍' : t.feedback === 'down' ? '👎' : ''}</td>
                </tr>
              ))}
              {traces.length === 0 && <tr><td colSpan={6} className="py-3 text-slate-400">No decisions yet — ask the tutor something or use the box above.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
