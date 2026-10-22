import React, { useState } from 'react';
import { 
  X, Sparkles, CheckCircle2, AlertTriangle, ArrowRight, RotateCcw, 
  Mic, MicOff, BookOpen, ChevronRight, Award
} from 'lucide-react';
import { api } from '../services/api';

interface ClaimItem {
  claim: string;
  status: 'correct' | 'unsupported_or_flawed';
  verification_confidence?: number;
  supporting_doc?: string;
  page_number?: number;
  correcting_citation?: {
    document_name: string;
    page_number: number;
    corrective_fact: string;
  };
  feedback?: string;
}

interface TeachBackResult {
  concept_id: string;
  concept_name: string;
  overall_score: number;
  is_passed: boolean;
  correct_claims: ClaimItem[];
  wrong_claims: ClaimItem[];
  missing_key_points: string[];
  feedback: string;
  bkt_update: {
    before_probability: number;
    after_probability: number;
    mastery_gain: number;
  };
}

interface TeachBackModalProps {
  isOpen: boolean;
  onClose: () => void;
  courseId: string;
  conceptId: string;
  conceptName: string;
  onSuccess?: () => void;
}

export const TeachBackModal: React.FC<TeachBackModalProps> = ({
  isOpen,
  onClose,
  courseId,
  conceptId,
  conceptName,
  onSuccess
}) => {
  const [explanation, setExplanation] = useState('');
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [result, setResult] = useState<TeachBackResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleStartMic = () => {
    if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
      alert("Speech recognition is not supported in this browser. Please type your explanation.");
      return;
    }
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onstart = () => setIsRecording(true);
    recognition.onend = () => setIsRecording(false);
    recognition.onerror = () => setIsRecording(false);
    recognition.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript;
      setExplanation(prev => prev ? `${prev} ${transcript}` : transcript);
      setIsRecording(false);
    };

    recognition.start();
  };

  const handleSubmit = async () => {
    if (!explanation.trim()) {
      setError("Please provide an explanation in your own words before submitting.");
      return;
    }
    setError(null);
    setIsEvaluating(true);

    try {
      const data = await api.evaluateTeachBack(courseId, conceptId, explanation.trim());
      setResult(data);
      if (onSuccess) onSuccess();
    } catch (err: any) {
      setError(err?.message || "Failed to evaluate teach-back explanation. Please try again.");
    } finally {
      setIsEvaluating(false);
    }
  };

  const handleTryAgain = () => {
    setResult(null);
    setError(null);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in">
      <div className="relative w-full max-w-3xl max-h-[90vh] flex flex-col bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden text-slate-100">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950/50">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-white tracking-tight">Teach-Back Mode</h2>
                <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-300">
                  Feynman Method
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Explain <span className="text-indigo-300 font-medium">{conceptName}</span> in your own words. We will verify every factual claim against the course documents.
              </p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {!result ? (
            /* Input Form */
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-800 text-xs text-slate-300 space-y-1.5">
                <p className="font-semibold text-slate-200">How Teach-Back Works:</p>
                <ul className="list-disc list-inside space-y-1 text-slate-400">
                  <li>Break down the definition, operational mechanism, and why it matters.</li>
                  <li>Our NLI critic decomposes your sentences into atomic claims and checks entailment.</li>
                  <li>Accurate explanations boost your BKT mastery; discovered misconceptions are saved with corrections.</li>
                </ul>
              </div>

              <div className="relative">
                <textarea
                  value={explanation}
                  onChange={(e) => setExplanation(e.target.value)}
                  placeholder={`Explain ${conceptName} as if teaching a peer. For example: what is the core mechanism, how does it handle failure or scale, and what trade-offs exist?...`}
                  rows={6}
                  className="w-full px-4 py-3 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition resize-none"
                />
                <button
                  type="button"
                  onClick={handleStartMic}
                  className={`absolute right-3 bottom-3 p-2 rounded-lg text-xs font-medium flex items-center gap-1.5 transition ${
                    isRecording 
                      ? 'bg-red-500/20 text-red-400 border border-red-500/30 animate-pulse' 
                      : 'bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700'
                  }`}
                  title={isRecording ? "Recording voice..." : "Dictate via microphone"}
                >
                  {isRecording ? <MicOff className="w-4 h-4 text-red-400" /> : <Mic className="w-4 h-4" />}
                  <span>{isRecording ? "Listening..." : "Voice"}</span>
                </button>
              </div>

              {error && (
                <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-xs text-red-400 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 shrink-0" />
                  <span>{error}</span>
                </div>
              )}
            </div>
          ) : (
            /* Evaluation Results */
            <div className="space-y-6 animate-in fade-in">
              {/* Score Banner */}
              <div className={`p-5 rounded-2xl border flex items-center justify-between ${
                result.is_passed 
                  ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300' 
                  : 'bg-amber-500/10 border-amber-500/30 text-amber-300'
              }`}>
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    {result.is_passed ? (
                      <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                    ) : (
                      <AlertTriangle className="w-5 h-5 text-amber-400" />
                    )}
                    <span className="font-bold text-base">
                      {result.is_passed ? "Explanation Grounded & Verified!" : "Needs Revision: Unsupported Claims Found"}
                    </span>
                  </div>
                  <p className="text-xs text-slate-300 max-w-xl">
                    {result.feedback}
                  </p>
                </div>

                <div className="text-right space-y-1 pl-4 border-l border-slate-800">
                  <div className="text-2xl font-black tracking-tight text-white">
                    {result.overall_score}%
                  </div>
                  <div className="text-[10px] font-medium tracking-wide uppercase text-slate-400">
                    Teach-Back Score
                  </div>
                </div>
              </div>

              {/* BKT Mastery Probability Gain */}
              <div className="flex items-center justify-between px-4 py-3 rounded-xl bg-slate-950 border border-slate-800 text-xs">
                <span className="text-slate-400 font-medium">Bayesian Knowledge Tracing (BKT) Update:</span>
                <div className="flex items-center gap-3">
                  <span className="text-slate-400">P(L): {result.bkt_update.before_probability.toFixed(3)}</span>
                  <ArrowRight className="w-3.5 h-3.5 text-slate-600" />
                  <span className="font-semibold text-white">P(L): {result.bkt_update.after_probability.toFixed(3)}</span>
                  <span className={`px-2 py-0.5 rounded-full font-bold text-[11px] ${
                    result.bkt_update.mastery_gain >= 0 
                      ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30' 
                      : 'bg-rose-500/15 text-rose-400 border border-rose-500/30'
                  }`}>
                    {result.bkt_update.mastery_gain >= 0 ? '+' : ''}{(result.bkt_update.mastery_gain * 100).toFixed(1)}%
                  </span>
                </div>
              </div>

              {/* Verified Claims (Green) */}
              <div className="space-y-2">
                <h4 className="text-xs font-bold tracking-wider uppercase text-emerald-400 flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Accurate Grounded Claims ({result.correct_claims.length})</span>
                </h4>
                {result.correct_claims.length === 0 ? (
                  <p className="text-xs text-slate-500 italic pl-5">No claims were entailed by the course notes.</p>
                ) : (
                  <div className="space-y-2">
                    {result.correct_claims.map((cc, i) => (
                      <div key={i} className="p-3 rounded-xl bg-emerald-950/20 border border-emerald-800/30 text-xs space-y-1">
                        <div className="flex items-start gap-2">
                          <span className="text-emerald-400 font-bold shrink-0 mt-0.5">[+]</span>
                          <span className="text-slate-200">{cc.claim}</span>
                        </div>
                        {cc.supporting_doc && (
                          <div className="flex items-center gap-1.5 text-[11px] text-emerald-400/80 pl-4 font-mono">
                            <BookOpen className="w-3 h-3" />
                            <span>Verified in {cc.supporting_doc} (Page/Slide {cc.page_number || 1})</span>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Flawed / Unsupported Claims (Red/Amber) */}
              {result.wrong_claims.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-xs font-bold tracking-wider uppercase text-rose-400 flex items-center gap-1.5">
                    <AlertTriangle className="w-4 h-4" />
                    <span>Unsupported Claims & Misconceptions ({result.wrong_claims.length})</span>
                  </h4>
                  <div className="space-y-2">
                    {result.wrong_claims.map((wc, i) => (
                      <div key={i} className="p-3.5 rounded-xl bg-rose-950/20 border border-rose-800/30 text-xs space-y-2">
                        <div className="flex items-start gap-2">
                          <span className="text-rose-400 font-bold shrink-0 mt-0.5">[-]</span>
                          <span className="text-slate-200">{wc.claim}</span>
                        </div>
                        {wc.correcting_citation && (
                          <div className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800 text-[11px] text-slate-300 space-y-1">
                            <div className="font-semibold text-rose-300 flex items-center gap-1">
                              <span>Correction:</span>
                            </div>
                            <p className="text-slate-300 italic">"{wc.correcting_citation.corrective_fact}"</p>
                            <div className="flex items-center gap-1 text-[10px] text-slate-400 font-mono pt-1">
                              <BookOpen className="w-3 h-3" />
                              <span>Source: {wc.correcting_citation.document_name} (Page/Slide {wc.correcting_citation.page_number})</span>
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Missing Key Points */}
              {result.missing_key_points.length > 0 && (
                <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 text-xs space-y-2">
                  <h4 className="font-semibold text-slate-300">Essential Key Points Omitted:</h4>
                  <ul className="space-y-1 text-slate-400 list-disc list-inside">
                    {result.missing_key_points.map((kp, i) => (
                      <li key={i}><span className="text-slate-300">{kp}</span></li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-slate-800 bg-slate-950/50">
          {!result ? (
            <div className="flex items-center justify-between w-full">
              <span className="text-xs text-slate-500 font-mono">
                {explanation.trim().split(/\s+/).filter(Boolean).length} words
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 text-xs font-semibold text-slate-400 hover:text-white transition"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleSubmit}
                  disabled={isEvaluating || !explanation.trim()}
                  className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-semibold text-xs flex items-center gap-2 shadow-lg shadow-indigo-600/20 transition"
                >
                  {isEvaluating ? (
                    <>
                      <div className="w-3.5 h-3.5 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                      <span>Verifying Claims...</span>
                    </>
                  ) : (
                    <>
                      <span>Submit for Verification</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </>
                  )}
                </button>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-between w-full">
              <button
                type="button"
                onClick={handleTryAgain}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 flex items-center gap-2 transition"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Try Again</span>
              </button>
              <button
                type="button"
                onClick={onClose}
                className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs transition"
              >
                Done
              </button>
            </div>
          )}
        </div>

      </div>
    </div>
  );
};
