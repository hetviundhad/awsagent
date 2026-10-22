import React from 'react';
import { motion, HTMLMotionProps } from 'framer-motion';

export interface CardProps extends Omit<HTMLMotionProps<'div'>, 'children'> {
  children: React.ReactNode;
  variant?: 'default' | 'subtle' | 'highlighted';
  hoverLift?: boolean;
  className?: string;
  onClick?: () => void;
}

export const Card: React.FC<CardProps> = ({
  children,
  variant = 'default',
  hoverLift = false,
  className = '',
  onClick,
  ...props
}) => {
  const variantStyles = {
    default: 'bg-white border border-[#EAE6DF] shadow-paper',
    subtle: 'bg-[#F3EFE8] border border-[#EAE6DF]',
    highlighted: 'bg-white border-2 border-[#FFE45C] shadow-paper',
  };

  return (
    <motion.div
      whileHover={hoverLift ? { y: -3, boxShadow: '0 10px 24px -4px rgba(22, 19, 15, 0.08)' } : undefined}
      transition={{ duration: 0.2, ease: [0.2, 0.8, 0.2, 1] }}
      onClick={onClick}
      className={`rounded-2xl transition-colors ${variantStyles[variant]} ${onClick ? 'cursor-pointer' : ''} ${className}`}
      {...props}
    >
      {children}
    </motion.div>
  );
};
