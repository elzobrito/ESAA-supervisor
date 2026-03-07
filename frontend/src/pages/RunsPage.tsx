import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { extractErrorMessage } from '../services/api';
import { useProject } from '../services/projectContext';
import { submitTaskReview } from '../services/projects';
import { cancelRun, fetchRunStatus, fetchRuns, startNextRun, startTaskRun, stopRunAfterCurrent, submitRunDecision, type RunState } from '../services/runs';
import { RunConsoleDock } from '../components/runs/RunConsoleDock';
import { RunArtifactsPanel } from '../components/runs/RunArtifactsPanel';
import { RunHeader } from '../components/runs/RunHeader';
import { RunStepsTimeline } from '../components/runs/RunStepsTimeline';
import { useShell } from '../components/layout/AppShell';

const TERMINAL_STATUSES = new Set(['done', 'error', 'cancelled']);
const GLOBAL_RUN_ERROR_KEY = '__global__';

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function getTokenUsage(run: RunState | null): {
  total?: number;
  input?: number;
  output?: number;
  totalCostUsd?: number;
  byModel: Array<{ model: string; total?: number; input?: number; output?: number; costUsd?: number }>;
} | null {
  const agentResult = run?.agent_result;
  if (!isRecord(agentResult)) return null;
  const metadata = agentResult.metadata;
  if (!isRecord(metadata)) return null;
  const tokenUsage = metadata.token_usage;
  if (!isRecord(tokenUsage)) return null;

  const models = tokenUsage.models;
  const byModel = !isRecord(models)
    ? []
    : Object.entries(models).map(([model, payload]) => {
        const record = isRecord(payload) ? payload : {};
        const input = typeof record.input === 'number'
          ? record.input
          : typeof record.prompt === 'number'
            ? record.prompt
            : typeof record.inputTokens === 'number'
              ? record.inputTokens
              : undefined;
        const output = typeof record.candidates === 'number'
          ? record.candidates
          : typeof record.output === 'number'
            ? record.output
            : typeof record.outputTokens === 'number'
              ? record.outputTokens
              : undefined;
        const total = typeof record.total === 'number'
          ? record.total
          : (input ?? 0) + (output ?? 0) || undefined;
        return {
          model,
          total,
          input,
          output,
          costUsd: typeof record.costUSD === 'number' ? record.costUSD : undefined,
        };
      });

  const total = typeof tokenUsage.total === 'number'
    ? tokenUsage.total
    : byModel.reduce((sum, item) => sum + (item.total ?? 0), 0) || undefined;
  const input = typeof tokenUsage.input === 'number'
    ? tokenUsage.input
    : byModel.reduce((sum, item) => sum + (item.input ?? 0), 0) || undefined;
  const output = typeof tokenUsage.output === 'number'
    ? tokenUsage.output
    : byModel.reduce((sum, item) => sum + (item.output ?? 0), 0) || undefined;
  const totalCostUsd = typeof tokenUsage.total_cost_usd === 'number' ? tokenUsage.total_cost_usd : undefined;

  return { total, input, output, totalCostUsd, byModel };
}

export function RunsPage() {
  const { state, isLoading, error, reload } = useProject();
  const {
    selectedRunId,
    setSelectedRunId,
    runLogsById,
    setRunLogsById,
    runErrorsById,
    setRunErrorsById,
  } = useShell();
  const [runsById, setRunsById] = useState<Record<string, RunState>>({});
  const [selectedTaskRef, setSelectedTaskRef] = useState('');
  const [selectedAgentId, setSelectedAgentId] = useState('');
  const [executionMode, setExecutionMode] = useState<'manual' | 'continuous'>('manual');
  const [selectedAction, setSelectedAction] = useState('complete');
  const [agentTouched, setAgentTouched] = useState(false);
  const previousActiveRunIdsRef = useRef<string[]>([]);
  const pollRef = useRef<number | null>(null);

  const runnableTasks = useMemo(
    () => (state?.tasks ?? []).filter((task) => task.status !== 'done'),
    [state?.tasks],
  );
  const selectedTask = useMemo(
    () => (state?.tasks ?? []).find((task) => task.task_ref === selectedTaskRef) ?? null,
    [selectedTaskRef, state?.tasks],
  );
  const availableAgents = state?.available_agents ?? [];
  const selectedAgent = availableAgents.find((agent) => agent.agent_id === selectedAgentId) ?? null;

  const activeRuns = useMemo(
    () => (state?.active_runs ?? []).map((summary) => runsById[summary.run_id] ?? {
      run_id: summary.run_id,
      task_id: summary.task_id,
      agent_id: summary.agent_id,
      model_id: summary.model_id,
      roadmap_id: summary.roadmap_id,
      execution_mode: summary.execution_mode,
      status: summary.status,
      started_at: summary.started_at,
      awaiting_decision: summary.awaiting_decision,
      available_actions: [],
      logs: runLogsById[summary.run_id] ?? [],
    }).sort((left, right) => new Date(left.started_at).getTime() - new Date(right.started_at).getTime()),
    [runLogsById, runsById, state?.active_runs],
  );
  const selectedRun = useMemo(() => {
    if (selectedRunId && activeRuns.some((run) => run.run_id === selectedRunId) && runsById[selectedRunId]) {
      return runsById[selectedRunId];
    }
    if (selectedRunId && runsById[selectedRunId] && TERMINAL_STATUSES.has(runsById[selectedRunId].status)) {
      return runsById[selectedRunId];
    }
    return activeRuns[0] ?? null;
  }, [activeRuns, runsById, selectedRunId]);
  const selectedRunLogs = selectedRun ? runLogsById[selectedRun.run_id] ?? selectedRun.logs ?? [] : [];
  const selectedRunError = selectedRunId ? runErrorsById[selectedRunId] ?? null : null;
  const globalRunError = runErrorsById[GLOBAL_RUN_ERROR_KEY] ?? null;
  const tokenUsage = getTokenUsage(selectedRun);
  const isWaitingDecision = selectedRun?.status === 'waiting_input' && selectedRun.awaiting_decision;
  const isContinuousRun = selectedRun?.execution_mode === 'continuous';
  const selectedAgentBusy = selectedAgent?.busy ?? false;
  const selectedAgentAvailable = selectedAgent?.available ?? false;
  const canResumeSelectedTask = selectedTask?.status === 'in_progress' && !selectedTask.active_run_id;
  const canRunNext = state !== null
    && state.roadmap_mode !== 'aggregate'
    && state.eligible_task_ids.length > 0
    && state.remaining_run_slots > 0
    && selectedAgentAvailable
    && !selectedAgentBusy;
  const canRunSelected = state !== null
    && state.roadmap_mode !== 'aggregate'
    && selectedTask !== null
    && !selectedTask.active_run_id
    && state.remaining_run_slots > 0
    && selectedAgentAvailable
    && !selectedAgentBusy
    && (selectedTask.is_eligible || canResumeSelectedTask);

  const upsertRuns = useCallback((runs: RunState[]) => {
    if (runs.length === 0) return;
    setRunsById((current) => {
      const next = { ...current };
      runs.forEach((run) => {
        next[run.run_id] = run;
      });
      return next;
    });
    setRunLogsById((current) => {
      const next = { ...current };
      runs.forEach((run) => {
        next[run.run_id] = run.logs ?? current[run.run_id] ?? [];
      });
      return next;
    });
    setRunErrorsById((current) => {
      const next = { ...current };
      runs.forEach((run) => {
        next[run.run_id] = run.error_message ?? null;
      });
      return next;
    });
  }, [setRunErrorsById, setRunLogsById]);

  const hydrateRun = useCallback(async (runId: string): Promise<boolean> => {
    if (!state) return false;
    try {
      const updated = await fetchRunStatus(state.project.id, runId);
      upsertRuns([updated]);
      return TERMINAL_STATUSES.has(updated.status);
    } catch (err) {
      setRunErrorsById((current) => ({
        ...current,
        [runId]: extractErrorMessage(err),
      }));
      return false;
    }
  }, [setRunErrorsById, state, upsertRuns]);

  const stopPolling = useCallback(() => {
    if (pollRef.current !== null) {
      window.clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const refreshRuns = useCallback(async () => {
    if (!state) return;
    try {
      const fetchedRuns = await fetchRuns(state.project.id);
      upsertRuns(fetchedRuns);

      const nextActiveIds = fetchedRuns.map((run) => run.run_id);
      const previousActiveIds = previousActiveRunIdsRef.current;
      previousActiveRunIdsRef.current = nextActiveIds;

      if (!selectedRunId && nextActiveIds.length > 0) {
        setSelectedRunId(nextActiveIds[0]);
      }

      const completedIds = previousActiveIds.filter((runId) => !nextActiveIds.includes(runId));
      if (completedIds.length > 0) {
        const terminalStates = await Promise.all(completedIds.map((runId) => hydrateRun(runId)));
        if (terminalStates.some(Boolean)) {
          await reload();
        }
      }

       const staleTrackedIds = Object.values(runsById)
        .filter((run) => !nextActiveIds.includes(run.run_id) && !TERMINAL_STATUSES.has(run.status))
        .map((run) => run.run_id);
      if (staleTrackedIds.length > 0) {
        const refreshed = await Promise.all(staleTrackedIds.map((runId) => hydrateRun(runId)));
        if (refreshed.some(Boolean)) {
          await reload();
        }
      }

      setRunErrorsById((current) => ({
        ...current,
        [GLOBAL_RUN_ERROR_KEY]: null,
      }));
    } catch (err) {
      setRunErrorsById((current) => ({
        ...current,
        [GLOBAL_RUN_ERROR_KEY]: extractErrorMessage(err),
      }));
    }
  }, [hydrateRun, reload, runsById, selectedRunId, setRunErrorsById, setSelectedRunId, state, upsertRuns]);

  const startRun = useCallback(async (runner: () => Promise<RunState>) => {
    setRunErrorsById((current) => ({
      ...current,
      [GLOBAL_RUN_ERROR_KEY]: null,
    }));
    try {
      const created = await runner();
      upsertRuns([created]);
      previousActiveRunIdsRef.current = Array.from(new Set([...previousActiveRunIdsRef.current, created.run_id]));
      setSelectedRunId(created.run_id);
      await reload();
    } catch (err) {
      setRunErrorsById((current) => ({
        ...current,
        [GLOBAL_RUN_ERROR_KEY]: extractErrorMessage(err),
      }));
    }
  }, [reload, setRunErrorsById, setSelectedRunId, upsertRuns]);

  useEffect(() => {
    if (!selectedTaskRef && runnableTasks.length > 0) {
      setSelectedTaskRef(runnableTasks[0].task_ref);
    }
  }, [runnableTasks, selectedTaskRef]);

  useEffect(() => {
    if (!state) return;
    void refreshRuns();
    stopPolling();
    pollRef.current = window.setInterval(() => {
      void refreshRuns();
    }, 1500);
    return () => {
      stopPolling();
    };
  }, [refreshRuns, state, stopPolling]);

  useEffect(() => () => {
    stopPolling();
  }, [stopPolling]);

  useEffect(() => {
    if (selectedRun?.proposed_action) {
      setSelectedAction(selectedRun.proposed_action);
    }
  }, [selectedRun?.proposed_action]);

  useEffect(() => {
    if (!state || !selectedRun) return;
    const matchingTask = state.tasks.find((task) => task.task_id === selectedRun.task_id && task.roadmap_id === (selectedRun.roadmap_id ?? task.roadmap_id));
    if (matchingTask) {
      setSelectedTaskRef(matchingTask.task_ref);
    }
  }, [selectedRun, state]);

  useEffect(() => {
    if (selectedRunId && activeRuns.some((run) => run.run_id === selectedRunId)) return;
    if (!selectedRunId && activeRuns.length > 0) {
      setSelectedRunId(activeRuns[0].run_id);
    }
  }, [activeRuns, selectedRunId, setSelectedRunId]);

  useEffect(() => {
    if (!selectedTask) return;
    const nextAgentId = selectedTask.planning?.preferred_runner
      ?? availableAgents.find((agent) => agent.available && !agent.busy)?.agent_id
      ?? availableAgents.find((agent) => agent.available)?.agent_id
      ?? availableAgents[0]?.agent_id
      ?? '';
    if (!agentTouched || !selectedAgentId) {
      setSelectedAgentId(nextAgentId);
    }
  }, [agentTouched, availableAgents, selectedAgentId, selectedTask]);

  const handleReviewDecision = useCallback(async (decision: 'approve' | 'reject') => {
    if (!state || !selectedTask) return;
    try {
      await submitTaskReview(state.project.id, selectedTask.task_id, {
        decision,
        roadmapId: selectedTask.roadmap_id,
      });
      await reload();
    } catch (err) {
      setRunErrorsById((current) => ({
        ...current,
        [GLOBAL_RUN_ERROR_KEY]: extractErrorMessage(err),
      }));
    }
  }, [reload, selectedTask, setRunErrorsById, state]);

  const handleRunNext = useCallback(async () => {
    if (!state || state.roadmap_mode === 'aggregate') return;
    await startRun(() =>
      startNextRun(state.project.id, {
        agentId: selectedAgentId || undefined,
        roadmapId: state.selected_roadmap_id,
        executionMode,
      }),
    );
  }, [executionMode, selectedAgentId, startRun, state]);

  const handleRunSelected = useCallback(async () => {
    if (!state || !selectedTask) return;
    await startRun(() =>
      startTaskRun(state.project.id, {
        taskId: selectedTask.task_id,
        agentId: selectedAgentId || undefined,
        roadmapId: selectedTask.roadmap_id,
        executionMode,
      }),
    );
  }, [executionMode, selectedAgentId, selectedTask, startRun, state]);

  const handleCancel = useCallback(async () => {
    if (!state || !selectedRun) return;
    try {
      await cancelRun(state.project.id, selectedRun.run_id);
      const updated = await fetchRunStatus(state.project.id, selectedRun.run_id);
      upsertRuns([updated]);
      if (TERMINAL_STATUSES.has(updated.status)) {
        await reload();
      }
    } catch (err) {
      setRunErrorsById((current) => ({
        ...current,
        [selectedRun.run_id]: extractErrorMessage(err),
      }));
    }
  }, [reload, selectedRun, setRunErrorsById, state, upsertRuns]);

  const handleStopAfterCurrent = useCallback(async () => {
    if (!state || !selectedRun) return;
    try {
      await stopRunAfterCurrent(state.project.id, selectedRun.run_id);
      const updated = await fetchRunStatus(state.project.id, selectedRun.run_id);
      upsertRuns([updated]);
    } catch (err) {
      setRunErrorsById((current) => ({
        ...current,
        [selectedRun.run_id]: extractErrorMessage(err),
      }));
    }
  }, [selectedRun, setRunErrorsById, state, upsertRuns]);

  const handleDecision = useCallback(async (decision: 'apply' | 'reject') => {
    if (!state || !selectedRun) return;
    try {
      const updated = await submitRunDecision(state.project.id, selectedRun.run_id, {
        decision,
        selectedAction: decision === 'apply' ? selectedAction : undefined,
      });
      upsertRuns([updated]);
      if (TERMINAL_STATUSES.has(updated.status)) {
        await reload();
      }
    } catch (err) {
      setRunErrorsById((current) => ({
        ...current,
        [selectedRun.run_id]: extractErrorMessage(err),
      }));
    }
  }, [reload, selectedAction, selectedRun, setRunErrorsById, state, upsertRuns]);

  if (isLoading) return <div className="state-loading">Carregando execução...</div>;
  if (error || !state) return <div className="state-error">{error || 'Projeto indisponível.'}</div>;

  return (
    <section className="runs-page">
      <RunHeader run={selectedRun} activeRunCount={state.active_run_count} />
      <section className="run-control-card">
        <div className="run-control-grid">
          <label className="run-control-field">
            <span className="run-control-label">Agente</span>
            <select
              className="filter-select-ds"
              value={selectedAgentId}
              onChange={(event) => {
                setSelectedAgentId(event.target.value);
                setAgentTouched(true);
              }}
            >
              {availableAgents.map((agent) => (
                <option key={agent.agent_id} value={agent.agent_id} disabled={!agent.available}>
                  {agent.label}
                  {!agent.available ? ' (indisponível)' : agent.busy ? ' (ocupado)' : ''}
                </option>
              ))}
            </select>
          </label>

          <label className="run-control-field">
            <span className="run-control-label">Task</span>
            <select
              className="filter-select-ds"
              value={selectedTaskRef}
              onChange={(event) => {
                setSelectedTaskRef(event.target.value);
                setAgentTouched(false);
              }}
              disabled={runnableTasks.length === 0}
            >
              {runnableTasks.length === 0 ? (
                <option value="">Nenhuma task disponível</option>
              ) : (
                runnableTasks.map((task) => (
                  <option key={task.task_ref} value={task.task_ref}>
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
                : selectedTask?.roadmap_label
                  ?? state.available_roadmaps.find((item) => item.roadmap_id === state.selected_roadmap_id)?.label
                  ?? 'Principal'}
            </div>
          </div>

          <label className="run-control-field">
            <span className="run-control-label">Modo</span>
            <select
              className="filter-select-ds"
              value={executionMode}
              onChange={(event) => setExecutionMode(event.target.value as 'manual' | 'continuous')}
            >
              <option value="manual">Manual</option>
              <option value="continuous">Sequencial sem interrupção</option>
            </select>
          </label>
        </div>
        <div className="run-actions">
          <button className="btn-primary-ds" onClick={() => void handleRunSelected()} disabled={!canRunSelected}>
            Executar task selecionada
          </button>
          <button className="btn-secondary-ds" onClick={() => void handleRunNext()} disabled={!canRunNext}>
            Executar próxima elegível
          </button>
          <button
            className="btn-secondary-ds"
            onClick={() => void handleStopAfterCurrent()}
            disabled={!selectedRun || TERMINAL_STATUSES.has(selectedRun.status) || !isContinuousRun || selectedRun.stop_after_current}
          >
            {selectedRun?.stop_after_current ? 'Parada graciosa solicitada' : 'Parar após tarefa atual'}
          </button>
          <button
            className="btn-danger-ds"
            onClick={() => void handleCancel()}
            disabled={!selectedRun || TERMINAL_STATUSES.has(selectedRun.status)}
          >
            Cancelar run
          </button>
          <button className="btn-secondary-ds" onClick={() => void reload()}>
            Atualizar estado
          </button>
        </div>

        {state.roadmap_mode === 'aggregate' ? (
          <p className="run-help-text">
            A execução fica desabilitada no modo agregado. Escolha um roadmap específico no seletor do topo.
          </p>
        ) : null}
        {selectedAgent ? (
          <p className={`run-help-text ${selectedAgent.available && !selectedAgent.busy ? 'run-help-ok' : 'run-help-error'}`}>
            Agente selecionado: <strong>{selectedAgent.label}</strong> via <code>{selectedAgent.command}</code>.
            {!selectedAgent.available
              ? ' Não encontrado no ambiente.'
              : selectedAgent.busy
                ? ' Já está ocupado em outra run deste projeto.'
                : ' Disponível no ambiente.'}
          </p>
        ) : null}
        <p className="run-help-text">
          {executionMode === 'continuous'
            ? 'Modo sequencial: a proposta do agente é aplicada automaticamente e a próxima task elegível compatível com o mesmo agente é iniciada sem pausa.'
            : 'Modo manual: a run pausa em waiting_input para você decidir a ação final.'}
        </p>

        {selectedTask ? (
          <div className="run-task-preview">
            <div>
              <div className="task-id-cell">{selectedTask.task_id}</div>
              <strong>{selectedTask.title}</strong>
              <p>{selectedTask.description || 'Sem descrição adicional.'}</p>
            </div>
            <div className="run-task-preview-meta">
              <span className={`status-badge ${selectedTask.status}`}>{selectedTask.status}</span>
              <span className="kind-badge">{selectedTask.task_kind}</span>
              <span className="kind-badge">{selectedTask.planning?.preferred_runner ?? 'runner padrão'}</span>
              <span className={selectedTask.is_eligible || canResumeSelectedTask ? 'task-eligible-hint' : 'task-blocked-hint'}>
                {selectedTask.active_run_id
                  ? `Já em execução por ${selectedTask.active_agent ?? 'outro agente'}`
                  : selectedTask.is_eligible
                    ? 'Elegível para execução'
                    : canResumeSelectedTask
                      ? 'Task em progresso pronta para retomar.'
                      : selectedTask.ineligibility_reasons.join(' | ')}
              </span>
            </div>
          </div>
        ) : null}

        {globalRunError ? <p className="error-text">{globalRunError}</p> : null}
      </section>

      {activeRuns.length > 0 ? (
        <section className="run-active-grid">
          {activeRuns.map((run) => {
            const task = state.tasks.find((item) => item.task_id === run.task_id && item.roadmap_id === (run.roadmap_id ?? item.roadmap_id));
            return (
              <button
                key={run.run_id}
                type="button"
                className={`run-active-card${selectedRun?.run_id === run.run_id ? ' selected' : ''}`}
                onClick={() => setSelectedRunId(run.run_id)}
              >
                <div className="run-active-card-top">
                  <span className="task-id-cell">{run.task_id}</span>
                  <span className={`status-badge ${run.status}`}>{run.status}</span>
                </div>
                <strong>{task?.title ?? run.task_id}</strong>
                <div className="decision-history-meta">
                  <span>{run.agent_id}</span>
                  <span>{run.model_id ?? 'modelo padrão'}</span>
                  <span>{run.execution_mode === 'continuous' ? 'sequencial' : 'manual'}</span>
                </div>
                <div className={run.awaiting_decision ? 'task-blocked-hint' : 'task-eligible-hint'}>
                  {run.awaiting_decision ? 'Aguardando decisão manual' : 'Em execução'}
                </div>
              </button>
            );
          })}
        </section>
      ) : null}

      <RunStepsTimeline run={selectedRun} />
      <RunConsoleDock logs={selectedRunLogs} />

      <div className="run-results-grid">
        <section className="run-result-card">
          <h3 className="run-steps-title">Retorno da run</h3>
          {selectedRun ? (
            <div className="run-result-stack">
              <div className="run-result-grid">
                <div>
                  <strong>Run ID</strong>
                  <span className="task-id-cell">{selectedRun.run_id}</span>
                </div>
                <div>
                  <strong>Status</strong>
                  <span>{selectedRun.status}</span>
                </div>
                <div>
                  <strong>Agente</strong>
                  <span>{selectedRun.agent_id}</span>
                </div>
                <div>
                  <strong>Modelo</strong>
                  <span>{selectedRun.model_id ?? 'padrão da task'}</span>
                </div>
                <div>
                  <strong>Roadmap</strong>
                  <span>{selectedRun.roadmap_id ?? state.selected_roadmap_id}</span>
                </div>
                <div>
                  <strong>Modo</strong>
                  <span>{selectedRun.execution_mode === 'continuous' ? 'sequencial' : 'manual'}</span>
                </div>
                <div>
                  <strong>Início</strong>
                  <span>{new Date(selectedRun.started_at).toLocaleString()}</span>
                </div>
                <div>
                  <strong>Fim</strong>
                  <span>{selectedRun.ended_at ? new Date(selectedRun.ended_at).toLocaleString() : 'em andamento'}</span>
                </div>
                <div>
                  <strong>Tasks concluídas</strong>
                  <span>{selectedRun.completed_task_ids?.length ?? 0}</span>
                </div>
                <div>
                  <strong>Runs ativas</strong>
                  <span>{state.active_run_count} / 3</span>
                </div>
              </div>
              {selectedRun.stop_after_current ? (
                <div className="run-warning-box run-warning-neutral">
                  <strong>Parada graciosa pendente</strong>
                  <p>A execução contínua será encerrada quando a task atual terminar.</p>
                </div>
              ) : null}
              {selectedRun.error_message ? (
                <div className="run-warning-box">
                  <strong>Erro reportado</strong>
                  <p>{selectedRun.error_message}</p>
                </div>
              ) : null}
              {tokenUsage ? (
                <div className="run-json-card">
                  <div className="run-json-title">Uso de tokens</div>
                  <div className="run-result-grid">
                    <div>
                      <strong>Total</strong>
                      <span>{tokenUsage.total ?? 'n/d'}</span>
                    </div>
                    <div>
                      <strong>Entrada</strong>
                      <span>{tokenUsage.input ?? 'n/d'}</span>
                    </div>
                    <div>
                      <strong>Saída</strong>
                      <span>{tokenUsage.output ?? 'n/d'}</span>
                    </div>
                    <div>
                      <strong>Custo</strong>
                      <span>{tokenUsage.totalCostUsd !== undefined ? `$${tokenUsage.totalCostUsd.toFixed(6)}` : 'n/d'}</span>
                    </div>
                  </div>
                  {tokenUsage.byModel.length > 0 ? (
                    <div className="decision-history-list">
                      {tokenUsage.byModel.map((item) => (
                        <div key={item.model} className="decision-history-item">
                          <div className="decision-history-top">
                            <strong>{item.model}</strong>
                          </div>
                          <div className="decision-history-meta">
                            <span>total: {item.total ?? 'n/d'}</span>
                            <span>entrada: {item.input ?? 'n/d'}</span>
                            <span>saída: {item.output ?? 'n/d'}</span>
                            {item.costUsd !== undefined ? <span>custo: ${item.costUsd.toFixed(6)}</span> : null}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : null}
                </div>
              ) : null}
              <div className="run-json-card">
                <div className="run-json-title">Payload bruto disponível hoje</div>
                <pre className="event-payload-pre">{JSON.stringify(selectedRun, null, 2)}</pre>
              </div>
              <div className="run-json-card">
                <div className="run-json-title">Histórico de decisões</div>
                {selectedRun.decision_history && selectedRun.decision_history.length > 0 ? (
                  <div className="decision-history-list">
                    {selectedRun.decision_history.map((entry, index) => (
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
            <p className="panel-empty">Nenhuma run selecionada. Inicie uma task ou escolha uma execução ativa.</p>
          )}
        </section>

        <section className="run-result-card">
          <h3 className="run-steps-title">Decisão manual</h3>
          {selectedTask?.status === 'review' ? (
            <div className="run-decision-stack">
              <div className="run-warning-box run-warning-neutral">
                <strong>Tarefa em revisão</strong>
                <p>O trabalho técnico foi concluído. Você pode aprovar a entrega ou rejeitar para uma nova execução.</p>
              </div>
              <div className="run-actions">
                <button className="btn-primary-ds" onClick={() => void handleReviewDecision('approve')}>
                  Aprovar review
                </button>
                <button className="btn-secondary-ds" onClick={() => void handleReviewDecision('reject')}>
                  Rejeitar review
                </button>
              </div>
            </div>
          ) : null}
          {isWaitingDecision ? (
            <div className="run-decision-stack">
              <div className="run-warning-box run-warning-neutral">
                <strong>Aguardando sua escolha</strong>
                <p>O agente retornou uma proposta. Escolha a ação final e continue a execução.</p>
              </div>
              <label className="run-control-field">
                <span className="run-control-label">Ação a aplicar</span>
                <select
                  className="filter-select-ds"
                  value={selectedAction}
                  onChange={(event) => setSelectedAction(event.target.value)}
                >
                  {(selectedRun?.available_actions ?? ['claim', 'complete', 'issue.report']).map((action) => (
                    <option key={action} value={action}>
                      {action}
                    </option>
                  ))}
                </select>
              </label>
              <div className="run-actions">
                <button className="btn-primary-ds" onClick={() => void handleDecision('apply')}>
                  Aplicar proposta
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
                {(selectedRun?.execution_mode ?? executionMode) === 'continuous'
                  ? 'No modo sequencial, a proposta do agente é aplicada automaticamente e o sistema segue para a próxima task elegível compatível com o agente da run.'
                  : <>Quando o agente devolver uma proposta, a run vai pausar aqui em <code>waiting_input</code> para você escolher a ação.</>}
              </p>
            </div>
          )}
          {selectedRunError ? <p className="error-text">{selectedRunError}</p> : null}
          <RunArtifactsPanel artifacts={state.artifacts} />
        </section>
      </div>
    </section>
  );
}
