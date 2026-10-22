import React, { useState } from 'react';
import { Sparkles, FileText, Link as LinkIcon, ChevronDown, ChevronUp, Bot, ExternalLink } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface CompactStudyToolsProps {
  onOpenSummarizer: () => void;
  onOpenLinkExplainer: () => void;
}

export const CompactStudyTools: React.FC<CompactStudyToolsProps> = ({
  onOpenSummarizer,
  onOpenLinkExplainer,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const navigate = useNavigate();

  return (
    <div className="bg-white rounded-3xl border border-slate-200 overflow-hidden shadow-xs">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full p-4 flex items-center justify-between text-xs font-bold text-slate-800 hover:bg-slate-50 transition cursor-pointer"
      >
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-blue-600" />
          <span>Quick Study Solvers & Utilities</span>
        </div>
        {isOpen ? <ChevronUp className="h-4 w-4 text-slate-400" /> : <ChevronDown className="h-4 w-4 text-slate-400" />}
      </button>

      {isOpen && (
        <div className="p-4 pt-1 border-t border-slate-100 grid grid-cols-1 sm:grid-cols-3 gap-2.5 text-xs">
          <button
            onClick={onOpenSummarizer}
            className="p-3 rounded-2xl bg-slate-50 hover:bg-blue-50/60 border border-slate-200/80 text-left transition flex items-center gap-2.5 cursor-pointer"
          >
            <FileText className="h-4 w-4 text-blue-600 shrink-0" />
            <div>
              <div className="font-bold text-slate-800">Summarize Material</div>
              <div className="text-[11px] text-slate-500">Executive summary of notes</div>
            </div>
          </button>

          <button
            onClick={onOpenLinkExplainer}
            className="p-3 rounded-2xl bg-slate-50 hover:bg-blue-50/60 border border-slate-200/80 text-left transition flex items-center gap-2.5 cursor-pointer"
          >
            <LinkIcon className="h-4 w-4 text-purple-600 shrink-0" />
            <div>
              <div className="font-bold text-slate-800">Explain URL / Web Page</div>
              <div className="text-[11px] text-slate-500">Ground web research to course</div>
            </div>
          </button>

          <button
            onClick={() => navigate('/upload')}
            className="p-3 rounded-2xl bg-slate-50 hover:bg-blue-50/60 border border-slate-200/80 text-left transition flex items-center gap-2.5 cursor-pointer"
          >
            <ExternalLink className="h-4 w-4 text-emerald-600 shrink-0" />
            <div>
              <div className="font-bold text-slate-800">Video Whisper & Transcripts</div>
              <div className="text-[11px] text-slate-500">Ingest YouTube lectures</div>
            </div>
          </button>
        </div>
      )}
    </div>
  );
};
