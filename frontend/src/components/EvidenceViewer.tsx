import React from 'react'
import { usePHSEStore } from '../store/usePHSEStore'
import { Eye, Info, Database } from 'lucide-react'

interface LayerDetail {
  id: string;
  name: string;
  units: string;
  desc: string;
  scienceImpact: string;
}

const LAYERS: LayerDetail[] = [
  {
    id: 'dem',
    name: 'Digital Elevation Model (DEM)',
    units: 'Meters',
    desc: 'Topographic height map of the target region relative to lunar datum.',
    scienceImpact: 'Determines overall topographical constraints. Used to identify crater floors, ridges, and terrain slope hazard bounds.'
  },
  {
    id: 'cpr',
    name: 'Circular Polarization Ratio (CPR)',
    units: 'Ratio (SC/OC)',
    desc: 'The ratio of Same-Sense to Opposite-Sense circular polarization return from radar signals.',
    scienceImpact: 'High CPR (>1.0) inside shadowed craters indicates Coherent Backscatter Opposition Effect (CBOE) caused by subsurface water ice deposits. High CPR on sunlit slopes indicates blocky surface ejecta.'
  },
  {
    id: 'dop',
    name: 'Degree of Polarization (DOP)',
    units: 'Fraction (0.0 to 1.0)',
    desc: 'Measurement of the polarization degree of backscattered radar signal waves.',
    scienceImpact: 'Highly depolarized radar returns (low DOP <0.4) combined with high CPR confirm multiple volume scattering inside pure water ice sheets.'
  },
  {
    id: 'hazard',
    name: 'Landing Hazard Index',
    units: 'Scale (0.0 to 1.0)',
    desc: 'Fused multi-criteria hazard mapping incorporating local terrain slope, roughness, and boulder distributions.',
    scienceImpact: 'Defines safety exclusions for landing zone localization. Safe sites must obtain index scores below 0.35.'
  },
  {
    id: 'suitability',
    name: 'Landing Suitability Map',
    units: 'Score (0% to 100%)',
    desc: 'Overall landing suitability scoring blending hazard limits with water ice resource confidence maps.',
    scienceImpact: 'Directly guides landing site recommendation selection. The coordinate with maximum suitability score is selected.'
  },
  {
    id: 'geo_map',
    name: 'Refined Geological Interpretation Map',
    units: 'Class Codes',
    desc: 'Fitted geological mapping classifying pixels into discrete categories: Ice, Mixture, Ejecta, Pyroclastics, Regolith.',
    scienceImpact: 'Visualizes structural distribution. Shows where pure ice boundaries are concentrated.'
  },
  {
    id: 'entropy',
    name: 'Shannon Information Entropy',
    units: 'Bits',
    desc: 'Measures remaining geological classification uncertainty across all classes.',
    scienceImpact: 'Directly informs the AHS Sequential Planner. High entropy areas indicate areas requiring more observation layers.'
  }
];

export const EvidenceViewer: React.FC = () => {
  const activeLayer = usePHSEStore((state) => state.activeLayer);
  const setActiveLayer = usePHSEStore((state) => state.setActiveLayer);

  const selectedLayerObj = LAYERS.find(l => l.id === activeLayer) || LAYERS[0];

  return (
    <div className="flex flex-col h-full bg-[#0d1117] border border-white/5 rounded-lg overflow-hidden text-gray-200 shadow-xl">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-2.5 bg-[#161b22] border-b border-white/5 text-xs">
        <Database size={14} className="text-emerald-400" />
        <span className="font-semibold tracking-wider uppercase text-gray-300">Evidence Viewer</span>
      </div>

      <div className="flex-1 p-4 flex gap-4 overflow-hidden">
        {/* Layer list - Left column */}
        <div className="w-[180px] flex flex-col gap-1.5 overflow-y-auto border-r border-white/5 pr-3 select-none">
          <span className="text-gray-400 font-bold block mb-1 text-[10px] uppercase tracking-wider">Available Layers</span>
          {LAYERS.map((layer) => {
            const isActive = activeLayer === layer.id;
            return (
              <button
                key={layer.id}
                onClick={() => setActiveLayer(layer.id)}
                className={`flex items-center justify-between p-2 rounded text-left text-xxs transition-all ${
                  isActive 
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30' 
                    : 'bg-white/[0.01] hover:bg-white/[0.03] text-gray-400 border border-white/5'
                }`}
              >
                <span className="truncate pr-1">{layer.name.split(' (')[0]}</span>
                <Eye size={12} className={isActive ? 'text-emerald-400' : 'text-gray-600'} />
              </button>
            );
          })}
        </div>

        {/* Selected Layer Scientific Impact - Right column */}
        <div className="flex-1 overflow-y-auto space-y-3 pr-1 text-xxs leading-relaxed">
          <div>
            <h4 className="font-bold text-white text-xs">{selectedLayerObj.name}</h4>
            <div className="text-gray-500 font-mono mt-0.5">Units: {selectedLayerObj.units}</div>
          </div>

          <div className="p-2.5 bg-white/[0.01] border border-white/5 rounded-md space-y-1">
            <span className="text-gray-400 font-bold block text-[10px] uppercase">Description</span>
            <p className="text-gray-300 font-mono leading-normal">{selectedLayerObj.desc}</p>
          </div>

          <div className="p-2.5 bg-emerald-500/5 border border-emerald-500/10 rounded-md space-y-1">
            <div className="flex items-center gap-1.5 text-[10px] text-emerald-400 font-bold uppercase">
              <Info size={12} />
              <span>Scientific & Geological Impact</span>
            </div>
            <p className="text-emerald-300 font-mono leading-normal">{selectedLayerObj.scienceImpact}</p>
          </div>
        </div>
      </div>
    </div>
  )
}
