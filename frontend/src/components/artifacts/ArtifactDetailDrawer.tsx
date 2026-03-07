import { useEffect, useMemo, useState } from 'react';
import { Maximize2, X } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import { extractErrorMessage } from '../../services/api';
import { fetchArtifactContent, type ArtifactContentResponse, type ArtifactSummary } from '../../services/projects';

interface CatalogArtifact extends ArtifactSummary {
  artifact_origin: string;
  artifact_type: string;
}

interface ArtifactDetailDrawerProps {
  projectId: string;
  artifact: CatalogArtifact | null;
  open: boolean;
  onClose: () => void;
}

function isMarkdownFile(path: string) {
  return /\.md$/i.test(path);
}

function codeLanguage(path: string) {
  const ext = path.split('.').pop()?.toLowerCase();
  if (!ext) return 'text';
  const mapping: Record<string, string> = {
    py: 'python',
    ts: 'typescript',
    tsx: 'tsx',
    js: 'javascript',
    jsx: 'jsx',
    json: 'json',
    jsonl: 'json',
    yaml: 'yaml',
    yml: 'yaml',
    md: 'markdown',
    html: 'html',
    css: 'css',
    sh: 'bash',
    ps1: 'powershell',
    txt: 'text',
  };
  return mapping[ext] ?? ext;
}

function ArtifactContentBlock({ path, content }: { path: string; content: string }) {
  if (isMarkdownFile(path)) {
    return (
      <div className="artifact-markdown">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
      </div>
    );
  }

  return (
    <div className="artifact-code-view">
      <div className="artifact-code-label">{codeLanguage(path)}</div>
      <pre className="artifact-preview-pre artifact-preview-pre-lg">
        <code>{content}</code>
      </pre>
    </div>
  );
}

export function ArtifactDetailDrawer({ projectId, artifact, open, onClose }: ArtifactDetailDrawerProps) {
  const [preview, setPreview] = useState<ArtifactContentResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fullContent, setFullContent] = useState<ArtifactContentResponse | null>(null);
  const [fullLoading, setFullLoading] = useState(false);
  const [fullError, setFullError] = useState<string | null>(null);
  const [viewerOpen, setViewerOpen] = useState(false);

  const activeContent = useMemo(() => fullContent ?? preview, [fullContent, preview]);

  useEffect(() => {
    if (!open || !artifact) {
      setPreview(null);
      setError(null);
      setIsLoading(false);
      setFullContent(null);
      setFullError(null);
      setFullLoading(false);
      setViewerOpen(false);
      return;
    }

    let isActive = true;
    setIsLoading(true);
    setError(null);
    void fetchArtifactContent(projectId, artifact.path)
      .then((response) => {
        if (!isActive) return;
        setPreview(response);
      })
      .catch((err) => {
        if (!isActive) return;
        setError(extractErrorMessage(err));
      })
      .finally(() => {
        if (!isActive) return;
        setIsLoading(false);
      });

    return () => {
      isActive = false;
    };
  }, [artifact, open, projectId]);

  if (!open || !artifact) {
    return null;
  }

  const openFullViewer = async () => {
    setViewerOpen(true);
    if (fullContent || fullLoading) {
      return;
    }
    setFullLoading(true);
    setFullError(null);
    try {
      const response = await fetchArtifactContent(projectId, artifact.path, true);
      setFullContent(response);
    } catch (err) {
      setFullError(extractErrorMessage(err));
    } finally {
      setFullLoading(false);
    }
  };

  return (
    <>
      <div className="drawer-overlay" onClick={onClose} aria-hidden="true" />
      <aside className="drawer" aria-label="Detalhes do artefato">
        <div className="drawer-header">
          <div>
            <p className="task-id-cell">{artifact.category}</p>
            <h3 className="drawer-title">{artifact.name}</h3>
          </div>
          <button className="drawer-close" type="button" onClick={onClose} aria-label="Fechar detalhe">
            <X size={18} />
          </button>
        </div>
        <div className="drawer-body">
          <section className="drawer-section">
            <span className="drawer-section-label">Resumo</span>
            <div className="drawer-section-content">
              <span className={`integrity-badge ${artifact.integrity_status}`}>{artifact.integrity_status}</span>
              <span className="kind-badge">{artifact.artifact_type}</span>
              <p>{artifact.role}</p>
            </div>
          </section>
          <section className="drawer-section">
            <span className="drawer-section-label">Path</span>
            <div className="drawer-section-content artifact-drawer-path">{artifact.path}</div>
          </section>
          <section className="drawer-section">
            <span className="drawer-section-label">Classificação</span>
            <div className="drawer-section-content artifact-meta-grid">
              <div>
                <strong>Origem</strong>
                <span>{artifact.artifact_origin}</span>
              </div>
              <div>
                <strong>Categoria</strong>
                <span>{artifact.category}</span>
              </div>
              <div>
                <strong>Tipo</strong>
                <span>{artifact.artifact_type}</span>
              </div>
              <div>
                <strong>Papel</strong>
                <span>{artifact.role}</span>
              </div>
            </div>
          </section>
          <section className="drawer-section">
            <span className="drawer-section-label">Uso operacional</span>
            <div className="drawer-section-content">
              {artifact.integrity_status === 'ok'
                ? 'Artefato disponível para inspeção sem sinais de divergência.'
                : 'Artefato requer atenção operacional antes de confiar na projeção associada.'}
            </div>
          </section>
          <section className="drawer-section">
            <span className="drawer-section-label">Conteúdo</span>
            <div className="drawer-section-content">
              {isLoading ? <p>Carregando preview...</p> : null}
              {error ? <p className="error-text">{error}</p> : null}
              {!isLoading && !error && preview ? (
                <>
                  <div className="artifact-preview-meta">
                    <span>{preview.encoding}</span>
                    <span>{preview.size_bytes} bytes</span>
                    {preview.truncated ? <span>preview truncado</span> : <span>arquivo completo</span>}
                  </div>
                  <button className="btn-secondary-ds artifact-expand-btn" type="button" onClick={() => void openFullViewer()}>
                    <Maximize2 size={14} />
                    Abrir leitura ampliada
                  </button>
                  <ArtifactContentBlock path={artifact.path} content={preview.content} />
                </>
              ) : null}
            </div>
          </section>
        </div>
      </aside>

      {viewerOpen ? (
        <>
          <div className="modal-overlay" onClick={() => setViewerOpen(false)} aria-hidden="true" />
          <section className="artifact-viewer-modal">
            <div className="event-modal-header">
              <div>
                <p className="task-id-cell">{artifact.artifact_type}</p>
                <h3 className="drawer-title">{artifact.name}</h3>
                <p className="artifact-drawer-path">{artifact.path}</p>
              </div>
              <button className="drawer-close" type="button" onClick={() => setViewerOpen(false)} aria-label="Fechar leitura ampliada">
                <X size={18} />
              </button>
            </div>
            <div className="artifact-viewer-body">
              {fullLoading ? <div className="state-loading">Carregando arquivo completo...</div> : null}
              {fullError ? <p className="error-text">{fullError}</p> : null}
              {!fullLoading && !fullError && activeContent ? (
                <>
                  <div className="artifact-preview-meta">
                    <span>{activeContent.encoding}</span>
                    <span>{activeContent.size_bytes} bytes</span>
                    {activeContent.truncated ? <span>visualização limitada</span> : <span>arquivo completo</span>}
                  </div>
                  <ArtifactContentBlock path={artifact.path} content={activeContent.content} />
                </>
              ) : null}
            </div>
          </section>
        </>
      ) : null}
    </>
  );
}
