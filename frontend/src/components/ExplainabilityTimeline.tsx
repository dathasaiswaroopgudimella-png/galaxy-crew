import React, { useState } from 'react'
import Plot from 'react-plotly.js'
import { usePHSEStore } from '../store/usePHSEStore'
import { CheckCircle2, Circle } from 'lucide-react'

export const ExplainabilityTimeline: React.FC = () => {
  const results = usePHSEStore((state) => state.pipelineResults);
  const [selectedStep, setSelectedStep] = useState<number>(0);

  const trajectory = results?.trajectory ?? [0.0697, 0.0122, 0.0003];
  
  // Steps description mapping AHS decisions
  const steps = [
    { label: 'Prior', desc: 'Fuzzy constraint membership initialized.' },
    { label: 'Step 1: Illumination', desc: 'Assimilated terrain_illumination layer (AHS chosen).' },
    { label: 'Step 2: Roughness', desc: 'Assimilated terrain_roughness layer (AHS chosen).' }
  ];

  return (
    <div className="flex flex-col h-full bg-[#0d1117] border border-white/5 rounded-lg overflow-hidden text-gray-200 shadow-xl">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-2.5 bg-[#161b22] border-b border-white/5 text-xs">
        <span className="font-semibold tracking-wider uppercase text-gray-300">Explainability Timeline</span>
      </div>

      <div className="flex-1 p-4 flex flex-col gap-4 overflow-y-auto">
        {/* Horizontal Timeline Steps */}
        <div className="flex items-center justify-between relative px-6 py-2 bg-white/[0.01] border border-white/5 rounded-lg">
          {/* Connector Line */}
          <div className="absolute top-1/2 left-12 right-12 h-[2px] bg-white/10 -translate-y-1/2 z-0" />

          {steps.map((step, idx) => {
            const isCompleted = idx <= selectedStep;
            const isActive = idx === selectedStep;
            return (
              <button
                key={idx}
                onClick={() => setSelectedStep(idx)}
                className="flex flex-col items-center relative z-10 focus:outline-none"
              >
                <div className={`p-1.5 rounded-full border-2 transition-all ${
                  isActive 
                    ? 'bg-indigo-500 border-indigo-400 text-white scale-110 shadow-lg shadow-indigo-500/20' 
                    : isCompleted 
                      ? 'bg-indigo-950 border-indigo-500 text-indigo-400' 
                      : 'bg-[#0d1117] border-white/10 text-gray-600'
                }`}>
                  {isCompleted ? <CheckCircle2 size={14} /> : <Circle size={14} />}
                </div>
                <span className={`text-[10px] font-bold mt-1.5 transition-colors ${
                  isActive ? 'text-indigo-400' : 'text-gray-400'
                }`}>{step.label}</span>
              </button>
            );
          })}
        </div>

        {/* Step details */}
        <div className="p-3 bg-white/[0.01] border border-white/5 rounded-lg text-xxs">
          <span className="text-gray-400 font-bold block mb-1">Active Step Explanation</span>
          <p className="text-gray-300 leading-normal font-mono">{steps[selectedStep]?.desc ?? 'Prior bootstrap calculation.'}</p>
          <div className="mt-2 text-gray-500">
            Entropy at this step: <span className="text-white font-bold">{trajectory[selectedStep]?.toFixed(5) ?? '0.0000'} bits</span>
          </div>
        </div>

        {/* Plotly Entropy Plot */}
        <div className="flex-1 min-h-[160px] bg-white/[0.01] border border-white/5 rounded-lg p-2 flex items-center justify-center overflow-hidden">
          <Plot
            data={[
              {
                x: trajectory.map((_: number, i: number) => `It ${i}`),
                y: trajectory,
                type: 'scatter',
                mode: 'lines+markers',
                marker: { color: '#38bdf8', size: 8 },
                line: { color: '#818cf8', width: 3 },
                name: 'Mean Entropy'
              }
            ]}
            layout={{
              autosize: true,
              height: 150,
              margin: { l: 40, r: 15, t: 30, b: 30 },
              paper_bgcolor: 'rgba(0,0,0,0)',
              plot_bgcolor: 'rgba(0,0,0,0)',
              title: {
                text: 'Bayesian Entropy Convergence (Bits)',
                font: { color: '#f3f4f6', size: 10, family: 'Inter' }
              },
              xaxis: {
                gridcolor: 'rgba(255,255,255,0.05)',
                tickfont: { color: '#9ca3af', size: 9, family: 'JetBrains Mono' }
              },
              yaxis: {
                gridcolor: 'rgba(255,255,255,0.05)',
                tickfont: { color: '#9ca3af', size: 9, family: 'JetBrains Mono' }
              }
            }}
            config={{ displayModeBar: false, responsive: true }}
            style={{ width: '100%', height: '100%' }}
          />
        </div>
      </div>
    </div>
  )
}
