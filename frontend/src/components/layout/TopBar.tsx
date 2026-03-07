import { Link } from 'react-router-dom';
import { ShieldAlert, ShieldCheck } from 'lucide-react';
import type { RunState } from '../../services/runs';
import type { StateResponse } from '../../services/projects';
import { SidebarToggle } from './SidebarToggle';

const TERMINAL_RUN_STATUSES = new Set(['done', 'error', 'cancelled']);

interface TopBarProps {
  projectName: string;
  integrityMismatch: boolean;
  activeRun: RunState | null;
  onToggleSidebar: () => void;
  availableRoadmaps: StateResponse['available_roadmaps'];
  selectedRoadmapId: string;
  roadmapMode: StateResponse['roadmap_mode'];
  onChangeRoadmap: (roadmapId: string) => void;
}

export function TopBar({
  projectName,
  integrityMismatch,
  activeRun,
  onToggleSidebar,
  availableRoadmaps,
  selectedRoadmapId,
  roadmapMode,
  onChangeRoadmap,
}: TopBarProps) {
  const hasExecutingRun = activeRun !== null && !TERMINAL_RUN_STATUSES.has(activeRun.status);

  return (
    <header className="topbar">
      <div className="topbar-left">
        <SidebarToggle onToggle={onToggleSidebar} />
        <span className="topbar-brand">ESAA</span>
        <span className="topbar-project-name">{projectName}</span>
      </div>

      <div className="topbar-spacer" />

      <div className="topbar-right">
        <label className="topbar-roadmap-switch">
          <select className="filter-select-ds" value={roadmapMode === 'aggregate' ? 'aggregate' : selectedRoadmapId} onChange={(event) => onChangeRoadmap(event.target.value)}>
            <option value="roadmap.json">Principal</option>
            {availableRoadmaps
              .filter((roadmap) => roadmap.roadmap_id !== 'roadmap.json')
              .map((roadmap) => (
                <option key={roadmap.roadmap_id} value={roadmap.roadmap_id}>
                  {roadmap.label}
                </option>
              ))}
            <option value="aggregate">Todos os roadmaps</option>
          </select>
        </label>

        <Link className="topbar-project-switch" to="/projects">
          Trocar projeto
        </Link>

        {integrityMismatch ? (
          <span className="topbar-badge-mismatch" title="Integridade divergente">
            <ShieldAlert size={12} style={{ display: 'inline', verticalAlign: 'middle' }} />
            {' '}Mismatch
          </span>
        ) : (
          <span className="topbar-badge-consistent" title="Integridade verificada">
            <ShieldCheck size={12} style={{ display: 'inline', verticalAlign: 'middle' }} />
            {' '}Consistente
          </span>
        )}

        {hasExecutingRun && (
          <span className="topbar-badge-running">
            Executando
          </span>
        )}
      </div>
    </header>
  );
}
