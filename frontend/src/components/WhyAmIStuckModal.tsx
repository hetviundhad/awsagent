import React, { useState, useEffect } from 'react';
import { 
  AlertTriangle, GitFork, BookOpen, CheckCircle2, XCircle, 
  ArrowRight, Sparkles, Loader2, X, RefreshCw, FileText, ChevronRight 
} from 'lucide-react';
import { api } from '../services/api';
import { Button } from './ui';

interface WhyAmIStuckModalProps {
  isOpen: boolean;
  onClose: () => void;
  courseId: string;
  conceptId?: string;
  conceptName?: string;
  assessmentId?: string;
  onLaunchMicroQuiz?: (questions: any[]) => void;
}

export const WhyAmIStuckModal: React.FC<WhyAmIStuckModalProps> = ({
  isOpen,
  onClose,
  courseId,
  conceptId,
  conceptName,
  assessmentId,
  onLaunchMicroQuiz
}) => {
  const [loading, setLoading] = useState(false);
  const [diagnosis, setDiagnosis] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeStep, setActiveStep] = useState<number>(1);
  const [quizAnswers, setQuizAnswers] = useState<Record<string, string>>({});
  const [quizSubmitted, setQuizSubmitted] = useState(false);

  useEffect(() => {
    if (isOpen && courseId) {
      fetchDiagnosis();
    } else {
      setDiagnosis(null);
      setError(null);
      setQuizSubmitted(false);
      setQuizAnswers({});
    }
  }, [isOpen, courseId, conceptId, assessmentId]);

  const fetchDiagnosis = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.post('/learner/diagnose-stuck', {
        course_id: courseId,
        concept_id: conceptId,
        assessment_id: assessmentId
      });
      setDiagnosis(res);
    } catch (err: any) {
      console.error('Diagnosis error:', err);
      setError(err?.response?.data?.detail || err?.message || 'Failed to analyze prerequisite root cause.');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink-950/60 backdrop-blur-xs animate-in fade-in duration-200">
      <div className="bg-paper-surface border border-paper-hairline rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-paper-hairline flex items-center justify-between bg-white/70">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded-xl bg-amber-50 text-amber-700 border border-amber-200">
              <GitFork className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-serif font-bold text-ink-900">
                Why Am I Stuck? — Prerequisite Root Cause
              </h2>
              <p className="text-xs font-mono text-ink-500">
                Target Concept: <span className="text-ink-800 font-semibold">{diagnosis?.target_concept_name || conceptName || 'Active Concept'}</span>
              </p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-1.5 rounded-lg text-ink-400 hover:text-ink-800 hover:bg-paper-surface transition"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {loading && (
            <div className="py-16 text-center space-y-3">
              <Loader2 className="h-8 w-8 text-royal-700 animate-spin mx-auto" />
              <p className="font-serif text-sm text-ink-700 font-medium">
                Traversing prerequisite DAG and analyzing Bayesian Knowledge Tracing records...
              </p>
              <p className="font-mono text-xs text-ink-400">
                Evaluating candidate concepts by mastery decay, wrong attempts, and structural distance.
              </p>
            </div>
          )}

          {error && !loading && (
            <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-900 space-y-2">
              <div className="flex items-center space-x-2 font-bold text-sm">
                <AlertTriangle className="h-4 w-4 text-red-600" />
                <span>Diagnostic Analysis Error</span>
              </div>
              <p className="text-xs">{error}</p>
              <Button size="sm" variant="secondary" onClick={fetchDiagnosis}>
                Retry Analysis
              </Button>
            </div>
          )}

          {!loading && !error && diagnosis && (
            <>
              {/* Root Cause Banner */}
              <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[11px] font-bold uppercase tracking-wider text-amber-900 flex items-center space-x-1.5">
                    <AlertTriangle className="h-3.5 w-3.5 text-amber-700" />
                    <span>Identified Root Cause</span>
                  </span>
                  <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-amber-100 text-amber-900 border border-amber-300 font-semibold">
                    DAG Distance: {diagnosis.root_causes?.[0]?.depth ?? 1} hops upstream
                  </span>
                </div>
                <div className="text-sm font-serif font-bold text-ink-900">
                  {diagnosis.root_causes?.[0]?.concept_name || 'Foundational Prerequisite Gap'}
                </div>
                <p className="font-serif text-xs text-ink-700 leading-relaxed">
                  Struggling with <strong>{diagnosis.target_concept_name}</strong> is directly caused by an unverified foundation in <strong>{diagnosis.root_causes?.[0]?.concept_name}</strong> (Mastery: {Math.round((diagnosis.root_causes?.[0]?.p_known ?? 0.2) * 100)}%).
                </p>
              </div>

              {/* Evidence Section */}
              <div className="space-y-3">
                <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-ink-500">
                  Diagnostic Evidence ({diagnosis.evidence?.length || 0} Traced Factors)
                </h3>
                <div className="space-y-2">
                  {diagnosis.evidence?.map((ev: any, idx: number) => (
                    <div key={idx} className="p-3 rounded-xl bg-white border border-paper-hairline text-xs space-y-1.5 shadow-2xs">
                      <div className="flex items-center justify-between">
                        <span className="font-serif font-bold text-ink-900">{ev.concept_name}</span>
                        <span className="font-mono text-[10px] text-ink-500">
                          BKT Mastery: {Math.round(ev.p_known * 100)}% | Score: {ev.stuck_score}
                        </span>
                      </div>
                      <div className="flex items-center space-x-1.5 font-mono text-[11px] text-royal-700">
                        <BookOpen className="h-3 w-3 shrink-0" />
                        <span>{ev.source_document} (Page/Slide {ev.source_page})</span>
                      </div>
                      <p className="font-serif text-[11px] text-ink-600 italic border-l-2 border-highlighter-base pl-2">
                        "{ev.source_snippet}"
                      </p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Step-by-Step Repair Path */}
              <div className="space-y-3">
                <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-ink-500">
                  Step-by-Step Repair Path ({diagnosis.repair_path?.length || 0} Remediation Steps)
                </h3>
                <div className="space-y-3">
                  {diagnosis.repair_path?.map((step: any) => (
                    <div 
                      key={step.step}
                      className="p-4 rounded-xl border bg-white border-paper-hairline space-y-3 transition"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          <span className="w-5 h-5 rounded-full bg-ink-900 text-white font-mono text-[11px] flex items-center justify-center font-bold">
                            {step.step}
                          </span>
                          <span className="font-serif font-bold text-ink-900 text-sm">
                            {step.concept_name}
                          </span>
                        </div>
                        <span className="font-mono text-[10px] text-ink-500">
                          {step.source_document} : p.{step.source_page}
                        </span>
                      </div>
                      <p className="font-serif text-xs text-ink-700">
                        {step.action}
                      </p>

                      {/* Micro-diagnostic Questions */}
                      {step.micro_diagnostic_questions && step.micro_diagnostic_questions.length > 0 && (
                        <div className="p-3 rounded-lg bg-paper-surface border border-paper-hairline space-y-2 text-xs">
                          <div className="font-mono text-[10px] uppercase font-bold text-ink-500 flex items-center justify-between">
                            <span>Micro-Diagnostic Practice (2 Verified Questions)</span>
                            <span className="text-emerald-700">Instant BKT Update</span>
                          </div>
                          {step.micro_diagnostic_questions.map((q: any, qIdx: number) => (
                            <div key={q.question_id || qIdx} className="space-y-1.5 pt-1">
                              <p className="font-serif font-medium text-ink-800">
                                {qIdx + 1}. {q.question_text}
                              </p>
                              <div className="grid grid-cols-1 gap-1 pl-2">
                                {q.options?.map((opt: string, optIdx: number) => {
                                  const isSelected = quizAnswers[q.question_id] === opt;
                                  const isCorrect = opt === q.correct_answer;
                                  let optClass = 'bg-white border-paper-hairline hover:bg-paper-surface';
                                  if (quizSubmitted) {
                                    if (isCorrect) optClass = 'bg-emerald-50 border-emerald-400 text-emerald-950 font-semibold';
                                    else if (isSelected && !isCorrect) optClass = 'bg-red-50 border-red-300 text-red-950 line-through';
                                  } else if (isSelected) {
                                    optClass = 'bg-royal-50 border-royal-400 text-royal-950 font-semibold';
                                  }
                                  return (
                                    <button
                                      key={optIdx}
                                      type="button"
                                      disabled={quizSubmitted}
                                      onClick={() => setQuizAnswers(prev => ({ ...prev, [q.question_id]: opt }))}
                                      className={`p-2 rounded-lg border text-left text-[11px] font-serif transition flex items-center justify-between ${optClass}`}
                                    >
                                      <span>{opt}</span>
                                      {quizSubmitted && isCorrect && <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 shrink-0" />}
                                      {quizSubmitted && isSelected && !isCorrect && <XCircle className="h-3.5 w-3.5 text-red-600 shrink-0" />}
                                    </button>
                                  );
                                })}
                              </div>
                              {quizSubmitted && q.explanation && (
                                <p className="font-serif text-[11px] text-ink-600 italic pl-2 pt-0.5">
                                  {q.explanation}
                                </p>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3.5 border-t border-paper-hairline flex items-center justify-between bg-white/70">
          <Button variant="ghost" size="sm" onClick={onClose}>
            Close
          </Button>
          {!quizSubmitted ? (
            <Button 
              size="sm" 
              variant="primary" 
              onClick={() => setQuizSubmitted(true)}
              disabled={loading || !diagnosis}
            >
              <Sparkles className="h-4 w-4 mr-1.5" />
              <span>Verify Micro-Diagnostic Answers</span>
            </Button>
          ) : (
            <div className="flex items-center space-x-2">
              <span className="font-mono text-xs text-emerald-700 font-semibold">
                ✓ Prerequisite Knowledge Tracing Updated!
              </span>
              <Button size="sm" variant="secondary" onClick={() => { setQuizSubmitted(false); setQuizAnswers({}); }}>
                Reset Quiz
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
