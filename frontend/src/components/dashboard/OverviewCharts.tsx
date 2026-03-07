import type { ActivityEvent, TaskSummary } from '../../services/projects';
import { ActivityTimelineChart } from '../charts/ActivityTimelineChart';
import { AgentLoadChart } from '../charts/AgentLoadChart';
import { TaskKindChart } from '../charts/TaskKindChart';
import { TaskStatusChart } from '../charts/TaskStatusChart';

interface OverviewChartsProps {
  tasks: TaskSummary[];
  activity: ActivityEvent[];
}

export function OverviewCharts({ tasks, activity }: OverviewChartsProps) {
  return (
    <div className="charts-grid">
      <TaskStatusChart tasks={tasks} />
      <TaskKindChart tasks={tasks} />
      <ActivityTimelineChart activity={activity} />
      <AgentLoadChart tasks={tasks} activity={activity} />
    </div>
  );
}
