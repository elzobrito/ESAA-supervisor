import { X } from 'lucide-react';

import type { LessonSummary } from '../../services/projects';

interface LessonDetailDrawerProps {
  lesson: LessonSummary | null;
  open: boolean;
  onClose: () => void;
}

export function LessonDetailDrawer({ lesson, open, onClose }: LessonDetailDrawerProps) {
  if (!open || !lesson) {
    return null;
  }

  return (
    <>
      <div className="drawer-overlay" onClick={onClose} aria-hidden="true" />
      <aside className="drawer" aria-label="Detalhes da lição">
        <div className="drawer-header">
          <div>
            <p className="task-id-cell">{lesson.lesson_id}</p>
            <h3 className="drawer-title">{lesson.title}</h3>
          </div>
          <button className="drawer-close" type="button" onClick={onClose} aria-label="Fechar detalhe">
            <X size={18} />
          </button>
        </div>
        <div className="drawer-body">
          <section className="drawer-section">
            <span className="drawer-section-label">Estado</span>
            <div className="drawer-section-content">
              <span className="kind-badge">{lesson.status}</span>
            </div>
          </section>
          <section className="drawer-section">
            <span className="drawer-section-label">Regra operacional</span>
            <div className="drawer-section-content">
              <p>{lesson.rule || 'Sem regra detalhada registrada.'}</p>
            </div>
          </section>
          <section className="drawer-section">
            <span className="drawer-section-label">Aplicação prática</span>
            <div className="drawer-section-content">
              <p>Use esta lição para evitar repetir o mesmo desvio em novas execuções do fluxo ESAA.</p>
              <p>Quando aplicável, converta a regra em critério de revisão ou checklist de operação.</p>
            </div>
          </section>
        </div>
      </aside>
    </>
  );
}
