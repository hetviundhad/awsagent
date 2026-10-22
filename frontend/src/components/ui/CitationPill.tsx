import React from 'react';
import { motion } from 'framer-motion';
import { FileText, Video, Presentation } from 'lucide-react';
import { Citation } from '../../types';

export interface CitationPillProps {
  index: number;
  citation?: Citation;
  onClick?: () => void;
  onMouseEnter?: () => void;
  onMouseLeave?: () => void;
  isHighlighted?: boolean;
}

export const CitationPill: React.FC<CitationPillProps> = ({
  index,
  citation,
  onClick,
  onMouseEnter,
  onMouseLeave,
  isHighlighted = false,
}) => {
  const getSourceIcon = (type?: string) => {
    switch (type) {
      case 'video':
        return <Video className="h-3 w-3 text-[#1D4ED8]" />;
      case 'slide':
        return <Presentation className="h-3 w-3 text-[#059669]" />;
      default:
        return <FileText className="h-3 w-3 text-[#5E5A52]" />;
    }
  };

  const getSourceLabel = (c?: Citation) => {
    if (!c) return `[${index}]`;
    if (c.source_type === 'pdf' || c.page_number) return `p.${c.page_number || 1}`;
    if (c.source_type === 'video' || c.timestamp_start !== undefined) {
      const minutes = Math.floor((c.timestamp_start || 0) / 60);
      const seconds = Math.floor((c.timestamp_start || 0) % 60);
      return `${minutes}:${seconds < 10 ? '0' : ''}${seconds}`;
    }
    if (c.source_type === 'slide' || c.slide_number) return `slide ${c.slide_number || 1}`;
    return c.document_name ? c.document_name.slice(0, 16) : `[${index}]`;
  };

  return (
    <motion.button
      type="button"
      whileHover={{ y: -1, scale: 1.03 }}
      whileTap={{ scale: 0.97 }}
      onClick={onClick}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      className={`inline-flex items-center gap-1 px-2 py-0.5 mx-0.5 rounded text-xs font-mono font-medium transition-all duration-150 align-baseline cursor-pointer border ${
        isHighlighted
          ? 'bg-[#FFE45C] text-[#16130F] border-[#E5C936] shadow-sm font-semibold'
          : 'bg-[#F3EFE8] text-[#16130F] border-[#EAE6DF] hover:bg-[#FEF9C3] hover:border-[#FDE68A]'
      }`}
      title={citation?.document_name ? `${citation.document_name} • Click to inspect source` : 'View source grounding'}
    >
      <span className="text-[#1D4ED8] font-bold">[{index}]</span>
      {citation && (
        <>
          <span className="shrink-0">{getSourceIcon(citation.source_type)}</span>
          <span className="relative">
            <span className="text-[11px] text-[#5E5A52]">{getSourceLabel(citation)}</span>
            {/* Signature yellow marker underline */}
            <span className="absolute left-0 right-0 -bottom-[1px] h-[2px] bg-[#FFE45C] rounded-full" />
          </span>
        </>
      )}
    </motion.button>
  );
};
