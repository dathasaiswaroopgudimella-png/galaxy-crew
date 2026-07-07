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
        return 'border-amber-500/25 shadow-[0_0_15px_rgba(245,158,11,0.02)]';
      case 'emerald':
        return 'border-emerald-500/25 shadow-[0_0_15px_rgba(16,185,129,0.02)]';
      default:
        return 'border-cyan-500/20 shadow-[0_0_15px_rgba(0,229,255,0.02)]';
    }
  };

  const getAccentColor = () => {
    switch (theme) {
      case 'amber': return 'text-amber-400';
      case 'emerald': return 'text-emerald-400';
      default: return 'text-cyan-400';
    }
  };

  const getLeftLitBorder = () => {
    switch (theme) {
      case 'amber': return 'border-l-2 border-amber-500';
      case 'emerald': return 'border-l-2 border-emerald-500';
      default: return 'border-l-2 border-cyan-400';
    }
  };

  return (
    <div className={`flex flex-col h-full spatial-glass rounded-md overflow-hidden transition-all duration-300 relative ${getThemeClass()} ${className}`}>
      {/* Corner crosshairs for technical HUD aesthetic */}
      <div className="absolute top-1 left-1 text-[7px] text-white/10 select-none pointer-events-none font-mono font-light">+</div>
      <div className="absolute top-1 right-1 text-[7px] text-white/10 select-none pointer-events-none font-mono font-light">+</div>
      <div className="absolute bottom-1 left-1 text-[7px] text-white/10 select-none pointer-events-none font-mono font-light">+</div>
      <div className="absolute bottom-1 right-1 text-[7px] text-white/10 select-none pointer-events-none font-mono font-light">+</div>

      {/* Header */}
      <div className={`flex items-center justify-between px-4 py-2 bg-white/[0.01] border-b border-white/5 select-none shrink-0 ${getLeftLitBorder()}`}>
        <div className="flex items-center gap-2">
          {icon && <div className={`${getAccentColor()} opacity-80 flex items-center justify-center`}>{icon}</div>}
          <div>
            <span className="font-sans font-black tracking-wider uppercase text-[9px] block text-white">{title}</span>
            {subtitle && <span className="font-mono text-[7px] text-white/30 block leading-tight tracking-wider uppercase">{subtitle}</span>}
          </div>
        </div>
        {actions && <div className="flex items-center gap-2 relative z-10">{actions}</div>}
      </div>

      {/* Body */}
      <div className="flex-1 p-4 overflow-y-auto scrollbar-thin relative z-0">
        {children}
      </div>
    </div>
  );
};
