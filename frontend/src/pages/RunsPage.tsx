import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { extractErrorMessage } from '../services/api';
import { useProject } from '../services/projectContext';
import { subscribeToLogs, type LogEntry } from '../services/logStream';
import { cancelRun, fetchRunStatus, startNextRun, startTaskRun, submitRunDecision, type RunState } from '../services/runs';
import { RunConsoleDock } from '../components/runs/RunConsoleDock';
import { RunArtifactsPanel } from '../components/runs/RunArtifactsPanel';
import { RunHeader } from '../components/runs/RunHeader';
import { RunStepsTimeline } from '../components/runs/RunStepsTimeline';
import { useShell } from '../components/layout/AppShell';

const TERMINAL_STATUSES = new Set(['done', 'error', 'cancelled']);

export function RunsPage() {
  const { state, isLoading, error, reload } = useProject();
  const {
    activeRun: run,
    setActiveRun: setRun,
    activeRunLogs: logs,
    setActiveRunLogs: setLogs,
    activeRunError: runError,
    setActiveRunError: setRunError,
  } = useShell();
  const [selectedTaskId, setSelectedTaskId] = useState<string>('');
  const [selectedAgentId, setSelectedAgentId] = useState<string>('codex');
  const [selectedAction, setSelectedAction] = useState<string>('complete');
  const unsubRef = useRef<(() => void) | null>(null);
  const pollRef = useRef<number | null>(null);

  const runnableTasks = useMemo(
    () => (state?.tasks ?? []).filter((task) => task.status !== 'done'),
    [state?.tasks],
  );

  const selectedTask = useMemo(
    () => runnableTasks.find((task) => task.task_id === selectedTaskId) ?? null,
    [runnableTasks, selectedTaskId],
  );

  const canRunNext = state !== null && state.roadmap_mode !== 'aggregate' && state.eligible_task_ids.length > 0;
  const canRunSelected = selectedTask !== null && (selectedTask.is_eligible || selectedTask.status === 'in_progress');
  const isRunning = run !== null && !TERMINAL_STATUSES.has(run.status);
  const isWaitingDecision = run?.status === 'waiting_input' && run.awaiting_decision;
  const availableAgents = state?.available_agents ?? [];
  const selectedAgent = availableAgents.find((agent) => agent.agent_id === selectedAgentId) ?? null;

  useEffect(() => {
    if (!selectedTaskId && runnableTasks.length > 0) {
      setSelectedTaskId(runnableTasks[0].task_id);
    }
  }, [runnableTasks, selectedTaskId]);

  useEffect(() => {
    if (availableAgents.length === 0) {
      return;
    }
    if (!availableAgents.some((agent) => agent.agent_id === selectedAgentId && agent.available)) {
      const firstAvailable = availableAgents.find((agent) => agent.available);
      setSelectedAgentId(firstAvailable?.agent_id ?? availableAgents[0].agent_id);
    }
  }, [availableAgents, selectedAgentId]);

  useEffect(() => {
    if (run?.proposed_action) {
      setSelectedAction(run.proposed_action);
    }
  }, [run?.proposed_action]);

  useEffect(() => {
    return () => {
      unsubRef.current?.();
      if (pollRef.current !== null) {
        window.clearInterval(pollRef.current);
      }
    };
  }, []);

  const stopPolling = useCallback(() => {
    if (pollRef.current !== null) {
      window.clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const pollRun = useCallback((runId: string) => {
    stopPolling();
    pollRef.current = window.setInterval(async () => {
      try {
        const updated = await fetchRunStatus(state?.project.id ?? '', runId);
        setRun(updated);
        if (updated.logs?.length) {
          setLogs(updated.logs);
        }
        if (TERMINAL_STATUSES.has(updated.status)) {
          stopPolling();
          unsubRef.current?.();
          unsubRef.current = null;
          await reload();
        }
      } catch (err) {
        setRunError(extractErrorMessage(err));
        stopPolling();
      }
    }, 1500);
  }, [reload, state?.project.id, stopPolling]);

  const startRun = useCallback(async (runner: () => Promise<RunState>) => {
    setRunError(null);
    setLogs([]);
    unsubRef.current?.();
    unsubRef.current = null;
    stopPolling();
    try {
      const created = await runner();
      setRun(created);
      if (created.logs?.length) {
        setLogs(created.logs);
      }
      if (state) {
        unsubRef.current = subscribeToLogs(
          state.project.id,
          created.run_id,
          (entry) => {
            setLogs((current) => [...current, entry]);
          },
          (err) => setRunError(String(err)),
        );
      }
      pollRun(created.run_id);
    } catch (err) {
      setRunError(extractErrorMessage(err));
    }
  }, [pollRun, state, stopPolling]);

  useEffect(() => {
    if (!state || !run || TERMINAL_STATUSES.has(run.status)) {
      unsubRef.current?.();
      unsubRef.current = null;
      stopPolling();
      return;
    }

    unsubRef.current?.();
    unsubRef.current = subscribeToLogs(
      state.project.id,
      run.run_id,
      (entry) => {
        setLogs((current) => [...current, entry]);
      },
      (err) => setRunError(String(err)),
    );
    pollRun(run.run_id);

    return () => {
      unsubRef.current?.();
      unsubRef.current = null;
      stopPolling();
    };
  }, [pollRun, run, setLogs, setRunError, state, stopPolling]);

  const handleRunNext = useCallback(async () => {
    if (!state || state.roadmap_mode === 'aggregate') {
      return;
    }
    await startRun(() =>
      startNextRun(state.project.id, {
        agentId: selectedAgentId,
        roadmapId: state.selected_roadmap_id,
      }),
    );
  }, [selectedAgentId, startRun, state]);

  const handleRunSelected = useCallback(async () => {
    if (!state || !selectedTask) {
      return;
    }
    await startRun(() =>
      startTaskRun(state.project.id, {
        taskId: selectedTask.task_id,
        agentId: selectedAgentId,
        roadmapId: selectedTask.roadmap_id,
      }),
    );
  }, [selectedAgentId, selectedTask, startRun, state]);

  const handleCancel = useCallback(async () => {
    if (!state || !run) {
      return;
    }
    try {
      await cancelRun(state.project.id, run.run_id);
      const updated = await fetchRunStatus(state.project.id, run.run_id);
      setRun(updated);
    } catch (err) {
      setRunError(extractErrorMessage(err));
    }
  }, [run, state]);

  const handleDecision = useCallback(async (decision: 'apply' | 'reject') => {
    if (!state || !run) {
      return;
    }
    try {
      const updated = await submitRunDecision(state.project.id, run.run_id, {
        decision,
        selectedAction: decision === 'apply' ? selectedAction : undefined,
      });
      setRun(updated);
      if (updated.logs?.length) {
        setLogs(updated.logs);
      }
      if (!TERMINAL_STATUSES.has(updated.status)) {
        pollRun(updated.run_id);
      }
    } catch (err) {
      setRunError(extractErrorMessage(err));
    }
  }, [pollRun, run, selectedAction, state]);

  if (isLoading) return <div className="state-loading">Carregando execução...</div>;
  if (error || !state) return <div className="state-error">{error || 'Projeto indisponível.'}</div>;

  return (
    <section className="runs-page">
      <RunHeader run={run} />
      <section className="run-control-card">
        <div className="run-control-grid">
          <label className="run-control-field">
            <span className="run-control-label">Agente</span>
            <select
              className="filter-select-ds"
              value={selectedAgentId}
              onChange={(event) => setSelectedAgentId(event.target.value)}
              disabled={isRunning}
            >
              {availableAgents.map((agent) => (
                <option key={agent.agent_id} value={agent.agent_id} disabled={!agent.available}>
                  {agent.label}{agent.available ? '' : ' (indisponível)'}
                </option>
              ))}
            </select>
          </label>

          <label className="run-control-field">
            <span className="run-control-label">Task</span>
            <select
              className="filter-select-ds"
              value={selectedTaskId}
              onChange={(event) => setSelectedTaskId(event.target.value)}
              disabled={isRunning || runnableTasks.length === 0}
            >
              {runnableTasks.length === 0 ? (
                <option value="">Nenhuma task disponível</option>
              ) : (
                runnableTasks.map((task) => (
                  <option key={`${task.roadmap_id}:${task.task_id}`} value={task.task_id}>
                    {task.task_id} - {task.title}
                  </option>
                ))
              )}
            </select>
          </label>

          <div className="run-control-field">
            <span className="run-control-label">Roadmap</span>
            <div className="run-control-static">
              {state.roadmap_mode === 'aggregate'
                ? 'Selecione um roadmap específico no topo para executar'
                : selectedTask?.roadmap_label ?? state.available_roadmaps.find((item) => item.roadmap_id === state.selected_roadmap_id)?.label ?? 'Principal'}
            </div>
          </div>
        </div>

        <div className="run-actions">
          <button className="btn-primary-ds" onClick={() => void handleRunSelected()} disabled={isRunning || !canRunSelected}>
            Executar task selecionada
          </button>
          <button className="btn-secondary-ds" onClick={() => void handleRunNext()} disabled={isRunning || !canRunNext}>
            Executar próxima elegível
          </button>
          <button className="btn-danger-ds" onClick={() => void handleCancel()} disabled={!isRunning}>
            Cancelar run
          </button>
          <button className="btn-secondary-ds" onClick={() => void reload()} disabled={isRunning}>
            Atualizar estado
          </button>
        </div>

        {state.roadmap_mode === 'aggregate' ? (
          <p className="run-help-text">
            A execução fica desabilitada no modo agregado. Escolha um roadmap específico no seletor do topo.
          </p>
        ) : null}
        {selectedAgent ? (
          <p className={`run-help-text ${selectedAgent.available ? 'run-help-ok' : 'run-help-error'}`}>
            Agente selecionado: <strong>{selectedAgent.label}</strong> via <code>{selectedAgent.command}</code>
            {selectedAgent.available ? ' disponível no ambiente.' : ' não encontrado no ambiente.'}
          </p>
        ) : null}

        {selectedTask ? (
          <div className="run-task-preview">
            <div>
              <div className="task-id-cell">{selectedTask.task_id}</div>
              <strong>{selectedTask.title}</strong>
              <p>{selectedTask.description || 'Sem descrição adicional.'}</p>
            </div>
            <div className="run-task-preview-meta">
              <span className={`status-badge ${selectedTask.status}`}>{selectedTask.status}</span>
              <span className={`kind-badge`}>{selectedTask.task_kind}</span>
              <span className={selectedTask.is_eligible ? 'task-eligible-hint' : 'task-blocked-hint'}>
                {selectedTask.is_eligible
                  ? 'Elegível para execução'
                  : selectedTask.status === 'in_progress'
                    ? 'Task já iniciada: a tela permite retomar a execução.'
                    : selectedTask.ineligibility_reasons.join(' | ')}
              </span>
            </div>
          </div>
        ) : null}

        {runError ? <p className="error-text">{runError}</p> : null}
      </section>

      <RunStepsTimeline run={run} />
      <RunConsoleDock logs={logs} />

      <div className="run-results-grid">
        <section className="run-result-card">
          <h3 className="run-steps-title">Retorno da run</h3>
          {run ? (
            <div className="run-result-stack">
              <div className="run-result-grid">
                <div>
                  <strong>Run ID</strong>
                  <span className="task-id-cell">{run.run_id}</span>
                </div>
                <div>
                  <strong>Status</strong>
                  <span>{run.status}</span>
                </div>
                <div>
                  <strong>Agente</strong>
                  <span>{run.agent_id}</span>
                </div>
                <div>
                  <strong>Roadmap</strong>
                  <span>{run.roadmap_id ?? state.selected_roadmap_id}</span>
                </div>
                <div>
                  <strong>Início</strong>
                  <span>{new Date(run.started_at).toLocaleString()}</span>
                </div>
                <div>
                  <strong>Fim</strong>
                  <span>{run.ended_at ? new Date(run.ended_at).toLocaleString() : 'em andamento'}</span>
                </div>
              </div>
              {run.error_message ? (
                <div className="run-warning-box">
                  <strong>Erro reportado</strong>
                  <p>{run.error_message}</p>
                </div>
              ) : null}
              <div className="run-json-card">
                <div className="run-json-title">Payload bruto disponível hoje</div>
                <pre className="event-payload-pre">{JSON.stringify(run, null, 2)}</pre>
              </div>
              <div className="run-json-card">
                <div className="run-json-title">Histórico de decisões</div>
                {run.decision_history && run.decision_history.length > 0 ? (
                  <div className="decision-history-list">
                    {run.decision_history.map((entry, index) => (
                      <div key={`${entry.timestamp}-${index}`} className="decision-history-item">
                        <div className="decision-history-top">
                          <strong>{entry.stage}</strong>
                          <span>{new Date(entry.timestamp).toLocaleString()}</span>
                        </div>
                        <div className="decision-history-meta">
                          {entry.proposed_action ? <span>proposta: {entry.proposed_action}</span> : null}
                          {entry.selected_action ? <span>escolha: {entry.selected_action}</span> : null}
                          {entry.decision ? <span>decisão: {entry.decision}</span> : null}
                          {entry.actor ? <span>ator: {entry.actor}</span> : null}
                        </div>
                        {entry.notes ? <p>{entry.notes}</p> : null}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="panel-empty">Nenhuma decisão manual registrada ainda.</p>
                )}
              </div>
            </div>
          ) : (
            <p className="panel-empty">Nenhuma run iniciada nesta sessão.</p>
          )}
        </section>

        <section className="run-result-card">
          <h3 className="run-steps-title">Decisão manual</h3>
          {isWaitingDecision ? (
            <div className="run-decision-stack">
              <div className="run-warning-box run-warning-neutral">
                <strong>Aguardando sua escolha</strong>
                <p>
                  O agente retornou uma proposta. Escolha a ação final e continue a execução.
                </p>
              </div>
              <label className="run-control-field">
                <span className="run-control-label">Ação a aplicar</span>
                <select
                  className="filter-select-ds"
                  value={selectedAction}
                  onChange={(event) => setSelectedAction(event.target.value)}
                >
                  {(run?.available_actions ?? ['claim', 'complete', 'issue.report']).map((action) => (
                    <option key={action} value={action}>
                      {action}
                    </option>
                  ))}
                </select>
              </label>
              <div className="run-actions">
                <button className="btn-primary-ds" onClick={() => void handleDecision('apply')}>
                  Aplicar ação e continuar
                </button>
                <button className="btn-secondary-ds" onClick={() => void handleDecision('reject')}>
                  Rejeitar proposta
                </button>
              </div>
            </div>
          ) : (
            <div className="run-warning-box run-warning-neutral">
              <strong>Fluxo manual</strong>
              <p>
                Quando o agente devolver uma proposta, a run vai pausar aqui em <code>waiting_input</code> para você escolher a ação.
              </p>
            </div>
          )}
          <RunArtifactsPanel artifacts={state.artifacts} />
        </section>
      </div>
    </section>
  );
}
