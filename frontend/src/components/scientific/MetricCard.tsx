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
      case 'amber': return 'border-amber-500/25 bg-amber-950/5 hover:border-amber-500/35';
      case 'emerald': return 'border-emerald-500/25 bg-emerald-950/5 hover:border-emerald-500/35';
      case 'rose': return 'border-rose-500/25 bg-rose-950/5 hover:border-rose-500/35';
      default: return 'border-cyan-500/25 bg-cyan-950/5 hover:border-cyan-500/35';
    }
  };

  const getLedBg = () => {
    switch (statusColor) {
      case 'amber': return 'bg-amber-400 shadow-[0_0_8px_#fbbf24]';
      case 'emerald': return 'bg-emerald-400 shadow-[0_0_8px_#34d399]';
      case 'rose': return 'bg-rose-400 shadow-[0_0_8px_#f87171]';
      default: return 'bg-cyan-400 shadow-[0_0_8px_#00e5ff]';
    }
  };

  return (
    <div className={`p-3 border rounded flex flex-col justify-between gap-2.5 transition-all duration-300 relative group overflow-hidden ${getGlowBorder()}`}>
      {/* Decorative cyber corner ticks */}
      <div className="absolute top-0 left-0 w-1 h-1 border-t border-l border-white/10" />
      <div className="absolute bottom-0 right-0 w-1 h-1 border-b border-r border-white/10" />

      <div className="flex items-center justify-between gap-2 select-none">
        <span className="text-[7.5px] text-white/40 font-mono tracking-widest block uppercase font-bold">{label}</span>
        {icon && <div className="text-white/20 group-hover:text-white/40 transition-colors">{icon}</div>}
      </div>

      <div className="flex items-center gap-2">
        {/* Action indicator LED light */}
        <span className={`w-1 h-1 rounded-full ${getLedBg()}`} />
        <span className={`text-xs font-black font-mono tracking-wider uppercase ${valueColor}`}>{value}</span>
        {subValue && <span className="text-[8px] text-white/30 font-mono">{subValue}</span>}
      </div>
      
      {trend && (
        <div className="text-[7.5px] font-mono tracking-wider uppercase">
          <span className={trend.direction === 'up' ? 'text-emerald-400' : trend.direction === 'down' ? 'text-rose-400' : 'text-white/40'}>
            {trend.direction === 'up' ? '▲' : trend.direction === 'down' ? '▼' : '◆'} {trend.text}
          </span>
        </div>
      )}
    </div>
  );
};
