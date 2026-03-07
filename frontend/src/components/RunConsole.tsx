import React, { useEffect, useRef } from 'react';
import { LogEntry } from '../services/logStream';
import { RunState } from '../services/runs';

interface Props {
  run?: RunState | null;
  logs: LogEntry[];
  status: string;
}

const RunConsole: React.FC<Props> = ({ run, logs, status }) => {
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
        <div>
          <h3>Console de Execução</h3>
          {run && (
            <div className="run-meta">
              <span>Agente: {run.agent_id}</span>
              {run.model_id && <span>Modelo: {run.model_id}</span>}
              <span>Modo: {run.execution_mode}</span>
            </div>
          )}
        </div>
        <span className={`status-badge ${status}`}>{status}</span>
      </div>
      
      {run?.decision_history && run.decision_history.length > 0 && (
        <div className="run-stages">
          <h4>Etapas do Ciclo Supervisor</h4>
          <ul className="stage-list">
            {run.decision_history.map((entry, idx) => (
              <li key={idx}>
                <strong>{entry.stage}</strong> - {new Date(entry.timestamp).toLocaleTimeString()}
                {entry.decision && <span className="stage-decision"> [{entry.decision}]</span>}
                {entry.proposed_action && <span className="stage-action"> (Ação: {entry.proposed_action})</span>}
              </li>
            ))}
          </ul>
        </div>
      )}

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
