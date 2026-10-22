import React from 'react';
import { ThumbsUp, VolumeX, Sparkles, Heart } from 'lucide-react';
import { SilenceSpokenMessage } from '../../types';

interface GhostMarginProps {
  spokenMessage: SilenceSpokenMessage | null;
  suspectLines: number[];
  currentRung: number | string;
  onFeedback: (helpful: boolean) => void;
  feedbackGiven: boolean;
}

export const GhostMargin: React.FC<GhostMarginProps> = ({
  spokenMessage,
  suspectLines,
  currentRung,
  onFeedback,
  feedbackGiven,
}) => {
  const isBreather = currentRung === 'B' || spokenMessage?.rung === 'B';
  const isSpoken = spokenMessage && Boolean(spokenMessage.text) && !isBreather;
  const isUnderline = currentRung === 1 || (suspectLines.length > 0 && !isSpoken && !isBreather);

  return (
    <div className="w-full flex flex-col justify-start space-y-4">
      {/* Rung 1 Visual Indicator (Ghost Underline explanation) */}
      {isUnderline && (
        <div className="p-3 rounded-xl bg-amber-50/80 border border-amber-200/80 text-amber-900 text-xs shadow-2xs animate-in fade-in duration-300">
          <div className="flex items-center gap-1.5 font-bold text-amber-800 text-[11px] mb-1">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-500 animate-pulse" />
            <span>Rung 1: Ghost Underline Active</span>
          </div>
          <p className="text-[11px] text-amber-800/90 leading-relaxed font-sans">
            A soft wavy underline appears under line{' '}
            <strong className="font-mono">{(suspectLines[0] ?? 0) + 1}</strong>.
            The tutor chose <strong>zero words</strong> and <strong>zero tokens</strong> to preserve your focus.
          </p>
        </div>
      )}

      {/* Rung 2-4 Spoken Margin Note */}
      {isSpoken && (
        <div
          className="relative p-4 rounded-2xl bg-amber-50/60 border border-amber-200/90 shadow-sm text-slate-800 space-y-2.5 animate-in slide-in-from-right-3 duration-300 font-serif"
          style={{
            boxShadow: '0 4px 14px -3px rgba(245, 158, 11, 0.08)',
          }}
        >
          {/* Note header */}
          <div className="flex items-center justify-between text-[10px] font-sans text-amber-800/80 border-b border-amber-200/60 pb-1.5">
            <span className="font-bold uppercase tracking-wider flex items-center gap-1">
              <Sparkles className="h-3 w-3 text-amber-600" />
              {spokenMessage.rung === 2
                ? 'Socratic Margin Note (≤15 words)'
                : spokenMessage.rung === 3
                ? 'Margin Hint (≤30 words)'
                : 'Next Step (≤45 words)'}
            </span>
            <span className="font-mono text-slate-500 font-semibold">
              {spokenMessage.word_count} words
            </span>
          </div>

          {/* Margin text in handwritten/warm serif style */}
          <p className="text-sm text-slate-900 leading-relaxed italic">
            &ldquo;{spokenMessage.text}&rdquo;
          </p>

          {/* Feedback buttons */}
          <div className="flex items-center justify-between pt-1 border-t border-amber-200/50 text-[11px] font-sans">
            <span className="text-[10px] text-slate-400">Did the tutor time this well?</span>
            {feedbackGiven ? (
              <span className="text-[10px] font-medium text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-200">
                Feedback saved & adaptive thresholds adjusted
              </span>
            ) : (
              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => onFeedback(true)}
                  className="px-2 py-1 rounded-lg bg-white hover:bg-emerald-50 text-emerald-700 border border-slate-200 hover:border-emerald-300 text-[10px] font-medium flex items-center gap-1 transition shadow-2xs cursor-pointer"
                  title="Tutor interrupted at the right moment"
                >
                  <ThumbsUp className="h-3 w-3" />
                  <span>Helpful</span>
                </button>
                <button
                  onClick={() => onFeedback(false)}
                  className="px-2 py-1 rounded-lg bg-white hover:bg-rose-50 text-rose-700 border border-slate-200 hover:border-rose-300 text-[10px] font-medium flex items-center gap-1 transition shadow-2xs cursor-pointer"
                  title="Tutor interrupted too early or while thinking"
                >
                  <VolumeX className="h-3 w-3" />
                  <span>You interrupted me</span>
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Breather Banner */}
      {isBreather && spokenMessage && (
        <div className="p-4 rounded-2xl bg-purple-50/90 border border-purple-200 text-purple-900 shadow-sm space-y-2 animate-in fade-in duration-300">
          <div className="flex items-center gap-1.5 text-xs font-bold text-purple-800">
            <Heart className="h-3.5 w-3.5 text-purple-600 fill-purple-400" />
            <span>Human Breather</span>
          </div>
          <p className="text-xs text-purple-950 font-serif leading-relaxed italic">
            &ldquo;{spokenMessage.text}&rdquo;
          </p>
          <div className="flex justify-end pt-1">
            {!feedbackGiven && (
              <button
                onClick={() => onFeedback(true)}
                className="text-[10px] text-purple-700 hover:text-purple-900 underline font-medium cursor-pointer"
              >
                Thanks, I needed that
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
