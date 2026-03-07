import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { TasksDataGrid } from '../components/tasks/TasksDataGrid';
import { TaskDetailDrawer } from '../components/tasks/TaskDetailDrawer';
import { TasksFiltersBar } from '../components/tasks/TasksFiltersBar';
import { useShell } from '../components/layout/AppShell';
import { useProject } from '../services/projectContext';
import type { TaskSummary } from '../services/projects';
import { startTaskRun } from '../services/runs';

export function TasksPage() {
  const { state, isLoading, error, reload } = useProject();
  const { setActiveRun, setActiveRunLogs, setActiveRunError } = useShell();
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [kindFilter, setKindFilter] = useState('all');
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [runningTaskRef, setRunningTaskRef] = useState<string | null>(null);

  const kinds = useMemo(
    () => Array.from(new Set(state?.tasks.map((task) => task.task_kind).filter(Boolean) ?? [])),
    [state?.tasks],
  );

  const filteredTasks = useMemo(() => {
    const tasks = state?.tasks ?? [];
    return tasks.filter((task) => {
      const matchesQuery =
        query.trim() === '' ||
        `${task.task_id} ${task.roadmap_label} ${task.title} ${task.assigned_to ?? ''}`.toLowerCase().includes(query.toLowerCase());
      const matchesStatus = statusFilter === 'all' || task.status === statusFilter;
      const matchesKind = kindFilter === 'all' || task.task_kind === kindFilter;
      return matchesQuery && matchesStatus && matchesKind;
    });
  }, [kindFilter, query, state?.tasks, statusFilter]);

  const selectedTask = filteredTasks.find((task) => task.task_ref === selectedTaskId)
    ?? state?.tasks.find((task) => task.task_ref === selectedTaskId)
    ?? null;

  const handleRunTask = async (task: TaskSummary) => {
    if (!state) return;
    setRunningTaskRef(task.task_ref);
    setActiveRunError(null);
    setActiveRunLogs([]);
    try {
      const run = await startTaskRun(state.project.id, { taskId: task.task_id, roadmapId: task.roadmap_id });
      setActiveRun(run);
      navigate(`/projects/${state.project.id}/runs`);
    } catch {
      setRunningTaskRef(null);
    }
  };

  if (isLoading) return <div className="state-loading">Carregando tarefas...</div>;
  if (error || !state) return <div className="state-error">{error || 'Projeto indisponível.'}</div>;

  return (
    <section className="tasks-page">
      <h1 className="page-title">Tarefas</h1>
      <TasksFiltersBar
        query={query}
        statusFilter={statusFilter}
        kindFilter={kindFilter}
        kinds={kinds}
        onQueryChange={setQuery}
        onStatusChange={setStatusFilter}
        onKindChange={setKindFilter}
      />
      <TasksDataGrid
        tasks={filteredTasks}
        selectedTaskId={selectedTaskId}
        onSelectTask={setSelectedTaskId}
        onRunTask={(task) => void handleRunTask(task)}
        runningTaskRef={runningTaskRef}
      />
      <TaskDetailDrawer
        projectId={state.project.id}
        task={selectedTask}
        open={selectedTask !== null}
        onClose={() => setSelectedTaskId(null)}
        onTaskUpdated={reload}
      />
    </section>
  );
}
