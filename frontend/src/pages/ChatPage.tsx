import { useEffect, useMemo, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import { extractErrorMessage } from '../services/api';
import { createChatSession, deleteChatSession, fetchChatSession, fetchChatSessions, sendChatMessage, type ChatSession, type ChatSessionDetail } from '../services/chat';
import { useProject } from '../services/projectContext';

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function summarizeTokenUsage(metadata: Record<string, unknown> | undefined): string | null {
  if (!metadata || !isRecord(metadata)) {
    return null;
  }
  const tokenUsage = metadata.token_usage;
  if (!isRecord(tokenUsage)) {
    return null;
  }
  const total = typeof tokenUsage.total === 'number' ? tokenUsage.total : null;
  const cost = typeof tokenUsage.total_cost_usd === 'number' ? tokenUsage.total_cost_usd : null;
  if (total === null && cost === null) {
    return null;
  }
  if (total !== null && cost !== null) {
    return `${total} tokens · $${cost.toFixed(6)}`;
  }
  if (total !== null) {
    return `${total} tokens`;
  }
  return `$${cost?.toFixed(6)}`;
}

export function ChatPage() {
  const { state, isLoading, error } = useProject();
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [selectedSession, setSelectedSession] = useState<ChatSessionDetail | null>(null);
  const [selectedAgentId, setSelectedAgentId] = useState('codex');
  const [sessionMode, setSessionMode] = useState<'free' | 'task'>('free');
  const [selectedTaskId, setSelectedTaskId] = useState('');
  const [draft, setDraft] = useState('');
  const [pageError, setPageError] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const availableAgents = state?.available_agents ?? [];
  const availableTasks = useMemo(
    () => (state?.tasks ?? []).filter((task) => task.status !== 'done'),
    [state?.tasks],
  );

  useEffect(() => {
    if (!state) {
      return;
    }
    void (async () => {
      try {
        const items = await fetchChatSessions(state.project.id);
        setSessions(items);
        if (!selectedSessionId && items.length > 0) {
          setSelectedSessionId(items[0].session_id);
        }
      } catch (err) {
        setPageError(extractErrorMessage(err));
      }
    })();
  }, [state]);

  useEffect(() => {
    if (!state || !selectedSessionId) {
      setSelectedSession(null);
      return;
    }
    void (async () => {
      try {
        const detail = await fetchChatSession(state.project.id, selectedSessionId);
        setSelectedSession(detail);
      } catch (err) {
        setPageError(extractErrorMessage(err));
      }
    })();
  }, [selectedSessionId, state]);

  useEffect(() => {
    if (availableAgents.length === 0) {
      return;
    }
    if (!availableAgents.some((agent) => agent.agent_id === selectedAgentId && agent.available)) {
      const next = availableAgents.find((agent) => agent.available) ?? availableAgents[0];
      setSelectedAgentId(next.agent_id);
    }
  }, [availableAgents, selectedAgentId]);

  useEffect(() => {
    if (!selectedTaskId && availableTasks.length > 0) {
      setSelectedTaskId(availableTasks[0].task_id);
    }
  }, [availableTasks, selectedTaskId]);

  async function handleCreateSession() {
    if (!state) {
      return;
    }
    setPageError(null);
    setIsCreating(true);
    try {
      const detail = await createChatSession(state.project.id, {
        agentId: selectedAgentId,
        mode: sessionMode,
        taskId: sessionMode === 'task' ? selectedTaskId : undefined,
        roadmapId: sessionMode === 'task'
          ? availableTasks.find((task) => task.task_id === selectedTaskId)?.roadmap_id
          : undefined,
      });
      setSelectedSessionId(detail.session_id);
      setSelectedSession(detail);
      const items = await fetchChatSessions(state.project.id);
      setSessions(items);
    } catch (err) {
      setPageError(extractErrorMessage(err));
    } finally {
      setIsCreating(false);
    }
  }

  async function handleSendMessage() {
    if (!state || !selectedSession || !draft.trim()) {
      return;
    }
    setPageError(null);
    setIsSending(true);
    try {
      const detail = await sendChatMessage(state.project.id, selectedSession.session_id, draft.trim());
      setSelectedSession(detail);
      setDraft('');
      const items = await fetchChatSessions(state.project.id);
      setSessions(items);
    } catch (err) {
      setPageError(extractErrorMessage(err));
    } finally {
      setIsSending(false);
    }
  }

  async function handleDeleteSession(sessionId: string) {
    if (!state || isDeleting) {
      return;
    }
    const target = sessions.find((session) => session.session_id === sessionId);
    const confirmed = window.confirm(`Excluir a sessão "${target?.title ?? sessionId}"?`);
    if (!confirmed) {
      return;
    }
    setPageError(null);
    setIsDeleting(true);
    try {
      await deleteChatSession(state.project.id, sessionId);
      const items = await fetchChatSessions(state.project.id);
      setSessions(items);
      if (selectedSessionId === sessionId) {
        const nextSessionId = items[0]?.session_id ?? null;
        setSelectedSessionId(nextSessionId);
        if (!nextSessionId) {
          setSelectedSession(null);
        }
      }
    } catch (err) {
      setPageError(extractErrorMessage(err));
    } finally {
      setIsDeleting(false);
    }
  }

  if (isLoading) return <div className="state-loading">Carregando chat...</div>;
  if (error || !state) return <div className="state-error">{error || 'Projeto indisponível.'}</div>;

  return (
    <section className="chat-page">
      <h1 className="page-title">Chat</h1>
      <p className="page-subtitle">
        Sessões livres e sessões vinculadas à task, persistidas por projeto para trabalhar com os agentes fora do fluxo estrito de run.
      </p>

      <div className="chat-layout">
        <aside className="chat-sidebar">
          <section className="panel-card">
            <div className="panel-card-header">
              <h3 className="panel-card-title">Nova sessão</h3>
            </div>
            <div className="panel-card-body chat-setup-stack">
              <label className="run-control-field">
                <span className="run-control-label">Agente</span>
                <select className="filter-select-ds" value={selectedAgentId} onChange={(event) => setSelectedAgentId(event.target.value)}>
                  {availableAgents.map((agent) => (
                    <option key={agent.agent_id} value={agent.agent_id} disabled={!agent.available}>
                      {agent.label}{agent.available ? '' : ' (indisponível)'}
                    </option>
                  ))}
                </select>
              </label>
              <label className="run-control-field">
                <span className="run-control-label">Modo</span>
                <select className="filter-select-ds" value={sessionMode} onChange={(event) => setSessionMode(event.target.value as 'free' | 'task')}>
                  <option value="free">Chat livre</option>
                  <option value="task">Chat por task</option>
                </select>
              </label>
              {sessionMode === 'task' ? (
                <label className="run-control-field">
                  <span className="run-control-label">Task</span>
                  <select className="filter-select-ds" value={selectedTaskId} onChange={(event) => setSelectedTaskId(event.target.value)}>
                    {availableTasks.map((task) => (
                      <option key={`${task.roadmap_id}:${task.task_id}`} value={task.task_id}>
                        {task.task_id} - {task.title}
                      </option>
                    ))}
                  </select>
                </label>
              ) : null}
              <button className="btn-primary-ds" type="button" onClick={() => void handleCreateSession()} disabled={isCreating}>
                {isCreating ? 'Criando...' : 'Criar sessão'}
              </button>
            </div>
          </section>

          <section className="panel-card">
            <div className="panel-card-header">
              <h3 className="panel-card-title">Sessões</h3>
            </div>
            <div className="panel-card-body chat-sessions-list">
              {sessions.length === 0 ? (
                <p className="panel-empty">Nenhuma sessão criada ainda.</p>
              ) : (
                sessions.map((session) => (
                  <article
                    key={session.session_id}
                    className={`context-card ${selectedSessionId === session.session_id ? 'context-card-selected' : ''}`}
                  >
                    <button
                      type="button"
                      className="chat-session-card-button"
                      onClick={() => setSelectedSessionId(session.session_id)}
                    >
                      <div className="context-card-header">
                        <div className="context-card-title-wrap">
                          <strong>{session.title}</strong>
                        </div>
                        <span className="task-id-cell">{session.agent_id}</span>
                      </div>
                      <div className="context-card-meta">
                        <span className="kind-badge">{session.mode}</span>
                        {session.task_id ? <span className="task-id-cell">{session.task_id}</span> : null}
                      </div>
                      <p className="context-card-text">{session.last_message ?? 'Sem mensagens ainda.'}</p>
                    </button>
                    <div className="chat-session-card-actions">
                      <button
                        className="btn-danger-ds"
                        type="button"
                        onClick={() => void handleDeleteSession(session.session_id)}
                        disabled={isDeleting}
                      >
                        {isDeleting && selectedSessionId === session.session_id ? 'Excluindo...' : 'Excluir'}
                      </button>
                    </div>
                  </article>
                ))
              )}
            </div>
          </section>
        </aside>

        <div className="chat-main">
          <section className="panel-card chat-thread-card">
            <div className="panel-card-header">
              <h3 className="panel-card-title">
                {selectedSession ? selectedSession.title : 'Selecione ou crie uma sessão'}
              </h3>
              {selectedSession ? (
                <button
                  className="btn-danger-ds"
                  type="button"
                  onClick={() => void handleDeleteSession(selectedSession.session_id)}
                  disabled={isDeleting}
                >
                  {isDeleting ? 'Excluindo...' : 'Excluir sessão'}
                </button>
              ) : null}
            </div>
            <div className="panel-card-body chat-thread-body">
              {selectedSession ? (
                <>
                  <div className="chat-session-meta">
                    <span className="kind-badge">{selectedSession.mode}</span>
                    <span className="task-id-cell">{selectedSession.agent_id}</span>
                    {selectedSession.task_id ? <span className="task-id-cell">{selectedSession.task_id}</span> : null}
                  </div>
                  <div className="chat-messages">
                    {selectedSession.messages.length === 0 ? (
                      <p className="panel-empty">Nenhuma mensagem ainda. Envie a primeira instrução.</p>
                    ) : (
                      selectedSession.messages.map((message) => (
                        <article key={message.message_id} className={`chat-message chat-message-${message.role}`}>
                          <div className="chat-message-top">
                            <strong>{message.role === 'assistant' ? selectedSession.agent_id : 'user'}</strong>
                            <span>{new Date(message.created_at).toLocaleString()}</span>
                            {message.role === 'assistant' ? (
                              <span>{summarizeTokenUsage(message.metadata) ?? 'sem telemetria de tokens'}</span>
                            ) : null}
                          </div>
                          <div className="chat-message-content markdown-body">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
                          </div>
                        </article>
                      ))
                    )}
                  </div>
                  <div className="chat-composer">
                    <textarea
                      className="chat-textarea"
                      value={draft}
                      onChange={(event) => setDraft(event.target.value)}
                      placeholder={selectedSession.mode === 'task'
                        ? 'Converse com o agente no contexto da task selecionada...'
                        : 'Converse livremente com o agente sobre o projeto...'}
                    />
                    <div className="run-actions">
                      <button className="btn-primary-ds" type="button" onClick={() => void handleSendMessage()} disabled={isSending || !draft.trim()}>
                        {isSending ? 'Enviando...' : 'Enviar mensagem'}
                      </button>
                    </div>
                  </div>
                </>
              ) : (
                <p className="panel-empty">Crie uma sessão livre ou vinculada à task para começar.</p>
              )}
            </div>
          </section>
          {pageError ? <p className="error-text">{pageError}</p> : null}
        </div>
      </div>
    </section>
  );
}
