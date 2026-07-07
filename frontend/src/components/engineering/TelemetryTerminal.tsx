import React, { useEffect, useRef, useState } from 'react'
import { usePHSEStore } from '../../stores/usePHSEStore'
import { ScientificCard } from '../scientific/ScientificCard'
import { Terminal, Trash2, ShieldCheck, ShieldAlert, Copy } from 'lucide-react'

export const TelemetryTerminal: React.FC = () => {
  const logs = usePHSEStore((state) => state.telemetryLogs);
  const status = usePHSEStore((state) => state.websocketStatus);
  const clearLogs = usePHSEStore((state) => state.clearTelemetry);
  const terminalEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  useEffect(() => {
    if (autoScroll && terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll]);

  const handleScroll = () => {
    if (!containerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 30;
    setAutoScroll(isAtBottom);
  };

  const getLogColor = (type: string) => {
    switch (type) {
      case 'success': return 'text-emerald-400 font-bold';
      case 'warn': return 'text-amber-500 font-bold';
      case 'error': return 'text-rose-500 font-bold';
      default: return 'text-cyan-400';
    }
  };

  const handleCopyLogs = () => {
    const text = logs.map(l => `[${new Date(l.timestamp * 1000).toLocaleTimeString([], { hour12: false })}] [${l.source}] ${l.message}`).join('\n');
    navigator.clipboard.writeText(text);
  };

  return (
    <ScientificCard
      title="Telemetry Stream"
      subtitle="LIVE WEBSOCKET PIPELINE TRANSACTION LOGGER"
      icon={<Terminal size={14} className="text-white/60" />}
      actions={
        <div className="flex items-center gap-2 font-mono">
          <span className="flex items-center gap-1 text-[8px] font-bold">
            {status === 'connected' ? (
              <>
                <ShieldCheck size={10} className="text-emerald-400" />
                <span className="text-emerald-400 tracking-wider">LIVE</span>
              </>
            ) : status === 'connecting' ? (
              <>
                <span className="w-1 h-1 rounded-full bg-amber-500 animate-pulse mr-1" />
                <span className="text-amber-400 tracking-wider">SYNCING</span>
              </>
            ) : (
              <>
                <ShieldAlert size={10} className="text-rose-400" />
                <span className="text-rose-400 tracking-wider">OFFLINE</span>
              </>
            )}
          </span>
          <button 
            onClick={handleCopyLogs}
            className="p-1 hover:bg-white/5 rounded text-white/40 hover:text-white transition-colors cursor-pointer"
            title="Copy Logs"
          >
            <Copy size={10} />
          </button>
          <button 
            onClick={clearLogs} 
            className="p-1 hover:bg-white/5 rounded text-white/40 hover:text-rose-400 transition-colors cursor-pointer"
            title="Clear Terminal"
          >
            <Trash2 size={10} />
          </button>
        </div>
      }
    >
      <div className="crt-scanlines scan-effect h-full w-full bg-[#05070a] p-3 border border-white/5 rounded relative flex flex-col justify-between overflow-hidden">
        {/* CRT corner brackets */}
        <div className="absolute top-1 left-1 w-1 h-1 border-t border-l border-white/20 z-10" />
        <div className="absolute bottom-1 right-1 w-1 h-1 border-b border-r border-white/20 z-10" />

        <div 
          ref={containerRef}
          onScroll={handleScroll}
          className="flex-1 overflow-y-auto text-[8px] font-mono space-y-1 leading-snug scrollbar-thin select-text relative z-1"
          style={{ scrollbarWidth: 'thin' }}
        >
          {logs.length === 0 ? (
            <div className="text-white/25 italic font-bold uppercase tracking-wider p-2">Awaiting Telemetry Stream Packet Handshake...</div>
          ) : (
            logs.map((log, idx) => {
              const timeStr = new Date(log.timestamp * 1000).toLocaleTimeString([], { hour12: false });
              return (
                <div key={idx} className="flex gap-2 items-start hover:bg-white/[0.02] px-1 py-0.5 rounded transition-all">
                  <span className="text-white/30 shrink-0">[{timeStr}]</span>
                  <span className="text-white/40 shrink-0 font-bold">[{log.source.split('.').pop()?.toUpperCase()}]</span>
                  <span className={getLogColor(log.type)}>{log.message.toUpperCase()}</span>
                </div>
              );
            })
          )}
          {logs.length > 0 && (
            <div className="flex items-center gap-1 text-cyan-400 font-bold mt-1 px-1">
              <span>&gt;</span>
              <span className="w-1 h-2 bg-cyan-400 animate-pulse" />
            </div>
          )}
          <div ref={terminalEndRef} />
        </div>
      </div>
    </ScientificCard>
  );
};
