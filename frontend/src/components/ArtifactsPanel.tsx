import React from 'react';
import { BookOpen, FileCode, Settings, ShieldCheck } from 'lucide-react';

interface Artifact {
  name: string;
  path: string;
  role: string;
  category: string;
  integrity_status: string;
}

interface Props {
  artifacts: Artifact[];
}

const ArtifactsPanel: React.FC<Props> = ({ artifacts }) => {
  return (
    <div className="panel artifacts-panel">
      <h3>Artefatos Canônicos</h3>
      <ul className="artifact-list">
        {artifacts.map((art) => (
          <li key={art.path} className={`artifact-item ${art.integrity_status}`}>
            <span className="artifact-icon">
              {art.category === 'contract' ? (
                <ShieldCheck size={16} />
              ) : art.category === 'policy' ? (
                <Settings size={16} />
              ) : art.category === 'profile' ? (
                <BookOpen size={16} />
              ) : (
                <FileCode size={16} />
              )}
            </span>
            <div className="artifact-info">
              <span className="file-name">{art.name}</span>
              <span className="artifact-path">{art.path}</span>
              <span className="role-badge">{art.role}</span>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default ArtifactsPanel;
