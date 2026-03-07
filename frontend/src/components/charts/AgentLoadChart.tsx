import type { ActivityEvent, TaskSummary } from '../../services/projects';

interface AgentLoadChartProps {
  tasks: TaskSummary[];
  activity: ActivityEvent[];
}

type AgentRow = {
  agent: string;
  assigned: number;
  done: number;
};

function buildRows(tasks: TaskSummary[], activity: ActivityEvent[]): AgentRow[] {
  const agentMap = new Map<string, AgentRow>();

  tasks.forEach((task) => {
    if (!task.assigned_to) {
      return;
    }
    const row = agentMap.get(task.assigned_to) ?? { agent: task.assigned_to, assigned: 0, done: 0 };
    row.assigned += 1;
    if (task.status === 'done') {
      row.done += 1;
    }
    agentMap.set(task.assigned_to, row);
  });

  if (agentMap.size === 0) {
    activity.forEach((event) => {
      const key = event.actor || 'desconhecido';
      const row = agentMap.get(key) ?? { agent: key, assigned: 0, done: 0 };
      row.assigned += 1;
      agentMap.set(key, row);
    });
  }

  return Array.from(agentMap.values()).sort((a, b) => b.assigned - a.assigned).slice(0, 5);
}

export function AgentLoadChart({ tasks, activity }: AgentLoadChartProps) {
  const rows = buildRows(tasks, activity);
  const max = Math.max(...rows.map((row) => row.assigned), 1);

  return (
    <article className="chart-card chart-card-rich">
      <div className="chart-card-header">
        <div>
          <p className="chart-title">Carga por agente</p>
          <p className="chart-subtitle">Distribuicao de ownership e entregas concluidas.</p>
        </div>
      </div>

      {rows.length === 0 ? (
        <div className="chart-empty">Sem atribuicoes suficientes para comparar agentes.</div>
      ) : (
        <div className="agent-load-list">
          {rows.map((row) => (
            <div key={row.agent} className="agent-load-item">
              <div className="agent-load-header">
                <span className="agent-load-name">{row.agent}</span>
                <span className="agent-load-count">{row.assigned} tasks</span>
              </div>
              <div className="agent-load-track">
                <div className="agent-load-fill" style={{ width: `${Math.max(12, (row.assigned / max) * 100)}%` }} />
              </div>
              <div className="agent-load-meta">{row.done} concluidas</div>
            </div>
          ))}
        </div>
      )}
    </article>
  );
}
