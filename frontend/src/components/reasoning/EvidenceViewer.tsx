import React, { useState } from 'react'
import { usePHSEStore } from '../../stores/usePHSEStore'
import { ScientificCard } from '../scientific/ScientificCard'
import { Database, Eye, Info, Columns } from 'lucide-react'

interface ExtendedLayerDetail {
  id: string;
  name: string;
  units: string;
  desc: string;
  scienceImpact: string;
  range: string;
  confidence: string;
  contribHypothesis: string;
  contribLanding: string;
  contribRover: string;
  contribIce: string;
}

const EXTENDED_LAYERS: ExtendedLayerDetail[] = [
  {
    id: 'dem',
    name: 'Digital Elevation Model (DEM)',
    units: 'Meters',
    desc: 'Topographic height map of the target region relative to lunar datum.',
    scienceImpact: 'Determines topographical boundaries and local slope values.',
    range: '-4500m to 1200m',
    confidence: '99.8% (LOLA Laser Altimeter Fused)',
    contribHypothesis: 'Locks out steep slopes from pure ice hypothesis.',
    contribLanding: 'Mandatory slope exclusion (<15°) for landing hazard calculations.',
    contribRover: 'Identifies slope costs for rover traversal path constraints.',
    contribIce: 'Confirms topography of cold trap storage volumes.'
  },
  {
    id: 'cpr',
    name: 'Circular Polarization Ratio (CPR)',
    units: 'Ratio (SC/OC)',
    desc: 'Ratio of Same-Sense to Opposite-Sense circular polarization returns.',
    scienceImpact: 'High CPR inside PSR shadows points to water ice volumes; on sunlit slopes points to rocks.',
    range: '0.0 to 5.0',
    confidence: '95.2% (Mini-RF SAR Sensor)',
    contribHypothesis: 'Critical descriptor for ice vs blocky ejecta discrimination.',
    contribLanding: 'Identifies high suitability areas for scientific landing targeting.',
    contribRover: 'Locates hazards (boulder piles) to bypass during traverse planning.',
    contribIce: 'Primary indicator for subsurface volume estimation models.'
  },
  {
    id: 'dop',
    name: 'Degree of Polarization (DOP)',
    units: 'Fraction (0.0 to 1.0)',
    desc: 'Polarization degree index of radar signals.',
    scienceImpact: 'Depolarized radar returns (low DOP <0.4) combined with high CPR confirm multiple volume scattering inside pure water ice sheets.',
    range: '0.0 to 1.0',
    confidence: '94.0% (Radar Polarimetric Calibration)',
    contribHypothesis: 'Validates surface volume scattering vs rock double-bounce reflection.',
    contribLanding: 'Improves safety rating for potential landing sites.',
    contribRover: 'Validates track traction constraints (smooth ice vs blocky debris).',
    contribIce: 'Calculates ice purity fraction in resource volume models.'
  },
  {
    id: 'hazard',
    name: 'Landing Hazard Index',
    units: 'Scale (0.0 to 1.0)',
    desc: 'Fused multi-criteria hazard mapping incorporating local terrain slope, roughness, and boulder distributions.',
    scienceImpact: 'Excludes landing zones based on safety parameters.',
    range: '0.0 (Safe) to 1.0 (Critical)',
    confidence: '98.5% (Multi-sensor Fusion)',
    contribHypothesis: 'No direct geological hypothesis contribution.',
    contribLanding: 'Imposes strict exclusion boundaries (must be <0.35) for landing sites.',
    contribRover: 'Defines A* planner node travel penalties.',
    contribIce: 'No direct ice volume contribution.'
  },
  {
    id: 'suitability',
    name: 'Landing Suitability Map',
    units: 'Score (0% to 100%)',
    desc: 'Blending safety metrics with ice resources confidence maps.',
    scienceImpact: 'Pinpoints optimal sites balancing landing safety with scientific extraction potential.',
    range: '0.0 to 1.0',
    confidence: '96.4% (Fused Decision Matrix)',
    contribHypothesis: 'Drives overall mission priority.',
    contribLanding: 'Primary output determining the target landing coordinate (highest score).',
    contribRover: 'Establishes traversal start point.',
    contribIce: 'Validates target deposit viability.'
  },
  {
    id: 'geo_map',
    name: 'Geological Classification Map',
    units: 'Class Codes (1-5)',
    desc: 'Discrete geological classifications: Ice, Mixture, Ejecta, Pyroclastics, Regolith.',
    scienceImpact: 'Maps discrete boundaries of polar surface formations.',
    range: 'Discrete 1 to 5',
    confidence: '92.1% (Posterior MAP Classification)',
    contribHypothesis: 'Consolidates evidence updates into definite classifications.',
    contribLanding: 'Guarantees landing inside or near ice zones.',
    contribRover: 'Identifies traverse boundaries (e.g. avoiding steep ejecta blocks).',
    contribIce: 'Provides mask boundary for total ice mass volume calculations.'
  },
  {
    id: 'entropy',
    name: 'Shannon Information Entropy',
    units: 'Bits',
    desc: 'Remaining geological classification uncertainty.',
    scienceImpact: 'Guides the AHS planner toward high uncertainty zones for exploration.',
    range: '0.0 to 2.32 bits',
    confidence: '100% (Analytical Information Measure)',
    contribHypothesis: 'Drives information gain separation values.',
    contribLanding: 'Helps landing planner assess risk profile of target site.',
    contribRover: 'Flags zones requiring localized scanner measurements.',
    contribIce: 'Measures spatial variability confidence bounds.'
  }
];

export const EvidenceViewer: React.FC = () => {
  const activeLayer = usePHSEStore((state) => state.activeLayer);
  const setActiveLayer = usePHSEStore((state) => state.setActiveLayer);
  
  const [compareMode, setCompareMode] = useState(false);
  const [compareLayer, setCompareLayer] = useState<string>('cpr');

  const selectedLayerObj = EXTENDED_LAYERS.find(l => l.id === activeLayer) || EXTENDED_LAYERS[0];
  const compareLayerObj = EXTENDED_LAYERS.find(l => l.id === compareLayer) || EXTENDED_LAYERS[1];

  const renderLayerDetails = (layer: ExtendedLayerDetail) => {
    return (
      <div className="space-y-3 font-mono text-[9px] leading-relaxed">
        <div>
          <h4 className="font-sans font-black text-white text-[10px] tracking-wider uppercase">{layer.name}</h4>
          <div className="text-white/40 text-[8px] mt-0.5 uppercase tracking-widest">Units: {layer.units} | Range: {layer.range}</div>
        </div>

        <div className="p-2.5 bg-white/[0.01] border border-white/5 rounded space-y-1 relative">
          <div className="absolute top-0 left-0 w-1 h-1 border-t border-l border-white/20" />
          <span className="text-white/30 font-bold block uppercase text-[7px] tracking-widest">Physical Interpretation</span>
          <p className="text-white/70 leading-normal text-[9px]">{layer.desc}</p>
        </div>

        <div className="p-2.5 bg-emerald-500/[0.02] border border-emerald-500/10 rounded space-y-1">
          <div className="flex items-center gap-1 text-[8px] text-emerald-400 font-bold uppercase tracking-widest">
            <Info size={10} />
            <span>Geological & Mission Impact</span>
          </div>
          <p className="text-emerald-300/80 leading-normal text-[9px]">{layer.scienceImpact}</p>
        </div>

        <div className="p-2.5 bg-white/[0.01] border border-white/5 rounded space-y-2">
          <span className="text-white/30 font-bold block uppercase text-[7px] tracking-widest">Contribution Matrix</span>
          <div className="space-y-1 text-[8px]">
            <div className="flex justify-between border-b border-white/[0.02] py-0.5">
              <span className="text-white/40 uppercase">Hypothesis Separation:</span>
              <span className="text-white text-right font-semibold">{layer.contribHypothesis}</span>
            </div>
            <div className="flex justify-between border-b border-white/[0.02] py-0.5">
              <span className="text-white/40 uppercase">Landing Site:</span>
              <span className="text-white text-right font-semibold">{layer.contribLanding}</span>
            </div>
            <div className="flex justify-between border-b border-white/[0.02] py-0.5">
              <span className="text-white/40 uppercase">Rover Pathfinder:</span>
              <span className="text-white text-right font-semibold">{layer.contribRover}</span>
            </div>
            <div className="flex justify-between py-0.5">
              <span className="text-white/40 uppercase">Ice Volume Estimation:</span>
              <span className="text-white text-right font-semibold">{layer.contribIce}</span>
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <ScientificCard
      title="Evidence Viewer"
      subtitle="MULTI-SENSOR RASTER LAYER ANALYTICS"
      icon={<Database size={14} className="text-emerald-400" />}
      theme="emerald"
      actions={
        <button
          onClick={() => setCompareMode(!compareMode)}
          className={`flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[8px] font-bold border transition-all cursor-pointer font-mono uppercase tracking-widest ${
            compareMode 
              ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40' 
              : 'bg-white/[0.02] text-white/50 border-white/10 hover:text-white'
          }`}
        >
          <Columns size={10} />
          <span>{compareMode ? 'Dual Panel' : 'Compare'}</span>
        </button>
      }
    >
      <div className="flex h-full gap-3.5 overflow-hidden">
        {/* Layer list */}
        <div className="w-[130px] flex flex-col gap-1 overflow-y-auto border-r border-white/5 pr-2 select-none shrink-0 font-mono">
          <span className="text-white/30 font-bold block mb-1 text-[8px] uppercase tracking-widest">Active Sensor</span>
          {EXTENDED_LAYERS.map((layer) => {
            const isActive = activeLayer === layer.id;
            const isComparing = compareMode && compareLayer === layer.id;
            return (
              <button
                key={layer.id}
                onClick={() => {
                  if (compareMode && activeLayer !== layer.id) {
                    setCompareLayer(layer.id);
                  } else {
                    setActiveLayer(layer.id);
                  }
                }}
                className={`flex items-center justify-between p-2 rounded text-left text-[8px] font-bold tracking-wider uppercase transition-all select-none cursor-pointer border ${
                  isActive 
                    ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' 
                    : isComparing
                      ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                      : 'bg-white/[0.01] hover:bg-white/[0.03] text-white/50 border-white/5 hover:border-white/10'
                }`}
              >
                <span className="truncate pr-1">{layer.name.split(' (')[0]}</span>
                <Eye size={10} className={isActive || isComparing ? 'text-emerald-400' : 'text-white/20'} />
              </button>
            );
          })}
        </div>

        {/* Selected Layer Scientific details */}
        <div className="flex-1 flex gap-3.5 overflow-x-auto">
          <div className="flex-1 min-w-[180px] overflow-y-auto pr-1">
            {renderLayerDetails(selectedLayerObj)}
          </div>
          {compareMode && (
            <div className="flex-1 min-w-[180px] overflow-y-auto pr-1 border-l border-white/5 pl-3.5">
              <span className="text-amber-500 font-bold text-[8px] uppercase font-mono block mb-2 tracking-widest">Comparison sensor</span>
              {renderLayerDetails(compareLayerObj)}
            </div>
          )}
        </div>
      </div>
    </ScientificCard>
  );
};
