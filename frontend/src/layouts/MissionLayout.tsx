import React, { useState } from 'react'
import { usePHSEStore } from '../stores/usePHSEStore'
import { Compass, Brain, Cpu, RefreshCw, Award, MessageSquare, Send, MapPin, Activity } from 'lucide-react'
import { MetricCard } from '../components/scientific/MetricCard'

interface MissionLayoutProps {
  children: React.ReactNode;
}

export const MissionLayout: React.FC<MissionLayoutProps> = ({ children }) => {
  const activeMode = usePHSEStore((state) => state.activeMode);
  const setActiveMode = usePHSEStore((state) => state.setActiveMode);
  const results = usePHSEStore((state) => state.pipelineResults);
  const setPipelineResults = usePHSEStore((state) => state.setPipelineResults);

  const [recalculating, setRecalculating] = useState(false);
  const [assistantInput, setAssistantInput] = useState('');
  const [assistantResponse, setAssistantResponse] = useState<string | null>(null);
  const [assistantLoading, setAssistantLoading] = useState(false);
  const [useGemini, setUseGemini] = useState(false);

  const triggerRun = async () => {
    setRecalculating(true);
    try {
      const res = await fetch('/api/run', { method: 'POST' });
      const data = await res.json();
      setPipelineResults(data);
    } catch (e) {
      console.error("Failed to run pipeline:", e);
    } finally {
      setRecalculating(false);
    }
  };

  const handleAssistantSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!assistantInput.trim()) return;

    setAssistantLoading(true);
    setAssistantResponse(null);
    try {
      const res = await fetch('/api/assistant', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: assistantInput,
          mode: useGemini ? 'multimodal' : 'text'
        })
      });
      const data = await res.json();
      setAssistantResponse(data.response);
    } catch (err) {
      setAssistantResponse("Scientific assistant gateway timed out. Verify your API keys in .env.");
    } finally {
      setAssistantLoading(false);
    }
  };

  const landingCoords = results ? `X: ${results.landing_x.toString().padStart(4, '0')} / Y: ${results.landing_y.toString().padStart(4, '0')}` : 'AWAITING RUN';
  const landingScore = results ? `${(results.landing_score * 100).toFixed(2)}%` : '0.00%';
  const iceMass = results ? `${results.total_ice_tons.toFixed(2)} TONS` : '0.00 TONS';
  const iceVolume = results ? `${results.total_ice_m3.toFixed(2)} M³` : '0.00 M³';

  return (
    <div className="flex flex-col h-screen w-screen bg-[#030508] text-[#e2e8f0] font-sans overflow-hidden hud-grid-pattern">
      {/* 1. Scientific Header Bar */}
      <header className="flex items-center justify-between px-6 py-2.5 bg-[#090b0e]/95 backdrop-blur-lg border-b border-cyan-500/20 select-none shrink-0 z-10 shadow-[0_4px_20px_rgba(0,0,0,0.8)]">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-cyan-500/10 border border-cyan-500/30 rounded text-cyan-400">
            <Compass size={16} className="animate-spin-slow" />
          </div>
          <div>
            <h1 className="text-[11px] font-black tracking-widest text-white uppercase">PHSE Space-Tech Engine</h1>
            <span className="text-[8px] text-white/40 font-bold tracking-widest font-mono uppercase block leading-none mt-0.5">Lunar Landing Suitability Solver</span>
          </div>
        </div>

        {/* Tab switcher buttons */}
        <div className="flex bg-white/[0.02] border border-white/10 rounded p-0.5 text-[9px] font-bold font-mono uppercase tracking-wider">
          <button 
            onClick={() => setActiveMode('overview')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded transition-all duration-300 cursor-pointer ${
              activeMode === 'overview' 
                ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 shadow-[0_0_8px_rgba(6,182,212,0.15)]' 
                : 'text-white/40 hover:text-white'
            }`}
          >
            <Compass size={11} />
            <span>Mission Overview</span>
          </button>
          <button 
            onClick={() => setActiveMode('reasoning')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded transition-all duration-300 cursor-pointer ${
              activeMode === 'reasoning' 
                ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 shadow-[0_0_8px_rgba(6,182,212,0.15)]' 
                : 'text-white/40 hover:text-white'
            }`}
          >
            <Brain size={11} />
            <span>Scientific Reasoning</span>
          </button>
          <button 
            onClick={() => setActiveMode('engineering')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded transition-all duration-300 cursor-pointer ${
              activeMode === 'engineering' 
                ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 shadow-[0_0_8px_rgba(6,182,212,0.15)]' 
                : 'text-white/40 hover:text-white'
            }`}
          >
            <Cpu size={11} />
            <span>Engineering Logs</span>
          </button>
        </div>

        {/* ISRO Tag & Run button */}
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1.5 text-[8px] text-white/60 border border-white/10 px-2.5 py-1 rounded bg-white/[0.01] font-bold font-mono tracking-widest uppercase">
            <Award size={10} className="text-amber-500" />
            <span>Bharthiya Antariksh 2026</span>
          </span>
          <button 
            onClick={triggerRun}
            disabled={recalculating}
            className="flex items-center gap-2 px-3.5 py-1.5 bg-gradient-to-r from-cyan-500 to-blue-600 hover:opacity-90 disabled:opacity-50 text-black font-black text-[9px] tracking-widest rounded shadow-md shadow-cyan-500/10 border border-cyan-400/20 transition-all active:scale-95 cursor-pointer uppercase"
          >
            <RefreshCw size={11} className={recalculating ? 'animate-spin' : ''} />
            <span>{recalculating ? 'RUNNING...' : 'RUN PIPELINE'}</span>
          </button>
        </div>
      </header>

      {/* 2. Main Dashboard panel workspace grid */}
      <main className="flex-1 flex overflow-hidden p-4 gap-4 z-0 relative">
        {/* Persistent left sidebar metrics & assistant chat */}
        <div className="w-[280px] flex flex-col gap-4 shrink-0 overflow-y-auto pr-1">
          {/* Mission Metrics panel */}
          <div className="bg-slate-950/45 border border-cyan-500/20 rounded-lg p-3.5 space-y-3 shadow-lg select-none relative">
            <div className="absolute top-1.5 left-1.5 w-1 h-1 border-t border-l border-white/20" />
            <div className="absolute bottom-1.5 right-1.5 w-1 h-1 border-b border-r border-white/20" />
            
            <div className="text-white/40 font-mono font-bold tracking-widest uppercase text-[8px] flex items-center gap-1.5 border-b border-white/5 pb-2">
              <MapPin size={12} className="text-cyan-400" />
              <span>Mission Metrics</span>
            </div>

            <div className="space-y-2">
              <MetricCard label="Recommended Landing Site" value={landingCoords} valueColor="text-white" statusColor="cyan" />
              <MetricCard label="Landing Suitability Score" value={landingScore} valueColor="text-emerald-400" statusColor="emerald" />
              <MetricCard label="Estimated Ice Mass" value={iceMass} valueColor="text-cyan-400" statusColor="cyan" />
              <MetricCard label="Estimated Ice Volume" value={iceVolume} valueColor="text-cyan-400" statusColor="cyan" />
            </div>
          </div>

          {/* Multimodal assistant container */}
          <div className="flex-1 bg-slate-950/45 border border-cyan-500/20 rounded-lg p-3.5 flex flex-col gap-2.5 shadow-lg relative min-h-[220px]">
            <div className="absolute top-1.5 left-1.5 w-1 h-1 border-t border-l border-white/20" />
            <div className="absolute bottom-1.5 right-1.5 w-1 h-1 border-b border-r border-white/20" />

            <div className="text-white/40 font-mono font-bold tracking-widest uppercase text-[8px] flex items-center gap-1.5 border-b border-white/5 pb-2">
              <MessageSquare size={12} className="text-cyan-400" />
              <span>Scientific Assistant</span>
            </div>

            {/* Provider switch toggle */}
            <div className="flex justify-between items-center text-[8px] bg-white/[0.01] border border-white/5 p-1.5 rounded font-mono uppercase tracking-widest">
              <span className="text-white/40">Assistant Mode:</span>
              <button 
                onClick={() => setUseGemini(!useGemini)}
                className={`px-2 py-0.5 rounded font-extrabold transition-all cursor-pointer ${
                  useGemini ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30' : 'bg-slate-900 text-white/30 border border-white/5'
                }`}
              >
                {useGemini ? 'GEMINI' : 'OPENROUTER'}
              </button>
            </div>

            {/* Response area logs */}
            <div className="flex-1 overflow-y-auto text-[8.5px] space-y-1.5 pr-1 font-mono uppercase tracking-wider scrollbar-thin select-text min-h-[100px]">
              {assistantResponse ? (
                <div className="p-2.5 bg-black/40 border border-white/5 rounded text-white/80 leading-relaxed max-h-[140px] overflow-y-auto">
                  {assistantResponse}
                </div>
              ) : assistantLoading ? (
                <div className="text-cyan-400/60 italic animate-pulse flex items-center gap-1">
                  <Activity size={10} className="animate-pulse" />
                  <span>Ingesting query packets...</span>
                </div>
              ) : (
                <div className="text-white/20 italic">Awaiting query input... Ask helper about ice extraction parameters.</div>
              )}
            </div>

            {/* Search form */}
            <form onSubmit={handleAssistantSubmit} className="flex gap-2">
              <input
                type="text"
                value={assistantInput}
                onChange={(e) => setAssistantInput(e.target.value)}
                placeholder="ASK ASSISTANT..."
                className="flex-1 min-w-0 bg-[#05070a] border border-white/10 rounded px-2.5 py-1.5 text-[8.5px] text-white focus:outline-none focus:border-cyan-500/50 font-mono tracking-widest placeholder-white/20 uppercase"
              />
              <button 
                type="submit" 
                className="p-2 bg-cyan-500 text-black hover:bg-cyan-400 rounded shrink-0 active:scale-95 transition-all cursor-pointer"
              >
                <Send size={11} />
              </button>
            </form>
          </div>
        </div>

        {/* Dynamic central workspace panels */}
        <div className="flex-1 flex flex-col gap-4 overflow-hidden relative">
          {children}
        </div>
      </main>
    </div>
  );
};
