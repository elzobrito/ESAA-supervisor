import { useMemo, useState } from 'react';

import type { ActivityEvent } from '../../services/projects';
import { ActivityItem } from './ActivityItem';
import { EventPayloadModal } from './EventPayloadModal';

interface ActivityTimelineProps {
  events: ActivityEvent[];
}

function categoryFromAction(action: string) {
  if (action.includes('review')) return 'review';
  if (action.includes('complete')) return 'complete';
  if (action.includes('issue')) return 'issue';
  if (action.includes('lesson')) return 'lesson';
  return 'claim';
}

export function ActivityTimeline({ events }: ActivityTimelineProps) {
  const [query, setQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);

  const sortedEvents = useMemo(() => events.slice().sort((a, b) => b.event_seq - a.event_seq), [events]);
  const filteredEvents = useMemo(() => sortedEvents.filter((event) => {
    const haystack = `${event.action} ${event.actor} ${event.task_id ?? ''} ${JSON.stringify(event.payload ?? {})}`.toLowerCase();
    const matchesQuery = query.trim() === '' || haystack.includes(query.toLowerCase());
    const matchesCategory = categoryFilter === 'all' || categoryFromAction(event.action) === categoryFilter;
    return matchesQuery && matchesCategory;
  }), [categoryFilter, query, sortedEvents]);

  const selectedEvent = filteredEvents.find((event) => event.event_id === selectedEventId)
    ?? sortedEvents.find((event) => event.event_id === selectedEventId)
    ?? null;

  return (
    <>
      <div className="activity-hero-grid">
        <div className="catalog-summary-card">
          <span className="catalog-summary-label">Eventos visíveis</span>
          <strong>{filteredEvents.length}</strong>
        </div>
        <div className="catalog-summary-card">
          <span className="catalog-summary-label">Claims</span>
          <strong>{events.filter((event) => categoryFromAction(event.action) === 'claim').length}</strong>
        </div>
        <div className="catalog-summary-card">
          <span className="catalog-summary-label">Completes</span>
          <strong>{events.filter((event) => categoryFromAction(event.action) === 'complete').length}</strong>
        </div>
        <div className="catalog-summary-card">
          <span className="catalog-summary-label">Reviews</span>
          <strong>{events.filter((event) => categoryFromAction(event.action) === 'review').length}</strong>
        </div>
      </div>

      <div className="filters-bar activity-filters-bar">
        <input
          className="filter-input-ds"
          type="search"
          placeholder="Buscar por ação, actor, task ou payload"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <select className="filter-select-ds" value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value)}>
          <option value="all">Todas as categorias</option>
          <option value="claim">Claim</option>
          <option value="complete">Complete</option>
          <option value="review">Review</option>
          <option value="issue">Issue</option>
          <option value="lesson">Lesson</option>
        </select>
      </div>

      <div className="activity-timeline-list">
        {filteredEvents.length === 0 ? (
          <div className="catalog-empty-state">Nenhum evento corresponde aos filtros aplicados.</div>
        ) : (
          filteredEvents.map((event) => (
            <ActivityItem
              key={event.event_id}
              event={event}
              selected={selectedEventId === event.event_id}
              onSelect={(nextEvent) => setSelectedEventId(nextEvent.event_id)}
            />
          ))
        )}
      </div>

      <EventPayloadModal
        event={selectedEvent}
        open={selectedEvent !== null}
        onClose={() => setSelectedEventId(null)}
      />
    </>
  );
}
