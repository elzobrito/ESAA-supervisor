import { useEffect, useMemo, useState } from 'react';

import { ArtifactDetailDrawer } from '../components/artifacts/ArtifactDetailDrawer';
import { ArtifactsCatalogTable, type CatalogArtifact } from '../components/artifacts/ArtifactsCatalogTable';
import { ArtifactTypeFilter } from '../components/artifacts/ArtifactTypeFilter';
import { extractErrorMessage } from '../services/api';
import { browseProjectFiles, type ProjectFileBrowserResponse } from '../services/projects';
import { useProject } from '../services/projectContext';

function deriveOrigin(path: string) {
  const normalized = path.replace(/\\/g, '/').toLowerCase();
  if (normalized.includes('/.roadmap/')) return 'roadmap';
  if (normalized.includes('/docs/')) return 'docs';
  if (normalized.includes('/frontend/')) return 'frontend';
  if (normalized.includes('/backend/')) return 'backend';
  if (normalized.includes('/scripts/')) return 'scripts';
  return 'workspace';
}

function deriveType(path: string) {
  const normalized = path.replace(/\\/g, '/');
  const name = normalized.split('/').pop() ?? normalized;
  const extension = name.includes('.') ? name.split('.').pop() ?? 'file' : 'dir';
  return extension.toLowerCase();
}

export function ArtifactsPage() {
  const { state, isLoading, error } = useProject();
  const [query, setQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [integrityFilter, setIntegrityFilter] = useState('all');
  const [originFilter, setOriginFilter] = useState('all');
  const [roleFilter, setRoleFilter] = useState('all');
  const [selectedArtifactPath, setSelectedArtifactPath] = useState<string | null>(null);
  const [browser, setBrowser] = useState<ProjectFileBrowserResponse | null>(null);
  const [browserError, setBrowserError] = useState<string | null>(null);
  const [browserLoading, setBrowserLoading] = useState(false);

  const artifacts = useMemo<CatalogArtifact[]>(
    () => (state?.artifacts ?? []).map((artifact) => ({
      ...artifact,
      artifact_origin: deriveOrigin(artifact.path),
      artifact_type: deriveType(artifact.path),
    })),
    [state?.artifacts],
  );

  const categories = useMemo(
    () => Array.from(new Set(artifacts.map((artifact) => artifact.category))).sort(),
    [artifacts],
  );
  const integrities = useMemo(
    () => Array.from(new Set(artifacts.map((artifact) => artifact.integrity_status))).sort(),
    [artifacts],
  );
  const origins = useMemo(
    () => Array.from(new Set(artifacts.map((artifact) => artifact.artifact_origin))).sort(),
    [artifacts],
  );
  const roles = useMemo(
    () => Array.from(new Set(artifacts.map((artifact) => artifact.role))).sort(),
    [artifacts],
  );

  const filteredArtifacts = useMemo(() => artifacts.filter((artifact) => {
    const haystack = `${artifact.name} ${artifact.path} ${artifact.role}`.toLowerCase();
    const matchesQuery = query.trim() === '' || haystack.includes(query.toLowerCase());
    const matchesCategory = categoryFilter === 'all' || artifact.category === categoryFilter;
    const matchesIntegrity = integrityFilter === 'all' || artifact.integrity_status === integrityFilter;
    const matchesOrigin = originFilter === 'all' || artifact.artifact_origin === originFilter;
    const matchesRole = roleFilter === 'all' || artifact.role === roleFilter;
    return matchesQuery && matchesCategory && matchesIntegrity && matchesOrigin && matchesRole;
  }), [artifacts, categoryFilter, integrityFilter, originFilter, query, roleFilter]);

  const selectedArtifact = filteredArtifacts.find((artifact) => artifact.path === selectedArtifactPath)
    ?? artifacts.find((artifact) => artifact.path === selectedArtifactPath)
    ?? null;

  useEffect(() => {
    if (!state) {
      return;
    }
    setBrowserLoading(true);
    setBrowserError(null);
    void browseProjectFiles(state.project.id)
      .then(setBrowser)
      .catch((err) => setBrowserError(extractErrorMessage(err)))
      .finally(() => setBrowserLoading(false));
  }, [state]);

  const browserSelectedArtifact = useMemo<CatalogArtifact | null>(() => {
    if (!selectedArtifactPath || selectedArtifact) {
      return selectedArtifact;
    }
    const normalized = selectedArtifactPath.replace(/\\/g, '/');
    const name = normalized.split('/').pop() ?? normalized;
    return {
      name,
      path: selectedArtifactPath,
      category: 'source_of_truth',
      role: 'generic',
      integrity_status: 'ok',
      artifact_origin: deriveOrigin(selectedArtifactPath),
      artifact_type: deriveType(selectedArtifactPath),
    };
  }, [selectedArtifact, selectedArtifactPath]);

  const loadBrowser = async (path?: string | null) => {
    if (!state) {
      return;
    }
    setBrowserLoading(true);
    setBrowserError(null);
    try {
      const next = await browseProjectFiles(state.project.id, path ?? undefined);
      setBrowser(next);
    } catch (err) {
      setBrowserError(extractErrorMessage(err));
    } finally {
      setBrowserLoading(false);
    }
  };

  if (isLoading) return <div className="state-loading">Carregando artefatos...</div>;
  if (error || !state) return <div className="state-error">{error || 'Projeto indisponível.'}</div>;

  return (
    <section className="artifacts-page">
      <h1 className="page-title">Artefatos</h1>
      <p className="page-subtitle">
        Catálogo dedicado para inspeção dos artefatos canônicos, com filtros por origem, integridade e papel.
      </p>

      <div className="artifacts-summary-strip">
        <div className="catalog-summary-card">
          <span className="catalog-summary-label">Artefatos</span>
          <strong>{artifacts.length}</strong>
        </div>
        <div className="catalog-summary-card">
          <span className="catalog-summary-label">Com mismatch</span>
          <strong>{artifacts.filter((artifact) => artifact.integrity_status === 'mismatch').length}</strong>
        </div>
        <div className="catalog-summary-card">
          <span className="catalog-summary-label">Fontes</span>
          <strong>{origins.length}</strong>
        </div>
        <div className="catalog-summary-card">
          <span className="catalog-summary-label">Papéis</span>
          <strong>{roles.length}</strong>
        </div>
      </div>

      <div className="filters-bar artifacts-filters-grid">
        <input
          className="filter-input-ds"
          type="search"
          placeholder="Buscar por nome, path ou papel"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <ArtifactTypeFilter
          label="Categoria"
          value={categoryFilter}
          options={categories}
          allLabel="Todas as categorias"
          onChange={setCategoryFilter}
        />
        <ArtifactTypeFilter
          label="Integridade"
          value={integrityFilter}
          options={integrities}
          allLabel="Todos os estados"
          onChange={setIntegrityFilter}
        />
        <ArtifactTypeFilter
          label="Origem"
          value={originFilter}
          options={origins}
          allLabel="Todas as origens"
          onChange={setOriginFilter}
        />
        <ArtifactTypeFilter
          label="Papel"
          value={roleFilter}
          options={roles}
          allLabel="Todos os papéis"
          onChange={setRoleFilter}
        />
      </div>

      <ArtifactsCatalogTable
        artifacts={filteredArtifacts}
        selectedArtifactPath={selectedArtifactPath}
        onSelectArtifact={setSelectedArtifactPath}
      />
      <section className="project-browser-card">
        <div className="section-header">
          <div>
            <h2 className="section-title">Arquivos do projeto</h2>
            <p className="project-browser-path">{browser?.current_path || '.'}</p>
          </div>
          <div className="project-browser-actions">
            <button className="btn-secondary-ds" type="button" onClick={() => void loadBrowser(browser?.parent_path)} disabled={browserLoading || !browser?.parent_path}>
              Voltar pasta
            </button>
            <button className="btn-secondary-ds" type="button" onClick={() => void loadBrowser('')} disabled={browserLoading}>
              Raiz do projeto
            </button>
          </div>
        </div>
        {browserError ? <p className="error-text">{browserError}</p> : null}
        {browserLoading ? <div className="state-loading">Carregando arquivos...</div> : null}
        {!browserLoading && browser ? (
          <div className="project-browser-grid">
            <div className="project-browser-column">
              <span className="project-browser-title">Diretórios</span>
              {browser.directories.length === 0 ? <div className="catalog-empty-state">Nenhum diretório nesta pasta.</div> : null}
              {browser.directories.map((entry) => (
                <button key={entry.path} className="browser-entry-button" type="button" onClick={() => void loadBrowser(entry.path)}>
                  <span className="browser-entry-name">{entry.name}</span>
                  <span className="browser-entry-path">{entry.path}</span>
                </button>
              ))}
            </div>
            <div className="project-browser-column">
              <span className="project-browser-title">Arquivos</span>
              {browser.files.length === 0 ? <div className="catalog-empty-state">Nenhum arquivo nesta pasta.</div> : null}
              {browser.files.map((entry) => (
                <button key={entry.path} className="browser-entry-button browser-project-card" type="button" onClick={() => setSelectedArtifactPath(entry.path)}>
                  <span className="browser-entry-name">{entry.name}</span>
                  <span className="browser-entry-path">{entry.path}</span>
                </button>
              ))}
            </div>
          </div>
        ) : null}
      </section>
      <ArtifactDetailDrawer
        projectId={state.project.id}
        artifact={browserSelectedArtifact}
        open={browserSelectedArtifact !== null}
        onClose={() => setSelectedArtifactPath(null)}
      />
    </section>
  );
}
