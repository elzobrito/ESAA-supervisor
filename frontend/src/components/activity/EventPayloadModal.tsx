import { X } from 'lucide-react';

import type { ActivityEvent } from '../../services/projects';

interface EventPayloadModalProps {
  event: ActivityEvent | null;
  open: boolean;
  onClose: () => void;
}

function interpretEvent(event: ActivityEvent) {
  if (event.action.includes('claim')) {
    return 'Início formal da execução da task. A partir daqui, o agente passa a ser responsável pelo trabalho em andamento.';
  }
  if (event.action.includes('complete')) {
    return 'Entrega de execução com evidência registrada. Este passo move a task para inspeção ou encerra o output operacional.';
  }
  if (event.action.includes('review')) {
    return 'Resultado de revisão. Aprovação finaliza o ciclo; rejeição devolve a task para iteração.';
  }
  if (event.action.includes('issue')) {
    return 'Evento relacionado a bloqueio, risco ou desvio operacional identificado no fluxo.';
  }
  if (event.action.includes('lesson')) {
    return 'Registro de aprendizado operacional reutilizável em futuras execuções.';
  }
  return 'Evento operacional registrado na trilha de auditoria do projeto.';
}

function impactLabel(event: ActivityEvent) {
  if (event.action.includes('review.approve')) return 'Impacto alto: consolida estado final da task.';
  if (event.action.includes('complete')) return 'Impacto médio: registra entrega e evidência.';
  if (event.action.includes('claim')) return 'Impacto médio: reserva ownership da execução.';
  return 'Impacto contextual: depende da ação e do payload registrado.';
}

export function EventPayloadModal({ event, open, onClose }: EventPayloadModalProps) {
  if (!open || !event) {
    return null;
  }

  return (
    <>
      <div className="modal-overlay" onClick={onClose} aria-hidden="true" />
      <section className="event-modal" aria-label="Payload do evento">
        <div className="event-modal-header">
          <div>
            <p className="task-id-cell">#{event.event_seq}</p>
            <h3 className="drawer-title">{event.action}</h3>
          </div>
          <button className="drawer-close" type="button" onClick={onClose} aria-label="Fechar modal">
            <X size={18} />
          </button>
        </div>
        <div className="event-modal-body">
          <section className="drawer-section">
            <span className="drawer-section-label">Contexto</span>
            <div className="drawer-section-content event-context-grid">
              <div>
                <strong>Actor</strong>
                <span>{event.actor}</span>
              </div>
              <div>
                <strong>Task</strong>
                <span>{event.task_id || 'não informada'}</span>
              </div>
              <div>
                <strong>Prior status</strong>
                <span>{event.prior_status || 'não informado'}</span>
              </div>
              <div>
                <strong>Timestamp</strong>
                <span>{new Date(event.ts).toLocaleString()}</span>
              </div>
            </div>
          </section>
          <section className="drawer-section">
            <span className="drawer-section-label">Interpretação</span>
            <div className="drawer-section-content">
              <p>{interpretEvent(event)}</p>
              <p>{impactLabel(event)}</p>
            </div>
          </section>
          <section className="drawer-section">
            <span className="drawer-section-label">Payload bruto</span>
            <div className="drawer-section-content">
              <pre className="event-payload-pre">
                {JSON.stringify(event.payload ?? {}, null, 2)}
              </pre>
            </div>
          </section>
          <section className="drawer-section">
            <span className="drawer-section-label">Vínculos</span>
            <div className="drawer-section-content">
              <p>Task vinculada: {event.task_id || 'não disponível na trilha atual'}</p>
              <p>Run vinculada: {typeof event.payload?.run_id === 'string' ? event.payload.run_id : 'não informada'}</p>
            </div>
          </section>
        </div>
      </section>
    </>
  );
}
