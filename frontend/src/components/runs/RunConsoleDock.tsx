import { useEffect, useMemo, useRef, useState } from 'react';
import type { LogEntry } from '../../services/logStream';

interface RunConsoleDockProps {
  logs: LogEntry[];
}

export function RunConsoleDock({ logs }: RunConsoleDockProps) {
  const bodyRef = useRef<HTMLDivElement | null>(null);
  const [now, setNow] = useState(() => Date.now());

  const lastLogAt = useMemo(() => {
    if (logs.length === 0) {
      return null;
    }
    return new Date(logs[logs.length - 1].timestamp).getTime();
  }, [logs]);

  useEffect(() => {
    if (lastLogAt === null) {
      return;
    }
    const timer = window.setInterval(() => {
      setNow(Date.now());
    }, 1000);
    return () => window.clearInterval(timer);
  }, [lastLogAt]);

  useEffect(() => {
    if (!bodyRef.current) {
      return;
    }
    bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
  }, [logs]);

  const idleSeconds = lastLogAt === null ? null : Math.max(0, Math.floor((now - lastLogAt) / 1000));

  return (
    <section className="console-dock dock-md">
      <div className="console-dock-header">
        <span className="console-dock-title">Console dock</span>
        <span className="console-dock-idle">
          {idleSeconds === null ? 'Sem resposta ainda' : `Ultima resposta ha ${idleSeconds}s`}
        </span>
      </div>
      <div ref={bodyRef} className="console-dock-body">
        {logs.length === 0 ? (
          <div className="log-entry">
            <span className="log-source-system">Aguardando logs da próxima execução.</span>
          </div>
        ) : (
          logs.map((log, index) => (
            <div key={`${log.timestamp}-${index}`} className="log-entry">
              <span className="log-ts">{new Date(log.timestamp).toLocaleTimeString()}</span>
              <span className={`log-source-${log.source}`}>{log.source}</span>
              <span>{log.content}</span>
            </div>
          ))
        )}
      </div>
    </section>
  );
}
