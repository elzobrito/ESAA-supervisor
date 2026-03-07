import React from 'react';

interface Task {
  task_id: string;
  title: string;
  description?: string;
  task_kind: string;
  status: string;
  assigned_to?: string | null;
  depends_on?: string[];
  is_eligible?: boolean;
  ineligibility_reasons?: string[];
}

interface Props {
  task: Task | null;
}

const TaskDetails: React.FC<Props> = ({ task }) => {
  if (!task) {
    return (
      <div className="panel">
        <h3>Detalhe da tarefa</h3>
        <p className="empty-msg">Selecione uma tarefa para ver dependências, elegibilidade e descrição.</p>
      </div>
    );
  }

  return (
    <div className="panel">
      <h3>{task.task_id}</h3>
      <p className="task-kind-line">
        <span className="badge">{task.task_kind}</span>
        <span className={`badge ${task.status}`}>{task.status}</span>
      </p>
      <p>{task.title}</p>
      {task.description ? <p className="muted-text">{task.description}</p> : null}
      <p>
        <strong>Agente:</strong> {task.assigned_to || 'não atribuído'}
      </p>
      <p>
        <strong>Dependências:</strong> {task.depends_on?.length ? task.depends_on.join(', ') : 'nenhuma'}
      </p>
      <p>
        <strong>Elegibilidade:</strong> {task.is_eligible ? 'elegível' : 'inelegível'}
      </p>
      {!task.is_eligible && task.ineligibility_reasons?.length ? (
        <ul>
          {task.ineligibility_reasons.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
};

export default TaskDetails;
