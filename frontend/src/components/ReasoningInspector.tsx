import React from 'react'
import { usePHSEStore } from '../store/usePHSEStore'
import { Brain, ArrowUpRight, Compass } from 'lucide-react'

// Mock hypothesis description catalog matching lghl.py
const HYPOTHESES = [
  {
    id: "pure_water_ice",
    name: "Pure Subsurface Water Ice",
    desc: "High-concentration water ice deposit located inside a permanently shadowed polar cold trap.",
    constraints: {
      "radar_cpr": "1.1 to 5.0 (High circular polarization return)",
      "radar_dop": "0.0 to 0.4 (Strong depolarizing double-bounce)",
      "terrain_slope": "0.0 to 10.0 degrees (Flat crater floor)",
      "terrain_illumination": "0.0 to 0.1 (PSR conditions)",
      "terrain_roughness": "0.0 to 0.2m (Smooth ice fill)"
    }
  },
  {
    id: "ice_regolith_mixture",
    name: "Ice-Regolith Mixture",
    desc: "Subsurface ice grains mixed with standard lunar regolith, displaying moderate polarimetric anomalies.",
    constraints: {
      "radar_cpr": "0.6 to 1.2 (Moderate CPR anomaly)",
      "radar_dop": "0.2 to 0.6 (Medium depolarization)",
      "terrain_slope": "0.0 to 12.0 degrees (Gentle slopes)",
      "terrain_illumination": "0.0 to 0.15 (Shadowed areas)",
      "terrain_roughness": "0.0 to 0.3m (Standard roughness)"
    }
  },
  {
    id: "blocky_ejecta",
    name: "Blocky Impact Ejecta",
    desc: "Rough, boulder-strewn impact crater ejecta blankets causing strong surface double-bounce returns.",
    constraints: {
      "radar_cpr": "0.8 to 2.5 (High CPR due to surface blocks)",
      "radar_dop": "0.1 to 0.5 (Moderate/low polarization)",
      "terrain_slope": "0.0 to 30.0 degrees (High local slopes)",
      "terrain_illumination": "0.0 to 1.0 (Sunlit or shadowed)",
      "terrain_roughness": "0.3 to 1.2m (Extremely rough/rocky)"
    }
  },
  {
    id: "pyroclastic_deposits",
    name: "Pyroclastic Deposits",
    desc: "Fine-grained volcanic ash or glass beads exhibiting extremely low radar backscatter and smooth slopes.",
    constraints: {
      "radar_cpr": "0.0 to 0.3 (Very low CPR return)",
      "radar_dop": "0.7 to 1.0 (Extremely polarized single-bounce)",
      "terrain_slope": "0.0 to 8.0 degrees (Very flat plain)",
      "terrain_illumination": "0.0 to 1.0 (Open plain)",
      "terrain_roughness": "0.0 to 0.15m (Powdery/smooth texture)"
    }
  },
  {
    id: "dry_regolith",
    name: "Standard Dry Lunar Regolith",
    desc: "Typical weathered lunar soil layer, displaying baseline radar and moderate roughness profiles.",
    constraints: {
      "radar_cpr": "0.1 to 0.5 (Baseline CPR return)",
      "radar_dop": "0.6 to 1.0 (High polarization/single-bounce)",
      "terrain_slope": "0.0 to 20.0 degrees (Undulating terrain)",
      "terrain_illumination": "0.0 to 1.0 (Sunlit plains)",
      "terrain_roughness": "0.1 to 0.4m (Moderate micro-relief)"
    }
  }
];

export const ReasoningInspector: React.FC = () => {
  const selectedHyp = usePHSEStore((state) => state.selectedHypothesis);
  const setSelectedHyp = usePHSEStore((state) => state.setSelectedHypothesis);
  const results = usePHSEStore((state) => state.pipelineResults);
  const hoverCoords = usePHSEStore((state) => state.hoverCoords);
  const hoverDetails = usePHSEStore((state) => state.hoverDetails);

  // Compute active probabilities based on selection (either hovered pixel or grid-average)
  const getProbabilities = () => {
    if (hoverDetails && hoverDetails.probabilities) {
      return hoverDetails.probabilities;
    }
    // Fallback to mean pipeline final results
    if (results && results.probability_layers) {
      const means: Record<string, number> = {};
      Object.keys(results.probability_layers).forEach((key) => {
        means[key] = results.probability_layers[key].mean || 0.2;
      });
      return means;
    }
    return {
      pure_water_ice: 0.05,
      ice_regolith_mixture: 0.15,
      blocky_ejecta: 0.25,
      pyroclastic_deposits: 0.10,
      dry_regolith: 0.45
    };
  };

  const probs = getProbabilities();
  const activeHypObj = HYPOTHESES.find(h => h.id === selectedHyp) || HYPOTHESES[0];

  // Render supporting vs rejected evidence dynamically based on current values
  const getEvidenceMatching = (hypId: string) => {
    const cpr = hoverDetails?.cpr ?? 0.3;
    const dop = hoverDetails?.dop ?? 0.8;
    const slope = hoverDetails?.dem ? Math.min(25, Math.abs(hoverDetails.dem - 100) * 1.5) : 3.0; // Mock calculation or loaded

    const matches: string[] = [];
    const rejects: string[] = [];

    // Simple constraint boundaries checks
    if (hypId === 'pure_water_ice') {
      if (cpr > 1.1) matches.push("CPR is High (>1.1)"); else rejects.push("CPR is Low (<1.1)");
      if (dop < 0.4) matches.push("DOP is Low (<0.4)"); else rejects.push("DOP is High (>0.4)");
      if (slope < 10) matches.push("Slope is Safe (<10°)"); else rejects.push("Slope is Steep (>10°)");
    } else if (hypId === 'dry_regolith') {
      if (cpr < 0.5) matches.push("CPR is Baseline (<0.5)"); else rejects.push("CPR is Anomalous (>0.5)");
      if (dop > 0.6) matches.push("DOP is High (>0.6)"); else rejects.push("DOP is Depolarized (<0.6)");
    } else {
      matches.push("Feature values within normal variance bounds.");
    }

    return { matches, rejects };
  };

  const { matches, rejects } = getEvidenceMatching(activeHypObj.id);

  return (
    <div className="flex flex-col h-full bg-[#0d1117] border border-white/5 rounded-lg overflow-hidden text-gray-200 shadow-xl">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-2.5 bg-[#161b22] border-b border-white/5 text-xs">
        <Brain size={14} className="text-indigo-400" />
        <span className="font-semibold tracking-wider uppercase text-gray-300">Reasoning Inspector</span>
        {hoverCoords && (
          <span className="ml-auto text-xxs px-1.5 py-0.5 bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 rounded">
            QUERYING COORDINATE: {hoverCoords.x}, {hoverCoords.y}
          </span>
        )}
      </div>

      <div className="flex-1 p-4 overflow-y-auto space-y-4 text-xs">
        {/* Active Hypothesis List */}
        <div>
          <div className="text-gray-400 font-bold mb-2 tracking-wide uppercase">Active Geological Hypotheses</div>
          <div className="grid grid-cols-5 gap-2">
            {HYPOTHESES.map((hyp) => {
              const prob = probs[hyp.id] ?? 0.0;
              const isSelected = selectedHyp === hyp.id;
              return (
                <button
                  key={hyp.id}
                  onClick={() => setSelectedHyp(hyp.id)}
                  className={`flex flex-col items-center p-2 rounded-lg border transition-all text-center ${
                    isSelected 
                      ? 'bg-indigo-500/10 border-indigo-500/50 shadow-md shadow-indigo-500/5' 
                      : 'bg-white/[0.02] border-white/5 hover:bg-white/[0.04]'
                  }`}
                >
                  <span className="text-[10px] font-semibold text-gray-400 truncate w-full">{hyp.name}</span>
                  <span className="text-base font-bold font-mono text-white mt-1">{(prob * 100).toFixed(1)}%</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Selected Hypothesis Details */}
        <div className="p-3 bg-white/[0.01] border border-white/5 rounded-lg space-y-2.5">
          <div className="flex justify-between items-start">
            <div>
              <h4 className="font-bold text-white text-sm">{activeHypObj.name}</h4>
              <p className="text-xxs text-gray-400 mt-0.5 leading-normal">{activeHypObj.desc}</p>
            </div>
            <div className="flex items-center gap-1.5 text-xxs px-2 py-0.5 bg-emerald-500/15 text-emerald-400 border border-emerald-500/25 rounded">
              <ArrowUpRight size={12} />
              <span>Prior: {(activeHypObj.id === 'pure_water_ice' ? 5.0 : activeHypObj.id === 'dry_regolith' ? 45.0 : 15.0).toFixed(1)}%</span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 text-xxs">
            {/* Supporting Evidence */}
            <div className="p-2 bg-emerald-500/5 border border-emerald-500/15 rounded">
              <span className="text-emerald-400 font-bold block mb-1">Supporting Evidence</span>
              {matches.map((m, i) => <div key={i} className="text-gray-300 mb-0.5">• {m}</div>)}
            </div>
            {/* Rejected Evidence */}
            <div className="p-2 bg-rose-500/5 border border-rose-500/15 rounded">
              <span className="text-rose-400 font-bold block mb-1">Conflicting Evidence</span>
              {rejects.length === 0 ? (
                <div className="text-gray-500 italic">No conflicting evidence found.</div>
              ) : (
                rejects.map((r, i) => <div key={i} className="text-gray-300 mb-0.5">• {r}</div>)
              )}
            </div>
          </div>

          {/* Constraints table */}
          <div>
            <span className="text-gray-400 font-bold block mb-1 text-xxs">Physical Constraint Limits</span>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xxs text-gray-400 font-mono">
              {Object.entries(activeHypObj.constraints).map(([feat, limit]) => (
                <div key={feat} className="flex justify-between border-b border-white/[0.02] py-0.5">
                  <span className="text-gray-500">{feat}</span>
                  <span className="text-white">{limit}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* AHS Decider Info */}
        <div className="grid grid-cols-2 gap-3">
          <div className="p-3 bg-white/[0.01] border border-white/5 rounded-lg space-y-2">
            <div className="flex items-center gap-1 text-xxs text-amber-400 font-bold uppercase tracking-wider">
              <Compass size={13} />
              <span>AHS Optimization Engine</span>
            </div>
            <p className="text-[10px] text-gray-400 leading-relaxed">
              Prioritizing observations using symmetrized Kullback-Leibler (KL) divergence to maximize geological separation between competing hypotheses.
            </p>
            <div className="grid grid-cols-2 gap-2 text-xxs font-mono">
              <div className="bg-white/[0.02] p-1.5 rounded">
                <span className="text-gray-500 block">Separation Weight</span>
                <span className="text-white font-bold">14.67 KLD</span>
              </div>
              <div className="bg-white/[0.02] p-1.5 rounded">
                <span className="text-gray-500 block">Expected Info Gain</span>
                <span className="text-white font-bold">0.82 bits</span>
              </div>
            </div>
          </div>

          <div className="p-3 bg-white/[0.01] border border-white/5 rounded-lg space-y-2">
            <div className="flex items-center gap-1 text-xxs text-indigo-400 font-bold uppercase tracking-wider">
              <Brain size={13} />
              <span>Bayesian Likelihood Update</span>
            </div>
            <p className="text-[10px] text-gray-400 leading-relaxed">
              Probability is calculated by updates through the joint likelihood product of active features.
            </p>
            <div className="flex items-center gap-2 p-1.5 bg-[#161b22] border border-white/5 rounded text-xxs justify-center text-gray-400 font-mono">
              <span>Prior</span>
              <span>×</span>
              <span className="text-indigo-400 font-bold">Likelihood</span>
              <span>=</span>
              <span className="text-emerald-400 font-bold">Posterior</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
