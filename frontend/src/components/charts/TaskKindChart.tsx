import type { TaskSummary } from '../../services/projects';

interface TaskKindChartProps {
  tasks: TaskSummary[];
}

const KIND_LABELS: Record<string, string> = {
  spec: 'Spec',
  impl: 'Impl',
  qa: 'QA',
};

const KIND_COLORS: Record<string, string> = {
  spec: 'var(--color-accent)',
  impl: 'var(--color-info)',
  qa: 'var(--color-success)',
};

export function TaskKindChart({ tasks }: TaskKindChartProps) {
  const total = tasks.length || 1;
  const rows = ['spec', 'impl', 'qa'].map((kind) => {
    const count = tasks.filter((task) => task.task_kind === kind).length;
    return {
      kind,
      label: KIND_LABELS[kind] ?? kind,
      color: KIND_COLORS[kind] ?? 'var(--color-neutral)',
      count,
      pct: Math.round((count / total) * 100),
    };
  });

  return (
    <article className="chart-card chart-card-rich">
      <div className="chart-card-header">
        <div>
          <p className="chart-title">Tasks por tipo</p>
          <p className="chart-subtitle">Balanceamento entre especificacao, execucao e QA.</p>
        </div>
      </div>

      <div className="metric-bars">
        {rows.map((row) => (
          <div key={row.kind} className="metric-bar-row">
            <div className="metric-bar-meta">
              <span>{row.label}</span>
              <strong>{row.count}</strong>
            </div>
            <div className="metric-bar-track">
              <div className="metric-bar-fill" style={{ width: `${row.pct}%`, background: row.color }} />
            </div>
          </div>
        ))}
      </div>
    </article>
  );
}
