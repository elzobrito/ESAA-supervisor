import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import type { Dispatch, ReactNode, SetStateAction } from 'react';
import { TopBar } from './TopBar';
import { SidebarNav } from './SidebarNav';
import type { RunState } from '../../services/runs';
import type { LogEntry } from '../../services/logStream';
import type { StateResponse } from '../../services/projects';

/* ── Shell Context ─────────────────────────────────────── */

interface ShellContextValue {
  sidebarExpanded: boolean;
  toggleSidebar: () => void;
  activeRun: RunState | null;
  setActiveRun: Dispatch<SetStateAction<RunState | null>>;
  activeRunLogs: LogEntry[];
  setActiveRunLogs: Dispatch<SetStateAction<LogEntry[]>>;
  activeRunError: string | null;
  setActiveRunError: Dispatch<SetStateAction<string | null>>;
}

const ShellContext = createContext<ShellContextValue | null>(null);

export function useShell(): ShellContextValue {
  const ctx = useContext(ShellContext);
  if (!ctx) throw new Error('useShell must be used inside AppShell');
  return ctx;
}

/* ── AppShell ──────────────────────────────────────────── */

interface AppShellProps {
  children: ReactNode;
  projectId: string;
  projectName?: string;
  eligibleCount?: number;
  openIssuesCount?: number;
  integrityMismatch?: boolean;
  currentSearch?: string;
  availableRoadmaps?: StateResponse['available_roadmaps'];
  selectedRoadmapId?: string;
  roadmapMode?: StateResponse['roadmap_mode'];
  onChangeRoadmap?: (roadmapId: string) => void;
}

const STORAGE_KEY = 'esaa-sidebar-expanded';
const TERMINAL_RUN_STATUSES = new Set(['done', 'error', 'cancelled']);

function readSidebarPref(): boolean {
  try {
    const val = localStorage.getItem(STORAGE_KEY);
    return val === null ? true : val === 'true';
  } catch {
    return true;
  }
}

export function AppShell({
  children,
  projectId,
  projectName,
  eligibleCount = 0,
  openIssuesCount = 0,
  integrityMismatch = false,
  currentSearch = '',
  availableRoadmaps = [],
  selectedRoadmapId = 'roadmap.json',
  roadmapMode = 'single',
  onChangeRoadmap,
}: AppShellProps) {
  const [sidebarExpanded, setSidebarExpanded] = useState<boolean>(readSidebarPref);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [activeRun, setActiveRun] = useState<RunState | null>(null);
  const [activeRunLogs, setActiveRunLogs] = useState<LogEntry[]>([]);
  const [activeRunError, setActiveRunError] = useState<string | null>(null);
  const sidebarRef = useRef<HTMLElement>(null);

  const toggleSidebar = useCallback(() => {
    if (typeof window !== 'undefined' && window.innerWidth <= 1023) {
      setMobileOpen((prev) => !prev);
      return;
    }
    setSidebarExpanded((prev) => {
      const next = !prev;
      try { localStorage.setItem(STORAGE_KEY, String(next)); } catch {}
      return next;
    });
  }, []);

  // Close mobile overlay on route change
  useEffect(() => {
    setMobileOpen(false);
  }, [projectId]);

  useEffect(() => {
    setActiveRun(null);
    setActiveRunLogs([]);
    setActiveRunError(null);
  }, [projectId]);

  const hasExecutingRun = activeRun !== null && !TERMINAL_RUN_STATUSES.has(activeRun.status);

  const shellClass = [
    'app-shell',
    !sidebarExpanded ? 'sidebar-collapsed' : '',
  ].filter(Boolean).join(' ');

  const sidebarClass = [
    'sidebar',
    !sidebarExpanded ? 'collapsed' : '',
    mobileOpen ? 'mobile-open' : '',
  ].filter(Boolean).join(' ');

  return (
    <ShellContext.Provider
      value={{
        sidebarExpanded,
        toggleSidebar,
        activeRun,
        setActiveRun,
        activeRunLogs,
        setActiveRunLogs,
        activeRunError,
        setActiveRunError,
      }}
    >
      <div className={shellClass}>
        <TopBar
          projectName={projectName ?? projectId}
          integrityMismatch={integrityMismatch}
          activeRun={activeRun}
          onToggleSidebar={toggleSidebar}
          availableRoadmaps={availableRoadmaps}
          selectedRoadmapId={selectedRoadmapId}
          roadmapMode={roadmapMode}
          onChangeRoadmap={onChangeRoadmap ?? (() => {})}
        />

        <aside ref={sidebarRef} className={sidebarClass}>
          <SidebarNav
            expanded={sidebarExpanded}
            projectId={projectId}
            eligibleCount={eligibleCount}
            openIssuesCount={openIssuesCount}
            hasActiveRun={hasExecutingRun}
            integrityMismatch={integrityMismatch}
            currentSearch={currentSearch}
          />
        </aside>

        {mobileOpen && (
          <div
            className="sidebar-overlay"
            onClick={() => setMobileOpen(false)}
            aria-hidden="true"
          />
        )}

        <main className="main-content">
          {children}
        </main>
      </div>
    </ShellContext.Provider>
  );
}
