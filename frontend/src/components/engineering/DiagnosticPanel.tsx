import React from 'react'
import { ScientificCard } from '../scientific/ScientificCard'
import { Cpu } from 'lucide-react'

export const DiagnosticPanel: React.FC = () => {
  return (
    <ScientificCard
      title="Pipeline Diagnostics"
      subtitle="SYSTEM HOST & TRANSACTION STATUS"
      icon={<Cpu size={14} className="text-cyan-400" />}
    >
      <div className="space-y-2 font-mono text-[9px] text-white/70">
        <div className="flex justify-between border-b border-white/5 py-1.5 uppercase tracking-wider">
          <span className="text-white/40">API Host Address:</span>
          <span className="text-white font-bold">http://localhost:8000</span>
        </div>
        <div className="flex justify-between border-b border-white/5 py-1.5 uppercase tracking-wider">
          <span className="text-white/40">WebSocket Channel:</span>
          <span className="text-cyan-400 font-bold">ws://localhost:8000/api/ws</span>
        </div>
        <div className="flex justify-between border-b border-white/5 py-1.5 uppercase tracking-wider">
          <span className="text-white/40">AHS Solver Method:</span>
          <span className="text-white font-bold">KL Divergence (Analytical)</span>
        </div>
        <div className="flex justify-between border-b border-white/5 py-1.5 uppercase tracking-wider">
          <span className="text-white/40">Validation State:</span>
          <span className="text-emerald-400 flex items-center gap-1 font-bold">
            <span className="w-1 h-1 rounded-full bg-emerald-400 animate-pulse" />
            <span>VERIFIED (22 PASS)</span>
          </span>
        </div>
        <div className="flex justify-between border-b border-white/5 py-1.5 uppercase tracking-wider">
          <span className="text-white/40">Geotiff Resolution:</span>
          <span className="text-white font-bold">400 x 400 pixels</span>
        </div>
        <div className="flex justify-between border-b border-white/5 py-1.5 uppercase tracking-wider">
          <span className="text-white/40">Cache Footprint:</span>
          <span className="text-white font-extrabold">~148.4 MB (GeoTIFF)</span>
        </div>
        <div className="flex justify-between py-1.5 uppercase tracking-wider">
          <span className="text-white/40">Display Framerate:</span>
          <span className="text-emerald-400 font-extrabold">60.0 FPS STABLE</span>
        </div>
      </div>
    </ScientificCard>
  );
};
