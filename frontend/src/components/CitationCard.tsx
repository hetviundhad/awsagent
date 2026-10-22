import React from 'react';
import { FileText, Presentation, Video, Image as ImageIcon, ExternalLink, Bookmark } from 'lucide-react';
import { Citation } from '../types';

interface CitationCardProps {
  citation: Citation;
  onOpenSource: (citation: Citation) => void;
}

export const CitationCard: React.FC<CitationCardProps> = ({ citation, onOpenSource }) => {
  const getIcon = () => {
    switch (citation.source_type) {
      case 'slide':
        return <Presentation className="h-3.5 w-3.5 text-royal-700" />;
      case 'video':
        return <Video className="h-3.5 w-3.5 text-amber-700" />;
      case 'image':
        return <ImageIcon className="h-3.5 w-3.5 text-emerald-700" />;
      default:
        return <FileText className="h-3.5 w-3.5 text-ink-700" />;
    }
  };

  const getLocationLabel = () => {
    if (citation.page_number) return `p. ${citation.page_number}`;
    if (citation.slide_number) return `slide ${citation.slide_number}`;
    if (citation.timestamp_start !== undefined && citation.timestamp_start !== null) {
      const min = Math.floor(citation.timestamp_start / 60);
      const sec = Math.floor(citation.timestamp_start % 60).toString().padStart(2, '0');
      return `${min}:${sec}`;
    }
    return 'source chunk';
  };

  const getActionLabel = () => {
    if (citation.source_type === 'slide') return 'Slide note';
    if (citation.source_type === 'video') return 'Video clip';
    if (citation.source_type === 'image') return 'Diagram';
    return 'Inspect page';
  };

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={`Open citation ${citation.citation_index}: ${citation.document_name}, ${getLocationLabel()}`}
      onClick={() => onOpenSource(citation)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onOpenSource(citation);
        }
      }}
      className="group relative p-3 rounded-lg bg-white border border-paper-hairline hover:border-ink-900/30 hover:shadow-paper transition-all duration-200 cursor-pointer text-left overflow-hidden"
    >
      {/* Top margin note header */}
      <div className="flex items-center justify-between gap-2 mb-2 pb-1.5 border-b border-paper-hairline/60">
        <div className="flex items-center space-x-2 min-w-0">
          <span className="inline-flex items-center justify-center h-5 w-5 rounded bg-highlighter-base text-ink-900 font-mono font-bold text-[10px] shrink-0 border border-ink-900/10">
            {citation.citation_index || 1}
          </span>
          <div className="p-1 rounded bg-paper-surface border border-paper-hairline shrink-0">
            {getIcon()}
          </div>
          <span className="font-mono text-[11px] text-ink-600 font-medium truncate">
            {citation.document_name}
          </span>
        </div>

        <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-paper-surface border border-paper-hairline text-ink-700 shrink-0">
          {getLocationLabel()}
        </span>
      </div>

      {/* Snippet with yellow highlight */}
      <p className="text-xs text-ink-800 leading-relaxed font-serif line-clamp-2 pl-2 border-l-2 border-highlighter-base">
        "{citation.snippet}"
      </p>

      {citation.visual_description && (
        <div className="mt-2 text-[10px] text-ink-700 bg-paper-surface border border-paper-hairline px-2 py-1 rounded flex items-center gap-1.5">
          <ImageIcon className="h-3 w-3 text-royal-700 shrink-0" />
          <span className="truncate">{citation.visual_description}</span>
        </div>
      )}

      {/* Footer Show me button */}
      <div className="mt-2 pt-1.5 flex items-center justify-between text-[11px] text-ink-500 font-mono">
        <span className="text-[10px] text-ink-400 uppercase tracking-wider">
          {citation.source_type}
        </span>
        <span className="inline-flex items-center gap-1 text-royal-700 group-hover:text-royal-900 font-semibold group-hover:underline">
          <span>Show me</span>
          <ExternalLink className="h-3 w-3" />
        </span>
      </div>
    </div>
  );
};
