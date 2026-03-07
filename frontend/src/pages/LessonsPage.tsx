import { useState } from 'react';

import { LessonDetailDrawer } from '../components/lessons/LessonDetailDrawer';
import { LessonsPanel } from '../components/lessons/LessonsPanel';
import { useProject } from '../services/projectContext';

export function LessonsPage() {
  const { state, isLoading, error } = useProject();
  const [selectedLessonId, setSelectedLessonId] = useState<string | null>(null);

  if (isLoading) return <div className="state-loading">Carregando lições...</div>;
  if (error || !state) return <div className="state-error">{error || 'Projeto indisponível.'}</div>;

  const selectedLesson = state.lessons.find((lesson) => lesson.lesson_id === selectedLessonId) ?? null;

  return (
    <section>
      <h1 className="page-title">Lições</h1>
      <p className="page-subtitle">
        Lições aprendidas tratadas como referência operacional reutilizável, com abertura de contexto detalhado.
      </p>
      <div className="activity-hero-grid">
        <div className="catalog-summary-card">
          <span className="catalog-summary-label">Lições registradas</span>
          <strong>{state.lessons.length}</strong>
        </div>
        <div className="catalog-summary-card">
          <span className="catalog-summary-label">Ativas</span>
          <strong>{state.lessons.filter((lesson) => lesson.status === 'active').length}</strong>
        </div>
        <div className="catalog-summary-card">
          <span className="catalog-summary-label">Com regra</span>
          <strong>{state.lessons.filter((lesson) => lesson.rule.trim() !== '').length}</strong>
        </div>
        <div className="catalog-summary-card">
          <span className="catalog-summary-label">Sem detalhe</span>
          <strong>{state.lessons.filter((lesson) => lesson.rule.trim() === '').length}</strong>
        </div>
      </div>
      <LessonsPanel
        lessons={state.lessons}
        selectedLessonId={selectedLessonId}
        onSelectLesson={(lesson) => setSelectedLessonId(lesson.lesson_id)}
      />
      <LessonDetailDrawer
        lesson={selectedLesson}
        open={selectedLesson !== null}
        onClose={() => setSelectedLessonId(null)}
      />
    </section>
  );
}
