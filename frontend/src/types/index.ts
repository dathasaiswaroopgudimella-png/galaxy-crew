export interface TelemetryLog {
  timestamp: number;
  source: string;
  message: string;
  type: 'info' | 'warn' | 'error' | 'success';
}

export interface GeologicalHypothesis {
  id: string;
  name: string;
  desc: string;
  constraints: Record<string, string>;
  prior: number;
}

export interface LayerDetail {
  id: string;
  name: string;
  units: string;
  desc: string;
  scienceImpact: string;
}

export type ActiveMode = 'overview' | 'reasoning' | 'engineering';
