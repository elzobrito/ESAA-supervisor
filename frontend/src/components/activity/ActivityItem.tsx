import { AlertTriangle, BookOpenText, CheckCheck, ClipboardCheck, PlayCircle } from 'lucide-react';

import type { ActivityEvent } from '../../services/projects';

interface ActivityItemProps {
  event: ActivityEvent;
  selected: boolean;
  onSelect: (event: ActivityEvent) => void;
}

function getEventTone(action: string) {
  if (action.includes('review')) {
    return {
      label: 'Review',
      className: 'activity-tone-review',
      icon: ClipboardCheck,
    };
  }
  if (action.includes('complete')) {
    return {
      label: 'Complete',
      className: 'activity-tone-complete',
      icon: CheckCheck,
    };
  }
  if (action.includes('issue')) {
    return {
      label: 'Issue',
      className: 'activity-tone-issue',
      icon: AlertTriangle,
    };
  }
  if (action.includes('lesson')) {
    return {
      label: 'Lesson',
      className: 'activity-tone-lesson',
      icon: BookOpenText,
    };
  }
  return {
    label: 'Claim',
    className: 'activity-tone-claim',
    icon: PlayCircle,
  };
}

function summarize(event: ActivityEvent) {
  if (typeof event.payload?.summary === 'string') {
    return event.payload.summary;
  }
  if (typeof event.payload?.notes === 'string') {
    return event.payload.notes;
  }
  if (event.task_id) {
    return `${event.action} vinculado à task ${event.task_id}.`;
  }
  return `Evento ${event.action} registrado por ${event.actor}.`;
}

export function ActivityItem({ event, selected, onSelect }: ActivityItemProps) {
  const tone = getEventTone(event.action);
  const Icon = tone.icon;

  return (
    <button
      type="button"
      className={`activity-timeline-item ${tone.className} ${selected ? 'activity-timeline-item-selected' : ''}`}
      onClick={() => onSelect(event)}
    >
      <div className="activity-timeline-icon">
        <Icon size={16} />
      </div>
      <div className="activity-timeline-body">
        <div className="activity-timeline-header">
          <div className="activity-timeline-title-row">
            <span className="activity-timeline-tone">{tone.label}</span>
            <strong className="activity-timeline-action">{event.action}</strong>
            {event.task_id ? <span className="task-id-cell">{event.task_id}</span> : null}
          </div>
          <span className="activity-timeline-seq">#{event.event_seq}</span>
        </div>
        <p className="activity-timeline-summary">{summarize(event)}</p>
        <div className="activity-timeline-meta">
          <span>{event.actor}</span>
          <span>{new Date(event.ts).toLocaleString()}</span>
          {event.prior_status ? <span>prior: {event.prior_status}</span> : null}
        </div>
      </div>
    </button>
  );
}
