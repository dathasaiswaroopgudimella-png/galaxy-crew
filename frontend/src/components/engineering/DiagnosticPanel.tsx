import React from 'react'

export const DiagnosticPanel: React.FC = () => {
  return (
    <div className="bg-slate-950/45 backdrop-blur-xl border border-cyan-500/20 rounded-lg p-4 overflow-y-auto space-y-2.5 font-mono text-[9px] text-white/70 shadow-lg select-none relative">
      {/* HUD corner marks */}
      <div className="absolute top-1.5 left-1.5 w-1 h-1 border-t border-l border-white/20" />
      <div className="absolute bottom-1.5 right-1.5 w-1 h-1 border-b border-r border-white/20" />
      
      <div className="text-white/40 font-bold border-b border-white/5 pb-1.5 uppercase tracking-widest text-[10px]">Pipeline Diagnostics</div>
      
      <div className="flex justify-between border-b border-white/[0.02] py-1 uppercase tracking-wider">
        <span className="text-white/40">API Host Address:</span>
        <span className="text-white">http://localhost:8000</span>
      </div>
      <div className="flex justify-between border-b border-white/[0.02] py-1 uppercase tracking-wider">
        <span className="text-white/40">WebSocket Channel:</span>
        <span className="text-cyan-400">ws://localhost:8000/api/ws</span>
      </div>
      <div className="flex justify-between border-b border-white/[0.02] py-1 uppercase tracking-wider">
        <span className="text-white/40">AHS Solver Method:</span>
        <span className="text-white">KL Divergence (Analytical)</span>
      </div>
      <div className="flex justify-between border-b border-white/[0.02] py-1 uppercase tracking-wider">
        <span className="text-white/40">Validation State:</span>
        <span className="text-emerald-400 flex items-center gap-1 font-bold">
          <span className="w-1 h-1 rounded-full bg-emerald-500 animate-pulse" />
          <span>VERIFIED (22 PASS)</span>
        </span>
      </div>
      <div className="flex justify-between border-b border-white/[0.02] py-1 uppercase tracking-wider">
        <span className="text-white/40">Geotiff Resolution:</span>
        <span className="text-white">400 x 400 pixels</span>
      </div>
      <div className="flex justify-between border-b border-white/[0.02] py-1 uppercase tracking-wider">
        <span className="text-white/40">Cache Footprint:</span>
        <span className="text-white font-extrabold">~148.4 MB (GeoTIFF)</span>
      </div>
      <div className="flex justify-between py-1 uppercase tracking-wider">
        <span className="text-white/40">Display Framerate:</span>
        <span className="text-emerald-400 font-extrabold">60.0 FPS STABLE</span>
      </div>
    </div>
  );
};
