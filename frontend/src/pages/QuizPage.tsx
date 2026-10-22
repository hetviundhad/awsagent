import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  Clock, ArrowLeft, ArrowRight, Bookmark, 
  AlertTriangle, ShieldCheck, ShieldAlert, Send, Lock, Maximize2 
} from 'lucide-react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Assessment, Question } from '../types';
import { Button } from '../components/ui';

export const QuizPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { refreshProfile } = useAuth();
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [selectedAnswers, setSelectedAnswers] = useState<Record<string, string>>({});
  const [markedForReview, setMarkedForReview] = useState<Record<string, boolean>>({});
  const [timeLeft, setTimeLeft] = useState(900); // 15 mins
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(true);

  // Security & Proctoring State
  const [isSecureStarted, setIsSecureStarted] = useState(false);
  const [copyWarning, setCopyWarning] = useState<string | null>(null);
  const [violationAlert, setViolationAlert] = useState<string | null>(null);
  const hasAutoSubmittedRef = useRef(false);
  const warningTimerRef = useRef<any>(null);

  useEffect(() => {
    if (id) {
      loadAssessment(id);
    }
  }, [id]);

  useEffect(() => {
    if (!isSecureStarted) return;
    const timer = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          handleSubmit();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [isSecureStarted]);

  // Security Proctoring Listeners: Tab-switch, window blur, exit fullscreen
  useEffect(() => {
    if (!isSecureStarted || submitting || hasAutoSubmittedRef.current) return;

    const triggerSecurityAutoSubmit = (reason: string) => {
      if (hasAutoSubmittedRef.current) return;
      hasAutoSubmittedRef.current = true;
      setViolationAlert(reason);
      setSubmitting(true);

      if (assessment) {
        const timeSpent = (assessment.time_limit_minutes * 60) - timeLeft;
        api.submitAssessment(assessment.id, selectedAnswers, timeSpent, true, reason)
          .then(() => refreshProfile())
          .catch(() => {})
          .finally(() => {
            setTimeout(() => {
              navigate(`/assessments/${assessment.id}/report`);
            }, 2500);
          });
      }
    };

    const handleVisibilityChange = () => {
      if (document.hidden) {
        triggerSecurityAutoSubmit("Tab switch or minimization detected. The proctored exam was left unattended.");
      }
    };

    const handleWindowBlur = () => {
      triggerSecurityAutoSubmit("Focus lost: You navigated away from the proctored assessment window.");
    };

    const handleFullscreenChange = () => {
      if (!document.fullscreenElement) {
        triggerSecurityAutoSubmit("Fullscreen mode was exited. Proctored exams must remain in fullscreen.");
      }
    };

    const handleCopyCutPaste = (e: ClipboardEvent) => {
      e.preventDefault();
      triggerCopyWarning("Clipboard operations (Copy, Cut, Paste) are disabled during this assessment.");
    };

    const handleContextMenu = (e: MouseEvent) => {
      e.preventDefault();
      triggerCopyWarning("Right-click context menu is disabled in the secure examination environment.");
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      const isCopyCombo = (e.ctrlKey || e.metaKey) && ['c', 'v', 'x', 'a', 'p', 'u', 's'].includes(e.key.toLowerCase());
      const isDevTools = e.key === 'F12' || ((e.ctrlKey || e.metaKey) && e.shiftKey && ['i', 'j', 'c'].includes(e.key.toLowerCase()));
      const isAltTab = e.altKey && e.key === 'Tab';

      if (isCopyCombo || isDevTools || isAltTab) {
        e.preventDefault();
        e.stopPropagation();
        triggerCopyWarning("Keyboard shortcuts and screen capture/copying are blocked during the assessment.");
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('blur', handleWindowBlur);
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    document.addEventListener('copy', handleCopyCutPaste);
    document.addEventListener('cut', handleCopyCutPaste);
    document.addEventListener('paste', handleCopyCutPaste);
    document.addEventListener('contextmenu', handleContextMenu);
    window.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('blur', handleWindowBlur);
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
      document.removeEventListener('copy', handleCopyCutPaste);
      document.removeEventListener('cut', handleCopyCutPaste);
      document.removeEventListener('paste', handleCopyCutPaste);
      document.removeEventListener('contextmenu', handleContextMenu);
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isSecureStarted, assessment, selectedAnswers, timeLeft, submitting]);

  const triggerCopyWarning = (msg: string) => {
    setCopyWarning(msg);
    if (warningTimerRef.current) clearTimeout(warningTimerRef.current);
    warningTimerRef.current = setTimeout(() => {
      setCopyWarning(null);
    }, 3000);
  };

  const startSecureExam = async () => {
    try {
      if (document.documentElement.requestFullscreen) {
        await document.documentElement.requestFullscreen();
      }
    } catch (err) {
      console.warn("Fullscreen permission denied or not supported; continuing secure mode.");
    }
    setIsSecureStarted(true);
  };

  const loadAssessment = async (assessmentId: string) => {
    try {
      const data = await api.getAssessment(assessmentId);
      setAssessment(data);
      setTimeLeft(data.time_limit_minutes * 60);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectOption = (questionId: string, option: string) => {
    if (submitting || violationAlert) return;
    setSelectedAnswers((prev) => ({
      ...prev,
      [questionId]: option,
    }));
  };

  const toggleReview = (questionId: string) => {
    setMarkedForReview((prev) => ({
      ...prev,
      [questionId]: !prev[questionId],
    }));
  };

  const handleSubmit = async () => {
    if (!assessment || submitting) return;
    setSubmitting(true);
    hasAutoSubmittedRef.current = true;
    try {
      const timeSpent = (assessment.time_limit_minutes * 60) - timeLeft;
      await api.submitAssessment(assessment.id, selectedAnswers, timeSpent);
      await refreshProfile();
      if (document.fullscreenElement) {
        document.exitFullscreen().catch(() => {});
      }
      navigate(`/assessments/${assessment.id}/report`);
    } catch (e) {
      alert('Error submitting assessment');
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center bg-paper-canvas text-ink-500 font-serif text-xs">
        Loading secure exam environment...
      </div>
    );
  }

  if (!assessment || !assessment.questions || assessment.questions.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center bg-paper-canvas text-ink-500 font-serif text-xs">
        Assessment questions not found.
      </div>
    );
  }

  const currentQ: Question = assessment.questions[currentIndex];
  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <div 
      className="flex-1 flex flex-col h-full bg-paper-canvas overflow-hidden select-none"
      style={{ userSelect: 'none', WebkitUserSelect: 'none' }}
    >
      {/* Pre-Exam Lockdown Modal (Fullscreen Requirement) */}
      {!isSecureStarted && (
        <div className="fixed inset-0 z-50 bg-ink-950/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="max-w-lg w-full bg-white border border-paper-hairline rounded-2xl p-6 sm:p-8 space-y-6 shadow-paper-lg text-center">
            <div className="h-16 w-16 mx-auto rounded-2xl bg-paper-surface border border-paper-hairline flex items-center justify-center text-ink-900 shadow-paper-sm">
              <Lock className="h-8 w-8 text-royal-700" />
            </div>

            <div className="space-y-1">
              <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-status-refused bg-red-50 px-2 py-0.5 rounded border border-red-200">
                PROCTORED SAFE MODE
              </span>
              <h2 className="font-serif text-xl font-bold text-ink-900 tracking-tight mt-1">
                Exam Lockdown & Integrity Guardrails
              </h2>
              <p className="font-serif text-xs text-ink-600 leading-relaxed">
                This diagnostic assessment enforces automated proctoring rules to protect Bayesian calibration integrity.
              </p>
            </div>

            <div className="p-4 rounded-xl bg-paper-surface border border-paper-hairline text-left space-y-3 text-xs font-serif">
              <div className="flex items-start space-x-2.5">
                <Maximize2 className="h-4 w-4 text-royal-700 shrink-0 mt-0.5" />
                <span className="text-ink-700">
                  <strong className="text-ink-900 font-sans">Fullscreen Lock:</strong> You must maintain fullscreen mode throughout the examination.
                </span>
              </div>
              <div className="flex items-start space-x-2.5">
                <ShieldCheck className="h-4 w-4 text-emerald-700 shrink-0 mt-0.5" />
                <span className="text-ink-700">
                  <strong className="text-ink-900 font-sans">Anti-Copy Active:</strong> Text selection, copying, and right-click menus are disabled.
                </span>
              </div>
              <div className="flex items-start space-x-2.5">
                <AlertTriangle className="h-4 w-4 text-status-refused shrink-0 mt-0.5" />
                <span className="text-ink-700">
                  <strong className="text-status-refused font-sans">Auto-Submit Guard:</strong> Navigating away or minimizing the window will trigger an immediate auto-submission.
                </span>
              </div>
            </div>

            <Button
              variant="primary"
              onClick={startSecureExam}
              className="w-full justify-center py-3 text-sm"
            >
              <ShieldCheck className="h-4 w-4" />
              <span>Enter Fullscreen & Begin Assessment</span>
            </Button>
          </div>
        </div>
      )}

      {/* Security Violation Auto-Submit Overlay */}
      {violationAlert && (
        <div className="fixed inset-0 z-50 bg-ink-950/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="max-w-md w-full bg-white border-2 border-red-500 rounded-2xl p-6 space-y-4 text-center shadow-paper-lg">
            <div className="h-14 w-14 mx-auto rounded-full bg-red-100 text-red-600 flex items-center justify-center animate-bounce">
              <ShieldAlert className="h-8 w-8" />
            </div>
            <div className="space-y-1">
              <h2 className="font-mono text-sm font-bold text-red-700 uppercase tracking-wider">
                Proctoring Rule Activated
              </h2>
              <p className="font-serif text-xs text-ink-900 font-medium">
                {violationAlert}
              </p>
              <p className="font-serif text-[11px] text-ink-500 pt-1">
                Assessment has been automatically submitted. Redirecting to diagnostic report...
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Floating Copy Warning Toast */}
      {copyWarning && (
        <div className="fixed top-16 left-1/2 -translate-x-1/2 z-40 px-4 py-2 rounded-xl bg-ink-900 text-white font-mono font-bold text-xs shadow-paper-lg flex items-center space-x-2 animate-bounce border border-white/20">
          <ShieldAlert className="h-4 w-4 text-highlighter-base" />
          <span>{copyWarning}</span>
        </div>
      )}

      {/* Top Exam Header with Security Badges */}
      <div className="px-6 py-3 border-b border-paper-hairline bg-white flex items-center justify-between shrink-0 shadow-paper-sm">
        <div className="space-y-0.5">
          <div className="flex items-center space-x-2">
            <span className="font-serif text-sm font-bold text-ink-900">
              {assessment.title}
            </span>
            <span className="font-mono text-[10px] font-bold px-2 py-0.5 rounded bg-red-50 text-red-700 border border-red-200">
              SAFE MODE PROCTORED
            </span>
          </div>
          <div className="font-mono text-[11px] text-ink-500">
            Question {currentIndex + 1} of {assessment.questions.length}
          </div>
        </div>

        {/* Timer & Submit */}
        <div className="flex items-center space-x-3 font-mono">
          <div className="flex items-center space-x-2 px-3 py-1 rounded-lg bg-paper-surface border border-paper-hairline text-xs font-bold">
            <Clock className="h-4 w-4 text-royal-700" />
            <span className={timeLeft < 180 ? 'text-red-600 animate-pulse' : 'text-ink-900'}>
              {formatTime(timeLeft)}
            </span>
          </div>

          <Button
            variant="primary"
            onClick={handleSubmit}
            disabled={submitting}
            className="px-4 py-1.5 text-xs"
          >
            <Send className="h-3.5 w-3.5" />
            <span>{submitting ? 'Submitting...' : 'Submit Exam'}</span>
          </Button>
        </div>
      </div>

      {/* Main Question Interface */}
      <div className="flex-1 p-6 overflow-y-auto max-w-4xl w-full mx-auto space-y-6">
        {/* Meta badges */}
        <div className="flex items-center justify-between font-mono">
          <div className="flex items-center space-x-2">
            <span className="text-[11px] px-2 py-0.5 rounded bg-paper-surface text-ink-700 border border-paper-hairline">
              Difficulty: {currentQ.difficulty}
            </span>
            <span className="text-[11px] px-2 py-0.5 rounded bg-highlighter-soft text-ink-900 border border-ink-900/10">
              Source: {currentQ.source_document} ({currentQ.source_location})
            </span>
          </div>

          <button
            onClick={() => toggleReview(currentQ.id)}
            className={`flex items-center space-x-1 text-xs px-2.5 py-1 rounded-lg border transition ${
              markedForReview[currentQ.id]
                ? 'bg-amber-50 text-amber-900 border-amber-300 font-bold'
                : 'bg-white text-ink-600 border-paper-hairline hover:text-ink-900'
            }`}
          >
            <Bookmark className="h-3.5 w-3.5" />
            <span>{markedForReview[currentQ.id] ? 'Marked for Review' : 'Mark for Review'}</span>
          </button>
        </div>

        {/* Question Text Card */}
        <div className="p-6 sm:p-8 rounded-2xl bg-white border border-paper-hairline shadow-paper space-y-2">
          <div className="font-mono text-[10px] font-bold text-royal-700 uppercase tracking-wider">
            Item {currentIndex + 1}
          </div>
          <h2 className="font-serif text-lg sm:text-xl font-bold text-ink-900 leading-snug">
            {currentQ.question_text || (currentQ as any).question || (currentQ as any).stem || (currentQ as any).prompt || 'Assessment Question'}
          </h2>
        </div>

        {/* Options */}
        <div className="space-y-3 font-serif">
          {currentQ.options && currentQ.options.length > 0 ? (
            currentQ.options.map((option, idx) => {
              const letter = String.fromCharCode(65 + idx);
              const isSelected = selectedAnswers[currentQ.id] === option;

              return (
                <div
                  key={idx}
                  onClick={() => handleSelectOption(currentQ.id, option)}
                  className={`p-4 rounded-xl border text-xs sm:text-sm cursor-pointer transition flex items-start space-x-3.5 shadow-2xs ${
                    isSelected
                      ? 'bg-paper-surface border-2 border-royal-700 text-ink-900 font-semibold shadow-paper'
                      : 'bg-white border-paper-hairline text-ink-800 hover:border-ink-900/30 hover:bg-paper-surface'
                  }`}
                >
                  <div
                    className={`h-6 w-6 rounded-lg font-mono flex items-center justify-center text-xs font-bold shrink-0 transition-colors ${
                      isSelected
                        ? 'bg-royal-700 text-white'
                        : 'bg-paper-surface border border-paper-hairline text-ink-600'
                    }`}
                  >
                    {letter}
                  </div>
                  <div className="pt-0.5 leading-relaxed">{option}</div>
                </div>
              );
            })
          ) : (
            <div className="space-y-2">
              <label className="text-xs font-mono text-ink-600">Type exact response:</label>
              <input
                type="text"
                value={selectedAnswers[currentQ.id] || ''}
                onChange={(e) => handleSelectOption(currentQ.id, e.target.value)}
                placeholder="Enter exact numerical or conceptual term..."
                className="w-full px-4 py-3 rounded-xl bg-white border border-paper-hairline text-ink-900 text-sm font-serif focus:outline-none focus:ring-1 focus:ring-royal-700"
              />
            </div>
          )}
        </div>
      </div>

      {/* Bottom Navigation & Question Palette */}
      <div className="p-4 border-t border-paper-hairline bg-white shrink-0 shadow-paper-sm font-mono">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <button
            onClick={() => setCurrentIndex((prev) => Math.max(0, prev - 1))}
            disabled={currentIndex === 0}
            className="px-4 py-2 rounded-xl bg-paper-surface hover:bg-paper-canvas disabled:opacity-40 text-ink-700 text-xs font-semibold flex items-center space-x-1.5 border border-paper-hairline transition"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>Previous</span>
          </button>

          {/* Palette */}
          <div className="flex items-center space-x-1.5 overflow-x-auto">
            {assessment.questions.map((q, idx) => {
              const isAnswered = Boolean(selectedAnswers[q.id]);
              const isMarked = Boolean(markedForReview[q.id]);
              const isCurrent = idx === currentIndex;

              return (
                <button
                  key={idx}
                  onClick={() => setCurrentIndex(idx)}
                  className={`h-7 w-7 rounded-lg text-xs font-bold transition flex items-center justify-center ${
                    isCurrent
                      ? 'bg-royal-700 text-white'
                      : isMarked
                      ? 'bg-amber-50 text-amber-900 border border-amber-300'
                      : isAnswered
                      ? 'bg-emerald-50 text-emerald-900 border border-emerald-300'
                      : 'bg-paper-surface text-ink-600 border border-paper-hairline'
                  }`}
                >
                  {idx + 1}
                </button>
              );
            })}
          </div>

          <Button
            variant="primary"
            onClick={() => setCurrentIndex((prev) => Math.min(assessment.questions.length - 1, prev + 1))}
            disabled={currentIndex === assessment.questions.length - 1}
            className="px-4 py-2 text-xs"
          >
            <span>Next</span>
            <ArrowRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
};
