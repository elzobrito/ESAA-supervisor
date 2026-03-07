import type { ActivityEvent } from '../../services/projects';

interface ActivityTimelineChartProps {
  activity: ActivityEvent[];
}

function bucketLabel(ts: string): string {
  const date = new Date(ts);
  const hours = String(date.getUTCHours()).padStart(2, '0');
  return `${hours}:00`;
}

export function ActivityTimelineChart({ activity }: ActivityTimelineChartProps) {
  const counts = new Map<string, number>();

  activity.forEach((event) => {
    const label = bucketLabel(event.ts);
    counts.set(label, (counts.get(label) ?? 0) + 1);
  });

  const buckets = Array.from(counts.entries()).slice(-6).map(([label, count]) => ({ label, count }));
  const max = Math.max(...buckets.map((bucket) => bucket.count), 1);

  return (
    <article className="chart-card chart-card-rich">
      <div className="chart-card-header">
        <div>
          <p className="chart-title">Atividade recente</p>
          <p className="chart-subtitle">Volume de eventos por janela de tempo.</p>
        </div>
      </div>

      {buckets.length === 0 ? (
        <div className="chart-empty">Sem eventos suficientes para montar a timeline.</div>
      ) : (
        <div className="timeline-bars">
          {buckets.map((bucket) => (
            <div key={bucket.label} className="timeline-bar-item">
              <div
                className="timeline-bar-fill"
                style={{ height: `${Math.max(18, (bucket.count / max) * 120)}px` }}
                title={`${bucket.count} eventos`}
              />
              <span className="timeline-bar-value">{bucket.count}</span>
              <span className="timeline-bar-label">{bucket.label}</span>
            </div>
          ))}
        </div>
      )}
    </article>
  );
}
