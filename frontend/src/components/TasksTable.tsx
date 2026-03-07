import React, { useMemo, useState } from 'react';
import { AlertTriangle, CheckCircle, Clock, Eye, Play } from 'lucide-react';

interface Task {
  task_id: string;
  task_kind: string;
  title: string;
  status: string;
  assigned_to?: string | null;
  is_eligible?: boolean;
  ineligibility_reasons?: string[];
}

interface Props {
  tasks: Task[];
  selectedTaskId?: string | null;
  onRunTask: (taskId: string) => void;
  onViewDetails: (taskId: string) => void;
}

const TasksTable: React.FC<Props> = ({ tasks, selectedTaskId, onRunTask, onViewDetails }) => {
  const [statusFilter, setStatusFilter] = useState('all');
  const [kindFilter, setKindFilter] = useState('all');
  const [query, setQuery] = useState('');

  const kinds = useMemo(
    () => Array.from(new Set(tasks.map((task) => task.task_kind).filter(Boolean))).sort(),
    [tasks],
  );

  const filteredTasks = useMemo(
    () =>
      tasks.filter((task) => {
        const matchesStatus = statusFilter === 'all' || task.status === statusFilter;
        const matchesKind = kindFilter === 'all' || task.task_kind === kindFilter;
        const haystack = `${task.task_id} ${task.title} ${task.assigned_to ?? ''}`.toLowerCase();
        const matchesQuery = query.trim() === '' || haystack.includes(query.trim().toLowerCase());
        return matchesStatus && matchesKind && matchesQuery;
      }),
    [kindFilter, query, statusFilter, tasks],
  );

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'done':
        return <CheckCircle size={16} color="green" />;
      case 'in_progress':
        return <Clock size={16} color="blue" className="spin" />;
      case 'review':
        return <Eye size={16} color="orange" />;
      case 'todo':
        return <Play size={16} color="gray" />;
      default:
        return <AlertTriangle size={16} />;
    }
  };

  return (
    <div className="panel tasks-table-panel">
      <div className="panel-header stack-on-mobile">
        <h3>Tarefas do Roadmap</h3>
        <div className="filters-row">
          <input
            className="filter-input"
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Buscar por ID, título ou agente"
          />
          <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
            <option value="all">Todos os status</option>
            <option value="todo">To Do</option>
            <option value="in_progress">In Progress</option>
            <option value="review">Review</option>
            <option value="done">Done</option>
          </select>
          <select value={kindFilter} onChange={(event) => setKindFilter(event.target.value)}>
            <option value="all">Todos os tipos</option>
            {kinds.map((kind) => (
              <option key={kind} value={kind}>
                {kind}
              </option>
            ))}
          </select>
        </div>
      </div>
      <table className="tasks-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Título</th>
            <th>Tipo</th>
            <th>Status</th>
            <th>Agente</th>
            <th>Ações</th>
          </tr>
        </thead>
        <tbody>
          {filteredTasks.map((task) => (
            <tr
              key={task.task_id}
              className={`status-${task.status} ${selectedTaskId === task.task_id ? 'selected-row' : ''}`}
            >
              <td>{task.task_id}</td>
              <td>
                <div className="task-title-cell">
                  <span>{task.title}</span>
                  {task.is_eligible ? (
                    <span className="badge eligible">elegível</span>
                  ) : task.ineligibility_reasons?.length ? (
                    <span className="muted-text">{task.ineligibility_reasons[0]}</span>
                  ) : null}
                </div>
              </td>
              <td>{task.task_kind}</td>
              <td>
                <span className="status-cell">
                  {getStatusIcon(task.status)} {task.status}
                </span>
              </td>
              <td>{task.assigned_to || '-'}</td>
              <td>
                <div className="actions-row">
                  <button onClick={() => onViewDetails(task.task_id)} title="Ver detalhes">
                    <Eye size={14} />
                  </button>
                  {task.status === 'todo' && (
                    <button onClick={() => onRunTask(task.task_id)} title="Executar">
                      <Play size={14} />
                    </button>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default TasksTable;
