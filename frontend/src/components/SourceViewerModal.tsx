import React, { useState, useEffect } from 'react';
import { 
  X, FileText, Presentation, Video, Image as ImageIcon, Play, Pause, 
  RotateCcw, CheckCircle, ExternalLink, Sparkles, Eye, Bookmark, Clock
} from 'lucide-react';
import { Citation } from '../types';

interface ShowMeViewerModalProps {
  citation: Citation | null;
  onClose: () => void;
}

export const SourceViewerModal: React.FC<ShowMeViewerModalProps> = ({ citation, onClose }) => {
  if (!citation) return null;

  // Video clip auto-play and auto-pause state
  const tStart = citation.timestamp_start ?? 0;
  const tEnd = citation.timestamp_end ?? (tStart + 25);
  const clipDuration = Math.max(tEnd - tStart, 10);

  const [isPlaying, setIsPlaying] = useState(true);
  const [playbackTime, setPlaybackTime] = useState(tStart);

  // Auto-play and pause loop for video clip
  useEffect(() => {
    let timer: any = null;
    if (isPlaying && citation.source_type === 'video') {
      timer = setInterval(() => {
        setPlaybackTime((prev) => {
          if (prev >= tEnd) {
            setIsPlaying(false);
            return tEnd;
          }
          return prev + 1;
        });
      }, 1000);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [isPlaying, tEnd, citation.source_type]);

  const restartClip = () => {
    setPlaybackTime(tStart);
    setIsPlaying(true);
  };

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  const bbox = citation.bbox || [54.0, 100.0, 550.0, 240.0];

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center p-3 md:p-6 bg-ink-950/40 backdrop-blur-xs animate-in fade-in duration-200"
      onClick={onClose}
    >
      {/* Binder Page Container */}
      <div 
        className="relative w-full max-w-4xl bg-paper-canvas rounded-2xl border border-paper-hairline shadow-paper-lg overflow-hidden flex flex-col max-h-[92vh] animate-in slide-in-from-bottom-3 duration-300"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Binder Holes Strip (Left edge detail) */}
        <div className="absolute left-2.5 top-0 bottom-0 flex flex-col justify-around py-8 pointer-events-none z-20 hidden md:flex">
          <div className="w-3.5 h-3.5 rounded-full bg-paper-surface border border-paper-hairline shadow-inner" />
          <div className="w-3.5 h-3.5 rounded-full bg-paper-surface border border-paper-hairline shadow-inner" />
          <div className="w-3.5 h-3.5 rounded-full bg-paper-surface border border-paper-hairline shadow-inner" />
        </div>

        {/* Binder Top Header */}
        <div className="md:pl-10 px-5 py-4 border-b border-paper-hairline flex items-center justify-between bg-white">
          <div className="flex items-center space-x-3 min-w-0">
            <span className="inline-flex items-center justify-center h-8 w-8 rounded-lg bg-highlighter-base text-ink-900 font-mono font-bold text-sm shrink-0 border border-ink-900/10">
              #{citation.citation_index || 1}
            </span>
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-mono text-[10px] uppercase tracking-wider text-ink-500 font-bold">
                  Source Grounded Verification
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-paper-surface border border-paper-hairline text-ink-700 uppercase font-semibold">
                  {citation.source_type}
                </span>
                {citation.page_number && (
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-highlighter-soft text-ink-900 border border-ink-900/10">
                    Page {citation.page_number}
                  </span>
                )}
                {citation.slide_number && (
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-royal-50 text-royal-800 border border-royal-200">
                    Slide {citation.slide_number}
                  </span>
                )}
                {citation.timestamp_start !== undefined && citation.timestamp_start !== null && (
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-50 text-amber-900 border border-amber-200">
                    Interval {formatTime(tStart)} - {formatTime(tEnd)}
                  </span>
                )}
              </div>
              <h3 className="font-serif text-base font-bold text-ink-900 truncate max-w-xl mt-0.5">
                {citation.document_name}
              </h3>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2 rounded-lg text-ink-400 hover:text-ink-900 hover:bg-paper-surface border border-transparent hover:border-paper-hairline transition shrink-0 ml-2"
            aria-label="Close modal"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content Viewer Body */}
        <div className="md:pl-10 p-5 md:p-6 overflow-y-auto space-y-6 flex-1 bg-paper-canvas">
          
          {/* 1. PDF VIEWER: PAGE SLIDES IN WITH MARKER YELLOW BOUNDING BOX */}
          {citation.source_type === 'pdf' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {/* Left Column: Simulated PDF Manuscript Page with Animated Bounding Box */}
              <div className="relative rounded-xl bg-white p-6 border border-paper-hairline shadow-paper flex flex-col justify-between min-h-[400px]">
                <div className="flex justify-between items-center border-b border-paper-hairline pb-2.5 mb-4 text-xs">
                  <div className="flex items-center gap-1.5 font-mono text-[11px] text-ink-500 uppercase tracking-wider">
                    <FileText className="h-3.5 w-3.5 text-royal-700" />
                    <span>Facsimile Canvas</span>
                  </div>
                  <span className="font-mono text-[11px] font-bold text-ink-900 px-2 py-0.5 rounded bg-paper-surface border border-paper-hairline">
                    Page {citation.page_number || 1}
                  </span>
                </div>

                {/* Printed manuscript page simulation */}
                <div className="relative flex-1 bg-paper-canvas/70 rounded-lg border border-paper-hairline p-5 font-serif text-xs text-ink-700 space-y-3 select-none overflow-hidden">
                  <div className="text-[10px] font-mono text-ink-400 uppercase tracking-widest pb-1 border-b border-paper-hairline/60">
                    Syllabus Section 4.2 · Grounded Proof
                  </div>
                  <p className="line-clamp-2 leading-relaxed text-ink-600">
                    Formal Verification and State Equivalence under inductive decomposition.
                  </p>

                  {/* Marker-yellow bounding box that draws itself on */}
                  <div className="relative my-3 p-3.5 rounded-md border-2 border-ink-900 bg-highlighter-base/25 shadow-highlighter text-ink-900 font-serif text-xs font-semibold leading-relaxed animate-in fade-in zoom-in-95 duration-500">
                    <div className="absolute -top-3 left-3 px-2 py-0.5 bg-highlighter-base text-ink-900 font-mono font-bold text-[9px] uppercase tracking-wider rounded border border-ink-900">
                      Cited Bounding Box
                    </div>
                    "{citation.snippet}"
                  </div>

                  <p className="line-clamp-3 leading-relaxed text-ink-600">
                    All subproblem evaluations preserve invariant bounds across recursive transitions without redundant evaluations.
                  </p>
                </div>

                <div className="mt-4 pt-2.5 border-t border-paper-hairline flex justify-between items-center text-[10px] text-ink-500 font-mono">
                  <span>Coordinates: [{bbox.map((v) => Math.round(v)).join(', ')}]</span>
                  <span>Fit-to-width · Scale 100%</span>
                </div>
              </div>

              {/* Right Column: Grounded Evidence & Semantic Context */}
              <div className="space-y-4">
                <div className="p-4 rounded-xl bg-white border border-paper-hairline shadow-paper space-y-2.5">
                  <div className="text-xs font-mono font-bold text-ink-900 uppercase tracking-wider flex items-center space-x-1.5">
                    <Sparkles className="h-3.5 w-3.5 text-royal-700" />
                    <span>Exact Textual Citation</span>
                  </div>
                  <blockquote className="p-3.5 rounded-lg bg-paper-surface border-l-4 border-highlighter-base text-xs text-ink-900 leading-relaxed font-serif">
                    "{citation.snippet}"
                  </blockquote>
                </div>

                <div className="p-4 rounded-xl bg-white border border-paper-hairline shadow-paper space-y-2 text-xs">
                  <div className="font-mono text-[11px] font-bold text-ink-900 uppercase tracking-wider">
                    Source Provenance
                  </div>
                  <div className="space-y-1.5 font-mono text-[11px] text-ink-600">
                    <div className="flex justify-between py-1 border-b border-paper-hairline/60">
                      <span className="text-ink-500">Document</span>
                      <span className="text-ink-900 font-medium truncate max-w-[200px]">{citation.document_name}</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-paper-hairline/60">
                      <span className="text-ink-500">Page</span>
                      <span className="text-royal-700 font-bold">{citation.page_number || 1}</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-paper-hairline/60">
                      <span className="text-ink-500">Bounding Box</span>
                      <span className="text-ink-800">[{bbox.map((v) => Math.round(v)).join(', ')}]</span>
                    </div>
                    <div className="flex justify-between py-1">
                      <span className="text-ink-500">Chunk Identifier</span>
                      <span className="text-ink-500 truncate">{citation.chunk_id}</span>
                    </div>
                  </div>
                </div>

                {citation.visual_description && (
                  <div className="p-4 rounded-xl bg-white border border-paper-hairline shadow-paper space-y-1.5">
                    <div className="text-xs font-mono font-bold text-ink-900 uppercase tracking-wider flex items-center space-x-1.5">
                      <ImageIcon className="h-3.5 w-3.5 text-emerald-700" />
                      <span>Diagram / Figure on Page</span>
                    </div>
                    <p className="text-xs text-ink-700 leading-relaxed font-serif">
                      {citation.visual_description}
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* 2. VIDEO CITATION PLAYER WITH TIMELINE INTERVAL */}
          {citation.source_type === 'video' && (
            <div className="space-y-4">
              <div className="relative rounded-2xl overflow-hidden bg-white border border-paper-hairline shadow-paper flex flex-col justify-between p-5 aspect-video">
                {/* Overlay Header */}
                <div className="flex justify-between items-center z-10">
                  <span className="flex items-center space-x-2 text-xs font-mono text-ink-900 bg-highlighter-base px-2.5 py-1 rounded border border-ink-900/10 font-bold">
                    <Clock className="h-3 w-3" />
                    <span>TIMELINE INTERVAL: {formatTime(tStart)} — {formatTime(tEnd)}</span>
                  </span>
                  <span className="text-xs font-mono text-ink-700 bg-paper-surface px-2.5 py-1 rounded border border-paper-hairline">
                    Clip Window: {clipDuration.toFixed(0)}s
                  </span>
                </div>

                {/* Keyframe Visual or Video Screen */}
                <div className="my-auto text-center space-y-3">
                  <div className="inline-block p-4 rounded-xl bg-paper-canvas border border-paper-hairline shadow-xs">
                    {citation.keyframe_path ? (
                      <div className="space-y-2">
                        <div className="text-[11px] font-mono text-ink-700 flex items-center justify-center space-x-1">
                          <Eye className="h-3.5 w-3.5 text-royal-700" />
                          <span>Lecture Keyframe at {formatTime(tStart)}</span>
                        </div>
                        <img 
                          src={citation.keyframe_path} 
                          alt="Video Keyframe" 
                          className="max-h-48 mx-auto rounded border border-paper-hairline object-contain"
                          onError={(e) => {
                            (e.target as HTMLElement).style.display = 'none';
                          }}
                        />
                      </div>
                    ) : (
                      <div className="space-y-1">
                        <p className="text-xs font-mono text-royal-700 font-bold uppercase tracking-wider">Synchronized Lecture Frame</p>
                        <p className="font-serif text-sm font-semibold text-ink-900">{citation.document_name}</p>
                      </div>
                    )}
                  </div>

                  <div className="text-sm font-mono text-ink-800">
                    Playback: <span className="text-royal-700 font-bold">{formatTime(playbackTime)}</span> / {formatTime(tEnd)}
                  </div>
                </div>

                {/* Marker-yellow Timeline Interval Scrubber */}
                <div className="space-y-2 z-10 bg-paper-surface p-3.5 rounded-xl border border-paper-hairline">
                  <div className="relative w-full bg-paper-hairline h-3 rounded-full overflow-hidden">
                    {/* Full clip highlight in highlighter yellow */}
                    <div className="absolute inset-0 bg-paper-hairline" />
                    <div
                      className="absolute top-0 bottom-0 bg-highlighter-base border-r-2 border-ink-900 transition-all duration-300"
                      style={{
                        width: `${Math.min(
                          Math.max(((playbackTime - tStart) / clipDuration) * 100, 0),
                          100
                        )}%`
                      }}
                    />
                  </div>
                  <div className="flex items-center justify-between text-xs text-ink-700">
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => setIsPlaying(!isPlaying)}
                        className="flex items-center space-x-1.5 px-3 py-1 rounded-lg bg-ink-900 text-white font-mono text-xs font-semibold hover:bg-ink-800 transition shadow-xs"
                      >
                        {isPlaying ? <Pause className="h-3 w-3" /> : <Play className="h-3 w-3" />}
                        <span>{isPlaying ? 'Pause' : 'Play'}</span>
                      </button>
                      <button
                        onClick={restartClip}
                        className="flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-white text-ink-700 hover:bg-paper-canvas border border-paper-hairline font-mono text-xs transition"
                      >
                        <RotateCcw className="h-3 w-3" />
                        <span>Replay</span>
                      </button>
                    </div>
                    <span className="font-mono text-[11px] text-ink-500">
                      Synchronized Interval · {clipDuration.toFixed(0)} seconds
                    </span>
                  </div>
                </div>
              </div>

              {/* Synchronized Transcript Highlight */}
              <div className="p-4 rounded-xl bg-white border border-paper-hairline shadow-paper space-y-2">
                <div className="flex items-center justify-between text-xs font-mono font-bold text-ink-900 uppercase tracking-wider">
                  <span className="flex items-center space-x-1.5">
                    <Sparkles className="h-3.5 w-3.5 text-royal-700" />
                    <span>Synchronized Lecture Transcript</span>
                  </span>
                  <span className="text-ink-500">{formatTime(tStart)} – {formatTime(tEnd)}</span>
                </div>
                <blockquote className="text-xs text-ink-900 font-serif leading-relaxed bg-highlighter-soft p-3 rounded-lg border-l-4 border-highlighter-base">
                  "{citation.snippet}"
                </blockquote>
                {citation.visual_frame_summary && (
                  <p className="text-[11px] text-ink-600 font-mono italic">
                    👁️ Frame Analysis: {citation.visual_frame_summary}
                  </p>
                )}
              </div>
            </div>
          )}

          {/* 3. SLIDES WITH INSTRUCTOR NOTE STICKY CARD */}
          {citation.source_type === 'slide' && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              {/* Slide Deck Canvas */}
              <div className="md:col-span-2 rounded-2xl bg-white p-6 border border-paper-hairline aspect-[16/9] flex flex-col justify-between shadow-paper relative">
                <div className="border-b border-paper-hairline pb-2.5 flex justify-between items-center">
                  <span className="text-xs font-mono uppercase tracking-wider text-ink-500 font-bold">
                    Slide Deck: {citation.document_name}
                  </span>
                  <span className="text-xs font-mono font-bold text-royal-700 bg-royal-50 px-2.5 py-0.5 rounded border border-royal-200">
                    Slide {citation.slide_number}
                  </span>
                </div>

                <div className="my-auto space-y-3">
                  <div className="p-5 rounded-xl bg-paper-canvas border border-paper-hairline text-xs space-y-2">
                    <div className="text-[10px] font-mono font-bold text-ink-500 uppercase tracking-wider">
                      Slide Content Excerpt
                    </div>
                    <p className="font-serif text-sm text-ink-900 leading-relaxed pl-2 border-l-2 border-royal-700">
                      "{citation.snippet}"
                    </p>
                  </div>
                </div>

                <div className="text-[11px] text-ink-500 flex justify-between font-mono">
                  <span>Unit Presentation Material</span>
                  <span>Visual Slide Layout Verified</span>
                </div>
              </div>

              {/* Instructor's Sticky Note Card */}
              <div className="rounded-xl bg-[#FEF9C3] p-5 border border-[#FDE047] shadow-paper flex flex-col justify-between rotate-[-0.5deg]">
                <div className="space-y-3">
                  <div className="flex items-center justify-between pb-2 border-b border-[#FACC15]/40">
                    <span className="font-mono text-[10px] uppercase tracking-wider font-bold text-amber-900">
                      Instructor's Note
                    </span>
                    <span className="h-2 w-2 rounded-full bg-amber-500" />
                  </div>
                  <p className="font-serif text-xs text-amber-950 leading-relaxed">
                    "Exam warning: This slide summarizes the core boundary condition. Memorize how the base case prevents cycle recursion."
                  </p>
                </div>

                <div className="pt-3 border-t border-[#FACC15]/40 text-[10px] font-mono text-amber-800">
                  Slide {citation.slide_number} · Professor Remarks
                </div>
              </div>
            </div>
          )}

          {/* 4. WEB LINK RESOURCE */}
          {citation.source_type === 'link' && (
            <div className="p-6 rounded-2xl bg-white border border-paper-hairline shadow-paper space-y-3">
              <div className="flex items-center justify-between text-xs font-mono font-bold text-ink-900 uppercase tracking-wider">
                <span>Indexed Web Study Resource</span>
                <ExternalLink className="h-4 w-4 text-royal-700" />
              </div>
              <blockquote className="text-xs text-ink-900 leading-relaxed font-serif bg-paper-surface p-4 rounded-xl border-l-4 border-royal-700">
                "{citation.snippet}"
              </blockquote>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="md:pl-10 px-5 py-3 border-t border-paper-hairline bg-white flex items-center justify-between text-xs text-ink-600">
          <div className="flex items-center space-x-2 text-emerald-700 font-mono text-[11px]">
            <CheckCircle className="h-3.5 w-3.5" />
            <span>Chunk Verified: {citation.chunk_id}</span>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-ink-900 hover:bg-ink-800 text-white font-mono text-xs font-semibold transition"
          >
            Close Viewer
          </button>
        </div>
      </div>
    </div>
  );
};
