import type { RunState } from '../../services/runs';

interface RunHeaderProps {
  run: RunState | null;
}

export function RunHeader({ run }: RunHeaderProps) {
  return (
    <section className="run-header-card">
      <div>
        <h2 className="run-info-title">Execução supervisionada</h2>
        <div className="run-meta">
          <span>
            <span className="run-meta-label">Status:</span> {run?.status ?? 'idle'}
          </span>
          <span>
            <span className="run-meta-label">Task:</span> {run?.task_id ?? 'nenhuma'}
          </span>
          <span>
            <span className="run-meta-label">Runner:</span> {run?.agent_id ?? 'indefinido'}
          </span>
        </div>
      </div>
    </section>
  );
}
