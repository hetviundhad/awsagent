import React from 'react';

export interface PillProps {
  children: React.ReactNode;
  variant?: 'neutral' | 'verified' | 'ambiguous' | 'refused' | 'info' | 'highlighter';
  size?: 'xs' | 'sm' | 'md';
  icon?: React.ReactNode;
  className?: string;
}

export const Pill: React.FC<PillProps> = ({
  children,
  variant = 'neutral',
  size = 'sm',
  icon,
  className = '',
}) => {
  const sizeStyles = {
    xs: 'text-[10px] px-2 py-0.5 font-mono',
    sm: 'text-xs px-2.5 py-1',
    md: 'text-sm px-3 py-1.5',
  };

  const variantStyles = {
    neutral: 'bg-[#F3EFE8] text-[#5E5A52] border border-[#EAE6DF]',
    verified: 'bg-[#ECFDF5] text-[#059669] border border-[#A7F3D0] font-medium',
    ambiguous: 'bg-[#FFFBEB] text-[#D97706] border border-[#FDE68A] font-medium',
    refused: 'bg-[#FEF2F2] text-[#DC2626] border border-[#FECACA] font-medium',
    info: 'bg-[#EEF2FF] text-[#4F46E5] border border-[#C7D2FE] font-medium',
    highlighter: 'bg-[#FFE45C] text-[#16130F] border border-[#F5D843] font-semibold',
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full tracking-normal select-none ${sizeStyles[size]} ${variantStyles[variant]} ${className}`}
    >
      {icon && <span className="shrink-0">{icon}</span>}
      <span>{children}</span>
    </span>
  );
};
