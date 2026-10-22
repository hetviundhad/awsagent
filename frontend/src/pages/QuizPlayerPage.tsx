import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { 
  ArrowLeft, Check, X, Shield, Clock, 
  Sparkles, CheckCircle2, XCircle, BookOpen, 
  ExternalLink, Award, TrendingUp, AlertTriangle, AlertCircle, Layers, ChevronRight
} from 'lucide-react';
import { Button, Card, Pill } from '../components/ui';
import { api } from '../services/api';

interface QuestionItem {
  id: string;
  stem?: string;
  question?: string;
  options: string[];
  correct_answer?: string;
  correct_index?: number;
  correct?: number;
  explanation: string;
  supporting_quote?: string;
  source_doc_name?: string;
  source_page_slide_label?: string;
  concept_name?: string;
  difficulty?: string;
  chunk_id?: string;
}

export const QuizPlayerPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const stateData = (location.state as any) || {};
  const queryParams = new URLSearchParams(location.search);
  const assessmentId = stateData.id || queryParams.get('id') || '';
  const [assessmentData, setAssessmentData] = useState<any>(stateData);
  const [loadingQuiz, setLoadingQuiz] = useState<boolean>(false);

  useEffect(() => {
    if ((!assessmentData?.questions || assessmentData.questions.length === 0) && assessmentId) {
      setLoadingQuiz(true);
      api.getAssessment(assessmentId)
        .then((res) => {
          if (res) setAssessmentData(res);
        })
        .catch((e) => console.error("Error loading quiz:", e))
        .finally(() => setLoadingQuiz(false));
    }
  }, [assessmentId]);

  const quizTitle = assessmentData?.title || 'Adaptive Knowledge Assessment';
  const rawQuestions: any[] = (assessmentData?.questions && assessmentData.questions.length > 0)
    ? assessmentData.questions
    : [];

  // Normalize questions
  const questions: QuestionItem[] = rawQuestions.map((q, idx) => {
    let rawOptions: string[] = [];
    if (Array.isArray(q.options)) {
      rawOptions = q.options.map((opt: any) => typeof opt === 'string' ? opt : (opt?.text || opt?.label || String(opt)));
    }

    let correctIdx = 0;
    if (typeof q.correct === 'number') correctIdx = q.correct;
    else if (typeof q.correct_index === 'number') correctIdx = q.correct_index;
    else if (q.correct_answer && rawOptions.length > 0) {
      const ca = String(q.correct_answer).trim().toLowerCase();
      let found = rawOptions.findIndex((opt: string) => opt.trim().toLowerCase() === ca);
      if (found < 0 && ['a', 'b', 'c', 'd'].includes(ca)) {
        found = ['a', 'b', 'c', 'd'].indexOf(ca);
      }
      if (found < 0) {
        found = rawOptions.findIndex((opt: string) => 
          opt.toLowerCase().startsWith(ca + ')') ||
          opt.toLowerCase().startsWith(ca + '.')
        );
      }
      if (found >= 0 && found < rawOptions.length) correctIdx = found;
    }

    const questionTitle = q.question_text || q.stem || q.question || q.prompt || `Practice Item ${idx + 1}`;

    return {
      id: q.id || `q_${idx}`,
      question: questionTitle,
      options: rawOptions,
      correct: correctIdx,
      correct_answer: q.correct_answer || (rawOptions.length > 0 ? rawOptions[correctIdx] : ''),
      explanation: q.explanation || 'Verified from course reading material.',
      supporting_quote: q.supporting_quote || '',
      source_doc_name: q.source_doc_name || q.source_doc || '',
      source_page_slide_label: q.source_page_slide_label || q.location || '',
      concept_name: q.concept_name || q.topic || '',
      difficulty: q.difficulty || 'Intermediate',
      chunk_id: q.chunk_id || ''
    };
  });

  const [currentIndex, setCurrentIndex] = useState(0);
  const [selectedAnswers, setSelectedAnswers] = useState<Record<number, number>>({});
  const [selectedConfidences, setSelectedConfidences] = useState<Record<number, 'Sure' | 'Not sure' | 'Guess'>>({});
  const [timerSeconds, setTimerSeconds] = useState(0);
  const [isSourceModalOpen, setIsSourceModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [reportResult, setReportResult] = useState<any | null>(null);

  // Timer interval
  useEffect(() => {
    if (questions.length === 0 || reportResult) return;
    const interval = setInterval(() => {
      setTimerSeconds(s => s + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, [questions.length, reportResult]);

  if (loadingQuiz) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center bg-[#FAF8F5] text-[#16130F]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mb-3" />
        <p className="text-sm font-medium text-slate-600">Retrieving calibrated assessment questions...</p>
      </div>
    );
  }

  if (questions.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center bg-[#FAF8F5] text-[#16130F]">
        <div className="max-w-md space-y-4 bg-white p-8 rounded-3xl border border-[#EAE6DF] shadow-paper">
          <Shield className="h-12 w-12 text-[#1D4ED8] mx-auto opacity-80" />
          <h2 className="text-xl font-display font-bold text-[#16130F]">No Quiz Questions Selected</h2>
          <p className="text-xs text-[#5E5A52] leading-relaxed">
            Practice questions are calibrated dynamically from your uploaded documents and active course concepts.
          </p>
          <Button variant="primary" onClick={() => navigate('/dashboard')} className="w-full">
            Return to Study Desk
          </Button>
        </div>
      </div>
    );
  }

  const currentQ = questions[currentIndex] || questions[0];
  const totalQuestions = questions.length;
  const answeredCount = Object.keys(selectedAnswers).length;
  const selectedOption = selectedAnswers[currentIndex];
  const hasAnsweredCurrent = selectedOption !== undefined;
  const isCurrentCorrect = hasAnsweredCurrent && selectedOption === currentQ.correct;

  const handleSelectOption = (optIdx: number) => {
    if (hasAnsweredCurrent) return;
    setSelectedAnswers((prev) => ({
      ...prev,
      [currentIndex]: optIdx
    }));
  };

  const handlePrevious = () => {
    if (currentIndex > 0) setCurrentIndex((i) => i - 1);
  };

  const handleNext = () => {
    if (currentIndex < totalQuestions - 1) {
      setCurrentIndex((i) => i + 1);
    }
  };

  const handleFinishQuiz = async () => {
    setIsSubmitting(true);
    try {
      // Map numeric indexes to question IDs and string option values
      const submissionAnswers: Record<string, string> = {};
      const submissionConfidences: Record<string, string> = {};
      questions.forEach((q, idx) => {
        const chosenIdx = selectedAnswers[idx];
        if (chosenIdx !== undefined && q.options[chosenIdx]) {
          submissionAnswers[q.id] = q.options[chosenIdx];
          submissionConfidences[q.id] = selectedConfidences[idx] || 'Sure';
        }
      });

      if (assessmentId) {
        const res = await api.submitAssessment(assessmentId, submissionAnswers, timerSeconds, false, undefined, submissionConfidences);
        setReportResult(res);
      } else {
        // Calculate standalone score report
        let correctCount = 0;
        questions.forEach((q, idx) => {
          if (selectedAnswers[idx] === q.correct) correctCount += 1;
        });
        const scorePct = Math.round((correctCount / totalQuestions) * 100);
        setReportResult({
          score_percentage: scorePct,
          correct_count: correctCount,
          total_questions: totalQuestions,
          time_spent_seconds: timerSeconds,
          weak_concepts: questions.filter((q, idx) => selectedAnswers[idx] !== q.correct).map(q => q.concept_name).filter(Boolean),
          detected_misconceptions: []
        });
      }
    } catch (e) {
      console.warn('Quiz submit note:', e);
      // Fallback local report
      let correctCount = 0;
      questions.forEach((q, idx) => {
        if (selectedAnswers[idx] === q.correct) correctCount += 1;
      });
      setReportResult({
        score_percentage: Math.round((correctCount / totalQuestions) * 100),
        correct_count: correctCount,
        total_questions: totalQuestions,
        time_spent_seconds: timerSeconds,
        weak_concepts: []
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const progressPercent = Math.min(100, Math.max(5, ((currentIndex + 1) / totalQuestions) * 100));
  const formatTimer = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  // FINAL REPORT VIEW
  if (reportResult) {
    const accuracy = reportResult.score_pct ?? reportResult.score_percentage ?? Math.round((reportResult.correct_count / Math.max(reportResult.total_questions, 1)) * 100);
    const calib = reportResult.calibration;
    const miscProfile = reportResult.misconception_profile || [];

    return (
      <div className="flex-1 flex flex-col h-full overflow-y-auto bg-[#FAF8F5] text-slate-800 p-4 sm:p-8">
        <div className="max-w-3xl w-full mx-auto space-y-6">
          <div className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200 shadow-sm space-y-5">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-blue-600 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                  Assessment Completed
                </span>
                <h1 className="text-2xl font-bold text-slate-900 mt-1">{quizTitle}</h1>
              </div>
              <div className="text-right">
                <div className="text-3xl font-bold text-blue-600 font-mono">{accuracy}%</div>
                <div className="text-[11px] text-slate-500 font-medium">Accuracy</div>
              </div>
            </div>

            {/* Metrics */}
            <div className="grid grid-cols-3 gap-3 font-mono text-center pt-2">
              <div className="p-3 rounded-2xl bg-slate-50 border border-slate-100">
                <div className="text-lg font-bold text-slate-900">{reportResult.correct_count} / {reportResult.total_questions}</div>
                <div className="text-[10px] text-slate-500 uppercase">Correct</div>
              </div>
              <div className="p-3 rounded-2xl bg-slate-50 border border-slate-100">
                <div className="text-lg font-bold text-slate-900">{formatTimer(timerSeconds)}</div>
                <div className="text-[10px] text-slate-500 uppercase">Duration</div>
              </div>
              <div className="p-3 rounded-2xl bg-slate-50 border border-slate-100">
                <div className="text-lg font-bold text-emerald-600">Updated</div>
                <div className="text-[10px] text-slate-500 uppercase">BKT Mastery</div>
              </div>
            </div>

            {/* Part 5: Confidence Calibration Banner */}
            {calib && (
              <div className="p-4 rounded-2xl bg-blue-50/70 border border-blue-200 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <Shield className="h-4 w-4 text-blue-600" />
                    <span className="text-xs font-bold text-blue-950 font-mono">
                      Metacognitive Calibration (Brier Score: {calib.brier_score})
                    </span>
                  </div>
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-blue-100 text-blue-800 border border-blue-200">
                    {calib.rating}
                  </span>
                </div>
                <p className="text-xs text-blue-900 leading-relaxed">
                  {calib.confident_wrong_count > 0 ? (
                    <span className="text-amber-800 font-semibold">
                      Notice: You were confident and incorrect on {calib.confident_wrong_count} items. These suggest active misconceptions rather than guesses and have been weighted in your BKT model.
                    </span>
                  ) : (
                    <span>Great self-calibration! Your confidence matched your answer accuracy across submitted questions.</span>
                  )}
                </p>
              </div>
            )}

            {/* Concept / Weakness highlights */}
            {reportResult.weak_concepts && reportResult.weak_concepts.length > 0 && (
              <div className="p-4 rounded-2xl bg-amber-50/60 border border-amber-200 text-xs space-y-2">
                <div className="font-bold text-amber-900 flex items-center gap-1.5">
                  <AlertTriangle className="h-4 w-4 text-amber-600" />
                  <span>Concepts for Targeted Revision:</span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {reportResult.weak_concepts.map((concept: string, idx: number) => (
                    <span key={idx} className="px-2.5 py-0.5 rounded-full bg-white text-amber-900 font-medium border border-amber-200 text-[11px]">
                      {concept}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Part 5: Misconception Profile with Corrective Citations */}
            {miscProfile.length > 0 && (
              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-3">
                <div className="flex items-center space-x-2">
                  <AlertCircle className="h-4 w-4 text-red-600" />
                  <span className="text-xs font-bold text-slate-900 font-mono">
                    Diagnosed Misconceptions Profile ({miscProfile.length})
                  </span>
                </div>
                <div className="space-y-2.5">
                  {miscProfile.slice(0, 4).map((m: any, mIdx: number) => (
                    <div key={mIdx} className="p-3 bg-white rounded-xl border border-slate-200 text-xs space-y-1">
                      <div className="flex items-center justify-between text-[11px]">
                        <strong className="text-slate-800">{m.concept_name || 'Core Concept'}</strong>
                        {m.is_confident_wrong && (
                          <span className="text-[10px] bg-red-100 text-red-800 font-bold px-1.5 py-0.5 rounded border border-red-200">
                            Confident Error
                          </span>
                        )}
                      </div>
                      <p className="text-slate-600 italic">"{m.misconception}"</p>
                      {m.corrective_quote && (
                        <div className="pt-1 text-[11px] text-blue-800 font-sans border-t border-slate-100">
                          <strong>Course Correction:</strong> "{m.corrective_quote}"
                          {m.source_document && <span className="text-slate-500 ml-1">({m.source_document})</span>}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="pt-3 flex flex-col sm:flex-row gap-3">
              <button
                onClick={() => navigate('/dashboard')}
                className="flex-1 py-2.5 px-4 rounded-xl border border-slate-200 hover:bg-slate-50 font-bold text-xs text-slate-700 transition"
              >
                Back to Dashboard
              </button>
              <button
                onClick={() => navigate('/tutor')}
                className="flex-1 py-2.5 px-4 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs transition shadow-sm"
              >
                Ask AI Tutor About Weak Topics
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-[#FAF8F5] text-slate-800">
      {/* Top Header Bar */}
      <div className="h-14 border-b border-slate-200 px-6 flex items-center justify-between shrink-0 bg-white">
        <button
          onClick={() => navigate('/dashboard')}
          className="flex items-center space-x-1.5 text-xs font-mono font-bold text-blue-600 hover:text-blue-800 transition"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Exit to Dashboard</span>
        </button>

        <div className="flex items-center space-x-3">
          <div className="flex items-center gap-1.5 text-xs font-mono text-slate-600 bg-slate-100 px-2.5 py-1 rounded-lg">
            <Clock className="h-3.5 w-3.5 text-slate-500" />
            <span>{formatTimer(timerSeconds)}</span>
          </div>
          <span className="font-mono text-[10px] px-2.5 py-1 rounded-lg bg-blue-50 text-blue-700 font-bold border border-blue-200">
            {currentQ.difficulty || 'Adaptive'}
          </span>
        </div>
      </div>

      {/* Main Quiz Area */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-8 flex flex-col items-center relative">
        <div className="max-w-3xl w-full space-y-5">
          {/* Quiz Title & Header */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="font-mono text-[10px] font-bold text-blue-600 uppercase tracking-wider">
                Course Verified Assessment
              </span>
              <span className="text-xs font-mono text-slate-500">
                {answeredCount} of {totalQuestions} answered
              </span>
            </div>
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900">
              {quizTitle}
            </h1>
          </div>

          {/* Progress Bar */}
          <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden">
            <div
              className="bg-blue-600 h-full rounded-full transition-all duration-300"
              style={{ width: `${progressPercent}%` }}
            />
          </div>

          {/* Question Card */}
          <div className="bg-white rounded-3xl border border-slate-200 p-6 sm:p-8 shadow-sm space-y-6">
            
            {/* Question Stem & Source Chip */}
            <div className="space-y-3">
              <div className="flex items-start justify-between gap-3">
                <span className="text-xs font-mono font-bold text-blue-700 bg-blue-50 px-2.5 py-1 rounded-lg border border-blue-200 shrink-0">
                  Q{currentIndex + 1}
                </span>

                {/* Source chip */}
                {currentQ.source_doc_name && (
                  <button
                    onClick={() => setIsSourceModalOpen(true)}
                    className="flex items-center gap-1.5 text-[11px] font-mono font-semibold text-slate-600 bg-slate-100 hover:bg-slate-200 px-2.5 py-1 rounded-lg border border-slate-200 transition cursor-pointer"
                  >
                    <BookOpen className="h-3 w-3 text-blue-600" />
                    <span className="truncate max-w-[200px]">{currentQ.source_doc_name}</span>
                    {currentQ.source_page_slide_label && (
                      <span className="text-blue-700">({currentQ.source_page_slide_label})</span>
                    )}
                  </button>
                )}
              </div>

              <h2 className="text-base sm:text-lg font-semibold text-slate-900 leading-snug">
                {currentQ.question}
              </h2>

              {currentQ.concept_name && (
                <div className="text-[11px] font-mono text-slate-500">
                  Concept: <strong className="text-slate-800">{currentQ.concept_name}</strong>
                </div>
              )}
            </div>

            {/* Metacognitive Confidence Selector */}
            <div className="p-3 bg-slate-50 border border-slate-200/80 rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
              <span className="text-xs font-mono font-medium text-slate-600">
                How confident are you in this answer?
              </span>
              <div className="flex items-center space-x-1.5">
                {(['Sure', 'Not sure', 'Guess'] as const).map((conf) => {
                  const currConf = selectedConfidences[currentIndex] || 'Sure';
                  const isConfSelected = currConf === conf;
                  let btnColor = 'bg-white text-slate-600 border-slate-200 hover:bg-slate-100';
                  if (isConfSelected) {
                    if (conf === 'Sure') btnColor = 'bg-blue-600 text-white border-blue-600 shadow-sm';
                    else if (conf === 'Not sure') btnColor = 'bg-amber-600 text-white border-amber-600 shadow-sm';
                    else btnColor = 'bg-purple-600 text-white border-purple-600 shadow-sm';
                  }
                  return (
                    <button
                      key={conf}
                      type="button"
                      disabled={hasAnsweredCurrent}
                      onClick={() => setSelectedConfidences(prev => ({ ...prev, [currentIndex]: conf }))}
                      className={`text-xs font-mono font-bold px-3 py-1.5 rounded-xl border transition ${btnColor}`}
                    >
                      {conf}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Options */}
            <div className="space-y-3">
              {currentQ.options.map((opt, optIdx) => {
                const isSelected = selectedOption === optIdx;
                const isCorrectOption = currentQ.correct === optIdx;

                let rowStyle = 'border-slate-200 hover:border-slate-300 hover:bg-slate-50';
                let radioStyle = 'border-slate-300 bg-white';

                if (hasAnsweredCurrent) {
                  if (isSelected && !isCorrectOption) {
                    rowStyle = 'border-red-300 bg-red-50/60 text-red-950';
                    radioStyle = 'border-red-500 bg-red-500';
                  } else if (isCorrectOption) {
                    rowStyle = 'border-emerald-300 bg-emerald-50/70 text-emerald-950 font-medium';
                    radioStyle = 'border-emerald-500 bg-emerald-500';
                  } else {
                    rowStyle = 'border-slate-200 opacity-60';
                  }
                }

                return (
                  <div
                    key={optIdx}
                    onClick={() => handleSelectOption(optIdx)}
                    className={`flex items-center space-x-3.5 p-3.5 rounded-2xl border text-xs sm:text-sm transition cursor-pointer select-none ${rowStyle}`}
                  >
                    <div
                      className={`h-4 w-4 rounded-full border flex items-center justify-center shrink-0 transition ${radioStyle}`}
                    >
                      {isSelected && (
                        <div className="h-2 w-2 rounded-full bg-white" />
                      )}
                    </div>
                    <span className="flex-1 leading-relaxed">{opt}</span>
                  </div>
                );
              })}
            </div>

            {/* Immediate Cited Feedback */}
            {hasAnsweredCurrent && (
              <div
                className={`p-4 rounded-2xl border text-xs leading-relaxed space-y-2 transition-all ${
                  isCurrentCorrect
                    ? 'bg-emerald-50/90 border-emerald-300 text-emerald-950'
                    : 'bg-red-50/90 border-red-300 text-red-950'
                }`}
              >
                <div className="flex items-center space-x-2 font-mono font-bold">
                  {isCurrentCorrect ? (
                    <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full bg-emerald-700 text-white text-[11px]">
                      ✓ Correct Answer
                    </span>
                  ) : (
                    <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full bg-red-700 text-white text-[11px]">
                      ✗ Incorrect Answer
                    </span>
                  )}
                </div>
                
                <p className="text-slate-800 text-xs sm:text-[13px] pt-1">
                  {currentQ.explanation}
                </p>

                {currentQ.supporting_quote && (
                  <div className="mt-2 pt-2 border-t border-slate-200/60 text-[11px] font-sans text-slate-600 bg-white/70 p-2.5 rounded-xl">
                    <span className="font-bold text-slate-800 block mb-0.5">Course Evidence:</span>
                    <em>"{currentQ.supporting_quote}"</em>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Navigation Buttons */}
          <div className="flex items-center justify-between pt-2">
            <button
              onClick={handlePrevious}
              disabled={currentIndex === 0}
              className="px-5 py-2.5 rounded-xl border border-slate-200 bg-white text-slate-700 text-xs font-semibold hover:bg-slate-50 disabled:opacity-40 transition cursor-pointer"
            >
              Previous
            </button>

            {currentIndex === totalQuestions - 1 ? (
              <button
                onClick={handleFinishQuiz}
                disabled={isSubmitting}
                className="px-6 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold transition shadow-sm cursor-pointer disabled:opacity-50"
              >
                {isSubmitting ? 'Evaluating & Updating BKT...' : 'Finish & View Diagnostic Report'}
              </button>
            ) : (
              <button
                onClick={handleNext}
                className="px-6 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold transition shadow-sm cursor-pointer"
              >
                Next
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Source Citation Modal */}
      {isSourceModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-lg w-full p-6 space-y-4 shadow-xl border border-slate-200">
            <div className="flex items-center justify-between">
              <div className="font-bold text-sm text-slate-900 flex items-center gap-2">
                <BookOpen className="h-4 w-4 text-blue-600" />
                <span>Verified Source Material</span>
              </div>
              <button
                onClick={() => setIsSourceModalOpen(false)}
                className="p-1 rounded-full text-slate-400 hover:text-slate-700"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="space-y-2 text-xs">
              <div className="font-medium text-slate-800">
                Document: <span className="font-semibold">{currentQ.source_doc_name || 'Course Unit'}</span>
              </div>
              {currentQ.source_page_slide_label && (
                <div className="text-slate-600">
                  Location: <span className="font-mono">{currentQ.source_page_slide_label}</span>
                </div>
              )}
              {currentQ.supporting_quote && (
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-slate-700 mt-2">
                  <span className="font-bold text-[10px] uppercase text-slate-500 block mb-1">Supporting Excerpt</span>
                  <em>"{currentQ.supporting_quote}"</em>
                </div>
              )}
            </div>

            <div className="pt-2 flex justify-end">
              <button
                onClick={() => setIsSourceModalOpen(false)}
                className="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 font-semibold text-xs text-slate-800"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
