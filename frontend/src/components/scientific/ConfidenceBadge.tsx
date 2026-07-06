import React from 'react'

interface ConfidenceBadgeProps {
  score: number; // 0.0 to 1.0
  className?: string;
}

export const ConfidenceBadge: React.FC<ConfidenceBadgeProps> = ({
  score,
  className = '',
}) => {
  const getBadgeStyle = () => {
    if (score >= 0.8) {
      return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
    } else if (score >= 0.5) {
      return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
    } else {
      return 'bg-rose-500/10 text-rose-400 border-rose-500/30';
    }
  };

  const getLedBg = () => {
    if (score >= 0.8) return 'bg-emerald-400';
    if (score >= 0.5) return 'bg-amber-400';
    return 'bg-rose-400';
  };

  const getLabel = () => {
    if (score >= 0.8) return 'VERIFIED';
    if (score >= 0.5) return 'UNSTABLE';
    return 'CRITICAL';
  };

  return (
    <span className={`inline-flex items-center gap-1.5 text-[9px] font-bold font-mono px-2 py-0.5 border rounded ${getBadgeStyle()} ${className}`}>
      <span className={`w-1 h-1 rounded-full ${getLedBg()}`} />
      <span>{getLabel()}</span>
      <span>|</span>
      <span>{(score * 100).toFixed(2)}%</span>
    </span>
  );
};
