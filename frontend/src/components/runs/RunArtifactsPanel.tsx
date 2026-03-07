import type { ArtifactSummary } from '../../services/projects';

interface RunArtifactsPanelProps {
  artifacts: ArtifactSummary[];
}

export function RunArtifactsPanel({ artifacts }: RunArtifactsPanelProps) {
  const topArtifacts = artifacts.slice(0, 6);

  return (
    <section className="run-artifacts-card">
      <h3 className="run-steps-title">Artefatos monitorados</h3>
      {topArtifacts.length === 0 ? (
        <p className="panel-empty">Nenhum artefato carregado.</p>
      ) : (
        topArtifacts.map((artifact) => (
          <div key={artifact.path} className="artifact-row">
            <span className="artifact-name">{artifact.name}</span>
            <span className={`artifact-status-${artifact.integrity_status}`}>{artifact.integrity_status}</span>
          </div>
        ))
      )}
    </section>
  );
}
