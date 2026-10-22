import React from 'react';
import { BookOpen } from 'lucide-react';
import { Citation } from '../../types';

interface CitationChipsProps {
  citations: Citation[];
  onSelectCitation: (citation: Citation) => void;
}

export const CitationChips: React.FC<CitationChipsProps> = ({
  citations,
  onSelectCitation,
}) => {
  if (!citations || citations.length === 0) return null;

  return (
    <div className="pt-2 flex flex-wrap items-center gap-1.5">
      <span className="text-[10px] font-mono text-slate-500 uppercase font-semibold mr-0.5">
        From your material:
      </span>
      {citations.slice(0, 3).map((cit, idx) => {
        const docLabel = cit.document_title || cit.source_document || 'Course Unit';
        const locLabel = cit.page_or_slide || (cit.page ? `p. ${cit.page}` : cit.timestamp_start ? `${Math.floor(cit.timestamp_start / 60)}m` : null);

        return (
          <button
            key={cit.chunk_id || idx}
            type="button"
            onClick={() => onSelectCitation(cit)}
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-blue-50 hover:bg-blue-100 text-blue-900 border border-blue-200 text-xs font-mono transition cursor-pointer shadow-xs"
            title={cit.quote ? `"${cit.quote}"` : 'Open verified course citation'}
          >
            <BookOpen className="h-3 w-3 text-blue-600 shrink-0" />
            <span className="font-bold">[{idx + 1}]</span>
            <span className="truncate max-w-[140px]">{docLabel}</span>
            {locLabel && <span className="text-blue-700">({locLabel})</span>}
          </button>
        );
      })}
    </div>
  );
};
