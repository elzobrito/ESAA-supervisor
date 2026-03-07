import { useState } from 'react';

import { IssueDetailModal } from '../components/issues/IssueDetailModal';
import { OpenProblemsPanel } from '../components/issues/OpenProblemsPanel';
import { extractErrorMessage } from '../services/api';
import { useProject } from '../services/projectContext';
import { resolveIssue } from '../services/projects';

export function IssuesPage() {
  const { state, isLoading, error, reload } = useProject();
  const [selectedIssueId, setSelectedIssueId] = useState<string | null>(null);
  const [mutationError, setMutationError] = useState<string | null>(null);
  const [isResolving, setIsResolving] = useState(false);

  if (isLoading) return <div className="state-loading">Carregando issues...</div>;
  if (error || !state) return <div className="state-error">{error || 'Projeto indisponível.'}</div>;

  const projectState = state;
  const selectedIssue = projectState.open_issues.find((issue) => issue.issue_id === selectedIssueId) ?? null;

  async function handleResolveIssue() {
    if (!selectedIssue) {
      return;
    }
    setMutationError(null);
    setIsResolving(true);
    try {
      await resolveIssue(projectState.project.id, selectedIssue.issue_id);
      await reload();
      setSelectedIssueId(null);
    } catch (err) {
      setMutationError(extractErrorMessage(err));
    } finally {
      setIsResolving(false);
    }
  }

  return (
    <section>
      <h1 className="page-title">Problemas</h1>
      <p className="page-subtitle">
        Superfície contextual para inspeção de severidade, impacto e prioridade dos problemas abertos.
      </p>
      <div className="activity-hero-grid">
        <div className="catalog-summary-card">
          <span className="catalog-summary-label">Problemas abertos</span>
          <strong>{state.open_issues.length}</strong>
        </div>
        <div className="catalog-summary-card">
          <span className="catalog-summary-label">Alta severidade</span>
          <strong>{projectState.open_issues.filter((issue) => issue.severity === 'high').length}</strong>
        </div>
        <div className="catalog-summary-card">
          <span className="catalog-summary-label">Média severidade</span>
          <strong>{projectState.open_issues.filter((issue) => issue.severity === 'medium').length}</strong>
        </div>
        <div className="catalog-summary-card">
          <span className="catalog-summary-label">Baixa severidade</span>
          <strong>{projectState.open_issues.filter((issue) => issue.severity === 'low').length}</strong>
        </div>
      </div>
      <OpenProblemsPanel
        issues={projectState.open_issues}
        selectedIssueId={selectedIssueId}
        onSelectIssue={(issue) => setSelectedIssueId(issue.issue_id)}
      />
      {mutationError ? <p className="error-text">{mutationError}</p> : null}
      <IssueDetailModal
        issue={selectedIssue}
        open={selectedIssue !== null}
        onClose={() => setSelectedIssueId(null)}
        onResolve={() => void handleResolveIssue()}
        isResolving={isResolving}
      />
    </section>
  );
}
