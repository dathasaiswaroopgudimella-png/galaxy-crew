import { create } from 'zustand'
import type { TelemetryLog, ActiveMode } from '../types'

export interface PHSEState {
  activeMode: ActiveMode;
  activeLayer: string;
  selectedHypothesis: string | null;
  telemetryLogs: TelemetryLog[];
  pipelineResults: any | null;
  websocketStatus: 'connected' | 'disconnected' | 'connecting';
  hoverCoords: { x: number; y: number } | null;
  hoverDetails: any | null;
  playbackStep: number;
  isPlayMode: boolean;
  
  setActiveMode: (mode: ActiveMode) => void;
  setActiveLayer: (layer: string) => void;
  setSelectedHypothesis: (hyp: string | null) => void;
  addTelemetryLog: (log: Omit<TelemetryLog, 'timestamp'> & { timestamp?: number }) => void;
  setPipelineResults: (results: any) => void;
  setWebsocketStatus: (status: 'connected' | 'disconnected' | 'connecting') => void;
  setHoverCoords: (coords: { x: number; y: number } | null) => void;
  setHoverDetails: (details: any | null) => void;
  setPlaybackStep: (step: number) => void;
  setIsPlayMode: (isPlay: boolean) => void;
  clearTelemetry: () => void;
}

export const usePHSEStore = create<PHSEState>((set) => ({
  activeMode: 'overview',
  activeLayer: 'dem',
  selectedHypothesis: 'pure_water_ice',
  telemetryLogs: [],
  pipelineResults: null,
  websocketStatus: 'disconnected',
  hoverCoords: null,
  hoverDetails: null,
  playbackStep: 0,
  isPlayMode: false,

  setActiveMode: (mode) => set({ activeMode: mode }),
  setActiveLayer: (layer) => set({ activeLayer: layer }),
  setSelectedHypothesis: (hyp) => set({ selectedHypothesis: hyp }),
  addTelemetryLog: (log) => set((state) => ({
    telemetryLogs: [
      ...state.telemetryLogs,
      {
        ...log,
        timestamp: log.timestamp ?? Date.now() / 1000
      }
    ].slice(-100) // Keep last 100 entries to prevent memory bloating
  })),
  setPipelineResults: (results) => set({ pipelineResults: results }),
  setWebsocketStatus: (status) => set({ websocketStatus: status }),
  setHoverCoords: (coords) => set({ hoverCoords: coords }),
  setHoverDetails: (details) => set({ hoverDetails: details }),
  setPlaybackStep: (step) => set({ playbackStep: step }),
  setIsPlayMode: (isPlay) => set({ isPlayMode: isPlay }),
  clearTelemetry: () => set({ telemetryLogs: [] })
}))
