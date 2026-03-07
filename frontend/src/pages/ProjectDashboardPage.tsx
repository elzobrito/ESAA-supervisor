import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import ActivityPanel from '../components/ActivityPanel';
import ArtifactsPanel from '../components/ArtifactsPanel';
import IssuesPanel from '../components/IssuesPanel';
import LessonsPanel from '../components/LessonsPanel';
import RunConsole from '../components/RunConsole';
import RunControls from '../components/RunControls';
import RunStatusBadge from '../components/RunStatusBadge';
import TaskDetails from '../components/TaskDetails';
import TasksTable from '../components/TasksTable';
import { extractErrorMessage } from '../services/api';
import { fetchProjectState, type StateResponse } from '../services/projects';
import { subscribeToLogs, type LogEntry } from '../services/logStream';
import { cancelRun, fetchRunStatus, startNextRun, startTaskRun, type RunState } from '../services/runs';

export function ProjectDashboardPage() {
  const { projectId = '' } = useParams();
  const [state, setState] = useState<StateResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [run, setRun] = useState<RunState | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [runError, setRunError] = useState<string | null>(null);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const unsubRef = useRef<(() => void) | null>(null);

  const loadState = useCallback(async () => {
    try {
      const nextState = await fetchProjectState(projectId);
      setState(nextState);
      setSelectedTaskId((current) => current ?? nextState.tasks[0]?.task_id ?? null);
      setError(null);
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  }, [projectId]);

  useEffect(() => {
    void loadState();
  }, [loadState]);

  const isRunning = run !== null && !['done', 'error', 'cancelled'].includes(run.status);

  const selectedTask = useMemo(
    () => state?.tasks.find((task) => task.task_id === selectedTaskId) ?? null,
    [selectedTaskId, state?.tasks],
  );

  const pollRun = useCallback(
    (runId: string) => {
      const interval = setInterval(async () => {
        try {
          const updated = await fetchRunStatus(projectId, runId);
          setRun(updated);
          if (['done', 'error', 'cancelled'].includes(updated.status)) {
            clearInterval(interval);
            void loadState();
          }
        } catch {
          clearInterval(interval);
        }
      }, 1500);
    },
    [projectId, loadState],
  );

  const startRun = useCallback(
    async (runner: () => Promise<RunState>) => {
      setRunError(null);
      setLogs([]);
      unsubRef.current?.();
      unsubRef.current = null;
      try {
        const newRun = await runner();
        setRun(newRun);
        unsubRef.current = subscribeToLogs(
          projectId,
          newRun.run_id,
          (log) => setLogs((prev) => [...prev, log]),
          (err) => setRunError(String(err)),
        );
        pollRun(newRun.run_id);
      } catch (err) {
        setRunError(extractErrorMessage(err));
      }
    },
    [pollRun, projectId],
  );

  const handleRunNext = useCallback(async () => {
    await startRun(() => startNextRun(projectId));
  }, [projectId, startRun]);

  const handleRunTask = useCallback(
    async (taskId: string) => {
      setSelectedTaskId(taskId);
      await startRun(() => startTaskRun(projectId, taskId));
    },
    [projectId, startRun],
  );

  const handleCancel = useCallback(async () => {
    if (!run) return;
    try {
      await cancelRun(projectId, run.run_id);
    } catch (err) {
      setRunError(extractErrorMessage(err));
    }
  }, [projectId, run]);

  useEffect(() => {
    return () => {
      unsubRef.current?.();
    };
  }, []);

  return (
    <section className="page">
      <header className="page-header">
        <div>
          <Link className="back-link" to="/projects">
            Voltar
          </Link>
          <p className="eyebrow">Dashboard</p>
          <h2>{state?.project.name ?? projectId}</h2>
        </div>
        <div className="header-right">
          {run && <RunStatusBadge status={run.status} />}
          <div className={`status-pill ${state?.is_consistent ? 'ok' : 'warn'}`}>
            {state?.is_consistent ? 'Consistente' : 'Revisar integridade'}
          </div>
        </div>
      </header>

      {error ? <p className="error-text">{error}</p> : null}

      <RunControls
        onRunNext={() => void handleRunNext()}
        onRefresh={() => void loadState()}
        onCancel={() => void handleCancel()}
        isRunning={isRunning}
      />

      {runError ? <p className="error-text">{runError}</p> : null}

      {(run || logs.length > 0) && <RunConsole logs={logs} status={run?.status ?? 'idle'} />}

      {state ? (
        <div className="dashboard-layout">
          <div className="dashboard-main">
            <TasksTable
              tasks={state.tasks}
              selectedTaskId={selectedTaskId}
              onRunTask={(taskId) => void handleRunTask(taskId)}
              onViewDetails={setSelectedTaskId}
            />
            <TaskDetails task={selectedTask} />
            <ActivityPanel events={state.activity} />
          </div>
          <div className="dashboard-side">
            <ArtifactsPanel artifacts={state.artifacts} />
            <IssuesPanel issues={state.open_issues} />
            <LessonsPanel lessons={state.lessons} />
          </div>
        </div>
      ) : null}
    </section>
  );
}
