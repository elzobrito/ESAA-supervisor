import React from 'react';

interface Event {
  event_seq: number;
  event_id: string;
  action: string;
  ts: string;
  actor: string;
}

interface Props {
  events: Event[];
}

const ActivityPanel: React.FC<Props> = ({ events }) => {
  return (
    <div className="panel activity-panel">
      <h3>Atividade Recente</h3>
      <div className="timeline">
        {events.slice().reverse().map((ev) => (
          <div key={ev.event_id} className="timeline-item">
            <span className="ev-seq">#{ev.event_seq}</span>
            <div className="ev-content">
              <span className="ev-action">{ev.action}</span>
              <span className="ev-meta">
                {ev.actor} · {new Date(ev.ts).toLocaleString()}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ActivityPanel;
