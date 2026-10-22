import React from 'react';
import { ArrowRight, Sparkles, BookOpen, Layers } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface ContinueLearningCardProps {
  weakestConcept?: { name: string; mastery_probability: number } | null;
  onTargetedQuiz: (conceptName: string) => void;
  onAskTutor: (conceptName: string) => void;
}

export const ContinueLearningCard: React.FC<ContinueLearningCardProps> = ({
  weakestConcept,
  onTargetedQuiz,
  onAskTutor,
}) => {
  const navigate = useNavigate();

  if (!weakestConcept) {
    return (
      <div className="bg-white rounded-3xl p-5 border border-slate-200 shadow-xs flex items-center justify-between gap-4">
        <div>
          <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400 block mb-1">
            CONTINUE LEARNING
          </span>
          <h3 className="text-sm font-bold text-slate-800">Ready to test your knowledge</h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Take a diagnostic quiz to calibrate your personalized mastery curve.
          </p>
        </div>
        <button
          onClick={() => navigate('/assessments')}
          className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs transition shadow-xs shrink-0 flex items-center gap-1.5 cursor-pointer"
        >
          <span>Start Diagnostic</span>
          <ArrowRight className="h-3.5 w-3.5" />
        </button>
      </div>
    );
  }

  const pMastery = Math.round(weakestConcept.mastery_probability * 100);

  return (
    <div className="bg-gradient-to-r from-blue-50/70 via-indigo-50/40 to-white rounded-3xl p-5 sm:p-6 border border-blue-200 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-blue-700 bg-white px-2 py-0.5 rounded border border-blue-200">
            Recommended Next Step
          </span>
          <span className="text-[10px] font-mono text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200 font-bold">
            {pMastery}% Mastery
          </span>
        </div>
        <h3 className="text-base font-bold text-slate-900">
          Strengthen concept: <span className="text-blue-700">{weakestConcept.name}</span>
        </h3>
        <p className="text-xs text-slate-600">
          Targeted practice on this concept will yield the highest knowledge gain.
        </p>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        <button
          onClick={() => onAskTutor(weakestConcept.name)}
          className="px-3.5 py-2 rounded-xl border border-blue-200 bg-white hover:bg-blue-50 text-blue-800 font-bold text-xs transition cursor-pointer"
        >
          Ask Tutor
        </button>
        <button
          onClick={() => onTargetedQuiz(weakestConcept.name)}
          className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs transition shadow-xs flex items-center gap-1.5 cursor-pointer"
        >
          <span>Practice Concept</span>
          <ArrowRight className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
};
