import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { extractErrorMessage } from '../services/api';
import {
  browseProjects,
  fetchProjects,
  openProject,
  type FileSystemEntry,
  type ProjectBrowserResponse,
  type ProjectMetadata,
} from '../services/projects';

export function ProjectsPage() {
  const [projects, setProjects] = useState<ProjectMetadata[]>([]);
  const [browser, setBrowser] = useState<ProjectBrowserResponse | null>(null);
  const [isLoadingBrowser, setIsLoadingBrowser] = useState(false);
  const [openingPath, setOpeningPath] = useState<string | null>(null);
  const [pathInput, setPathInput] = useState('');
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  async function loadBrowser(path?: string) {
    setIsLoadingBrowser(true);
    try {
      setBrowser(await browseProjects(path));
      setPathInput(path ?? '');
      setError(null);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setIsLoadingBrowser(false);
    }
  }

  useEffect(() => {
    void (async () => {
      try {
        setProjects(await fetchProjects());
        await loadBrowser();
      } catch (err) {
        setError(extractErrorMessage(err));
      }
    })();
  }, []);

  useEffect(() => {
    if (browser?.current_path) {
      setPathInput(browser.current_path);
    }
  }, [browser?.current_path]);

  async function handleOpenProject(path: string) {
    try {
      setOpeningPath(path);
      const project = await openProject(path);
      navigate(`/projects/${project.id}`);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setOpeningPath(null);
    }
  }

  return (
    <div className="projects-page">
      <header className="projects-header">
        <p className="projects-eyebrow">ESAA Supervisor</p>
        <h1 className="projects-title">Escolha um projeto para abrir</h1>
      </header>
      {error ? <p className="error-text">{error}</p> : null}

      <section className="project-browser-card">
        <div className="section-header">
          <div>
            <h2 className="section-title">Navegador de pastas</h2>
            <p className="project-browser-path">{browser?.current_path ?? 'Carregando diretório...'}</p>
          </div>
          <div className="project-browser-actions">
            <button className="btn-secondary-ds" type="button" onClick={() => void loadBrowser()}>
              Ir para raiz
            </button>
            {browser?.parent_path ? (
              <button className="btn-secondary-ds" type="button" onClick={() => void loadBrowser(browser.parent_path ?? undefined)}>
                Voltar pasta
              </button>
            ) : null}
          </div>
        </div>

        <div className="project-browser-manual">
          <input
            className="filter-input-ds"
            type="text"
            value={pathInput}
            placeholder="Digite um caminho completo, ex.: C:\\Users\\..."
            onChange={(event) => setPathInput(event.target.value)}
          />
          <button className="btn-primary-ds" type="button" onClick={() => void loadBrowser(pathInput || undefined)}>
            Abrir pasta
          </button>
        </div>

        <div className="project-browser-grid">
          <div className="project-browser-column">
            <h3 className="project-browser-title">Pastas</h3>
            {isLoadingBrowser ? (
              <p className="panel-empty">Carregando pastas...</p>
            ) : browser?.directories.length ? (
              browser.directories.map((directory: FileSystemEntry) => (
                <button
                  key={directory.path}
                  className="browser-entry-button"
                  type="button"
                  onClick={() => void loadBrowser(directory.path)}
                >
                  <span className="browser-entry-name">{directory.name}</span>
                  <span className="browser-entry-path">{directory.path}</span>
                </button>
              ))
            ) : (
              <p className="panel-empty">Nenhuma subpasta navegável aqui.</p>
            )}
          </div>

          <div className="project-browser-column">
            <h3 className="project-browser-title">Projetos detectados</h3>
            {browser?.projects.length ? (
              browser.projects.map((project) => {
                const targetPath = project.project_path ?? project.base_path ?? '';
                return (
                  <article className="project-card browser-project-card" key={`${project.id}-${project.base_path}`}>
                    <p className="project-card-id">{project.id}</p>
                    <h2 className="project-card-name">{project.name}</h2>
                    {project.project_path ? <p className="project-card-path">{project.project_path}</p> : null}
                    <button
                      className="project-card-link"
                      type="button"
                      onClick={() => void handleOpenProject(targetPath)}
                      disabled={openingPath === targetPath}
                    >
                      {openingPath === targetPath ? 'Abrindo...' : 'Abrir projeto'}
                    </button>
                  </article>
                );
              })
            ) : (
              <p className="panel-empty">Nenhum projeto com `.roadmap/roadmap.json` foi encontrado nesta pasta.</p>
            )}
          </div>
        </div>
      </section>

      <div className="projects-grid">
        {projects.map((project) => {
          const targetPath = project.project_path ?? project.base_path ?? '';
          return (
            <article className="project-card" key={project.id}>
              <p className="project-card-id">{project.id}</p>
              <h2 className="project-card-name">{project.name}</h2>
              {project.project_path ? <p className="project-card-path">{project.project_path}</p> : null}
              <button
                className="project-card-link"
                type="button"
                onClick={() => void handleOpenProject(targetPath)}
                disabled={openingPath === targetPath}
              >
                {openingPath === targetPath ? 'Abrindo...' : 'Abrir projeto'}
              </button>
            </article>
          );
        })}
      </div>
    </div>
  );
}
