import React, { useEffect, useRef, useState } from 'react'
import { usePHSEStore } from '../store/usePHSEStore'
import { Terminal, Trash2, ShieldCheck, ShieldAlert } from 'lucide-react'

export const TelemetryTerminal: React.FC = () => {
  const logs = usePHSEStore((state) => state.telemetryLogs);
  const status = usePHSEStore((state) => state.websocketStatus);
  const clearLogs = usePHSEStore((state) => state.clearTelemetry);
  const terminalEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  // Auto scroll to bottom when new logs arrive
  useEffect(() => {
    if (autoScroll && terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll]);

  const handleScroll = () => {
    if (!containerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    // If user scrolled up by more than 30px, disable auto-scroll
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 30;
    setAutoScroll(isAtBottom);
  };

  const getLogColor = (type: string) => {
    switch (type) {
      case 'success': return 'text-emerald-400';
      case 'warn': return 'text-amber-400';
      case 'error': return 'text-rose-400 font-semibold';
      default: return 'text-cyan-400';
    }
  };

  return (
    <div className="flex flex-col h-full bg-[#0d1117] border border-white/5 rounded-lg overflow-hidden font-mono shadow-xl">
      {/* Header bar */}
      <div className="flex items-center justify-between px-4 py-2 bg-[#161b22] border-b border-white/5 text-xs text-gray-400">
        <div className="flex items-center gap-2">
          <Terminal size={14} className="text-gray-400" />
          <span className="font-semibold tracking-wider uppercase text-gray-300">Telemetry Stream</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5">
            {status === 'connected' ? (
              <>
                <ShieldCheck size={13} className="text-emerald-500" />
                <span className="text-emerald-400 font-medium">LIVE</span>
              </>
            ) : status === 'connecting' ? (
              <>
                <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
                <span className="text-amber-400">CONNECTING...</span>
              </>
            ) : (
              <>
                <ShieldAlert size={13} className="text-rose-500" />
                <span className="text-rose-400 font-medium">OFFLINE</span>
              </>
            )}
          </span>
          <button 
            onClick={clearLogs} 
            className="p-1 hover:bg-white/5 rounded text-gray-500 hover:text-rose-400 transition-colors"
            title="Clear Terminal"
          >
            <Trash2 size={13} />
          </button>
        </div>
      </div>

      {/* Terminal Output */}
      <div 
        ref={containerRef}
        onScroll={handleScroll}
        className="flex-1 p-4 overflow-y-auto text-xs space-y-1.5 leading-relaxed scrollbar-thin select-text"
        style={{ scrollbarWidth: 'thin' }}
      >
        {logs.length === 0 ? (
          <div className="text-gray-600 italic">No telemetry data. Trigger calculation or wait for updates...</div>
        ) : (
          logs.map((log, idx) => {
            const timeStr = new Date(log.timestamp * 1000).toLocaleTimeString([], { hour12: false });
            return (
              <div key={idx} className="flex gap-2 items-start hover:bg-white/[0.02] px-1 py-0.5 rounded">
                <span className="text-gray-600 shrink-0">[{timeStr}]</span>
                <span className="text-gray-500 shrink-0 font-semibold">[{log.source.split('.').pop()}]</span>
                <span className={getLogColor(log.type)}>{log.message}</span>
              </div>
            );
          })
        )}
        <div ref={terminalEndRef} />
      </div>
    </div>
  )
}
