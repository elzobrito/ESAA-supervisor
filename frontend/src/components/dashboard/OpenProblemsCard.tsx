import type { IssueSummary } from '../../services/projects';

interface OpenProblemsCardProps {
  issues: IssueSummary[];
}

export function OpenProblemsCard({ issues }: OpenProblemsCardProps) {
  const topIssues = issues.slice(0, 4);

  return (
    <section className="panel-card">
      <div className="panel-card-header">
        <h3 className="panel-card-title">Problemas em aberto</h3>
      </div>
      <div className="panel-card-body">
        {topIssues.length === 0 ? (
          <p className="panel-empty">Nenhum problema aberto.</p>
        ) : (
          topIssues.map((issue) => (
            <article key={issue.issue_id} className={`issue-item sev-${issue.severity}`}>
              <span className="issue-item-title">{issue.title}</span>
              <span className="issue-item-sev">
                {issue.issue_id} · {issue.severity}
              </span>
            </article>
          ))
        )}
      </div>
    </section>
  );
}
