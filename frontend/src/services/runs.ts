import { api } from './api';

export type RunLogEntry = {
  timestamp: string;
  source: 'stdout' | 'stderr' | 'system';
  content: string;
};

export type RunDecisionEntry = {
  timestamp: string;
  stage: string;
  proposed_action?: string | null;
  selected_action?: string | null;
  decision?: string | null;
  actor?: string | null;
  notes?: string | null;
};

export type RunState = {
  run_id: string;
  task_id: string;
  agent_id: string;
  model_id?: string | null;
  reasoning_effort?: string | null;
  roadmap_id?: string | null;
  execution_mode?: 'manual' | 'continuous';
  status: string;
  started_at: string;
  ended_at?: string | null;
  exit_code?: number | null;
  error_message?: string | null;
  awaiting_decision?: boolean;
  proposed_action?: string | null;
  available_actions?: string[];
  agent_result?: Record<string, unknown> | null;
  decision_history?: RunDecisionEntry[];
  logs?: RunLogEntry[];
  completed_task_ids?: string[];
  stop_after_current?: boolean;
};

export async function startNextRun(
  projectId: string,
  options?: { agentId?: string; roadmapId?: string; executionMode?: 'manual' | 'continuous' },
): Promise<RunState> {
  const response = await api.post<RunState>(`/projects/${projectId}/runs/next`, {
    agent_id: options?.agentId,
    roadmap_id: options?.roadmapId,
    execution_mode: options?.executionMode,
  });
  return response.data;
}

export async function startTaskRun(
  projectId: string,
  options: string | { taskId: string; agentId?: string; roadmapId?: string; executionMode?: 'manual' | 'continuous' },
): Promise<RunState> {
  const payload = typeof options === 'string'
    ? { task_id: options }
    : {
        task_id: options.taskId,
        agent_id: options.agentId,
        roadmap_id: options.roadmapId,
        execution_mode: options.executionMode,
      };
  const response = await api.post<RunState>(`/projects/${projectId}/runs/task`, {
    ...payload,
  });
  return response.data;
}

export async function fetchRunStatus(projectId: string, runId: string): Promise<RunState> {
  const response = await api.get<RunState>(`/projects/${projectId}/runs/${runId}`);
  return response.data;
}

export async function fetchRuns(projectId: string): Promise<RunState[]> {
  const response = await api.get<RunState[]>(`/projects/${projectId}/runs`);
  return response.data;
}

export async function submitRunDecision(
  projectId: string,
  runId: string,
  options: { decision: 'apply' | 'reject'; selectedAction?: string },
): Promise<RunState> {
  const response = await api.post<RunState>(`/projects/${projectId}/runs/${runId}/decision`, {
    decision: options.decision,
    selected_action: options.selectedAction,
  });
  return response.data;
}

export async function cancelRun(projectId: string, runId: string): Promise<void> {
  await api.delete(`/projects/${projectId}/runs/${runId}`);
}

export async function stopRunAfterCurrent(projectId: string, runId: string): Promise<void> {
  await api.post(`/projects/${projectId}/runs/${runId}/stop-after-current`);
}
