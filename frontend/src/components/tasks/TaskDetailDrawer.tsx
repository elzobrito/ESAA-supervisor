import { useState } from 'react';
import { X } from 'lucide-react';
import { extractErrorMessage } from '../../services/api';
import { resetTaskToTodo, submitTaskReview } from '../../services/projects';
import type { TaskSummary } from '../../services/projects';
import { TaskStatusBadge } from './TaskStatusBadge';

interface TaskDetailDrawerProps {
  projectId: string;
  task: TaskSummary | null;
  open: boolean;
  onClose: () => void;
  onTaskUpdated: () => void;
}

export function TaskDetailDrawer({ projectId, task, open, onClose, onTaskUpdated }: TaskDetailDrawerProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [mutationError, setMutationError] = useState<string | null>(null);

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
              Agente atual: {task.assigned_to || 'não atribuído'}
            </div>
          </section>
          {mutationError ? <p className="error-text">{mutationError}</p> : null}
        </div>
        <div className="drawer-footer">
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
