import React, { useEffect } from 'react'
import Plot from 'react-plotly.js'
import { usePHSEStore } from '../../stores/usePHSEStore'
import { ScientificCard } from '../scientific/ScientificCard'
import { 
  Play, 
  Pause, 
  SkipForward, 
  SkipBack, 
  CheckCircle2, 
  HelpCircle,
  TrendingUp,
  TrendingDown
} from 'lucide-react'

export const ExplainabilityTimeline: React.FC = () => {
  const results = usePHSEStore((state) => state.pipelineResults);
  const playbackStep = usePHSEStore((state) => state.playbackStep);
  const setPlaybackStep = usePHSEStore((state) => state.setPlaybackStep);
  const isPlayMode = usePHSEStore((state) => state.isPlayMode);
  const setIsPlayMode = usePHSEStore((state) => state.setIsPlayMode);

  const trajectory = results?.trajectory ?? [0.0697, 0.0122, 0.0003];

  const steps = [
    { 
      label: 'Bootstrap', 
      desc: 'Initialized prior geological classification maps. High initial uncertainty across cold traps.',
      hypothesisImpact: 'All hypotheses sit near baseline priors. Standard dry regolith is dominant (45%).'
    },
    { 
      label: 'AHS Step 1: Illumination', 
      desc: 'Symmetrized KL Divergence chose the illumination mask. PSR cold trap bounds identified.',
      hypothesisImpact: 'Subsurface water ice confidence increases slightly on shadowed pixels. Ejecta details remains neutral.'
    },
    { 
      label: 'AHS Step 2: Roughness', 
      desc: 'Assimilated surface roughness measurements. Smooth features inside PSR cold trap detected.',
      hypothesisImpact: 'Pure Subsurface Water Ice becomes highly favored (>90%) on smooth shadowed zones. Blocky ejecta is rejected.'
    }
  ];

  // Playback timer implementation
  useEffect(() => {
    let interval: number | null = null;
    if (isPlayMode) {
      interval = window.setInterval(() => {
        setPlaybackStep((playbackStep + 1) % steps.length);
      }, 3000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isPlayMode, playbackStep]);

  const handleNext = () => {
    setPlaybackStep((playbackStep + 1) % steps.length);
  };

  const handlePrev = () => {
    setPlaybackStep((playbackStep - 1 + steps.length) % steps.length);
  };

  return (
    <ScientificCard
      title="Explainability Timeline"
      subtitle="STEP-BY-STEP BAYESIAN CONVERGENCE REPLAY"
      icon={<HelpCircle size={14} className="text-cyan-400" />}
      actions={
        <div className="flex items-center bg-white/[0.02] border border-white/10 rounded p-0.5 font-mono">
          <button 
            onClick={handlePrev} 
            className="p-1 hover:bg-white/5 rounded text-white/50 hover:text-white transition-colors cursor-pointer"
            title="Previous Step"
          >
            <SkipBack size={10} />
          </button>
          <button 
            onClick={() => setIsPlayMode(!isPlayMode)} 
            className={`p-1 rounded transition-colors cursor-pointer ${isPlayMode ? 'bg-cyan-500/20 text-cyan-400' : 'text-white/50 hover:text-white'}`}
            title={isPlayMode ? "Pause" : "Play Playback"}
          >
            {isPlayMode ? <Pause size={10} /> : <Play size={10} />}
          </button>
          <button 
            onClick={handleNext} 
            className="p-1 hover:bg-white/5 rounded text-white/50 hover:text-white transition-colors cursor-pointer"
            title="Next Step"
          >
            <SkipForward size={10} />
          </button>
        </div>
      }
    >
      <div className="space-y-3.5 text-xs">
        {/* Horizontal Navigation nodes */}
        <div className="flex items-center justify-between relative px-6 py-2.5 bg-black/40 border border-white/5 rounded select-none">
          <div className="absolute top-1/2 left-10 right-10 h-[1px] bg-white/10 -translate-y-1/2 z-0" />

          {steps.map((step, idx) => {
            const isCompleted = idx <= playbackStep;
            const isActive = idx === playbackStep;
            return (
              <button
                key={idx}
                onClick={() => {
                  setPlaybackStep(idx);
                  setIsPlayMode(false);
                }}
                className="flex flex-col items-center relative z-10 focus:outline-none cursor-pointer"
              >
                <div className={`p-1 rounded-full border transition-all ${
                  isActive 
                    ? 'bg-cyan-500 border-cyan-400 text-black scale-110 shadow-[0_0_10px_#22d3ee]' 
                    : isCompleted 
                      ? 'bg-cyan-950/60 border-cyan-500/50 text-cyan-400' 
                      : 'bg-slate-950 border-white/10 text-white/20'
                }`}>
                  <CheckCircle2 size={10} />
                </div>
                <span className={`text-[8px] font-mono font-bold mt-1 transition-colors uppercase tracking-wider ${
                  isActive ? 'text-cyan-400 font-extrabold' : 'text-white/40'
                }`}>{step.label.split(': ').pop()}</span>
              </button>
            );
          })}
        </div>

        {/* Detailed step explanation details */}
        <div className="grid grid-cols-2 gap-3">
          <div className="p-3 bg-white/[0.01] border border-white/5 rounded space-y-1.5 font-mono text-[9px]">
            <span className="text-white/30 block uppercase font-bold tracking-widest text-[8px]">Step Operation Details</span>
            <p className="text-white/80 leading-relaxed min-h-[48px]">{steps[playbackStep]?.desc}</p>
            <div className="text-white/30 pt-1.5 border-t border-white/[0.02] flex justify-between">
              <span>Entropy Convergence:</span>
              <span className="text-cyan-400 font-bold">{trajectory[playbackStep]?.toFixed(5) ?? '0.0000'} bits</span>
            </div>
          </div>

          <div className="p-3 bg-white/[0.01] border border-white/5 rounded space-y-1.5 font-mono text-[9px]">
            <span className="text-white/30 block uppercase font-bold tracking-widest text-[8px]">Hypotheses Evolution Impact</span>
            <p className="text-white/80 leading-relaxed min-h-[48px]">{steps[playbackStep]?.hypothesisImpact}</p>
            <div className="text-white/30 pt-1.5 border-t border-white/[0.02] flex items-center gap-1.5">
              {playbackStep === 2 ? (
                <>
                  <TrendingUp size={11} className="text-emerald-400" />
                  <span className="text-emerald-400 font-bold uppercase tracking-wider text-[8px]">Deposit verified (AHS Lock)</span>
                </>
              ) : (
                <>
                  <TrendingDown size={11} className="text-amber-400" />
                  <span className="text-amber-400 uppercase tracking-wider text-[8px]">Assimilation active...</span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Plotly Entropy Plot */}
        <div className="bg-black/30 border border-white/10 rounded p-1.5 flex items-center justify-center overflow-hidden h-[120px]">
          <Plot
            data={[
              {
                x: trajectory.map((_: number, i: number) => `STEP ${i}`),
                y: trajectory,
                type: 'scatter',
                mode: 'lines+markers',
                marker: { color: '#00e5ff', size: 6 },
                line: { color: '#2979ff', width: 2 },
                name: 'Shannon Entropy'
              }
            ]}
            layout={{
              autosize: true,
              height: 105,
              margin: { l: 35, r: 15, t: 15, b: 20 },
              paper_bgcolor: 'rgba(0,0,0,0)',
              plot_bgcolor: 'rgba(0,0,0,0)',
              title: {
                text: 'Bayesian Entropy Convergence (Bits)',
                font: { color: '#90a4ae', size: 8, family: 'IBM Plex Sans' }
              },
              xaxis: {
                gridcolor: 'rgba(255,255,255,0.03)',
                tickfont: { color: '#90a4ae', size: 7, family: 'JetBrains Mono' }
              },
              yaxis: {
                gridcolor: 'rgba(255,255,255,0.03)',
                tickfont: { color: '#90a4ae', size: 7, family: 'JetBrains Mono' }
              }
            }}
            config={{ displayModeBar: false, responsive: true }}
            style={{ width: '100%', height: '100%' }}
          />
        </div>
      </div>
    </ScientificCard>
  );
};
