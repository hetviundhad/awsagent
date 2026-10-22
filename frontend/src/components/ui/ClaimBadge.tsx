import React from 'react';
import { CheckCircle2, AlertTriangle, XCircle, ShieldCheck } from 'lucide-react';
import { motion } from 'framer-motion';

export interface ClaimBadgeProps {
  status: 'verified' | 'ambiguous' | 'refused' | 'grounded';
  score?: number;
  className?: string;
  showIcon?: boolean;
}

export const ClaimBadge: React.FC<ClaimBadgeProps> = ({
  status,
  score,
  className = '',
  showIcon = true,
}) => {
  const configs = {
    verified: {
      label: 'Verified by Course Material',
      shortLabel: 'Verified',
      icon: CheckCircle2,
      bg: 'bg-[#ECFDF5]',
      border: 'border-[#A7F3D0]',
      text: 'text-[#059669]',
    },
    grounded: {
      label: 'Syllabus Grounded',
      shortLabel: 'Grounded',
      icon: ShieldCheck,
      bg: 'bg-[#ECFDF5]',
      border: 'border-[#A7F3D0]',
      text: 'text-[#059669]',
    },
    ambiguous: {
      label: 'Ambiguous Context',
      shortLabel: 'Ambiguous',
      icon: AlertTriangle,
      bg: 'bg-[#FFFBEB]',
      border: 'border-[#FDE68A]',
      text: 'text-[#D97706]',
    },
    refused: {
      label: 'Unsupported / Refused',
      shortLabel: 'Refused',
      icon: XCircle,
      bg: 'bg-[#FEF2F2]',
      border: 'border-[#FECACA]',
      text: 'text-[#DC2626]',
    },
  };

  const config = configs[status] || configs.verified;
  const Icon = config.icon;

  return (
    <motion.span
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.2 }}
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-medium border ${config.bg} ${config.border} ${config.text} ${className}`}
    >
      {showIcon && (
        <motion.span
          initial={{ rotate: -15, scale: 0.8 }}
          animate={{ rotate: 0, scale: 1 }}
          transition={{ duration: 0.2 }}
          className="shrink-0"
        >
          <Icon className="h-3.5 w-3.5" />
        </motion.span>
      )}
      <span>{config.shortLabel}</span>
      {score !== undefined && (
        <span className="opacity-75 font-mono text-[11px]">({(score * 100).toFixed(0)}%)</span>
      )}
    </motion.span>
  );
};
