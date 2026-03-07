import React, { useEffect, useRef } from 'react';
import { LogEntry } from '../services/logStream';

interface Props {
  logs: LogEntry[];
  status: string;
}

const RunConsole: React.FC<Props> = ({ logs, status }) => {
  const logEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [logs]);

  return (
    <div className="panel run-console-panel">
      <div className="panel-header">
        <h3>Console de Execução</h3>
        <span className={`status-badge ${status}`}>{status}</span>
      </div>
      <div className="console-log-area">
        {logs.length === 0 ? (
          <p className="empty-msg">Aguardando início da execução...</p>
        ) : (
          logs.map((log, idx) => (
            <div key={idx} className={`log-line source-${log.source}`}>
              <span className="log-ts">[{new Date(log.timestamp).toLocaleTimeString()}]</span>
              <span className="log-source">[{log.source.toUpperCase()}]</span>
              <span className="log-content">{log.content}</span>
            </div>
          ))
        )}
        <div ref={logEndRef} />
      </div>
    </div>
  );
};

export default RunConsole;
