import { api } from './api';

export type ChatMessage = {
  message_id: string;
  role: string;
  content: string;
  created_at: string;
  metadata: Record<string, unknown>;
};

export type ChatSession = {
  session_id: string;
  title: string;
  agent_id: string;
  mode: string;
  task_id?: string | null;
  roadmap_id?: string | null;
  created_at: string;
  updated_at: string;
  message_count: number;
  last_message?: string | null;
};

export type ChatSessionDetail = ChatSession & {
  messages: ChatMessage[];
};

type ChatSessionMutationResponse = {
  session_id: string;
  deleted: boolean;
  message: string;
};

const CHAT_REQUEST_TIMEOUT_MS = 180000;

export async function fetchChatSessions(projectId: string): Promise<ChatSession[]> {
  const response = await api.get<ChatSession[]>(`/projects/${projectId}/chat/sessions`, {
    timeout: CHAT_REQUEST_TIMEOUT_MS,
  });
  return response.data;
}

export async function createChatSession(
  projectId: string,
  options: { agentId: string; mode: 'free' | 'task'; taskId?: string; roadmapId?: string; title?: string },
): Promise<ChatSessionDetail> {
  const response = await api.post<ChatSessionDetail>(`/projects/${projectId}/chat/sessions`, {
    agent_id: options.agentId,
    mode: options.mode,
    task_id: options.taskId,
    roadmap_id: options.roadmapId,
    title: options.title,
  }, {
    timeout: CHAT_REQUEST_TIMEOUT_MS,
  });
  return response.data;
}

export async function fetchChatSession(projectId: string, sessionId: string): Promise<ChatSessionDetail> {
  const response = await api.get<ChatSessionDetail>(`/projects/${projectId}/chat/sessions/${sessionId}`, {
    timeout: CHAT_REQUEST_TIMEOUT_MS,
  });
  return response.data;
}

export async function sendChatMessage(projectId: string, sessionId: string, content: string): Promise<ChatSessionDetail> {
  const response = await api.post<ChatSessionDetail>(`/projects/${projectId}/chat/sessions/${sessionId}/messages`, {
    content,
  }, {
    timeout: CHAT_REQUEST_TIMEOUT_MS,
  });
  return response.data;
}

export async function deleteChatSession(projectId: string, sessionId: string): Promise<ChatSessionMutationResponse> {
  const response = await api.delete<ChatSessionMutationResponse>(`/projects/${projectId}/chat/sessions/${sessionId}`, {
    timeout: CHAT_REQUEST_TIMEOUT_MS,
  });
  return response.data;
}
