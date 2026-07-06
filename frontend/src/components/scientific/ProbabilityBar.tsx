import React from 'react'

interface ProbabilityBarProps {
  value: number; // 0.0 to 1.0
  colorClass?: string;
  heightClass?: string;
}

export const ProbabilityBar: React.FC<ProbabilityBarProps> = ({
  value,
  colorClass = 'bg-cyan-500',
  heightClass = 'h-1.5',
}) => {
  const percent = Math.min(100, Math.max(0, value * 100));

  return (
    <div className="w-full bg-white/[0.02] border border-white/10 rounded-sm p-[1.5px] relative">
      <div 
        className={`transition-all duration-500 rounded-sm relative overflow-hidden ${colorClass} ${heightClass}`} 
        style={{ width: `${percent}%` }}
      >
        {/* Glow sheen effect */}
        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-pulse" />
      </div>
    </div>
  );
};
