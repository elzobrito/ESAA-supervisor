interface TasksFiltersBarProps {
  query: string;
  statusFilter: string;
  kindFilter: string;
  kinds: string[];
  onQueryChange: (value: string) => void;
  onStatusChange: (value: string) => void;
  onKindChange: (value: string) => void;
}

export function TasksFiltersBar({
  query,
  statusFilter,
  kindFilter,
  kinds,
  onQueryChange,
  onStatusChange,
  onKindChange,
}: TasksFiltersBarProps) {
  return (
    <div className="filters-bar">
      <input
        className="filter-input-ds"
        type="search"
        placeholder="Buscar por ID, título ou agente"
        value={query}
        onChange={(event) => onQueryChange(event.target.value)}
      />
      <select className="filter-select-ds" value={statusFilter} onChange={(event) => onStatusChange(event.target.value)}>
        <option value="all">Todos os status</option>
        <option value="todo">To Do</option>
        <option value="in_progress">In Progress</option>
        <option value="review">Review</option>
        <option value="done">Done</option>
      </select>
      <select className="filter-select-ds" value={kindFilter} onChange={(event) => onKindChange(event.target.value)}>
        <option value="all">Todos os tipos</option>
        {kinds.map((kind) => (
          <option key={kind} value={kind}>
            {kind}
          </option>
        ))}
      </select>
    </div>
  );
}
