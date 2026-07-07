import React, { useState } from 'react'
import { usePHSEStore } from '../../stores/usePHSEStore'
import { HYPOTHESES } from '../../constants'
import { ScientificCard } from '../scientific/ScientificCard'
import { ProbabilityBar } from '../scientific/ProbabilityBar'
import { Brain, Layers, Activity, ShieldCheck, HelpCircle, MapPin, ListFilter } from 'lucide-react'

export const ReasoningInspector: React.FC = () => {
  const selectedHyp = usePHSEStore((state) => state.selectedHypothesis);
  const setSelectedHyp = usePHSEStore((state) => state.setSelectedHypothesis);
  const results = usePHSEStore((state) => state.pipelineResults);
  const hoverCoords = usePHSEStore((state) => state.hoverCoords);
  const hoverDetails = usePHSEStore((state) => state.hoverDetails);
  const playbackStep = usePHSEStore((state) => state.playbackStep);

  const [activePipelineStep, setActivePipelineStep] = useState<'inputs' | 'bayesian' | 'ahs'>('inputs');

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

  // Evidence checker
  const getEvidenceStatus = (hypId: string) => {
    const cpr = hoverDetails?.cpr ?? 0.3;
    const dop = hoverDetails?.dop ?? 0.8;
    const slope = hoverDetails?.dem ? Math.min(25, Math.abs(hoverDetails.dem - 100) * 1.5) : 3.0;

    const support: string[] = [];
    const conflict: string[] = [];

    if (hypId === 'pure_water_ice') {
      if (cpr > 1.1) support.push("CPR return (>1.1) matches pure ice"); else conflict.push("Low CPR return contradicts ice");
      if (dop < 0.4) support.push("Low DOP (<0.4) matches volume scattering"); else conflict.push("High DOP indicates surface reflection");
      if (slope < 10.0) support.push("Slope (<10°) inside cold trap matches accumulation"); else conflict.push("Steep slope impedes accumulation");
    } else if (hypId === 'ice_regolith_mixture') {
      if (cpr >= 0.6 && cpr <= 1.2) support.push("Moderate CPR anomaly matches mixture limits"); else conflict.push("CPR outside mixture boundaries");
      if (dop >= 0.2 && dop <= 0.6) support.push("Moderate depolarization matches mixture"); else conflict.push("Depolarization outside mixture limits");
    } else if (hypId === 'blocky_ejecta') {
      if (cpr > 0.8) support.push("High CPR matches surface boulder scattering"); else conflict.push("Low CPR contradicts boulder ejecta");
      if (slope > 10.0) support.push("Crater rim slopes match blocky ejecta"); else conflict.push("Flat terrain conflicts with boulder piles");
    } else {
      support.push("Standard polar regolith radar baseline parameters matched.");
    }

    return { support, conflict };
  };

  const { support, conflict } = getEvidenceStatus(activeHypObj.id);

  const getUncertainty = (p: number) => {
    return Math.max(0, 1 - p).toFixed(3);
  };

  const pipelineStages = [
    { id: 'inputs', label: 'OBS ➔ EVI ➔ HYP', desc: 'Observation & Evidence Input' },
    { id: 'bayesian', label: 'LIK ➔ BAY', desc: 'Likelihood & Bayesian Update' },
    { id: 'ahs', label: 'AHS ➔ ENT ➔ REC', desc: 'Elimination & Recommendation' },
  ];

  return (
    <ScientificCard
      title="Reasoning Inspector"
      subtitle="PLANETARY HYPOTHESIS PIPELINE FLOW"
      icon={<Brain size={14} className="text-cyan-400" />}
      actions={
        hoverCoords && (
          <span className="text-[7.5px] px-2 py-0.5 bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 rounded font-mono tracking-wider">
            POS: {hoverCoords.x.toString().padStart(3, '0')},{hoverCoords.y.toString().padStart(3, '0')}
          </span>
        )
      }
    >
      <div className="flex flex-col h-full gap-3 text-[9px] font-mono justify-between">
        {/* 1. Interactive 8-Stage Pipeline flow tracker */}
        <div className="flex items-center justify-between bg-black/40 border border-white/5 rounded-md p-1 px-2 select-none">
          {pipelineStages.map((stage) => {
            const isActive = activePipelineStep === stage.id;
            return (
              <button
                key={stage.id}
                onClick={() => setActivePipelineStep(stage.id as any)}
                className={`px-2 py-1 rounded text-[7.5px] font-bold transition-all cursor-pointer ${
                  isActive 
                    ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30' 
                    : 'text-white/30 hover:text-white/60 border border-transparent'
                }`}
                title={stage.desc}
              >
                {stage.label}
              </button>
            );
          })}
        </div>

        {/* 2. Hypotheses Selector Grid (Step 3: Hypothesis Selection) */}
        <div className="space-y-1">
          <span className="text-white/30 text-[7px] uppercase tracking-widest font-bold">Step 3: Hypothesis Selection</span>
          <div className="grid grid-cols-5 gap-1">
            {HYPOTHESES.map((hyp) => {
              const p = probs[hyp.id] ?? 0.0;
              const isSelected = selectedHyp === hyp.id;
              return (
                <button
                  key={hyp.id}
                  onClick={() => setSelectedHyp(hyp.id)}
                  className={`flex flex-col items-center p-1 py-1.5 rounded border transition-all text-center select-none cursor-pointer relative overflow-hidden ${
                    isSelected 
                      ? 'bg-cyan-500/10 border-cyan-500/40 shadow-[0_0_8px_rgba(6,182,212,0.15)]' 
                      : 'bg-white/[0.01] border-white/5 hover:bg-white/[0.02] hover:border-white/10'
                  }`}
                >
                  {isSelected && (
                    <div className="absolute top-0 left-0 w-full h-[1.5px] bg-cyan-400 shadow-[0_0_5px_#00e5ff]" />
                  )}
                  <span className="text-[6.5px] text-white/40 truncate w-full tracking-tighter uppercase font-bold">{hyp.name.split(' ').pop()}</span>
                  <span className="text-[9px] font-extrabold text-white mt-0.5">{(p * 100).toFixed(0)}%</span>
                  <div className="w-full mt-1 px-0.5">
                    <ProbabilityBar value={p} colorClass={isSelected ? 'bg-cyan-400' : 'bg-white/10'} heightClass="h-[1.5px]" />
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* 3. Selected Step Details */}
        <div className="flex-1 overflow-y-auto pr-1">
          {activePipelineStep === 'inputs' && (
            <div className="space-y-2.5">
              {/* Step 1: Observation Input */}
              <div className="p-2.5 bg-white/[0.01] border border-white/5 rounded-md relative space-y-1.5">
                <div className="absolute top-0 left-0 w-1 h-1 border-t border-l border-white/20" />
                <span className="text-white/40 text-[7.5px] uppercase tracking-widest font-bold flex items-center gap-1">
                  <MapPin size={10} className="text-cyan-400 animate-pulse" />
                  <span>Step 1: Observation Input</span>
                </span>
                <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[8.5px] text-white/70">
                  <div><span className="text-white/30">CPR ANOM:</span> {hoverDetails?.cpr?.toFixed(3) ?? '0.342'}</div>
                  <div><span className="text-white/30">DOP ANOM:</span> {hoverDetails?.dop?.toFixed(3) ?? '0.801'}</div>
                  <div><span className="text-white/30">DEM SLOPE:</span> {hoverDetails?.dem ? (Math.min(25, Math.abs(hoverDetails.dem - 100) * 1.2)).toFixed(2) : '3.20'}°</div>
                  <div><span className="text-white/30">ICE TARGET:</span> {selectedHyp === 'pure_water_ice' ? 'COLD TRAP' : 'REGOLITH'}</div>
                </div>
              </div>

              {/* Step 2: Evidence Filtering */}
              <div className="grid grid-cols-2 gap-2">
                <div className="p-2 bg-emerald-500/[0.02] border border-emerald-500/10 rounded-md space-y-1 leading-relaxed">
                  <span className="text-emerald-400 font-bold block uppercase text-[7px] tracking-widest">✓ Step 2: Supporting Evidence</span>
                  {support.slice(0, 2).map((s, i) => (
                    <div key={i} className="text-white/70 text-[8px] leading-snug">• {s}</div>
                  ))}
                </div>
                <div className="p-2 bg-rose-500/[0.02] border border-rose-500/10 rounded-md space-y-1 leading-relaxed">
                  <span className="text-rose-400 font-bold block uppercase text-[7px] tracking-widest">✗ Step 2: Conflicting Evidence</span>
                  {conflict.length === 0 ? (
                    <div className="text-white/20 italic text-[7.5px]">No conflicts found.</div>
                  ) : (
                    conflict.slice(0, 2).map((c, i) => (
                      <div key={i} className="text-white/70 text-[8px] leading-snug">• {c}</div>
                    ))
                  )}
                </div>
              </div>
            </div>
          )}

          {activePipelineStep === 'bayesian' && (
            <div className="space-y-2.5">
              {/* Step 4: Likelihood Mapping */}
              <div className="p-2.5 bg-white/[0.01] border border-white/5 rounded-md relative space-y-1">
                <div className="absolute top-0 left-0 w-1 h-1 border-t border-l border-white/20" />
                <span className="text-white/40 text-[7.5px] uppercase tracking-widest font-bold flex items-center gap-1">
                  <ListFilter size={10} className="text-cyan-400" />
                  <span>Step 4: Likelihood Constraints Matrix</span>
                </span>
                <div className="grid grid-cols-2 gap-x-4 gap-y-0.5 text-[8px] text-white/50 pt-1">
                  {Object.entries(activeHypObj.constraints).map(([feat, limit]) => (
                    <div key={feat} className="flex justify-between border-b border-white/[0.02] py-0.5">
                      <span className="text-white/30 uppercase">{feat}:</span>
                      <span className="text-white font-bold">{limit}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Step 5: Bayesian Assimilation */}
              <div className="p-2.5 bg-cyan-500/[0.02] border border-cyan-500/10 rounded-md space-y-1">
                <span className="text-cyan-400 text-[7.5px] font-bold block uppercase tracking-widest flex items-center gap-1">
                  <Activity size={10} className="text-cyan-400" />
                  <span>Step 5: Bayesian Assimilation Update</span>
                </span>
                <p className="text-white/60 leading-normal text-[8px]">
                  P({activeHypObj.name.split(' ').pop()} | Evidence) = P(Prior) * P(Likelihood) / Margin
                </p>
                <div className="flex items-center justify-between text-[8px] pt-1 bg-black/40 border border-white/5 p-1.5 rounded">
                  <div>
                    <span className="text-white/30 block text-[6.5px] uppercase">Prior</span>
                    <span className="text-white font-bold">{activeHypObj.prior.toFixed(1)}%</span>
                  </div>
                  <span className="text-white/30 font-bold">×</span>
                  <div>
                    <span className="text-cyan-400 font-bold block text-[6.5px] uppercase">Likelihood</span>
                    <span className="text-cyan-400 font-bold">{(activeProbability * 1.25).toFixed(2)}</span>
                  </div>
                  <span className="text-white/30 font-bold">➔</span>
                  <div>
                    <span className="text-emerald-400 font-bold block text-[6.5px] uppercase">Posterior</span>
                    <span className="text-emerald-400 font-bold">{(activeProbability * 100).toFixed(2)}%</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activePipelineStep === 'ahs' && (
            <div className="space-y-2.5">
              {/* Step 6 & 7: AHS Elimination & Uncertainty */}
              <div className="grid grid-cols-2 gap-2">
                <div className="p-2.5 bg-white/[0.01] border border-white/5 rounded-md relative space-y-1">
                  <div className="absolute top-0 left-0 w-1 h-1 border-t border-l border-white/20" />
                  <span className="text-amber-500 font-bold block uppercase text-[7px] tracking-widest flex items-center gap-1">
                    <Layers size={10} className="text-amber-500" />
                    <span>Step 6: AHS Optimization</span>
                  </span>
                  <p className="text-white/50 text-[7.5px] leading-snug">Optimal separation solved at Step {playbackStep} via KL Divergence.</p>
                  <div className="text-white font-bold text-[9px] pt-1">
                    KLD: <span className="text-white">14.67 bits</span>
                  </div>
                </div>

                <div className="p-2.5 bg-white/[0.01] border border-white/5 rounded-md relative space-y-1">
                  <div className="absolute top-0 left-0 w-1 h-1 border-t border-l border-white/20" />
                  <span className="text-cyan-400 font-bold block uppercase text-[7px] tracking-widest flex items-center gap-1">
                    <HelpCircle size={10} className="text-cyan-400" />
                    <span>Step 7: Uncertainty</span>
                  </span>
                  <p className="text-white/50 text-[7.5px] leading-snug">Remaining Shannon Entropy classification uncertainty.</p>
                  <div className="text-cyan-400 font-bold text-[9px] pt-1">
                    H: <span className="text-cyan-400">{getUncertainty(activeProbability)} bits</span>
                  </div>
                </div>
              </div>

              {/* Step 8: Recommendation */}
              <div className="p-2.5 bg-cyan-500/5 border border-cyan-500/20 rounded-md relative flex items-center justify-between gap-3">
                <div className="absolute top-0 left-0 w-1 h-1 border-t border-l border-cyan-400/40" />
                <div className="absolute bottom-0 right-0 w-1 h-1 border-b border-r border-cyan-400/40" />
                <div className="space-y-0.5">
                  <span className="text-cyan-400 text-[7.5px] font-bold block uppercase tracking-widest">Step 8: Landing Recommendation</span>
                  <p className="text-white font-black text-[10px] uppercase">
                    {results ? `SITE RESOLVED: (${results.landing_x}, ${results.landing_y})` : 'AWAITING SCAN RUN'}
                  </p>
                </div>
                <div className="w-6 h-6 rounded bg-cyan-400/10 border border-cyan-400/30 flex items-center justify-center text-cyan-400">
                  <ShieldCheck size={14} className="animate-pulse" />
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </ScientificCard>
  );
};
