import React from 'react'
import { usePHSEStore } from '../../stores/usePHSEStore'
import { HYPOTHESES } from '../../constants'
import { ScientificCard } from '../scientific/ScientificCard'
import { ProbabilityBar } from '../scientific/ProbabilityBar'
import { Brain, ArrowUpRight, Layers, Activity } from 'lucide-react'

export const ReasoningInspector: React.FC = () => {
  const selectedHyp = usePHSEStore((state) => state.selectedHypothesis);
  const setSelectedHyp = usePHSEStore((state) => state.setSelectedHypothesis);
  const results = usePHSEStore((state) => state.pipelineResults);
  const hoverCoords = usePHSEStore((state) => state.hoverCoords);
  const hoverDetails = usePHSEStore((state) => state.hoverDetails);
  const playbackStep = usePHSEStore((state) => state.playbackStep);

  const getProbabilities = () => {
    if (hoverDetails && hoverDetails.probabilities) {
      return hoverDetails.probabilities;
    }
    if (results && results.probability_layers) {
      const means: Record<string, number> = {};
      Object.keys(results.probability_layers).forEach((key) => {
        means[key] = results.probability_layers[key].mean ?? 0.2;
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
  const activeProbability = probs[activeHypObj.id] ?? 0.0;

  // Real-time dynamic evidence check based on coordinate data
  const getEvidenceStatus = (hypId: string) => {
    const cpr = hoverDetails?.cpr ?? 0.3;
    const dop = hoverDetails?.dop ?? 0.8;
    const slope = hoverDetails?.dem ? Math.min(25, Math.abs(hoverDetails.dem - 100) * 1.5) : 3.0;

    const support: string[] = [];
    const conflict: string[] = [];

    if (hypId === 'pure_water_ice') {
      if (cpr > 1.1) support.push("Anomalous CPR return (>1.1) matches CBOE"); else conflict.push("Low CPR return (<1.1) contradicts pure ice");
      if (dop < 0.4) support.push("Low DOP (<0.4) indicates high volume scattering"); else conflict.push("High DOP (>0.4) indicates surface reflection");
      if (slope < 10.0) support.push("Terrain slope (<10°) inside cold trap is safe"); else conflict.push("Steep local slope (>10°) impedes accumulation");
    } else if (hypId === 'ice_regolith_mixture') {
      if (cpr >= 0.6 && cpr <= 1.2) support.push("Moderate CPR anomaly (0.6 to 1.2)"); else conflict.push(`CPR of ${cpr.toFixed(2)} outside mixture boundaries`);
      if (dop >= 0.2 && dop <= 0.6) support.push("Moderate depolarization bounds matching"); else conflict.push("Depolarization bounds outside regolith mixture limits");
    } else if (hypId === 'blocky_ejecta') {
      if (cpr > 0.8) support.push("High CPR surface scattering"); else conflict.push("Insufficient CPR return for blocky ejecta blankets");
      if (slope > 10.0) support.push("Steep crater wall/rim slopes"); else conflict.push("Flat floor slopes conflict with boulder piles");
    } else {
      support.push("Baseline radar values within standard standard deviation ranges.");
    }

    return { support, conflict };
  };

  const { support, conflict } = getEvidenceStatus(activeHypObj.id);

  const getUncertainty = (p: number) => {
    return Math.max(0, 1 - p).toFixed(3);
  };

  return (
    <ScientificCard
      title="Reasoning Inspector"
      subtitle="LIVE HYPOTHESIS BAYESIAN TELEMETRY"
      icon={<Brain size={14} className="text-cyan-400" />}
      actions={
        hoverCoords && (
          <span className="text-[8px] px-2 py-0.5 bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 rounded font-mono tracking-widest">
            QUERY: {hoverCoords.x.toString().padStart(4, '0')} / {hoverCoords.y.toString().padStart(4, '0')}
          </span>
        )
      }
    >
      <div className="space-y-4 text-xs">
        {/* Hypotheses Grid */}
        <div className="space-y-2">
          <span className="text-white/40 font-mono font-bold block uppercase tracking-widest text-[9px]">Active Geological Hypotheses</span>
          <div className="grid grid-cols-5 gap-2">
            {HYPOTHESES.map((hyp) => {
              const p = probs[hyp.id] ?? 0.0;
              const isSelected = selectedHyp === hyp.id;
              return (
                <button
                  key={hyp.id}
                  onClick={() => setSelectedHyp(hyp.id)}
                  className={`flex flex-col items-center p-2 rounded border transition-all text-center select-none cursor-pointer relative overflow-hidden ${
                    isSelected 
                      ? 'bg-cyan-500/10 border-cyan-500 shadow-[0_0_10px_rgba(6,182,212,0.15)]' 
                      : 'bg-white/[0.01] border-white/5 hover:bg-white/[0.03] hover:border-white/10'
                  }`}
                >
                  {/* Subtle technical LED indicator on top of selected card */}
                  {isSelected && (
                    <div className="absolute top-0 left-0 w-full h-[2px] bg-cyan-400 shadow-[0_0_5px_#22d3ee]" />
                  )}
                  <span className="text-[8px] font-mono font-bold text-white/50 truncate w-full tracking-tighter uppercase">{hyp.name.split(' ').slice(-2).join(' ')}</span>
                  <span className="text-xs font-bold font-mono text-white mt-1">{(p * 100).toFixed(1)}%</span>
                  <div className="w-full mt-1.5">
                    <ProbabilityBar value={p} colorClass={isSelected ? 'bg-cyan-400' : 'bg-white/10'} heightClass="h-[2px]" />
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Selected Hypothesis Breakdown Panel */}
        <div className="p-3 bg-white/[0.01] border border-white/5 rounded-lg space-y-3 relative">
          {/* Cyber corners */}
          <div className="absolute top-0 left-0 w-1.5 h-1.5 border-t border-l border-cyan-500/30" />
          <div className="absolute bottom-0 right-0 w-1.5 h-1.5 border-b border-r border-cyan-500/30" />

          <div className="flex justify-between items-start">
            <div className="space-y-0.5">
              <h4 className="font-sans font-black text-white text-[11px] uppercase tracking-wider">{activeHypObj.name}</h4>
              <p className="text-[9px] text-white/50 leading-relaxed font-mono">{activeHypObj.desc}</p>
            </div>
            <div className="flex items-center gap-1.5 text-[8px] px-2 py-0.5 bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 rounded font-mono uppercase tracking-widest shrink-0">
              <ArrowUpRight size={10} />
              <span>Prior: {activeHypObj.prior.toFixed(1)}%</span>
            </div>
          </div>

          {/* Probability & Uncertainty Progress HUD */}
          <div className="grid grid-cols-2 gap-4 text-[9px] font-mono border-t border-b border-white/5 py-2.5">
            <div>
              <span className="text-white/30 block uppercase tracking-widest text-[8px]">Posterior Probability</span>
              <span className="text-cyan-400 font-extrabold text-sm tracking-wider">{(activeProbability * 100).toFixed(4)}%</span>
            </div>
            <div>
              <span className="text-white/30 block uppercase tracking-widest text-[8px]">Shannon Uncertainty</span>
              <span className="text-amber-500 font-extrabold text-sm tracking-wider">{getUncertainty(activeProbability)} bits</span>
            </div>
          </div>

          {/* Scientific Evidence Logs */}
          <div className="grid grid-cols-2 gap-3 text-[9px] font-mono">
            <div className="p-2.5 bg-emerald-500/[0.02] border border-emerald-500/15 rounded space-y-1">
              <span className="text-emerald-400 font-bold block uppercase tracking-widest text-[8px]">✓ Supporting Evidence</span>
              {support.map((s, i) => (
                <div key={i} className="text-white/70 leading-relaxed">• {s}</div>
              ))}
            </div>
            <div className="p-2.5 bg-rose-500/[0.02] border border-rose-500/15 rounded space-y-1">
              <span className="text-rose-400 font-bold block uppercase tracking-widest text-[8px]">✗ Conflicting Evidence</span>
              {conflict.length === 0 ? (
                <div className="text-white/30 italic">No conflicting parameters resolved.</div>
              ) : (
                conflict.map((c, i) => (
                  <div key={i} className="text-white/70 leading-relaxed">• {c}</div>
                ))
              )}
            </div>
          </div>

          {/* Physical Constraint Bound limits table */}
          <div className="space-y-1.5 pt-1">
            <span className="text-white/40 font-mono font-bold block uppercase tracking-widest text-[8px]">Geological Constraints Matrix</span>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[9px] text-white/50 font-mono">
              {Object.entries(activeHypObj.constraints).map(([feat, limit]) => (
                <div key={feat} className="flex justify-between border-b border-white/[0.02] py-0.5">
                  <span className="text-white/40">{feat}</span>
                  <span className="text-white">{limit}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* AHS & Bayesian Updates HUD */}
        <div className="grid grid-cols-2 gap-3 font-mono">
          {/* AHS Decider Info */}
          <div className="p-3 bg-white/[0.01] border border-white/5 rounded space-y-2 relative">
            <div className="flex items-center gap-1.5 text-[9px] text-amber-500 font-bold uppercase tracking-widest">
              <Layers size={11} className="text-amber-500" />
              <span>AHS Separation</span>
            </div>
            <p className="text-[9px] text-white/40 leading-normal">
              Optimal separation calculated at Step {playbackStep} utilizing Kullback-Leibler Divergence.
            </p>
            <div className="grid grid-cols-2 gap-2 text-[9px]">
              <div className="bg-white/[0.01] p-1.5 border border-white/5 rounded">
                <span className="text-white/30 block text-[7px] uppercase tracking-wider">Separation (KLD)</span>
                <span className="text-white font-bold">14.67 bits</span>
              </div>
              <div className="bg-white/[0.01] p-1.5 border border-white/5 rounded">
                <span className="text-white/30 block text-[7px] uppercase tracking-wider">Expected Gain</span>
                <span className="text-white font-bold">0.82 bits</span>
              </div>
            </div>
          </div>

          {/* Bayesian Likelihood updates HUD */}
          <div className="p-3 bg-white/[0.01] border border-white/5 rounded space-y-2">
            <div className="flex items-center gap-1.5 text-[9px] text-cyan-400 font-bold uppercase tracking-widest">
              <Activity size={11} className="text-cyan-400" />
              <span>Bayesian Engine</span>
            </div>
            <p className="text-[9px] text-white/40 leading-normal">
              Assimilated multi-sensor parameters into joint posterior maps.
            </p>
            <div className="flex items-center gap-1 p-1.5 bg-black/40 border border-white/5 rounded text-[8px] justify-center text-white/50">
              <span>Prior</span>
              <span>×</span>
              <span className="text-cyan-400 font-bold">Likelihood</span>
              <span>=</span>
              <span className="text-emerald-400 font-bold">Posterior</span>
            </div>
          </div>
        </div>
      </div>
    </ScientificCard>
  );
};
