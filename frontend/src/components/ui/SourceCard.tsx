import React from 'react';
import { motion } from 'framer-motion';
import { FileText, Video, Presentation, ExternalLink, ArrowRight } from 'lucide-react';
import { Citation } from '../../types';

export interface SourceCardProps {
  citation: Citation;
  index?: number;
  onShowMe?: () => void;
  className?: string;
  isExpanded?: boolean;
}

export const SourceCard: React.FC<SourceCardProps> = ({
  citation,
  index,
  onShowMe,
  className = '',
}) => {
  const isVideo = citation.source_type === 'video' || citation.timestamp_start !== undefined;
  const isSlide = citation.source_type === 'slide' || citation.slide_number !== undefined;
  const isPdf = !isVideo && !isSlide;

  const formatTime = (seconds?: number) => {
    if (seconds === undefined) return 'Keyframe';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
  };

  const getTypeBadge = () => {
    if (isVideo) {
      return {
        label: `Video Clip • ${formatTime(citation.timestamp_start)}`,
        icon: Video,
        accentBg: 'bg-[#EEF2FF]',
        accentText: 'text-[#1D4ED8]',
        border: 'border-[#C7D2FE]',
      };
    }
    if (isSlide) {
      return {
        label: `Slide ${citation.slide_number || 1}`,
        icon: Presentation,
        accentBg: 'bg-[#ECFDF5]',
        accentText: 'text-[#059669]',
        border: 'border-[#A7F3D0]',
      };
    }
    return {
      label: `Textbook Page ${citation.page_number || 1}`,
      icon: FileText,
      accentBg: 'bg-[#F3EFE8]',
      accentText: 'text-[#16130F]',
      border: 'border-[#EAE6DF]',
    };
  };

  const badge = getTypeBadge();
  const Icon = badge.icon;

  return (
    <motion.div
      whileHover={{ y: -2 }}
      transition={{ duration: 0.15 }}
      className={`bg-white rounded-xl border border-[#EAE6DF] shadow-paper overflow-hidden transition-all hover:border-[#D6D0C5] hover:shadow-paper-md ${className}`}
    >
      {/* Notebook binder header strip */}
      <div className="bg-[#FAF8F5] border-b border-[#EAE6DF] px-3.5 py-2 flex items-center justify-between text-xs">
        <div className="flex items-center gap-2">
          {index !== undefined && (
            <span className="font-mono font-bold text-[#1D4ED8] bg-[#EFF6FF] px-1.5 py-0.5 rounded text-[11px] border border-[#BFDBFE]">
              [{index}]
            </span>
          )}
          <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full font-mono text-[11px] font-medium border ${badge.accentBg} ${badge.accentText} ${badge.border}`}>
            <Icon className="h-3 w-3" />
            <span>{badge.label}</span>
          </span>
        </div>

        <span className="text-[11px] text-[#7B766C] truncate max-w-[150px] font-mono">
          {citation.document_name}
        </span>
      </div>

      {/* Snippet body with signature marker highlight */}
      <div className="p-3.5 space-y-2.5">
        <div className="text-xs text-[#5E5A52] leading-relaxed relative pl-3 border-l-2 border-[#FFE45C]">
          <p className="line-clamp-3 italic">
            "{citation.snippet || 'Source verified by course material chunk.'}"
          </p>
        </div>

        {/* Action button */}
        {onShowMe && (
          <div className="pt-2 flex items-center justify-between border-t border-[#F3EFE8]">
            <span className="text-[11px] font-mono text-[#7B766C]">
              {isPdf ? 'Bounding box ready' : isVideo ? 'Keyframe synced' : 'Instructor notes attached'}
            </span>
            <button
              type="button"
              onClick={onShowMe}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[#FFE45C] hover:bg-[#FCD34D] text-[#16130F] font-semibold text-xs transition border border-[#F5D843] shadow-xs cursor-pointer"
            >
              <span>Show Me</span>
              <ArrowRight className="h-3 w-3" />
            </button>
          </div>
        )}
      </div>
    </motion.div>
  );
};
