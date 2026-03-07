import React from 'react';
import { Lightbulb } from 'lucide-react';

interface Lesson {
  lesson_id: string;
  title: string;
}

interface Props {
  lessons: Lesson[];
}

const LessonsPanel: React.FC<Props> = ({ lessons }) => {
  return (
    <div className="panel lessons-panel">
      <h3>Lições Aprendidas</h3>
      {lessons.length === 0 ? (
        <p className="empty-msg">Nenhuma lição registrada.</p>
      ) : (
        <ul className="lesson-list">
          {lessons.map(lesson => (
            <li key={lesson.lesson_id} className="lesson-item">
              <Lightbulb size={14} color="gold" />
              <span className="lesson-title">{lesson.title}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default LessonsPanel;
