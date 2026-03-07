import type { TaskSummary } from '../../services/projects';

interface NextEligibleTasksCardProps {
  tasks: TaskSummary[];
}

export function NextEligibleTasksCard({ tasks }: NextEligibleTasksCardProps) {
  const eligibleTasks = tasks.filter((task) => task.is_eligible).slice(0, 3);

  return (
    <section className="panel-card">
      <div className="panel-card-header">
        <h3 className="panel-card-title">Próximas elegíveis</h3>
      </div>
      <div className="panel-card-body">
        {eligibleTasks.length === 0 ? (
          <p className="panel-empty">Nenhuma tarefa elegível no momento.</p>
        ) : (
          eligibleTasks.map((task) => (
            <article key={task.task_ref} className="eligible-item">
              <span className="eligible-item-id">{task.task_id}</span>
              <span className="eligible-item-title">{task.title}</span>
              <span className="eligible-item-meta">
                {task.roadmap_label} · {task.task_kind} · {task.status}
              </span>
            </article>
          ))
        )}
      </div>
    </section>
  );
}
