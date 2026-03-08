import type { TaskSummary } from '../../services/projects';
import { TaskStatusBadge } from './TaskStatusBadge';

interface TasksDataGridProps {
  availableAgents: Array<{
    agent_id: string;
    available: boolean;
    busy: boolean;
  }>;
  activeRunCount: number;
  remainingRunSlots: number;
  roadmapConsistencyById: Record<string, boolean>;
  tasks: TaskSummary[];
  selectedTaskId: string | null;
  onSelectTask: (taskId: string) => void;
  onRunTask: (task: TaskSummary) => void;
  runningTaskRef: string | null;
}

export function TasksDataGrid({
  availableAgents,
  activeRunCount,
  remainingRunSlots,
  roadmapConsistencyById,
  tasks,
  selectedTaskId,
  onSelectTask,
  onRunTask,
  runningTaskRef,
}: TasksDataGridProps) {
  return (
    <div className="data-grid-container">
      <table className="data-grid">
        <thead>
          <tr>
            <th>ID</th>
            <th>Título</th>
            <th>Tipo</th>
            <th>Status</th>
            <th>Padrão</th>
            <th>Execução ativa</th>
            <th>Elegibilidade</th>
            <th>Ações</th>
          </tr>
        </thead>
        <tbody>
          {tasks.map((task) => (
            (() => {
              const preferredRunner = task.planning?.preferred_runner ?? '-';
              const preferredAgent = preferredRunner !== '-' ? availableAgents.find((agent) => agent.agent_id === preferredRunner) : null;
              const agentUnavailable = preferredAgent ? !preferredAgent.available : false;
              const agentBusy = preferredRunner !== '-' && availableAgents.some((agent) => agent.agent_id === preferredRunner && agent.busy);
              const canResume = task.status === 'in_progress' && !task.active_run_id;
              const canExecute = task.status === 'todo' || canResume;
              const ownershipConflict = canResume && !!task.assigned_to && preferredRunner !== '-' && task.assigned_to !== preferredRunner;
              let disabledReason: string | null = null;

              if (!canExecute) {
                disabledReason = 'Task não está em estado executável.';
              } else if (task.active_run_id) {
                disabledReason = 'Task já está em execução.';
              } else if (remainingRunSlots <= 0) {
                disabledReason = `Projeto já atingiu o limite de ${activeRunCount} runs ativas.`;
              } else if (agentUnavailable) {
                disabledReason = `Agente ${preferredRunner} não está disponível no ambiente.`;
              } else if (agentBusy) {
                disabledReason = `Agente ${preferredRunner} já está ocupado.`;
              } else if (ownershipConflict) {
                disabledReason = `Task em progresso atribuída a ${task.assigned_to}. Regreda para todo antes de trocar para ${preferredRunner}.`;
              } else if (!canResume && !task.is_eligible) {
                disabledReason = task.ineligibility_reasons[0] ?? 'Task inelegível.';
              }

              return (
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
                  <td>
                    <div>{preferredRunner}</div>
                  </td>
                  <td>
                    {task.active_run_id ? (
                      <>
                        <div>{task.active_agent ?? '-'}</div>
                        <div className="task-roadmap-hint">{task.active_model ?? 'modelo padrão'}</div>
                      </>
                    ) : '-'}
                  </td>
                  <td>{canResume || task.is_eligible ? 'Sim' : 'Não'}</td>
                  <td>
                    {canExecute && (
                      <button
                        className="btn-primary-ds"
                        type="button"
                        disabled={runningTaskRef === task.task_ref || disabledReason !== null}
                        onClick={(e) => { e.stopPropagation(); onRunTask(task); }}
                        style={{ fontSize: '0.75rem', padding: '4px 12px', minHeight: 'unset' }}
                        title={disabledReason ?? 'Executar com os padrões da task'}
                      >
                        {runningTaskRef === task.task_ref ? 'Iniciando...' : 'Executar'}
                      </button>
                    )}
                  </td>
                </tr>
              );
            })()
          ))}
        </tbody>
      </table>
    </div>
  );
}
