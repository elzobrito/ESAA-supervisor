import { X } from 'lucide-react';

import type { IssueSummary } from '../../services/projects';

interface IssueDetailModalProps {
  issue: IssueSummary | null;
  open: boolean;
  onClose: () => void;
  onResolve: (issue: IssueSummary) => void;
  isResolving: boolean;
}

function severityImpact(severity: string) {
  if (severity === 'high') {
    return 'Impacto alto: pode bloquear fluxo operacional ou comprometer a confiabilidade da leitura.';
  }
  if (severity === 'medium') {
    return 'Impacto moderado: exige atenção antes da próxima iteração sensível.';
  }
  return 'Impacto baixo: monitorar e consolidar quando houver janela adequada.';
}

export function IssueDetailModal({ issue, open, onClose, onResolve, isResolving }: IssueDetailModalProps) {
  if (!open || !issue) {
    return null;
  }

  return (
    <>
      <div className="modal-overlay" onClick={onClose} aria-hidden="true" />
      <section className="event-modal" aria-label="Detalhes do problema">
        <div className="event-modal-header">
          <div>
            <p className="task-id-cell">{issue.issue_id}</p>
            <h3 className="drawer-title">{issue.title}</h3>
          </div>
          <button className="drawer-close" type="button" onClick={onClose} aria-label="Fechar modal">
            <X size={18} />
          </button>
        </div>
        <div className="event-modal-body">
          <section className="drawer-section">
            <span className="drawer-section-label">Estado atual</span>
            <div className="drawer-section-content event-context-grid">
              <div>
                <strong>Status</strong>
                <span>{issue.status}</span>
              </div>
              <div>
                <strong>Severidade</strong>
                <span>{issue.severity}</span>
              </div>
            </div>
          </section>
          <section className="drawer-section">
            <span className="drawer-section-label">Impacto</span>
            <div className="drawer-section-content">
              <p>{severityImpact(issue.severity)}</p>
            </div>
          </section>
          <section className="drawer-section">
            <span className="drawer-section-label">Contexto operacional</span>
            <div className="drawer-section-content">
              <p>Este problema permanece aberto e deve ser considerado ao priorizar a próxima rodada de execução.</p>
              <p>Use a severidade como guia para decidir se o desvio bloqueia ou apenas reduz confiança no estado atual.</p>
            </div>
          </section>
          <section className="drawer-section">
            <span className="drawer-section-label">Ação</span>
            <div className="drawer-section-content">
              <button
                type="button"
                className="btn-primary-ds"
                onClick={() => onResolve(issue)}
                disabled={isResolving}
              >
                {isResolving ? 'Resolvendo...' : 'Resolver issue'}
              </button>
            </div>
          </section>
        </div>
      </section>
    </>
  );
}
