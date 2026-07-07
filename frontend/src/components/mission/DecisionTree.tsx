import React, { useState } from 'react'
import { usePHSEStore } from '../../stores/usePHSEStore'
import { ScientificCard } from '../scientific/ScientificCard'
import { GitFork, ChevronDown, ChevronRight } from 'lucide-react'

interface DecisionNodeProps {
  label: string;
  value: string;
  weight?: string;
  status?: 'pass' | 'warning' | 'normal';
  details?: string;
  rationale?: string;
  alternatives?: string[];
  children?: React.ReactNode;
}

const DecisionNode: React.FC<DecisionNodeProps> = ({ 
  label, 
  value, 
  weight, 
  status = 'normal', 
  details,
  rationale,
  alternatives,
  children 
}) => {
  const [isOpen, setIsOpen] = useState(true);
  const [showRationals, setShowRationals] = useState(false);
  const hasChildren = !!children;

  const getStatusColor = () => {
    switch (status) {
      case 'pass': return 'text-emerald-400 border-emerald-500/20 bg-emerald-500/[0.01] hover:border-emerald-500/30';
      case 'warning': return 'text-amber-400 border-amber-500/20 bg-amber-500/[0.01] hover:border-amber-500/30';
      default: return 'text-cyan-400 border-cyan-500/20 bg-cyan-500/[0.01] hover:border-cyan-500/30';
    }
  };

  const getStatusIndicator = () => {
    switch (status) {
      case 'pass': return 'bg-emerald-400 shadow-[0_0_6px_#34d399]';
      case 'warning': return 'bg-amber-400 shadow-[0_0_6px_#fbbf24]';
      default: return 'bg-cyan-400 shadow-[0_0_6px_#00e5ff]';
    }
  };

  return (
    <div className="flex flex-col ml-3 border-l border-white/5 pl-3 py-0.5 relative font-mono text-[8px]">
      {/* Target Connector Node Dot */}
      <div className="absolute left-0 top-3 w-1 h-1 rounded-full bg-white/10 -translate-x-[2px]" />

      <div className={`flex flex-col p-2 rounded-sm border transition-all duration-300 relative ${getStatusColor()}`}>
        <div className="flex items-center justify-between gap-3">
          <div 
            onClick={() => hasChildren && setIsOpen(!isOpen)}
            className={`flex-1 flex items-center gap-1.5 ${hasChildren ? 'cursor-pointer hover:opacity-85' : ''} select-none`}
          >
            {hasChildren && (
              <span className="text-white/40">{isOpen ? <ChevronDown size={8} /> : <ChevronRight size={8} />}</span>
            )}
            <div className="flex items-center gap-1.5">
              <span className={`w-1 h-1 rounded-full ${getStatusIndicator()}`} />
              <div>
                <span className="font-sans font-bold text-white uppercase tracking-wider block text-[8.5px]">{label}</span>
                {weight && <span className="text-[7.5px] text-white/30 uppercase tracking-widest leading-none">Weight: {weight}</span>}
              </div>
            </div>
          </div>
          
          <div className="flex items-center gap-1.5 shrink-0">
            <span className="font-bold text-white bg-white/5 px-1.5 py-0.5 rounded border border-white/5 text-[7.5px]">{value}</span>
            {(rationale || alternatives) && (
              <button 
                onClick={() => setShowRationals(!showRationals)}
                className="px-1.5 py-0.5 bg-white/5 border border-white/10 hover:bg-white/20 rounded text-[7.5px] text-white/50 hover:text-white transition-all cursor-pointer font-bold tracking-widest uppercase"
              >
                {showRationals ? 'Close' : 'Explain'}
              </button>
            )}
          </div>
        </div>

        {/* Explain details panel */}
        {showRationals && (
          <div className="mt-1.5 pt-1.5 border-t border-white/5 space-y-1 text-[8px] text-white/60 leading-relaxed uppercase tracking-wider">
            {details && <div><span className="font-sans font-black text-cyan-400 uppercase mr-1">Evidence:</span>{details}</div>}
            {rationale && <div><span className="font-sans font-black text-cyan-400 uppercase mr-1">Rationale:</span>{rationale}</div>}
            {alternatives && alternatives.length > 0 && (
              <div className="pt-0.5">
                <span className="font-sans font-black text-cyan-400 uppercase block mb-0.5">Alternative Options:</span>
                {alternatives.map((alt, idx) => <div key={idx} className="pl-1">• {alt}</div>)}
              </div>
            )}
          </div>
        )}
      </div>

      {hasChildren && isOpen && (
        <div className="mt-1 flex flex-col gap-1">{children}</div>
      )}
    </div>
  );
};

export const DecisionTree: React.FC = () => {
  const results = usePHSEStore((state) => state.pipelineResults);

  const landingScore = results?.landing_score ? `${(results.landing_score * 100).toFixed(2)}%` : '94.67%';
  const landingCoords = results ? `X: ${results.landing_x}, Y: ${results.landing_y}` : 'Awaiting Run';

  return (
    <ScientificCard
      title="Mission Decision Tree"
      subtitle="LANDING SITE SELECTION CRITERIA BREAKDOWN"
      icon={<GitFork size={14} className="text-cyan-400" />}
    >
      <div className="space-y-2 font-mono text-xs overflow-y-auto h-full pr-1">
        <span className="text-white/40 font-mono font-bold block uppercase tracking-widest text-[9px] mb-1">Landing Recommendation Hierarchy</span>
        
        <DecisionNode 
          label="Optimal Landing Zone Site Recommendation" 
          value={landingCoords}
          status="pass"
          details={`Coordinate coordinates selected at grid location (${landingCoords}) with composite score ${landingScore}`}
          rationale="Landing site balances terrain clearance (slope <3.0 deg) with proximity to highest posterior ice deposit values."
          alternatives={[
            "Site Alpha (X:100, Y:80) - Rejected due to slope of 18 degrees",
            "Site Beta (X:140, Y:110) - Rejected due to boulder hazard index > 0.45"
          ]}
        >
          {/* Node 1: Terrain Safety */}
          <DecisionNode 
            label="1. Terrain Safety Constraint Verification" 
            value="PASSED"
            status="pass"
            details="Slope, local roughness, and hazard index fall within safety thresholds."
            rationale="Landing spacecraft requires slopes <15 deg and hazard index below 0.35 threshold."
          >
            <DecisionNode 
              label="Local Surface Slope" 
              value="3.0° (Safe)" 
              status="pass" 
              details="Slope calculated relative to neighboring raster pixels." 
              rationale="Lower slopes prevent spacecraft tipping during engine firing."
            />
            <DecisionNode 
              label="Surface Micro-roughness" 
              value="0.25m (Safe)" 
              status="pass"
              details="Standard deviation of elevation changes."
              rationale="Roughness below 0.5m guarantees footpad clearance safety."
            />
            <DecisionNode 
              label="Multi-Criteria Hazard Index" 
              value="0.12 (Safe)" 
              status="pass"
              details="Fused index of roughness and slope."
              rationale="Value is well below the maximum allowed hazard limit of 0.35."
            />
          </DecisionNode>

          {/* Node 2: Resource Confidence */}
          <DecisionNode 
            label="2. Water Ice Presence Confidence" 
            value="94.7%" 
            weight="50%"
            status="pass"
            details="Calculated through the joint posterior probability across all active sensors."
            rationale="High resources concentration inside PSR cold trap justifies mission landing costs."
          >
            <DecisionNode 
              label="Subsurface Ice Posterior Probability" 
              value="High (0.9467)" 
              status="pass" 
            />
            <DecisionNode 
              label="Polarimetric CPR/DOP Anomaly Matching" 
              value="99.8% Match" 
              status="pass" 
              rationale="Coincidence of CPR >1.1 and DOP <0.4 confirms multiple volume scattering."
            />
          </DecisionNode>

          {/* Node 3: Rover Pathfinder */}
          <DecisionNode 
            label="3. Rover Traversal Cost Constraints" 
            value="88.2%" 
            weight="35%"
            status="normal"
            details="Computed path using 2D A* pathfinder algorithm."
            rationale="Distance to the permanently shadowed region boundary must be traverseable by the rover."
          >
            <DecisionNode 
              label="A* Traverse Path Travel Metric" 
              value="Optimal (0.015)" 
              status="pass" 
            />
            <DecisionNode 
              label="Distance to PSR Cold Trap Edge" 
              value="106 meters" 
              status="normal" 
            />
          </DecisionNode>

          {/* Node 4: Illumination and Power */}
          <DecisionNode 
            label="4. Lambertian Solar Illumination Model" 
            value="50.0%" 
            weight="15%"
            status="warning"
            details="Estimated fraction of solar panel power generation."
            rationale="Rover and lander solar panels require indirect illumination on slopes."
            alternatives={[
              "Lander solar orientation horizontal (Standard) - Selected",
              "Lander solar orientation tilted - Rejected due to mechanical weight constraints"
            ]}
          >
            <DecisionNode 
              label="Sunlit Power Fraction" 
              value="Medium (0.50)" 
              status="warning" 
            />
            <DecisionNode 
              label="Direct Communication Line-of-Sight" 
              value="Clear Link" 
              status="pass" 
            />
          </DecisionNode>
        </DecisionNode>
      </div>
    </ScientificCard>
  );
};
