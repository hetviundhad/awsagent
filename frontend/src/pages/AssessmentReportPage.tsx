import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  Award, CheckCircle, XCircle, AlertTriangle, ArrowRight, ShieldCheck, 
  RotateCcw, Sparkles, Volume2, Layers, BookOpen, Play, Pause, ChevronLeft, ChevronRight, X
} from 'lucide-react';
import { api } from '../services/api';
import { AssessmentReport } from '../types';
import { Button, Card, Pill, Modal } from '../components/ui';

export const AssessmentReportPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [report, setReport] = useState<AssessmentReport | null>(null);
  const [loading, setLoading] = useState(true);

  // Misconception Remediation States
  const [flashcardModalOpen, setFlashcardModalOpen] = useState(false);
  const [activeFlashcards, setActiveFlashcards] = useState<any[]>([]);
  const [flashcardIdx, setFlashcardIdx] = useState(0);
  const [flashcardFlipped, setFlashcardFlipped] = useState(false);
  const [loadingFlashcards, setLoadingFlashcards] = useState(false);

  const [audioModalOpen, setAudioModalOpen] = useState(false);
  const [activeAudioBrief, setActiveAudioBrief] = useState<any | null>(null);
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const [loadingAudio, setLoadingAudio] = useState(false);

  useEffect(() => {
    if (id) {
      loadReport();
    }
  }, [id]);

  useEffect(() => {
    return () => {
      if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  const loadReport = async () => {
    try {
      const data = await api.getAssessmentReport(id!);
      setReport(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateFlashcards = async (misconception: string, conceptName?: string) => {
    try {
      setLoadingFlashcards(true);
      setFlashcardModalOpen(true);
      setFlashcardIdx(0);
      setFlashcardFlipped(false);
      const res = await api.getMisconceptionFlashcards(misconception, conceptName);
      setActiveFlashcards(res || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingFlashcards(false);
    }
  };

  const handlePlayAudioBrief = async (misconception: string, conceptName?: string) => {
    try {
      setLoadingAudio(true);
      setAudioModalOpen(true);
      setIsPlayingAudio(false);
      if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }

      const res = await api.getMisconceptionBrief(misconception, conceptName);
      setActiveAudioBrief(res);

      if (typeof window !== 'undefined' && 'speechSynthesis' in window && res?.script) {
        const utterance = new SpeechSynthesisUtterance(res.script);
        utterance.rate = 1.0;
        utterance.pitch = 1.0;
        utterance.onend = () => setIsPlayingAudio(false);
        utterance.onerror = () => setIsPlayingAudio(false);
        window.speechSynthesis.speak(utterance);
        setIsPlayingAudio(true);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingAudio(false);
    }
  };

  const toggleAudioPlayback = () => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) return;

    if (isPlayingAudio) {
      window.speechSynthesis.pause();
      setIsPlayingAudio(false);
    } else {
      if (window.speechSynthesis.paused) {
        window.speechSynthesis.resume();
        setIsPlayingAudio(true);
      } else if (activeAudioBrief?.script) {
        const utterance = new SpeechSynthesisUtterance(activeAudioBrief.script);
        utterance.onend = () => setIsPlayingAudio(false);
        utterance.onerror = () => setIsPlayingAudio(false);
        window.speechSynthesis.speak(utterance);
        setIsPlayingAudio(true);
      }
    }
  };

  const closeAudioModal = () => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
    setIsPlayingAudio(false);
    setAudioModalOpen(false);
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center bg-paper-canvas text-ink-500 font-serif text-xs">
        <div className="flex items-center space-x-2 bg-white px-4 py-2 rounded-xl border border-paper-hairline shadow-paper-sm">
          <div className="w-4 h-4 border-2 border-royal-700 border-t-transparent rounded-full animate-spin" />
          <span>Compiling Bayesian diagnostic report and misconception analysis...</span>
        </div>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="flex-1 p-8 bg-paper-canvas text-ink-700 font-serif">
        Assessment report could not be found.
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto bg-paper-canvas p-6 lg:p-8 space-y-6 max-w-6xl w-full mx-auto">
      {/* Top Banner / Score Header */}
      <div className="p-6 rounded-2xl bg-white border border-paper-hairline shadow-paper flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-royal-700 bg-royal-50 px-2 py-0.5 rounded border border-royal-200">
              BAYESIAN DIAGNOSTIC REPORT
            </span>
            <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-highlighter-base text-ink-900 font-bold border border-ink-900/10">
              SOURCE GROUNDED
            </span>
          </div>
          <h1 className="font-serif text-2xl sm:text-3xl font-bold text-ink-900 tracking-tight mt-1">
            Knowledge Verification Summary
          </h1>
          <p className="font-serif text-xs text-ink-600">
            Answers verified against uploaded course textbook pages and lecture slides with Bayesian Knowledge Tracing updates.
          </p>
        </div>

        <div className="flex items-center space-x-5">
          <div className="text-right font-mono">
            <div className="text-xs text-ink-500 uppercase tracking-wider">Overall Accuracy</div>
            <div className="text-3xl sm:text-4xl font-bold text-ink-900">
              {report.score_percentage}%
            </div>
          </div>
          <div className="h-14 w-14 rounded-2xl bg-paper-surface border border-paper-hairline flex items-center justify-center text-royal-700 shadow-paper-sm">
            <Award className="h-7 w-7" />
          </div>
        </div>
      </div>

      {/* KPI Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 font-mono">
        <div className="p-4 rounded-xl bg-white border border-paper-hairline text-center space-y-1 shadow-paper-sm">
          <div className="text-[11px] font-medium text-ink-500 uppercase tracking-wider">Questions Answered</div>
          <div className="text-2xl font-bold text-ink-900">
            {report.correct_count} / {report.total_questions}
          </div>
          <div className="text-[10px] text-emerald-700 font-semibold font-serif">Grounded in Course Material</div>
        </div>

        <div className="p-4 rounded-xl bg-white border border-paper-hairline text-center space-y-1 shadow-paper-sm">
          <div className="text-[11px] font-medium text-ink-500 uppercase tracking-wider">Time Spent</div>
          <div className="text-2xl font-bold text-ink-900">
            {Math.floor(report.time_spent_seconds / 60)}m {report.time_spent_seconds % 60}s
          </div>
          <div className="text-[10px] text-ink-500 font-serif">Pacing on track</div>
        </div>

        <div className="p-4 rounded-xl bg-white border border-paper-hairline text-center space-y-1 shadow-paper-sm">
          <div className="text-[11px] font-medium text-ink-500 uppercase tracking-wider">Weak Concepts</div>
          <div className="text-2xl font-bold text-amber-700">{report.weak_concepts.length}</div>
          <div className="text-[10px] text-ink-500 font-serif">Requires targeted review</div>
        </div>

        <div className="p-4 rounded-xl bg-white border border-paper-hairline text-center space-y-1 shadow-paper-sm">
          <div className="text-[11px] font-medium text-ink-500 uppercase tracking-wider">Misconceptions</div>
          <div className="text-2xl font-bold text-status-refused">{report.detected_misconceptions.length}</div>
          <div className="text-[10px] text-ink-500 font-serif">Remediations ready</div>
        </div>
      </div>

      {/* Misconceptions & Interactive Diagnostic CTAs */}
      {report.detected_misconceptions.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-serif text-base font-bold text-ink-900 flex items-center space-x-2">
              <AlertTriangle className="h-4 w-4 text-amber-600" />
              <span>Diagnosed Conceptual Misconceptions ({report.detected_misconceptions.length})</span>
            </h3>
            <span className="font-mono text-xs text-ink-500">
              Interactive cognitive remediations
            </span>
          </div>

          <div className="space-y-3">
            {report.detected_misconceptions.map((misc, idx) => (
              <div
                key={idx}
                className="p-5 rounded-2xl bg-amber-50/50 border border-amber-300 space-y-4 shadow-paper-sm"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-1 flex-1">
                    <div className="font-mono text-[10px] font-bold text-amber-900 uppercase tracking-wider">
                      Misconception #{idx + 1}
                    </div>
                    <div className="font-serif text-sm font-semibold text-ink-900 leading-relaxed">
                      "{misc}"
                    </div>
                  </div>

                  <span className="px-2.5 py-1 rounded-full text-[10px] font-mono font-bold bg-amber-100 text-amber-950 border border-amber-300 shrink-0">
                    High Priority
                  </span>
                </div>

                {/* 2 Interactive CTAs: Flashcards + 2-Min Audio Brief */}
                <div className="flex flex-wrap items-center gap-3 pt-2 border-t border-amber-200 font-mono">
                  <button
                    onClick={() => handleGenerateFlashcards(misc)}
                    className="px-3.5 py-2 rounded-xl bg-white hover:bg-paper-surface border border-paper-hairline text-ink-800 font-semibold text-xs flex items-center space-x-2 transition shadow-paper-sm"
                  >
                    <Layers className="h-4 w-4 text-royal-700" />
                    <span>Generate Flashcards</span>
                  </button>

                  <button
                    onClick={() => handlePlayAudioBrief(misc)}
                    className="px-3.5 py-2 rounded-xl bg-ink-900 hover:bg-ink-800 text-white font-semibold text-xs flex items-center space-x-2 transition shadow-paper-sm"
                  >
                    <Volume2 className="h-4 w-4 text-highlighter-base" />
                    <span>Play 2-Minute Audio Brief</span>
                  </button>

                  <button
                    onClick={() => navigate(`/tutor?concept=${encodeURIComponent('Remediation')}&message=${encodeURIComponent(`I encountered this misconception: "${misc}". Can you explain how to avoid this error?`)}`)}
                    className="px-3.5 py-2 rounded-xl bg-white hover:bg-paper-surface text-ink-700 text-xs font-semibold flex items-center space-x-1.5 border border-paper-hairline transition ml-auto"
                  >
                    <span>Discuss in Tutor</span>
                    <ArrowRight className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Detailed Source-Linked Answer Review */}
      <div className="space-y-4">
        <h3 className="font-serif text-lg font-bold text-ink-900 flex items-center space-x-2">
          <ShieldCheck className="h-5 w-5 text-royal-700" />
          <span>Source-Linked Answer Audit</span>
        </h3>

        <div className="space-y-4">
          {report.detailed_feedbacks.map((fb, idx) => (
            <div
              key={idx}
              className={`p-5 rounded-2xl border space-y-3 shadow-paper bg-white ${
                fb.is_correct
                  ? 'border-emerald-300'
                  : 'border-red-300'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center space-x-2 font-mono">
                  {fb.is_correct ? (
                    <CheckCircle className="h-5 w-5 text-emerald-600" />
                  ) : (
                    <XCircle className="h-5 w-5 text-status-refused" />
                  )}
                  <span className="text-xs font-bold text-ink-900">
                    Question {idx + 1}: {fb.is_correct ? 'Correct' : 'Incorrect'}
                  </span>
                </div>

                <span className="text-xs font-mono text-ink-700 bg-paper-surface px-2.5 py-0.5 rounded border border-paper-hairline">
                  {fb.source_document} ({fb.source_location})
                </span>
              </div>

              <p className="font-serif text-sm font-semibold text-ink-900">
                {fb.question_text}
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs pt-1 font-serif">
                <div className="p-3 rounded-xl bg-paper-surface border border-paper-hairline">
                  <span className="font-mono text-[10px] text-ink-500 uppercase tracking-wider block mb-0.5">Your Response:</span>
                  <span className={fb.is_correct ? 'text-emerald-800 font-bold' : 'text-status-refused font-bold'}>
                    {fb.student_answer}
                  </span>
                </div>

                <div className="p-3 rounded-xl bg-paper-surface border border-paper-hairline">
                  <span className="font-mono text-[10px] text-ink-500 uppercase tracking-wider block mb-0.5">Grounded Course Answer:</span>
                  <span className="text-emerald-800 font-bold">{fb.correct_answer}</span>
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-paper-surface border border-paper-hairline text-xs text-ink-800 leading-relaxed font-serif pl-3 border-l-4 border-highlighter-base">
                <span className="font-bold text-ink-900">Course Evidence: </span>
                {fb.explanation}
              </div>

              {fb.likely_misconception && (
                <div className="text-[11px] font-serif text-amber-950 bg-amber-50/70 border border-amber-300 p-2.5 rounded-lg flex items-center justify-between">
                  <span>⚠️ <strong className="font-semibold">Misconception Note:</strong> {fb.likely_misconception}</span>
                  <button
                    onClick={() => handlePlayAudioBrief(fb.likely_misconception!)}
                    className="font-mono text-[10px] text-royal-700 hover:text-royal-900 underline font-bold shrink-0 ml-2"
                  >
                    Listen to audio brief
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* --- Flashcard Modal --- */}
      {flashcardModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink-950/40 backdrop-blur-xs animate-in fade-in">
          <div className="bg-white border border-paper-hairline rounded-2xl max-w-lg w-full p-6 shadow-paper-lg space-y-5 relative">
            <div className="flex items-center justify-between border-b border-paper-hairline pb-3">
              <div className="flex items-center space-x-2">
                <Layers className="h-5 w-5 text-royal-700" />
                <h3 className="font-serif text-base font-bold text-ink-900">Remediation Flashcards</h3>
              </div>
              <button
                onClick={() => setFlashcardModalOpen(false)}
                className="p-1 rounded-lg text-ink-400 hover:text-ink-900 hover:bg-paper-surface"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {loadingFlashcards ? (
              <div className="py-12 text-center text-xs font-serif text-ink-500 flex items-center justify-center space-x-2">
                <div className="w-4 h-4 border-2 border-royal-700 border-t-transparent rounded-full animate-spin" />
                <span>Synthesizing cognitive flashcards for this misconception...</span>
              </div>
            ) : activeFlashcards.length > 0 ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between text-xs font-mono text-ink-500">
                  <span>Card {flashcardIdx + 1} of {activeFlashcards.length}</span>
                  <span className="text-royal-700 font-semibold">Click to flip</span>
                </div>

                {/* Flip Card on warm cream surface */}
                <div
                  onClick={() => setFlashcardFlipped(!flashcardFlipped)}
                  className="min-h-[220px] p-6 rounded-2xl bg-paper-canvas border border-paper-hairline hover:border-royal-700 transition cursor-pointer flex flex-col justify-between shadow-paper"
                >
                  <div className="font-mono text-[10px] uppercase font-bold text-royal-700 tracking-wider">
                    {flashcardFlipped ? 'REVERSE • INTUITION & CORE RULE' : 'PROMPT • CONCEPTUAL CHALLENGE'}
                  </div>

                  <div className="font-serif text-sm font-semibold text-ink-900 leading-relaxed my-4 text-center">
                    {flashcardFlipped 
                      ? activeFlashcards[flashcardIdx]?.back 
                      : activeFlashcards[flashcardIdx]?.front}
                  </div>

                  <div className="font-serif text-[11px] text-ink-500 text-center italic">
                    {flashcardFlipped
                      ? `Hint: ${activeFlashcards[flashcardIdx]?.hint || 'Remember the syllabus definition.'}`
                      : '(Click card to reveal explanation)'}
                  </div>
                </div>

                {/* Navigation Buttons */}
                <div className="flex items-center justify-between pt-2 font-mono">
                  <button
                    disabled={flashcardIdx === 0}
                    onClick={() => { setFlashcardIdx(flashcardIdx - 1); setFlashcardFlipped(false); }}
                    className="px-3 py-1.5 rounded-lg bg-paper-surface disabled:opacity-40 text-ink-700 text-xs font-semibold flex items-center space-x-1 border border-paper-hairline"
                  >
                    <ChevronLeft className="h-4 w-4" />
                    <span>Previous</span>
                  </button>

                  <button
                    onClick={() => setFlashcardFlipped(!flashcardFlipped)}
                    className="px-3.5 py-1.5 rounded-lg bg-highlighter-base text-ink-900 text-xs font-bold border border-ink-900/10"
                  >
                    Flip Card
                  </button>

                  <button
                    disabled={flashcardIdx === activeFlashcards.length - 1}
                    onClick={() => { setFlashcardIdx(flashcardIdx + 1); setFlashcardFlipped(false); }}
                    className="px-3 py-1.5 rounded-lg bg-paper-surface disabled:opacity-40 text-ink-700 text-xs font-semibold flex items-center space-x-1 border border-paper-hairline"
                  >
                    <span>Next</span>
                    <ChevronRight className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ) : (
              <div className="py-8 text-center text-xs font-serif text-ink-500">No flashcards generated.</div>
            )}
          </div>
        </div>
      )}

      {/* --- 2-Minute Audio Brief Modal with Waveform --- */}
      {audioModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink-950/40 backdrop-blur-xs animate-in fade-in">
          <div className="bg-white border border-paper-hairline rounded-2xl max-w-lg w-full p-6 shadow-paper-lg space-y-5 relative">
            <div className="flex items-center justify-between border-b border-paper-hairline pb-3">
              <div className="flex items-center space-x-2">
                <Volume2 className="h-5 w-5 text-royal-700" />
                <h3 className="font-serif text-base font-bold text-ink-900">2-Minute AI Audio Brief</h3>
              </div>
              <button
                onClick={closeAudioModal}
                className="p-1 rounded-lg text-ink-400 hover:text-ink-900 hover:bg-paper-surface"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {loadingAudio ? (
              <div className="py-12 text-center text-xs font-serif text-ink-500 flex items-center justify-center space-x-2">
                <div className="w-4 h-4 border-2 border-royal-700 border-t-transparent rounded-full animate-spin" />
                <span>Synthesizing voice briefing and tutor script...</span>
              </div>
            ) : activeAudioBrief ? (
              <div className="space-y-4">
                {/* Audio Wave Visualizer on warm paper background */}
                <div className="p-6 rounded-2xl bg-paper-canvas border border-paper-hairline flex flex-col items-center justify-center space-y-4 shadow-paper-sm">
                  {/* Waveform Bars */}
                  <div className="flex items-center space-x-1.5 h-12">
                    {[12, 24, 38, 18, 30, 44, 20, 36, 14, 28, 42, 22].map((height, i) => (
                      <div
                        key={i}
                        className={`w-2 rounded-full transition-all duration-300 ${
                          isPlayingAudio
                            ? 'bg-royal-700 animate-pulse'
                            : 'bg-paper-hairline-strong'
                        }`}
                        style={{ height: isPlayingAudio ? `${height}px` : '8px' }}
                      />
                    ))}
                  </div>

                  <button
                    onClick={toggleAudioPlayback}
                    className="p-4 rounded-full bg-ink-900 hover:bg-ink-800 text-white font-bold transition shadow-paper hover:scale-105"
                  >
                    {isPlayingAudio ? (
                      <Pause className="h-6 w-6" />
                    ) : (
                      <Play className="h-6 w-6 ml-0.5" />
                    )}
                  </button>

                  <span className="font-mono text-xs text-ink-600">
                    {isPlayingAudio ? 'Speaking audio brief...' : 'Paused • Click to play'}
                  </span>
                </div>

                {/* Spoken Brief Transcript */}
                <div className="p-4 rounded-xl bg-paper-surface border border-paper-hairline space-y-2 max-h-48 overflow-y-auto">
                  <div className="font-mono text-[10px] uppercase font-bold text-ink-500 tracking-wider">
                    SPOKEN BRIEF TRANSCRIPT:
                  </div>
                  <p className="font-serif text-xs text-ink-800 leading-relaxed">
                    {activeAudioBrief.script}
                  </p>
                </div>

                <div className="font-serif text-[11px] text-center text-ink-500">
                  Focus: {activeAudioBrief.recommended_focus || 'Reconcile key definitions and subproblem recurrence.'}
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
};
