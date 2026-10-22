import React, { useState } from 'react';
import { Layers, ChevronRight, ChevronDown, CheckCircle2, AlertCircle } from 'lucide-react';

export interface PrereqConcept {
  id: string;
  name: string;
  mastery_probability?: number;
  prerequisites?: string[];
}

interface PrerequisitePanelProps {
  concepts: PrereqConcept[];
  onSelectConcept?: (conceptName: string) => void;
}

export const PrerequisitePanel: React.FC<PrerequisitePanelProps> = ({
  concepts,
  onSelectConcept,
}) => {
  const [isOpen, setIsOpen] = useState(false);

  if (!concepts || concepts.length === 0) return null;

  return (
    <div className="border border-slate-200 rounded-2xl bg-white overflow-hidden shadow-xs">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full p-3 flex items-center justify-between text-xs font-bold text-slate-700 bg-slate-50/70 hover:bg-slate-100 transition cursor-pointer"
      >
        <div className="flex items-center gap-2">
          <Layers className="h-3.5 w-3.5 text-blue-600" />
          <span>Prerequisites & Mastery ({concepts.length})</span>
        </div>
        {isOpen ? <ChevronDown className="h-3.5 w-3.5 text-slate-400" /> : <ChevronRight className="h-3.5 w-3.5 text-slate-400" />}
      </button>

      {isOpen && (
        <div className="p-3 divide-y divide-slate-100 max-h-56 overflow-y-auto space-y-1 text-xs">
          {concepts.map((concept) => {
            const mastery = concept.mastery_probability !== undefined 
              ? Math.round(concept.mastery_probability * 100) 
              : null;
            const isHigh = mastery !== null && mastery >= 70;
            const isMedium = mastery !== null && mastery >= 40 && mastery < 70;

            return (
              <div 
                key={concept.id}
                onClick={() => onSelectConcept && onSelectConcept(concept.name)}
                className="py-2 flex items-center justify-between hover:bg-slate-50 px-2 rounded-lg cursor-pointer transition"
              >
                <div className="min-w-0 pr-2">
                  <div className="font-semibold text-slate-800 truncate">{concept.name}</div>
                  {concept.prerequisites && concept.prerequisites.length > 0 && (
                    <div className="text-[10px] text-slate-400 truncate">
                      Requires: {concept.prerequisites.join(', ')}
                    </div>
                  )}
                </div>

                <div className="shrink-0 text-right">
                  {mastery !== null ? (
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-bold ${
                      isHigh 
                        ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                        : isMedium
                          ? 'bg-amber-50 text-amber-700 border border-amber-200'
                          : 'bg-slate-100 text-slate-600'
                    }`}>
                      {mastery}% BKT
                    </span>
                  ) : (
                    <span className="text-[10px] font-mono text-slate-400">Not assessed</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
