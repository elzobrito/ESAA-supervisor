import { useState } from 'react';

import { extractErrorMessage } from '../services/api';
import { useProject } from '../services/projectContext';
import { repairIntegrity } from '../services/projects';

export function IntegrityPage() {
  const { state, isLoading, error, reload } = useProject();
  const [repairMessage, setRepairMessage] = useState<string | null>(null);
  const [repairError, setRepairError] = useState<string | null>(null);
  const [isRepairing, setIsRepairing] = useState(false);

  if (isLoading) return <div className="state-loading">Carregando integridade...</div>;
  if (error || !state) return <div className="state-error">{error || 'Projeto indisponível.'}</div>;

  const projectState = state;
  const brokenArtifacts = projectState.artifacts.filter((artifact) => artifact.integrity_status !== 'ok');

  async function handleRepairIntegrity() {
    setRepairMessage(null);
    setRepairError(null);
    setIsRepairing(true);
    try {
      const response = await repairIntegrity(
        projectState.project.id,
        projectState.roadmap_mode === 'aggregate' ? undefined : projectState.selected_roadmap_id,
      );
      await reload();
      setRepairMessage(response.message);
    } catch (err) {
      setRepairError(extractErrorMessage(err));
    } finally {
      setIsRepairing(false);
    }
  }

  return (
    <section>
      <h1 className="page-title">Integridade</h1>
      <div className="panel-card">
        <div className="panel-card-body">
          <p>
            Estado geral: <span className={`integrity-badge ${state.is_consistent ? 'ok' : 'mismatch'}`}>{state.is_consistent ? 'ok' : 'mismatch'}</span>
          </p>
          <p>
            Roadmap selecionado: <span className={`integrity-badge ${state.selected_roadmap_load_status === 'error' ? 'mismatch' : state.selected_roadmap_load_status === 'warning' ? 'warn' : 'ok'}`}>{state.selected_roadmap_load_status}</span>
          </p>
          {state.selected_roadmap_warning ? <p className="task-blocked-hint">{state.selected_roadmap_warning}</p> : null}
          <p>Artefatos com atenção: {brokenArtifacts.length}</p>
          <div className="run-actions">
            <button type="button" className="btn-primary-ds" onClick={() => void handleRepairIntegrity()} disabled={isRepairing}>
              {isRepairing ? 'Resolvendo...' : 'Resolver integridade'}
            </button>
          </div>
          {repairMessage ? <p className="success-text">{repairMessage}</p> : null}
          {repairError ? <p className="error-text">{repairError}</p> : null}
          {brokenArtifacts.length > 0 ? (
            <div className="run-json-card">
              <div className="run-json-title">Artefatos com atenção</div>
              <ul className="catalog-list">
                {brokenArtifacts.map((artifact) => (
                  <li key={artifact.path}>
                    <strong>{artifact.name}</strong> <span className="task-id-cell">{artifact.path}</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}
