import { api } from './api';

export type ProjectMetadata = {
  id: string;
  name: string;
  base_path?: string;
  project_path?: string;
  is_active?: boolean;
};

export type FileSystemEntry = {
  name: string;
  path: string;
};

export type ProjectBrowserResponse = {
  current_path: string;
  parent_path?: string | null;
  directories: FileSystemEntry[];
  projects: ProjectMetadata[];
};

export type ArtifactContentResponse = {
  path: string;
  content: string;
  truncated: boolean;
  encoding: string;
  size_bytes: number;
};

export type ProjectFileEntry = {
  name: string;
  path: string;
  kind: 'directory' | 'file';
};

export type ProjectFileBrowserResponse = {
  current_path: string;
  parent_path?: string | null;
  directories: ProjectFileEntry[];
  files: ProjectFileEntry[];
};

export type TaskSummary = {
  task_ref: string;
  task_id: string;
  roadmap_id: string;
  roadmap_label: string;
  title: string;
  task_kind: string;
  description?: string;
  status: string;
  assigned_to?: string | null;
  depends_on?: string[];
  is_eligible: boolean;
  ineligibility_reasons: string[];
};

export type IssueSummary = {
  issue_id: string;
  status: string;
  severity: string;
  title: string;
};

export type LessonSummary = {
  lesson_id: string;
  status: string;
  title: string;
  rule: string;
};

export type ArtifactSummary = {
  name: string;
  path: string;
  category: string;
  role: string;
  integrity_status: string;
};

export type ActivityEvent = {
  event_seq: number;
  event_id: string;
  ts: string;
  actor: string;
  action: string;
  task_id?: string | null;
  prior_status?: string | null;
  payload?: Record<string, unknown>;
};

export type StateResponse = {
  project: { id: string; name: string; base_path: string; is_active: boolean };
  roadmap_mode: 'single' | 'aggregate';
  selected_roadmap_id: string;
  available_roadmaps: Array<{
    roadmap_id: string;
    label: string;
    task_count: number;
    is_default: boolean;
    is_consistent: boolean;
  }>;
  available_agents: Array<{
    agent_id: string;
    label: string;
    available: boolean;
    command: string;
  }>;
  tasks: TaskSummary[];
  open_issues: IssueSummary[];
  lessons: LessonSummary[];
  artifacts: ArtifactSummary[];
  activity: ActivityEvent[];
  eligible_task_ids: string[];
  last_event_seq: number;
  is_consistent: boolean;
};

export type TaskMutationResponse = {
  task_id: string;
  roadmap_id: string;
  status: string;
  message: string;
};

export type IssueMutationResponse = {
  issue_id: string;
  status: string;
  message: string;
};

export type IntegrityRepairResponse = {
  repaired_roadmaps: string[];
  artifact_issues_after: number;
  is_consistent: boolean;
  message: string;
};

export async function fetchProjects(): Promise<ProjectMetadata[]> {
  const response = await api.get<ProjectMetadata[]>('/projects');
  return response.data;
}

export async function browseProjects(path?: string): Promise<ProjectBrowserResponse> {
  const response = await api.get<ProjectBrowserResponse>('/projects/browse', {
    params: path ? { path } : undefined,
  });
  return response.data;
}

export async function openProject(path: string): Promise<ProjectMetadata> {
  const response = await api.post<ProjectMetadata>('/projects/open', { path });
  return response.data;
}

export async function fetchArtifactContent(projectId: string, path: string, full = false): Promise<ArtifactContentResponse> {
  const response = await api.get<ArtifactContentResponse>(`/projects/${projectId}/artifacts/content`, {
    params: { path, full },
  });
  return response.data;
}

export async function browseProjectFiles(projectId: string, path?: string): Promise<ProjectFileBrowserResponse> {
  const response = await api.get<ProjectFileBrowserResponse>(`/projects/${projectId}/files/browse`, {
    params: path !== undefined ? { path } : undefined,
  });
  return response.data;
}

export async function resetTaskToTodo(projectId: string, taskId: string, roadmapId: string): Promise<TaskMutationResponse> {
  const response = await api.post<TaskMutationResponse>(`/projects/${projectId}/tasks/reset`, {
    task_id: taskId,
    roadmap_id: roadmapId,
  });
  return response.data;
}

export async function submitTaskReview(
  projectId: string,
  taskId: string,
  options: { decision: 'approve' | 'reject'; roadmapId?: string },
): Promise<TaskMutationResponse> {
  const response = await api.post<TaskMutationResponse>(`/projects/${projectId}/tasks/${taskId}/review`, {
    decision: options.decision,
    roadmap_id: options.roadmapId,
  });
  return response.data;
}

export async function resolveIssue(projectId: string, issueId: string, resolutionSummary?: string): Promise<IssueMutationResponse> {
  const response = await api.post<IssueMutationResponse>(`/projects/${projectId}/issues/resolve`, {
    issue_id: issueId,
    resolution_summary: resolutionSummary,
  });
  return response.data;
}

export async function repairIntegrity(projectId: string, roadmapId?: string): Promise<IntegrityRepairResponse> {
  const response = await api.post<IntegrityRepairResponse>(`/projects/${projectId}/integrity/repair`, {
    roadmap_id: roadmapId,
  });
  return response.data;
}

export async function fetchProjectState(projectId: string, roadmap?: string): Promise<StateResponse> {
  const response = await api.get<StateResponse>(`/projects/${projectId}/state`, {
    params: roadmap ? { roadmap } : undefined,
  });
  return response.data;
}
