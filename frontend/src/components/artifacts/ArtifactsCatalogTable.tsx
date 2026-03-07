import type { ArtifactSummary } from '../../services/projects';

export interface CatalogArtifact extends ArtifactSummary {
  artifact_origin: string;
  artifact_type: string;
}

interface ArtifactsCatalogTableProps {
  artifacts: CatalogArtifact[];
  selectedArtifactPath: string | null;
  onSelectArtifact: (artifactPath: string) => void;
}

function integrityLabel(status: string) {
  if (status === 'ok') return 'OK';
  if (status === 'mismatch') return 'Mismatch';
  if (status === 'missing') return 'Missing';
  return status;
}

export function ArtifactsCatalogTable({
  artifacts,
  selectedArtifactPath,
  onSelectArtifact,
}: ArtifactsCatalogTableProps) {
  if (artifacts.length === 0) {
    return <div className="catalog-empty-state">Nenhum artefato corresponde aos filtros aplicados.</div>;
  }

  return (
    <div className="data-grid-container">
      <table className="data-grid artifacts-grid">
        <thead>
          <tr>
            <th>Artefato</th>
            <th>Categoria</th>
            <th>Tipo</th>
            <th>Origem</th>
            <th>Papel</th>
            <th>Integridade</th>
          </tr>
        </thead>
        <tbody>
          {artifacts.map((artifact) => (
            <tr
              key={artifact.path}
              className={selectedArtifactPath === artifact.path ? 'row-selected' : ''}
              onClick={() => onSelectArtifact(artifact.path)}
            >
              <td>
                <div className="task-title-text">{artifact.name}</div>
                <div className="artifact-path-text">{artifact.path}</div>
              </td>
              <td><span className="kind-badge">{artifact.category}</span></td>
              <td>{artifact.artifact_type}</td>
              <td>{artifact.artifact_origin}</td>
              <td>{artifact.role}</td>
              <td>
                <span className={`integrity-badge ${artifact.integrity_status}`}>
                  {integrityLabel(artifact.integrity_status)}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
