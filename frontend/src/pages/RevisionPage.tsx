import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layers, Sparkles, BookOpen, AlertTriangle, RefreshCw, CheckCircle, ArrowRight } from 'lucide-react';
import { api } from '../services/api';
import { Button, Card, Pill } from '../components/ui';

interface RevisionPageProps {
  activeCourseId: string;
  studentId?: string;
}

export const RevisionPage: React.FC<RevisionPageProps> = ({ 
  activeCourseId, 
  studentId = 'default_student' 
}) => {
  const navigate = useNavigate();
  const [revision, setRevision] = useState<any>(null);
  const [flippedCards, setFlippedCards] = useState<Record<number, boolean>>({});
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [courseDetail, setCourseDetail] = useState<any>(null);

  const effectiveCourseId = activeCourseId || localStorage.getItem('studymind_active_course') || '';

  useEffect(() => {
    loadRevision();
  }, [effectiveCourseId]);

  const loadRevision = async () => {
    setLoading(true);
    try {
      let targetId = effectiveCourseId;
      if (!targetId) {
        const cList = await api.getCourses().catch(() => []);
        if (cList && cList.length > 0) {
          targetId = cList[0].id;
          localStorage.setItem('studymind_active_course', targetId);
        }
      }

      if (targetId) {
        const [revData, cData] = await Promise.all([
          api.getRevision(targetId, studentId).catch(() => null),
          api.getCourse(targetId).catch(() => null),
        ]);
        setRevision(revData);
        setCourseDetail(cData);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const targetId = effectiveCourseId || activeCourseId;
      const data = await api.generateRevision(targetId, undefined, studentId);
      setRevision(data);
    } catch (e) {
      alert('Failed to generate revision pack');
    } finally {
      setGenerating(false);
    }
  };

  const toggleCard = (idx: number) => {
    setFlippedCards((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  if (loading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center bg-paper-canvas p-12 space-y-4">
        <div className="relative flex items-center justify-center">
          <div className="w-12 h-12 rounded-full border-2 border-royal-200 border-t-royal-600 animate-spin" />
          <Layers className="w-5 h-5 text-royal-600 absolute" />
        </div>
        <div className="text-center space-y-1">
          <p className="font-serif text-sm font-semibold text-ink-800">
            Compiling targeted revision pack and formula cheat sheets...
          </p>
          <p className="text-xs text-ink-500 font-mono">
            Indexing key definitions, common misconceptions, and flashcard decks
          </p>
        </div>
      </div>
    );
  }

  const docCount = courseDetail?.documents?.length || 0;
  const conceptCount = courseDetail?.concepts?.length || 0;

  if (!revision || (!revision.flashcards && !revision.misconceptions && !revision.cheat_sheet)) {
    if (docCount > 0 || conceptCount > 0) {
      return (
        <div className="flex-1 flex flex-col items-center justify-center bg-paper-canvas p-6 text-center space-y-4">
          <div className="p-4 rounded-2xl bg-royal-50 text-royal-700 border border-royal-200">
            <Layers className="h-8 w-8" />
          </div>
          <div className="max-w-md space-y-2">
            <h2 className="font-serif text-xl font-bold text-ink-900">
              {courseDetail?.course?.name || 'Active Course'} Material Ready
            </h2>
            <p className="text-xs text-ink-600 leading-relaxed">
              We indexed {docCount} document(s) and {conceptCount} concept(s). Click below to generate your personalized revision pack, flashcards, and cheat sheet.
            </p>
          </div>
          <Button
            variant="primary"
            onClick={handleGenerate}
            disabled={generating}
            className="cursor-pointer"
          >
            <Sparkles className="h-4 w-4 mr-2" />
            <span>{generating ? 'Synthesizing...' : 'Generate Revision Pack Now'}</span>
          </Button>
        </div>
      );
    }

    return (
      <div className="flex-1 flex flex-col items-center justify-center bg-paper-canvas p-6 text-center space-y-4">
        <div className="p-4 rounded-2xl bg-amber-50 text-amber-700 border border-amber-200">
          <Layers className="h-8 w-8" />
        </div>
        <div className="max-w-md space-y-2">
          <h2 className="font-serif text-xl font-bold text-ink-900">No Course Material Processed Yet</h2>
          <p className="text-xs text-ink-600 leading-relaxed">
            Active Revision Hub generates misconception debiasing, spaced repetition cards, and formula cheat sheets directly from your uploaded course documents.
          </p>
        </div>
        <button
          onClick={() => navigate('/dashboard', { state: { openCreateCourse: true } })}
          className="px-4 py-2.5 rounded-xl bg-ink-900 text-white font-mono text-xs font-bold shadow-paper transition hover:bg-ink-800 cursor-pointer"
        >
          Create Course with Document &rarr;
        </button>
      </div>
    );
  }

  return (
    <div className="flex-1 p-6 lg:p-8 space-y-6 overflow-y-auto max-w-5xl w-full mx-auto bg-paper-canvas">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-royal-700 bg-royal-50 px-2 py-0.5 rounded border border-royal-200">
              HIGH-YIELD REVISION DESK
            </span>
            <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-highlighter-base text-ink-900 font-bold border border-ink-900/10">
              SYNTHESIS
            </span>
          </div>
          <h1 className="font-serif text-3xl font-bold text-ink-900 tracking-tight mt-1">
            {revision?.topic_name || 'Course Syllabus'} • Revision Pack
          </h1>
          <p className="font-serif text-xs text-ink-600 mt-0.5">
            Synthesized from weak concept telemetry, key formulas, common student misconceptions, and index flashcards.
          </p>
        </div>

        <Button
          variant="primary"
          onClick={handleGenerate}
          disabled={generating}
        >
          <Sparkles className="h-4 w-4" />
          <span>{generating ? 'Regenerating...' : 'Regenerate Pack'}</span>
        </Button>
      </div>

      {/* Summary briefing */}
      <div className="p-6 rounded-2xl bg-white border border-paper-hairline space-y-2 shadow-paper">
        <h3 className="font-serif text-base font-bold text-ink-900 flex items-center space-x-2">
          <BookOpen className="h-4 w-4 text-royal-700" />
          <span>Executive Conceptual Summary</span>
        </h3>
        <p className="font-serif text-xs text-ink-700 leading-relaxed pl-3 border-l-2 border-highlighter-base">
          {revision?.summary || 'No revision material yet. Generate a pack from your current weak concepts.'}
        </p>
      </div>

      {/* Key Definitions & Formulas */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Definitions */}
        <div className="p-6 rounded-2xl bg-white border border-paper-hairline space-y-4 shadow-paper">
          <h3 className="font-serif text-base font-bold text-ink-900">Essential Definitions</h3>
          <div className="space-y-3 font-serif">
            {revision?.key_definitions?.map((def: any, i: number) => (
              <div key={i} className="p-3.5 rounded-xl bg-paper-surface border border-paper-hairline text-xs space-y-1">
                <div className="font-mono font-bold text-royal-700">{def.term}</div>
                <div className="text-ink-700 leading-relaxed">{def.definition}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Formulas */}
        <div className="p-6 rounded-2xl bg-white border border-paper-hairline space-y-4 shadow-paper">
          <h3 className="font-serif text-base font-bold text-ink-900">Governing State Recurrences</h3>
          <div className="space-y-3">
            {revision?.key_formulas?.map((form: any, i: number) => (
              <div key={i} className="p-3.5 rounded-xl bg-paper-surface border border-paper-hairline text-xs space-y-1">
                <div className="font-mono text-xs text-ink-900 bg-white p-2.5 rounded-lg border border-paper-hairline shadow-2xs font-bold">
                  {form.formula}
                </div>
                <div className="text-ink-500 font-serif text-[11px] pt-1">{form.context}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Common Mistakes */}
      <div className="p-6 rounded-2xl bg-amber-50/50 border border-amber-300 space-y-4 shadow-paper">
        <h3 className="font-serif text-base font-bold text-amber-950 flex items-center space-x-2">
          <AlertTriangle className="h-4 w-4 text-amber-700" />
          <span>High-Frequency Mistakes & Misconceptions</span>
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {revision?.common_mistakes?.map((cm: any, i: number) => (
            <div key={i} className="p-4 rounded-xl bg-white border border-amber-200 text-xs space-y-2 shadow-paper-sm">
              <div className="font-mono font-bold text-status-refused">✗ {cm.mistake}</div>
              <div className="font-serif text-ink-800 leading-relaxed">
                <strong className="text-emerald-800 font-sans">Correction: </strong>
                {cm.correction}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Interactive Flashcards */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-serif text-base font-bold text-ink-900 flex items-center space-x-2">
            <Layers className="h-4 w-4 text-royal-700" />
            <span>Interactive Recall Flashcards</span>
          </h3>
          <span className="font-mono text-xs text-ink-500">Click any card to flip</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 font-serif">
          {revision?.flashcards?.map((card: any, idx: number) => {
            const isFlipped = Boolean(flippedCards[idx]);
            return (
              <div
                key={idx}
                onClick={() => toggleCard(idx)}
                className={`p-6 rounded-2xl border cursor-pointer transition-all duration-200 min-h-[170px] flex flex-col justify-between shadow-paper ${
                  isFlipped
                    ? 'bg-paper-canvas border-royal-700 text-ink-900'
                    : 'bg-white border-paper-hairline text-ink-800 hover:border-ink-900/30'
                }`}
              >
                <div className="font-mono text-[10px] uppercase font-bold text-ink-400 tracking-wider">
                  {isFlipped ? 'REVERSE • INTUITION' : 'PROMPT • CHALLENGE'}
                </div>
                <div className="text-xs sm:text-sm font-bold leading-relaxed my-auto text-center">
                  {isFlipped ? card.back : card.front}
                </div>
                <div className="font-mono text-[10px] text-right text-royal-700 font-semibold">
                  {isFlipped ? 'Click for prompt' : 'Click to flip'}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
