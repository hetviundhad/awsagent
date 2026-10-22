import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';

export interface MasteryRingProps {
  value: number; // 0.0 to 1.0 or 0 to 100
  size?: number; // size in px
  strokeWidth?: number;
  label?: string;
  sublabel?: string;
  showThreshold?: boolean; // highlight 60% prerequisite threshold
  thresholdValue?: number; // default 0.6
  color?: string;
  className?: string;
}

export const MasteryRing: React.FC<MasteryRingProps> = ({
  value,
  size = 110,
  strokeWidth = 9,
  label = 'Mastery',
  sublabel,
  showThreshold = true,
  thresholdValue = 0.6,
  color,
  className = '',
}) => {
  // Normalize value to 0-1
  const normalizedValue = Math.min(Math.max(value > 1 ? value / 100 : value, 0), 1);
  const percentage = Math.round(normalizedValue * 100);

  // Animated counter
  const [displayCount, setDisplayCount] = useState(0);

  useEffect(() => {
    let start = 0;
    const duration = 900;
    const startTime = performance.now();

    const animateCount = (now: number) => {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // Ease out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplayCount(Math.round(eased * percentage));

      if (progress < 1) {
        requestAnimationFrame(animateCount);
      }
    };

    requestAnimationFrame(animateCount);
  }, [percentage]);

  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - normalizedValue * circumference;

  // Determine color based on threshold or prop
  const getRingColor = () => {
    if (color) return color;
    if (normalizedValue >= 0.8) return '#059669'; // Verified emerald
    if (normalizedValue >= 0.6) return '#1D4ED8'; // Royal blue (unlocked)
    if (normalizedValue >= 0.4) return '#D97706'; // Amber
    return '#DC2626'; // Needs review coral
  };

  const ringColor = getRingColor();

  return (
    <div className={`relative inline-flex flex-col items-center justify-center ${className}`}>
      <div style={{ width: size, height: size }} className="relative flex items-center justify-center">
        <svg width={size} height={size} className="transform -rotate-90">
          {/* Hairline track */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke="#EAE6DF"
            strokeWidth={strokeWidth}
            fill="transparent"
          />

          {/* 60% Prerequisite Threshold indicator marker */}
          {showThreshold && (
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              stroke="#FFE45C"
              strokeWidth={strokeWidth + 2}
              strokeDasharray={`3 ${circumference}`}
              strokeDashoffset={circumference - thresholdValue * circumference}
              fill="transparent"
              strokeLinecap="round"
              className="opacity-90"
            />
          )}

          {/* Animated Progress Ring */}
          <motion.circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke={ringColor}
            strokeWidth={strokeWidth}
            fill="transparent"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset }}
            transition={{ duration: 0.9, ease: [0.2, 0.8, 0.2, 1] }}
            strokeLinecap="round"
          />
        </svg>

        {/* Center label */}
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
          <span className="font-mono text-xl font-bold tracking-tight text-[#16130F]">
            {displayCount}%
          </span>
          {label && (
            <span className="text-[10px] font-mono uppercase tracking-wider text-[#7B766C]">
              {label}
            </span>
          )}
        </div>
      </div>

      {sublabel && (
        <span className="mt-2 text-xs text-[#5E5A52] font-medium text-center">
          {sublabel}
        </span>
      )}
    </div>
  );
};
