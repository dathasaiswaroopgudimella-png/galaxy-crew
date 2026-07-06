import { useEffect } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { usePHSEStore } from './stores/usePHSEStore'
import { useWebsocket } from './hooks/useWebsocket'
import { MissionLayout } from './layouts/MissionLayout'
import { MissionControl } from './pages/MissionControl'

const queryClient = new QueryClient()

function AppContent() {
  // Mount the WebSocket telemetry channel
  useWebsocket();

  const setPipelineResults = usePHSEStore((state) => state.setPipelineResults);

  // Ingest initial pipeline data on bootup
  const fetchInitialResults = async () => {
    try {
      const res = await fetch('/api/run', { method: 'POST' });
      const data = await res.json();
      setPipelineResults(data);
    } catch (e) {
      console.error("Initial pipeline fetch error:", e);
    }
  };

  useEffect(() => {
    fetchInitialResults();
  }, []);

  return (
    <MissionLayout>
      <MissionControl />
    </MissionLayout>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppContent />
    </QueryClientProvider>
  );
}

export default App
