import { useEffect, useRef } from 'react'
import { usePHSEStore } from '../stores/usePHSEStore'

export const useWebsocket = () => {
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  
  const addTelemetryLog = usePHSEStore((state) => state.addTelemetryLog);
  const setWebsocketStatus = usePHSEStore((state) => state.setWebsocketStatus);

  const connect = () => {
    if (socketRef.current) {
      socketRef.current.close();
    }

    setWebsocketStatus('connecting');
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    // Use target address; default to backend port 8000 if running Vite dev server
    const host = window.location.port === '3000' ? `${window.location.hostname}:8000` : window.location.host;
    const wsUrl = `${protocol}//${host}/api/ws`;

    try {
      const ws = new WebSocket(wsUrl);
      socketRef.current = ws;

      ws.onopen = () => {
        setWebsocketStatus('connected');
        addTelemetryLog({
          source: 'System',
          message: 'Connected to PHSE real-time telemetry stream.',
          type: 'success'
        });
      };

      ws.onmessage = (event) => {
        try {
          const logData = JSON.parse(event.data);
          addTelemetryLog({
            timestamp: logData.timestamp,
            source: logData.source || 'PHSE-Core',
            message: logData.message,
            type: logData.type || 'info'
          });
        } catch (e) {
          addTelemetryLog({
            source: 'Websocket',
            message: `Raw message: ${event.data}`,
            type: 'info'
          });
        }
      };

      ws.onclose = () => {
        setWebsocketStatus('disconnected');
        socketRef.current = null;
        // Auto reconnect after 3 seconds
        reconnectTimeoutRef.current = window.setTimeout(() => {
          connect();
        }, 3000);
      };

      ws.onerror = () => {
        setWebsocketStatus('disconnected');
      };

    } catch (err: any) {
      console.error('WebSocket connection error:', err);
      setWebsocketStatus('disconnected');
    }
  };

  useEffect(() => {
    connect();
    return () => {
      if (socketRef.current) {
        socketRef.current.onclose = null;
        socketRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, []);

  return socketRef.current;
};
