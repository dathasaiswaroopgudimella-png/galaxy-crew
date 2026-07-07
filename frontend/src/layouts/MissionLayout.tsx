import React, { useState } from 'react'
import { usePHSEStore } from '../stores/usePHSEStore'
import { Compass, Brain, Cpu, RefreshCw, Award, Send, Activity } from 'lucide-react'

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
    <div className="flex h-screen w-screen bg-[#030508] text-[#e2e8f0] font-sans overflow-hidden grid-overlay">
      {/* 1. Sidebar console */}
      <aside className="w-[260px] shrink-0 matte-engineering flex flex-col h-full z-40 relative select-none">
        {/* Logo Section */}
        <div className="px-6 py-6 border-b border-white/5 flex flex-col gap-1">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 bg-cyan-500/10 rounded border border-cyan-500/30 flex items-center justify-center text-cyan-400">
              <Compass size={16} className="animate-spin-slow" />
            </div>
            <div>
              <h2 className="text-xs font-black tracking-widest text-white uppercase">PHSE CONTROL</h2>
              <span className="text-[7.5px] text-white/30 font-bold tracking-widest font-mono uppercase block leading-none mt-0.5">Space-Tech Engine</span>
            </div>
          </div>
          <span className="text-[7.5px] text-cyan-400 font-mono tracking-widest uppercase block mt-1.5">● Active Session</span>
        </div>

        {/* Navigation Tabs */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          <button 
            onClick={() => setActiveMode('overview')}
            className={`w-full flex items-center gap-3 px-4 py-3.5 rounded text-[10px] font-bold font-mono tracking-widest transition-all text-left cursor-pointer uppercase ${
              activeMode === 'overview' 
                ? 'text-cyan-400 edge-lit-cyan bg-cyan-500/5 border border-cyan-500/10' 
                : 'text-white/40 hover:text-white/75 hover:bg-white/[0.01] border border-transparent'
            }`}
          >
            <Compass size={14} />
            <span>Terrain Overview</span>
          </button>
          <button 
            onClick={() => setActiveMode('reasoning')}
            className={`w-full flex items-center gap-3 px-4 py-3.5 rounded text-[10px] font-bold font-mono tracking-widest transition-all text-left cursor-pointer uppercase ${
              activeMode === 'reasoning' 
                ? 'text-cyan-400 edge-lit-cyan bg-cyan-500/5 border border-cyan-500/10' 
                : 'text-white/40 hover:text-white/75 hover:bg-white/[0.01] border border-transparent'
            }`}
          >
            <Brain size={14} />
            <span>Scientific Logic</span>
          </button>
          <button 
            onClick={() => setActiveMode('engineering')}
            className={`w-full flex items-center gap-3 px-4 py-3.5 rounded text-[10px] font-bold font-mono tracking-widest transition-all text-left cursor-pointer uppercase ${
              activeMode === 'engineering' 
                ? 'text-cyan-400 edge-lit-cyan bg-cyan-500/5 border border-cyan-500/10' 
                : 'text-white/40 hover:text-white/75 hover:bg-white/[0.01] border border-transparent'
            }`}
          >
            <Cpu size={14} />
            <span>Telemetry Terminal</span>
          </button>
        </nav>

        {/* Assistant & Controls Panel */}
        <div className="p-4 border-t border-white/5 space-y-4">
          {/* Initiate Scan Button */}
          <button 
            onClick={triggerRun}
            disabled={recalculating}
            className="w-full py-3 bg-[#0066ff] hover:brightness-110 disabled:opacity-50 text-white font-bold tracking-widest text-[9px] rounded-sm shadow-[0_0_15px_rgba(0,102,255,0.25)] flex items-center justify-center gap-2 transition-all active:scale-98 cursor-pointer uppercase"
          >
            <RefreshCw size={11} className={recalculating ? 'animate-spin' : ''} />
            <span>{recalculating ? 'INGESTING...' : 'INITIATE SCAN'}</span>
          </button>

          {/* Scientific Assistant */}
          <div className="spatial-glass p-3 rounded-lg flex flex-col gap-2 relative min-h-[200px]">
            <div className="text-white/30 font-mono font-bold tracking-wider uppercase text-[7.5px] flex items-center justify-between border-b border-white/5 pb-1.5">
              <span>Scientific Assistant</span>
              <button 
                type="button"
                onClick={() => setUseGemini(!useGemini)}
                className="text-[7px] text-cyan-400 font-extrabold tracking-wider hover:opacity-85"
              >
                [{useGemini ? 'GEMINI' : 'OPENROUTER'}]
              </button>
            </div>

            <div className="flex-1 overflow-y-auto text-[8px] space-y-1.5 pr-1 font-mono uppercase tracking-wider scrollbar-thin select-text min-h-[80px] max-h-[120px]">
              {assistantResponse ? (
                <div className="p-2 bg-black/40 border border-white/5 rounded text-white/80 leading-relaxed overflow-y-auto max-h-[110px]">
                  {assistantResponse}
                </div>
              ) : assistantLoading ? (
                <div className="text-cyan-400/60 italic animate-pulse flex items-center gap-1">
                  <Activity size={10} className="animate-pulse" />
                  <span>Querying satellite...</span>
                </div>
              ) : (
                <div className="text-white/20 italic">Ask assistant about ice concentration parameters...</div>
              )}
            </div>

            <form onSubmit={handleAssistantSubmit} className="flex gap-1.5">
              <input
                type="text"
                value={assistantInput}
                onChange={(e) => setAssistantInput(e.target.value)}
                placeholder="ASK CHAT..."
                className="flex-1 min-w-0 bg-[#05070a] border border-white/10 rounded px-2 py-1 text-[8px] text-white focus:outline-none focus:border-cyan-500/50 font-mono tracking-wider placeholder-white/20 uppercase"
              />
              <button 
                type="submit" 
                className="p-1.5 bg-cyan-500 text-black hover:bg-cyan-400 rounded shrink-0 active:scale-95 transition-all cursor-pointer"
              >
                <Send size={9} />
              </button>
            </form>
          </div>

          {/* Commander profile */}
          <div className="flex items-center gap-3 pt-3 border-t border-white/5">
            <div className="w-8 h-8 rounded-full border border-white/10 overflow-hidden grayscale hover:grayscale-0 transition-all duration-500">
              <img alt="Commander Vance" className="w-full h-full object-cover" src="https://lh3.googleusercontent.com/aida-public/AB6AXuDbsQCcEtjd_jgzPQFcQSQNUdYgKW1BR85_2zyTefm1vPUJT2Tu8kZz3-AeouZEaO0OW4RhKIknsbjoKMYj0e6JA2weNjj9ktTj155fs2JjU3Gh1GFRrNeNgqd0R42Y-SmCwXrv5p9CyvdY69XXEerRHrL9GufnNI4PXZwBOSkbdyoD8YtNbfdsy-JnchEdvV8x4Bve10ieR2OCs1yDMGG8Zky-Nc1OJsWafDfinQ5V_Twc9E-vGwMd2A"/>
            </div>
            <div>
              <p className="font-mono text-[9px] font-bold text-white">CMD. A. VANCE</p>
              <p className="text-[7.5px] text-white/30 uppercase tracking-widest">Mission Lead</p>
            </div>
          </div>
        </div>
      </aside>

      {/* 2. Main Workstation Panel */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        {/* Top Header telemetry beam */}
        <header className="flex justify-between items-center w-full px-8 h-16 bg-[#0c0e10]/80 backdrop-blur-md border-b border-white/5 select-none shrink-0 z-30">
          <div className="flex items-center gap-6">
            <h1 className="font-sans font-black text-sm tracking-widest text-white uppercase">PHSE MISSION CONTROL</h1>
            <div className="flex items-center gap-2 px-2.5 py-0.5 bg-cyan-500/10 rounded-full border border-cyan-500/20">
              <div className="status-pip animate-pulse" />
              <span className="font-mono text-[8px] text-cyan-400 font-bold tracking-wider uppercase">Telemetry Stable</span>
            </div>
          </div>

          {/* Telemetry Widgets */}
          <div className="flex items-center gap-6 text-[9px] font-mono">
            <div className="border-l border-white/10 pl-4 py-1">
              <span className="text-white/30 block uppercase text-[7.5px] tracking-wider">Lander Target</span>
              <span className="text-white font-bold">{landingCoords}</span>
            </div>
            <div className="border-l border-white/10 pl-4 py-1">
              <span className="text-white/30 block uppercase text-[7.5px] tracking-wider">Suitability</span>
              <span className="text-emerald-400 font-bold">{landingScore}</span>
            </div>
            <div className="border-l border-white/10 pl-4 py-1">
              <span className="text-white/30 block uppercase text-[7.5px] tracking-wider">Ice mass</span>
              <span className="text-cyan-400 font-bold">{iceMass}</span>
            </div>
            <div className="border-l border-white/10 pl-4 py-1">
              <span className="text-white/30 block uppercase text-[7.5px] tracking-wider">Ice volume</span>
              <span className="text-cyan-400 font-bold">{iceVolume}</span>
            </div>
          </div>

          {/* ISRO watermark */}
          <div className="flex items-center gap-1.5 text-[8.5px] text-white/50 border border-white/10 px-2 py-0.5 rounded bg-white/[0.01] font-bold font-mono tracking-wider uppercase">
            <Award size={10} className="text-amber-500" />
            <span>Antariksh 2026</span>
          </div>
        </header>

        {/* 3. Children workspace content */}
        <main className="flex-1 overflow-hidden p-6 relative">
          {children}
        </main>
      </div>
    </div>
  );
};
