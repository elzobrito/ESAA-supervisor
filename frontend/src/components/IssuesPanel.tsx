import React from 'react';
import { AlertCircle } from 'lucide-react';

interface Issue {
  issue_id: string;
  title: string;
  severity: string;
  status: string;
}

interface Props {
  issues: Issue[];
}

const IssuesPanel: React.FC<Props> = ({ issues }) => {
  const openIssues = issues.filter(i => i.status === 'open');

  return (
    <div className="panel issues-panel">
      <h3>Problemas em Aberto</h3>
      {openIssues.length === 0 ? (
        <p className="empty-msg">Nenhum problema detectado.</p>
      ) : (
        <ul className="issue-list">
          {openIssues.map(issue => (
            <li key={issue.issue_id} className={`issue-item sev-${issue.severity}`}>
              <AlertCircle size={14} />
              <span className="issue-title">{issue.title}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default IssuesPanel;
