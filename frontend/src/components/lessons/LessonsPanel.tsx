import { BookOpenText } from 'lucide-react';

import type { LessonSummary } from '../../services/projects';

interface LessonsPanelProps {
  lessons: LessonSummary[];
  selectedLessonId: string | null;
  onSelectLesson: (lesson: LessonSummary) => void;
}

export function LessonsPanel({ lessons, selectedLessonId, onSelectLesson }: LessonsPanelProps) {
  if (lessons.length === 0) {
    return <div className="catalog-empty-state">Nenhuma lição registrada no estado atual.</div>;
  }

  return (
    <div className="context-card-grid">
      {lessons.map((lesson) => (
        <button
          key={lesson.lesson_id}
          type="button"
          className={`context-card lesson-card ${selectedLessonId === lesson.lesson_id ? 'context-card-selected' : ''}`}
          onClick={() => onSelectLesson(lesson)}
        >
          <div className="context-card-header">
            <div className="context-card-title-wrap">
              <BookOpenText size={16} />
              <strong>{lesson.title}</strong>
            </div>
            <span className="task-id-cell">{lesson.lesson_id}</span>
          </div>
          <div className="context-card-meta">
            <span className="kind-badge">{lesson.status}</span>
          </div>
          <p className="context-card-text">{lesson.rule || 'Lição registrada sem regra detalhada.'}</p>
        </button>
      ))}
    </div>
  );
}
