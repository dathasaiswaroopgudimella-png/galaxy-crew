import React from 'react'

interface MetricCardProps {
  label: string;
  value: string | number;
  subValue?: string;
  icon?: React.ReactNode;
  trend?: {
    direction: 'up' | 'down' | 'stable';
    text: string;
  };
  valueColor?: string;
  statusColor?: 'cyan' | 'amber' | 'emerald' | 'rose';
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  subValue,
  icon,
  trend,
  valueColor = 'text-white',
  statusColor = 'cyan',
}) => {
  const getGlowBorder = () => {
    switch (statusColor) {
      case 'amber': return 'border-amber-500/20 bg-amber-950/5 hover:border-amber-500/40';
      case 'emerald': return 'border-emerald-500/20 bg-emerald-950/5 hover:border-emerald-500/40';
      case 'rose': return 'border-rose-500/20 bg-rose-950/5 hover:border-rose-500/40';
      default: return 'border-cyan-500/20 bg-cyan-950/5 hover:border-cyan-500/40';
    }
  };

  const getLedBg = () => {
    switch (statusColor) {
      case 'amber': return 'bg-amber-400 shadow-[0_0_8px_#fbbf24]';
      case 'emerald': return 'bg-emerald-400 shadow-[0_0_8px_#34d399]';
      case 'rose': return 'bg-rose-400 shadow-[0_0_8px_#f87171]';
      default: return 'bg-cyan-400 shadow-[0_0_8px_#22d3ee]';
    }
  };

  return (
    <div className={`border p-3 rounded-lg flex items-start justify-between gap-3 transition-all duration-300 relative group overflow-hidden ${getGlowBorder()}`}>
      {/* Decorative cyber corner ticks */}
      <div className="absolute top-0 left-0 w-1.5 h-1.5 border-t border-l border-white/20" />
      <div className="absolute bottom-0 right-0 w-1.5 h-1.5 border-b border-r border-white/20" />

      <div className="space-y-1">
        <span className="text-[8px] text-white/50 font-mono tracking-widest block uppercase font-bold">{label}</span>
        <div className="flex items-baseline gap-1.5">
          {/* Action indicator LED light */}
          <span className={`w-1 h-1 rounded-full mr-1.5 self-center ${getLedBg()}`} />
          <span className={`text-sm font-extrabold font-mono tracking-wider ${valueColor}`}>{value}</span>
          {subValue && <span className="text-[9px] text-white/40 font-mono font-medium">{subValue}</span>}
        </div>
        {trend && (
          <div className="flex items-center gap-1">
            <span className={`text-[8px] font-mono font-bold tracking-wider ${
              trend.direction === 'up' ? 'text-emerald-400' : trend.direction === 'down' ? 'text-rose-400' : 'text-gray-400'
            }`}>
              {trend.direction === 'up' ? '▲' : trend.direction === 'down' ? '▼' : '◆'} {trend.text}
            </span>
          </div>
        )}
      </div>
      {icon && <div className="text-white/30 group-hover:text-white/60 transition-colors p-1 bg-white/[0.01] border border-white/5 rounded">{icon}</div>}
    </div>
  );
};
