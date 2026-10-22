import React from 'react';
import { motion, HTMLMotionProps } from 'framer-motion';

export interface ButtonProps extends Omit<HTMLMotionProps<'button'>, 'children'> {
  variant?: 'primary' | 'secondary' | 'highlighter' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  children: React.ReactNode;
  icon?: React.ReactNode;
  iconPosition?: 'left' | 'right';
  isLoading?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'md',
  children,
  icon,
  iconPosition = 'left',
  isLoading = false,
  className = '',
  disabled,
  ...props
}) => {
  const baseClasses = 'inline-flex items-center justify-center font-medium transition-all duration-150 rounded-xl focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed select-none';

  const sizeClasses = {
    sm: 'text-xs px-3 py-1.5 gap-1.5 min-h-[36px]',
    md: 'text-sm px-4 py-2.5 gap-2 min-h-[44px]',
    lg: 'text-base px-6 py-3.5 gap-2.5 min-h-[48px]',
  };

  const variantClasses = {
    primary: 'bg-[#1D4ED8] hover:bg-[#1E40AF] text-white shadow-paper focus-visible:ring-[#1D4ED8] border border-[#1D4ED8]',
    secondary: 'bg-white hover:bg-[#F3EFE8] text-[#16130F] border border-[#EAE6DF] shadow-paper hover:border-[#D6D0C5] focus-visible:ring-[#1D4ED8]',
    highlighter: 'bg-[#FFE45C] hover:bg-[#FCD34D] text-[#16130F] font-semibold border border-[#F5D843] shadow-paper focus-visible:ring-[#16130F]',
    ghost: 'bg-transparent hover:bg-[#F3EFE8] text-[#5E5A52] hover:text-[#16130F] focus-visible:ring-[#1D4ED8]',
    danger: 'bg-[#FEF2F2] hover:bg-[#FEE2E2] text-[#DC2626] border border-[#FECACA] focus-visible:ring-[#DC2626]',
  };

  return (
    <motion.button
      whileHover={{ y: disabled || isLoading ? 0 : -1 }}
      whileTap={{ y: disabled || isLoading ? 0 : 0, scale: disabled || isLoading ? 1 : 0.98 }}
      transition={{ duration: 0.15, ease: [0.2, 0.8, 0.2, 1] }}
      className={`${baseClasses} ${sizeClasses[size]} ${variantClasses[variant]} ${className}`}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? (
        <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
      ) : (
        <>
          {icon && iconPosition === 'left' && <span className="shrink-0">{icon}</span>}
          <span>{children}</span>
          {icon && iconPosition === 'right' && <span className="shrink-0">{icon}</span>}
        </>
      )}
    </motion.button>
  );
};
