import React from 'react';
import { motion } from 'framer-motion';
import { ShieldAlert, BookOpen, ArrowRight } from 'lucide-react';

export interface RefusalNoticeProps {
  query?: string;
  retrievalScore?: number; // e.g. 0.08
  threshold?: number; // 0.20
  courseName?: string;
  onExploreCourse?: () => void;
  className?: string;
}

export const RefusalNotice: React.FC<RefusalNoticeProps> = ({
  query,
  retrievalScore = 0.09,
  threshold = 0.20,
  courseName = 'your course syllabus',
  onExploreCourse,
  className = '',
}) => {
  const scorePercent = Math.min(Math.max(retrievalScore * 100, 0), 100);
  const thresholdPercent = threshold * 100;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.2, 0.8, 0.2, 1] }}
      className={`bg-white rounded-2xl border border-[#FECACA] p-5 shadow-paper space-y-4 ${className}`}
    >
      {/* Designed Header */}
      <div className="flex items-start gap-3.5">
        <div className="h-10 w-10 rounded-xl bg-[#FEF2F2] border border-[#FECACA] text-[#DC2626] flex items-center justify-center shrink-0">
          <ShieldAlert className="h-5 w-5" />
        </div>
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="font-mono text-[11px] font-semibold uppercase tracking-wider text-[#DC2626] bg-[#FEF2F2] px-2 py-0.5 rounded-full border border-[#FECACA]">
              Zero-Hallucination Guardrail Refusal
            </span>
            <span className="font-mono text-xs text-[#7B766C]">
              Threshold Gate: &tau; &ge; {threshold.toFixed(2)}
            </span>
          </div>
          <h4 className="font-display text-base font-bold text-[#16130F]">
            This question falls outside the verified course materials
          </h4>
          <p className="text-xs text-[#5E5A52] leading-relaxed">
            StudyMind AI is strictly grounded in your uploaded documents. Rather than fabricating an answer, 
            the tutor refuses requests that lack direct textual proof in <span className="font-semibold text-[#16130F]">{courseName}</span>.
          </p>
        </div>
      </div>

      {/* Retrieval score calibrated visualizer */}
      <div className="bg-[#FAF8F5] rounded-xl p-3.5 border border-[#EAE6DF] space-y-2">
        <div className="flex items-center justify-between text-xs font-mono">
          <span className="text-[#5E5A52]">Hybrid Retrieval Confidence (RRF k=60):</span>
          <span className="font-bold text-[#DC2626]">{retrievalScore.toFixed(3)}</span>
        </div>

        {/* Progress bar with threshold marker */}
        <div className="relative h-3 w-full bg-[#EAE6DF] rounded-full overflow-visible">
          {/* Fill up to score */}
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${scorePercent}%` }}
            transition={{ duration: 0.6, ease: [0.2, 0.8, 0.2, 1] }}
            className="h-full bg-[#DC2626] rounded-full"
          />

          {/* Calibrated 0.20 Threshold Tick */}
          <div
            style={{ left: `${thresholdPercent}%` }}
            className="absolute -top-1 bottom-0 w-[3px] bg-[#16130F] rounded-full"
            title={`Required Grounding Threshold: ${threshold.toFixed(2)}`}
          >
            <span className="absolute -top-5 -translate-x-1/2 font-mono text-[9px] font-bold text-[#16130F] bg-[#FFE45C] px-1 rounded shadow-xs">
              &tau;={threshold.toFixed(2)}
            </span>
          </div>
        </div>

        <div className="flex items-center justify-between text-[11px] font-mono text-[#7B766C] pt-1">
          <span>0.00 (Unrelated)</span>
          <span className="text-[#16130F] font-bold">Minimum 0.20 required to answer</span>
          <span>1.00 (Exact match)</span>
        </div>
      </div>

      {onExploreCourse && (
        <div className="pt-2 flex items-center justify-between">
          <span className="text-xs text-[#5E5A52]">
            Want to learn concepts in the syllabus?
          </span>
          <button
            type="button"
            onClick={onExploreCourse}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#1D4ED8] hover:text-[#1E40AF]"
          >
            <BookOpen className="h-3.5 w-3.5" />
            <span>Inspect Course Syllabus</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </div>
      )}
    </motion.div>
  );
};
