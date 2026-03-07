import { useMemo, useState } from 'react';

import type { ActivityEvent } from '../../services/projects';
import { ActivityItem } from './ActivityItem';
import { EventPayloadModal } from './EventPayloadModal';

interface ActivityTimelineProps {
  events: ActivityEvent[];
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function categoryFromAction(action: string) {
  if (action.includes('review')) return 'review';
  if (action.includes('complete')) return 'complete';
  if (action.includes('issue')) return 'issue';
  if (action.includes('lesson')) return 'lesson';
  return 'claim';
}

function extractEventUsage(event: ActivityEvent): { total?: number; totalCostUsd?: number } | null {
  const payload = event.payload;
  if (!isRecord(payload)) {
    return null;
  }
  const execution = payload.agent_execution;
  if (!isRecord(execution)) {
    return null;
  }
  const tokenUsage = execution.token_usage;
  if (!isRecord(tokenUsage)) {
    return null;
  }
  return {
    total: typeof tokenUsage.total === 'number' ? tokenUsage.total : undefined,
    totalCostUsd: typeof tokenUsage.total_cost_usd === 'number' ? tokenUsage.total_cost_usd : undefined,
  };
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
  const tokenEvents = useMemo(
    () => sortedEvents
      .map((event) => ({ event, usage: extractEventUsage(event) }))
      .filter((item) => item.usage !== null),
    [sortedEvents],
  );
  const totalTokens = tokenEvents.reduce((sum, item) => sum + (item.usage?.total ?? 0), 0);
  const totalCostUsd = tokenEvents.reduce((sum, item) => sum + (item.usage?.totalCostUsd ?? 0), 0);
  const usageByTask = useMemo(() => {
    const grouped = new Map<string, { taskId: string; events: number; totalTokens: number; totalCostUsd: number }>();
    for (const item of tokenEvents) {
      const taskId = item.event.task_id ?? 'Sem task';
      const current = grouped.get(taskId) ?? { taskId, events: 0, totalTokens: 0, totalCostUsd: 0 };
      current.events += 1;
      current.totalTokens += item.usage?.total ?? 0;
      current.totalCostUsd += item.usage?.totalCostUsd ?? 0;
      grouped.set(taskId, current);
    }
    return Array.from(grouped.values()).sort((a, b) => b.totalTokens - a.totalTokens).slice(0, 6);
  }, [tokenEvents]);

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
        <div className="catalog-summary-card">
          <span className="catalog-summary-label">Eventos com tokens</span>
          <strong>{tokenEvents.length}</strong>
        </div>
        <div className="catalog-summary-card">
          <span className="catalog-summary-label">Tokens totais</span>
          <strong>{totalTokens || 0}</strong>
        </div>
        <div className="catalog-summary-card">
          <span className="catalog-summary-label">Custo total</span>
          <strong>{totalCostUsd > 0 ? `$${totalCostUsd.toFixed(6)}` : 'n/d'}</strong>
        </div>
      </div>

      {usageByTask.length > 0 ? (
        <div className="run-json-card">
          <div className="run-json-title">Consumo por task</div>
          <div className="decision-history-list">
            {usageByTask.map((item) => (
              <div key={item.taskId} className="decision-history-item">
                <div className="decision-history-top">
                  <strong>{item.taskId}</strong>
                </div>
                <div className="decision-history-meta">
                  <span>eventos: {item.events}</span>
                  <span>tokens: {item.totalTokens}</span>
                  <span>custo: {item.totalCostUsd > 0 ? `$${item.totalCostUsd.toFixed(6)}` : 'n/d'}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}

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
