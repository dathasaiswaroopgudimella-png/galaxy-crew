import React from 'react'
import { usePHSEStore } from '../stores/usePHSEStore'
import { ThreeViewer } from '../components/viewer3d/ThreeViewer'
import { DecisionTree } from '../components/mission/DecisionTree'
import { TelemetryTerminal } from '../components/engineering/TelemetryTerminal'
import { ReasoningInspector } from '../components/reasoning/ReasoningInspector'
import { ExplainabilityTimeline } from '../components/reasoning/ExplainabilityTimeline'
import { EvidenceViewer } from '../components/reasoning/EvidenceViewer'
import { DiagnosticPanel } from '../components/engineering/DiagnosticPanel'

export const MissionControl: React.FC = () => {
  const activeMode = usePHSEStore((state) => state.activeMode);

  return (
    <div className="flex-1 flex flex-col gap-4 overflow-hidden">
      {/* 3D Visualizer Workspace - Centered Centerpiece */}
      <div className="flex-1 min-h-[320px]">
        <ThreeViewer />
      </div>

      {/* Mode Specific Analysis Workspace - Bottom panel using asymmetric grids */}
      <div className="h-[250px] shrink-0">
        {activeMode === 'overview' && (
          <div className="grid grid-cols-[3fr_2fr] gap-4 h-full">
            <DecisionTree />
            <TelemetryTerminal />
          </div>
        )}

        {activeMode === 'reasoning' && (
          <div className="grid grid-cols-[4fr_3fr_3fr] gap-4 h-full">
            <ReasoningInspector />
            <ExplainabilityTimeline />
            <EvidenceViewer />
          </div>
        )}

        {activeMode === 'engineering' && (
          <div className="grid grid-cols-[3fr_2fr] gap-4 h-full">
            <TelemetryTerminal />
            <DiagnosticPanel />
          </div>
        )}
      </div>
    </div>
  );
};
