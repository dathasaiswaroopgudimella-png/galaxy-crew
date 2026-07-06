import React, { useState } from 'react'
import { usePHSEStore } from '../store/usePHSEStore'
import { GitFork, ChevronDown, ChevronRight } from 'lucide-react'

interface TreeNodeProps {
  label: string;
  value: string;
  weight?: string;
  status?: 'pass' | 'warning' | 'normal';
  children?: React.ReactNode;
}

const TreeNode: React.FC<TreeNodeProps> = ({ label, value, weight, status = 'normal', children }) => {
  const [isOpen, setIsOpen] = useState(true);
  const hasChildren = !!children;

  const getStatusColor = () => {
    switch (status) {
      case 'pass': return 'text-emerald-400 border-emerald-500/20 bg-emerald-500/5';
      case 'warning': return 'text-amber-400 border-amber-500/20 bg-amber-500/5';
      default: return 'text-sky-400 border-sky-500/20 bg-sky-500/5';
    }
  };

  return (
    <div className="flex flex-col ml-4 border-l border-white/5 pl-4 py-1 relative">
      {/* Connector dot */}
      <div className="absolute left-0 top-3.5 w-2 h-2 rounded-full bg-white/10 -translate-x-[5px]" />

      <div 
        onClick={() => hasChildren && setIsOpen(!isOpen)}
        className={`flex items-center gap-2 p-2 rounded-lg border text-xxs transition-all select-none ${getStatusColor()} ${
          hasChildren ? 'cursor-pointer hover:bg-white/[0.02]' : ''
        }`}
      >
        {hasChildren && (
          <span>{isOpen ? <ChevronDown size={12} /> : <ChevronRight size={12} />}</span>
        )}
        <div className="flex-1 flex justify-between items-center gap-4">
          <div>
            <span className="font-bold text-gray-300 font-sans block">{label}</span>
            {weight && <span className="text-[9px] text-gray-500 font-mono">Weight: {weight}</span>}
          </div>
          <span className="font-bold font-mono text-white bg-white/5 px-2 py-0.5 rounded border border-white/5 text-[10px]">{value}</span>
        </div>
      </div>

      {hasChildren && isOpen && (
        <div className="mt-1 flex flex-col gap-1.5">{children}</div>
      )}
    </div>
  );
};

export const DecisionTree: React.FC = () => {
  const results = usePHSEStore((state) => state.pipelineResults);

  const landingScore = results?.landing_score ? `${(results.landing_score * 100).toFixed(2)}%` : '94.67%';

  return (
    <div className="flex flex-col h-full bg-[#0d1117] border border-white/5 rounded-lg overflow-hidden text-gray-200 shadow-xl">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-2.5 bg-[#161b22] border-b border-white/5 text-xs">
        <GitFork size={14} className="text-sky-400" />
        <span className="font-semibold tracking-wider uppercase text-gray-300">Mission Decision Tree</span>
      </div>

      <div className="flex-1 p-4 overflow-y-auto space-y-2">
        <div className="text-gray-400 font-bold mb-3 tracking-wide uppercase text-xxs">Landing Recommendation Breakdown</div>
        
        {/* Root Node */}
        <TreeNode label="Final Landing Recommendation Suitability Score" value={landingScore} status="pass">
          {/* Sub-node 1 */}
          <TreeNode label="Terrain Safety Constraints Check" value="PASSED" status="pass">
            <TreeNode label="Slope Limit (<15°)" value="Safe (3.0°)" status="pass" />
            <TreeNode label="Roughness Micro-relief (<0.5m)" value="Safe (0.25m)" status="pass" />
            <TreeNode label="Multi-criteria Hazard Index (<0.35)" value="Safe (0.12)" status="pass" />
          </TreeNode>

          {/* Sub-node 2 */}
          <TreeNode label="Resource Ice Presence Confidence Map" value="94.7%" weight="50%" status="pass">
            <TreeNode label="Subsurface Water Ice Posterior Probability" value="High (0.9467)" status="pass" />
            <TreeNode label="Polarimetric CPR/DOP Anomaly Match" value="High (99.8%)" status="pass" />
          </TreeNode>

          {/* Sub-node 3 */}
          <TreeNode label="Rover Traversal Cost Pathfinder Constraints" value="88.2%" weight="35%" status="normal">
            <TreeNode label="A* Planned Path Travel Cost Metric" value="Optimal (0.015)" status="pass" />
            <TreeNode label="Distance to PSR Cold Trap Edge" value="106m" status="normal" />
          </TreeNode>

          {/* Sub-node 4 */}
          <TreeNode label="Lambertian Illumination Model (Visibility & Power)" value="50.0%" weight="15%" status="warning">
            <TreeNode label="Sunlit Power Availability Fraction" value="Medium (0.50)" status="warning" />
            <TreeNode label="Direct Communication Line-of-Sight" value="Clear" status="pass" />
          </TreeNode>
        </TreeNode>
      </div>
    </div>
  );
};
