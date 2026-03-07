import type { TaskSummary } from '../../services/projects';

interface TaskStatusChartProps {
  tasks: TaskSummary[];
}

const STATUS_META: Array<{ status: string; label: string; color: string }> = [
  { status: 'done', label: 'Done', color: 'var(--color-success)' },
  { status: 'in_progress', label: 'Em andamento', color: 'var(--color-info)' },
  { status: 'review', label: 'Review', color: 'var(--color-warning)' },
  { status: 'todo', label: 'Todo', color: 'var(--color-neutral)' },
];

export function TaskStatusChart({ tasks }: TaskStatusChartProps) {
  const total = tasks.length || 1;
  const rows = STATUS_META.map((entry) => {
    const count = tasks.filter((task) => task.status === entry.status).length;
    return { ...entry, count, pct: Math.round((count / total) * 100) };
  });

  return (
    <article className="chart-card chart-card-rich">
      <div className="chart-card-header">
        <div>
          <p className="chart-title">Tasks por status</p>
          <p className="chart-subtitle">Distribuicao atual do fluxo operacional.</p>
        </div>
        <span className="chart-total">{tasks.length} total</span>
      </div>

      <div className="stacked-bar" aria-hidden="true">
        {rows.map((row) => (
          <span
            key={row.status}
            className="stacked-bar-segment"
            style={{ width: `${row.pct}%`, background: row.color }}
          />
        ))}
      </div>

      <div className="chart-legend-grid">
        {rows.map((row) => (
          <div key={row.status} className="chart-legend-item">
            <span className="chart-dot" style={{ background: row.color }} />
            <span className="chart-legend-label">{row.label}</span>
            <span className="chart-legend-value">
              {row.count}
              {' '}
              <small>{row.pct}%</small>
            </span>
          </div>
        ))}
      </div>
    </article>
  );
}
