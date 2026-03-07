export interface LogEntry {
  timestamp: string;
  source: 'stdout' | 'stderr' | 'system';
  content: string;
}

export const subscribeToLogs = (
  projectId: string, 
  runId: string, 
  onLog: (log: LogEntry) => void,
  onError: (err: any) => void
) => {
  const url = `http://localhost:8000/api/v1/projects/${projectId}/logs/stream/${runId}`;
  const eventSource = new EventSource(url);

  eventSource.addEventListener('log', (event) => {
    try {
      const logEntry = JSON.parse(event.data);
      onLog(logEntry);
    } catch (err) {
      console.error('Error parsing log event:', err);
    }
  });

  eventSource.onerror = (err) => {
    onError(err);
    eventSource.close();
  };

  return () => eventSource.close();
};
