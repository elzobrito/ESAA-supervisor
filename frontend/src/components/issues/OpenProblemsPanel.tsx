import { AlertTriangle } from 'lucide-react';

import type { IssueSummary } from '../../services/projects';

interface OpenProblemsPanelProps {
  issues: IssueSummary[];
  selectedIssueId: string | null;
  onSelectIssue: (issue: IssueSummary) => void;
}

function severityLabel(severity: string) {
  if (severity === 'high') return 'Alta';
  if (severity === 'medium') return 'Média';
  return 'Baixa';
}

function severityTone(severity: string) {
  if (severity === 'high') return 'severity-high';
  if (severity === 'medium') return 'severity-medium';
  return 'severity-low';
}

export function OpenProblemsPanel({ issues, selectedIssueId, onSelectIssue }: OpenProblemsPanelProps) {
  if (issues.length === 0) {
    return <div className="catalog-empty-state">Nenhum problema aberto no estado atual.</div>;
  }

  return (
    <div className="context-card-grid">
      {issues.map((issue) => (
        <button
          key={issue.issue_id}
          type="button"
          className={`context-card ${severityTone(issue.severity)} ${selectedIssueId === issue.issue_id ? 'context-card-selected' : ''}`}
          onClick={() => onSelectIssue(issue)}
        >
          <div className="context-card-header">
            <div className="context-card-title-wrap">
              <AlertTriangle size={16} />
              <strong>{issue.title}</strong>
            </div>
            <span className="task-id-cell">{issue.issue_id}</span>
          </div>
          <div className="context-card-meta">
            <span className={`severity-chip ${severityTone(issue.severity)}`}>{severityLabel(issue.severity)}</span>
            <span className="kind-badge">{issue.status}</span>
          </div>
          <p className="context-card-text">
            {issue.severity === 'high'
              ? 'Requer ação prioritária ou decisão explícita antes de confiar no próximo passo.'
              : 'Exige contexto adicional e acompanhamento na trilha operacional.'}
          </p>
        </button>
      ))}
    </div>
  );
}
