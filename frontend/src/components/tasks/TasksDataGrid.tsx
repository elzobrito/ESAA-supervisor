import type { TaskSummary } from '../../services/projects';
import { TaskStatusBadge } from './TaskStatusBadge';

interface TasksDataGridProps {
  tasks: TaskSummary[];
  selectedTaskId: string | null;
  onSelectTask: (taskId: string) => void;
  onRunTask: (task: TaskSummary) => void;
  runningTaskRef: string | null;
}

export function TasksDataGrid({ tasks, selectedTaskId, onSelectTask, onRunTask, runningTaskRef }: TasksDataGridProps) {
  return (
    <div className="data-grid-container">
      <table className="data-grid">
        <thead>
          <tr>
            <th>ID</th>
            <th>Título</th>
            <th>Tipo</th>
            <th>Status</th>
            <th>Agente</th>
            <th>Elegibilidade</th>
            <th>Ações</th>
          </tr>
        </thead>
        <tbody>
          {tasks.map((task) => (
            <tr
              key={task.task_ref}
              className={selectedTaskId === task.task_ref ? 'row-selected' : ''}
              onClick={() => onSelectTask(task.task_ref)}
            >
              <td className="task-id-cell">{task.task_id}</td>
              <td>
                <div className="task-title-text">{task.title}</div>
                <div className="task-roadmap-hint">{task.roadmap_label}</div>
                {task.is_eligible ? (
                  <div className="task-eligible-hint">Elegível agora</div>
                ) : task.ineligibility_reasons[0] ? (
                  <div className="task-blocked-hint">{task.ineligibility_reasons[0]}</div>
                ) : null}
              </td>
              <td>
                <span className="kind-badge">{task.task_kind}</span>
              </td>
              <td>
                <TaskStatusBadge status={task.status} />
              </td>
              <td>{task.assigned_to || '-'}</td>
              <td>{task.is_eligible ? 'Sim' : 'Não'}</td>
              <td>
                {task.status === 'todo' && (
                  <button
                    className="btn-primary-ds"
                    type="button"
                    disabled={runningTaskRef === task.task_ref}
                    onClick={(e) => { e.stopPropagation(); onRunTask(task); }}
                    style={{ fontSize: '0.75rem', padding: '4px 12px', minHeight: 'unset' }}
                  >
                    {runningTaskRef === task.task_ref ? 'Iniciando...' : 'Executar'}
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
