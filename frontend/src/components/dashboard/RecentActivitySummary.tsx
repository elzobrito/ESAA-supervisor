import type { ActivityEvent } from '../../services/projects';

interface RecentActivitySummaryProps {
  activity: ActivityEvent[];
}

export function RecentActivitySummary({ activity }: RecentActivitySummaryProps) {
  const events = activity.slice().reverse().slice(0, 6);

  return (
    <section className="panel-card">
      <div className="panel-card-header">
        <h3 className="panel-card-title">Atividade recente</h3>
      </div>
      <div className="panel-card-body">
        {events.length === 0 ? (
          <p className="panel-empty">Sem eventos recentes.</p>
        ) : (
          events.map((event) => (
            <div key={event.event_id} className="activity-item">
              <span className="activity-seq">#{event.event_seq}</span>
              <span className="activity-action">{event.action}</span>
              <span className="activity-meta">{event.actor}</span>
              <span className="activity-time">{new Date(event.ts).toLocaleTimeString()}</span>
            </div>
          ))
        )}
      </div>
    </section>
  );
}
