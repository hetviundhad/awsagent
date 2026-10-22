import React from 'react';
import { Layers, Clock, ArrowRight, CheckCircle2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface DueReviewsCardProps {
  dueCount: number;
  onStartReview: () => void;
}

export const DueReviewsCard: React.FC<DueReviewsCardProps> = ({
  dueCount,
  onStartReview,
}) => {
  const navigate = useNavigate();

  return (
    <div className="bg-white rounded-3xl p-5 sm:p-6 border border-slate-200 shadow-xs space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400 block mb-0.5">
            Spaced Repetition
          </span>
          <h2 className="text-base font-bold text-slate-900">Due Reviews</h2>
        </div>
        <div className="h-8 w-8 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center">
          <Clock className="h-4 w-4" />
        </div>
      </div>

      {dueCount > 0 ? (
        <div className="space-y-3">
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-slate-900">{dueCount}</span>
            <span className="text-xs text-slate-500">flashcards scheduled for review today</span>
          </div>
          <button
            onClick={onStartReview}
            className="w-full py-2.5 px-4 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs transition shadow-xs flex items-center justify-center gap-1.5 cursor-pointer"
          >
            <span>Review Flashcards Now</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-emerald-700 text-xs font-semibold">
            <CheckCircle2 className="h-4 w-4" />
            <span>All caught up for today!</span>
          </div>
          <p className="text-xs text-slate-500">
            No cards are due right now. Keep your memory sharp with a self-paced quiz.
          </p>
          <button
            onClick={() => navigate('/revision')}
            className="w-full py-2 px-3 rounded-xl border border-slate-200 hover:bg-slate-50 text-slate-700 font-bold text-xs transition flex items-center justify-center gap-1.5 cursor-pointer"
          >
            <span>Browse Revision Decks</span>
          </button>
        </div>
      )}
    </div>
  );
};
