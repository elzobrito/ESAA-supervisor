import { useEffect, useMemo, useState } from 'react';
import { X } from 'lucide-react';
import { extractErrorMessage } from '../../services/api';
import { resetTaskToTodo, submitTaskReview, updateTaskPlanning } from '../../services/projects';
import type { TaskSummary } from '../../services/projects';
import { TaskStatusBadge } from './TaskStatusBadge';

interface TaskDetailDrawerProps {
  projectId: string;
  availableAgents: Array<{
    agent_id: string;
    label: string;
    available: boolean;
    busy: boolean;
  }>;
  remainingRunSlots: number;
  task: TaskSummary | null;
  open: boolean;
  onClose: () => void;
  onTaskUpdated: () => void;
  onExecuteTask: (task: TaskSummary, overrides: { agentId?: string }) => Promise<void>;
}

export function TaskDetailDrawer({
  projectId,
  availableAgents,
  remainingRunSlots,
  task,
  open,
  onClose,
  onTaskUpdated,
  onExecuteTask,
}: TaskDetailDrawerProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [mutationError, setMutationError] = useState<string | null>(null);
  const [preferredRunner, setPreferredRunner] = useState('');

  const selectedAgent = useMemo(
    () => availableAgents.find((agent) => agent.agent_id === preferredRunner) ?? null,
    [availableAgents, preferredRunner],
  );
  const canResumeTask = task?.status === 'in_progress' && !task.active_run_id;
  const canExecuteNow = !!task
    && !task.active_run_id
    && remainingRunSlots > 0
    && !!selectedAgent
    && selectedAgent.available
    && !selectedAgent.busy
    && (task.is_eligible || canResumeTask);

  useEffect(() => {
    if (!task) {
      return;
    }
    const nextPreferredRunner = task.planning?.preferred_runner ?? availableAgents.find((agent) => !agent.busy)?.agent_id ?? availableAgents[0]?.agent_id ?? '';
    setPreferredRunner(nextPreferredRunner);
  }, [availableAgents, task]);

  if (!open || !task) {
    return null;
  }

  const handleResetToTodo = async () => {
    setIsSubmitting(true);
    setMutationError(null);
    try {
      await resetTaskToTodo(projectId, task.task_id, task.roadmap_id);
      await onTaskUpdated();
      onClose();
    } catch (error) {
      setMutationError(extractErrorMessage(error));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReviewDecision = async (decision: 'approve' | 'reject') => {
    setIsSubmitting(true);
    setMutationError(null);
    try {
      await submitTaskReview(projectId, task.task_id, {
        decision,
        roadmapId: task.roadmap_id,
      });
      await onTaskUpdated();
      onClose();
    } catch (error) {
      setMutationError(extractErrorMessage(error));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSavePlanning = async () => {
    setIsSubmitting(true);
    setMutationError(null);
    try {
      await updateTaskPlanning(projectId, task.task_id, {
        roadmapId: task.roadmap_id,
        preferredRunner,
      });
      await onTaskUpdated();
    } catch (error) {
      setMutationError(extractErrorMessage(error));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleExecuteNow = async () => {
    setIsSubmitting(true);
    setMutationError(null);
    try {
      await onExecuteTask(task, {
        agentId: preferredRunner || undefined,
      });
      onClose();
    } catch (error) {
      setMutationError(extractErrorMessage(error));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      <div className="drawer-overlay" onClick={onClose} aria-hidden="true" />
      <aside className="drawer" aria-label="Detalhes da tarefa">
        <div className="drawer-header">
          <div>
            <p className="task-id-cell">{task.task_id}</p>
            <h3 className="drawer-title">{task.title}</h3>
          </div>
          <button className="drawer-close" type="button" onClick={onClose} aria-label="Fechar detalhe">
            <X size={18} />
          </button>
        </div>
        <div className="drawer-body">
          <section className="drawer-section">
            <span className="drawer-section-label">Resumo</span>
            <div className="drawer-section-content">
              <TaskStatusBadge status={task.status} /> <span className="kind-badge">{task.task_kind}</span>
              <span className="kind-badge">{task.roadmap_label}</span>
              <p>{task.description || 'Sem descrição detalhada.'}</p>
            </div>
          </section>
          <section className="drawer-section">
            <span className="drawer-section-label">Dependências</span>
            <div className="drawer-section-content">
              {task.depends_on?.length ? task.depends_on.join(', ') : 'Nenhuma dependência.'}
            </div>
          </section>
          <section className="drawer-section">
            <span className="drawer-section-label">Elegibilidade</span>
            <div className="drawer-section-content">
              {task.is_eligible ? (
                <p className="task-eligible-hint">Task elegível.</p>
              ) : task.ineligibility_reasons.length ? (
                <ul>
                  {task.ineligibility_reasons.map((reason) => (
                    <li key={reason}>{reason}</li>
                  ))}
                </ul>
              ) : (
                'Sem sinais de elegibilidade.'
              )}
            </div>
          </section>
          <section className="drawer-section">
            <span className="drawer-section-label">Execução</span>
            <div className="drawer-section-content">
              <p>Agente atual: {task.assigned_to || 'não atribuído'}</p>
              <p>Run ativa: {task.active_run_id ?? 'nenhuma'}</p>
              <p>Slots disponíveis: {remainingRunSlots}</p>
              {selectedAgent ? (
                <p className={selectedAgent.available && !selectedAgent.busy ? 'task-eligible-hint' : 'task-blocked-hint'}>
                  Override atual: {selectedAgent.label}
                  {!selectedAgent.available ? ' indisponível no ambiente.' : selectedAgent.busy ? ' ocupado em outra run.' : ' disponível.'}
                </p>
              ) : null}
            </div>
          </section>
          <section className="drawer-section">
            <span className="drawer-section-label">Padrão da task</span>
            <div className="drawer-section-content">
              <label className="run-control-field">
                <span className="run-control-label">Agente padrão</span>
                <select className="filter-select-ds" value={preferredRunner} onChange={(event) => setPreferredRunner(event.target.value)}>
                  {availableAgents.map((agent) => (
                    <option key={agent.agent_id} value={agent.agent_id}>
                      {agent.label}{agent.busy ? ' (ocupado)' : ''}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </section>
          {mutationError ? <p className="error-text">{mutationError}</p> : null}
        </div>
        <div className="drawer-footer">
          <button
            className="btn-primary-ds"
            type="button"
            onClick={() => void handleExecuteNow()}
            disabled={isSubmitting || !canExecuteNow}
          >
            Executar agora
          </button>
          <button
            className="btn-secondary-ds"
            type="button"
            onClick={() => void handleSavePlanning()}
            disabled={isSubmitting || !preferredRunner || !selectedAgent || !selectedAgent.available}
          >
            Salvar padrão
          </button>
          {task.status === 'review' ? (
            <>
              <button
                className="btn-primary-ds"
                type="button"
                onClick={() => void handleReviewDecision('approve')}
                disabled={isSubmitting}
              >
                Aprovar review
              </button>
              <button
                className="btn-danger-ds"
                type="button"
                onClick={() => void handleReviewDecision('reject')}
                disabled={isSubmitting}
              >
                Rejeitar review
              </button>
            </>
          ) : null}
          <button
            className="btn-secondary-ds"
            type="button"
            onClick={() => void handleResetToTodo()}
            disabled={isSubmitting || task.status === 'todo'}
          >
            Regredir para todo
          </button>
        </div>
      </aside>
    </>
  );
}
