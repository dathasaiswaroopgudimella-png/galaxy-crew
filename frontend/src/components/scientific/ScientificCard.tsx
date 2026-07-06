import React from 'react'

interface ScientificCardProps {
  title: string;
  subtitle?: string;
  icon?: React.ReactNode;
  actions?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  theme?: 'cyan' | 'amber' | 'emerald';
}

export const ScientificCard: React.FC<ScientificCardProps> = ({
  title,
  subtitle,
  icon,
  actions,
  children,
  className = '',
  theme = 'cyan',
}) => {
  const getThemeClass = () => {
    switch (theme) {
      case 'amber':
        return 'border-amber-500/25 bg-amber-950/20 text-amber-100 shadow-[0_0_15px_rgba(245,158,11,0.02)]';
      case 'emerald':
        return 'border-emerald-500/25 bg-emerald-950/20 text-emerald-100 shadow-[0_0_15px_rgba(16,185,129,0.02)]';
      default:
        return 'border-cyan-500/20 bg-slate-950/40 text-cyan-50 shadow-[0_0_15px_rgba(0,229,255,0.02)]';
    }
  };

  const getHeaderBg = () => {
    switch (theme) {
      case 'amber':
        return 'bg-amber-500/10 border-b border-amber-500/10';
      case 'emerald':
        return 'bg-emerald-500/10 border-b border-emerald-500/10';
      default:
        return 'bg-cyan-500/5 border-b border-cyan-500/10';
    }
  };

  const getAccentColor = () => {
    switch (theme) {
      case 'amber': return 'text-amber-400';
      case 'emerald': return 'text-emerald-400';
      default: return 'text-cyan-400';
    }
  };

  return (
    <div className={`flex flex-col h-full border rounded-lg backdrop-blur-xl overflow-hidden transition-all duration-300 relative ${getThemeClass()} ${className}`}>
      {/* Corner crosshairs for technical HUD aesthetic */}
      <div className="absolute top-1 left-1 text-[8px] text-white/10 select-none pointer-events-none font-mono">+</div>
      <div className="absolute top-1 right-1 text-[8px] text-white/10 select-none pointer-events-none font-mono">+</div>
      <div className="absolute bottom-1 left-1 text-[8px] text-white/10 select-none pointer-events-none font-mono">+</div>
      <div className="absolute bottom-1 right-1 text-[8px] text-white/10 select-none pointer-events-none font-mono">+</div>

      {/* Header */}
      <div className={`flex items-center justify-between px-4 py-2 select-none shrink-0 ${getHeaderBg()}`}>
        <div className="flex items-center gap-2">
          {icon && <div className={`${getAccentColor()} opacity-80`}>{icon}</div>}
          <div>
            <span className="font-sans font-black tracking-wider uppercase text-[10px] block">{title}</span>
            {subtitle && <span className="font-mono text-[8px] text-white/40 block leading-tight tracking-wider">{subtitle}</span>}
          </div>
        </div>
        {actions && <div className="flex items-center gap-2 relative z-10">{actions}</div>}
      </div>

      {/* Body */}
      <div className="flex-1 p-3.5 overflow-y-auto scrollbar-thin relative z-0">
        {children}
      </div>
    </div>
  );
};
