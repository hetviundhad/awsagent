import React from 'react';
import { LineChart, CheckCircle2, TrendingUp, AlertCircle } from 'lucide-react';
import { LearnerProfile } from '../../types';

interface MasterySummaryCardProps {
  profile: LearnerProfile | null;
  totalConcepts: number;
}

export const MasterySummaryCard: React.FC<MasterySummaryCardProps> = ({
  profile,
  totalConcepts,
}) => {
  const overallMastery = profile?.overall_mastery !== undefined 
    ? Math.round(profile.overall_mastery * 100) 
    : 0;

  const conceptStates = profile?.concept_states || {};
  const conceptKeys = Object.keys(conceptStates);
  
  const masteredCount = conceptKeys.filter(k => (conceptStates[k].mastery_probability || 0) >= 0.7).length;
  const inProgressCount = conceptKeys.filter(k => {
    const p = conceptStates[k].mastery_probability || 0;
    return p >= 0.3 && p < 0.7;
  }).length;
  const unassessedCount = Math.max(0, totalConcepts - conceptKeys.length);

  return (
    <div className="bg-white rounded-3xl p-5 sm:p-6 border border-slate-200 shadow-xs space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400 block mb-0.5">
            Knowledge Tracing
          </span>
          <h2 className="text-base font-bold text-slate-900">Mastery Summary</h2>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold font-mono text-blue-600">{overallMastery}%</div>
          <div className="text-[10px] text-slate-400 font-mono">Overall Mastery</div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden flex">
        <div 
          className="bg-emerald-500 h-full transition-all duration-300" 
          style={{ width: `${(masteredCount / Math.max(totalConcepts, 1)) * 100}%` }}
          title="Mastered"
        />
        <div 
          className="bg-amber-400 h-full transition-all duration-300" 
          style={{ width: `${(inProgressCount / Math.max(totalConcepts, 1)) * 100}%` }}
          title="In Progress"
        />
      </div>

      {/* Stats Breakdown */}
      <div className="grid grid-cols-3 gap-2 text-center text-xs font-mono pt-1">
        <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100">
          <div className="text-base font-bold text-emerald-700">{masteredCount}</div>
          <div className="text-[10px] text-slate-500 uppercase">Mastered</div>
        </div>
        <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100">
          <div className="text-base font-bold text-amber-700">{inProgressCount}</div>
          <div className="text-[10px] text-slate-500 uppercase">Practicing</div>
        </div>
        <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100">
          <div className="text-base font-bold text-slate-700">{unassessedCount}</div>
          <div className="text-[10px] text-slate-500 uppercase">To Start</div>
        </div>
      </div>
    </div>
  );
};
