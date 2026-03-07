import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import type { Dispatch, ReactNode, SetStateAction } from 'react';
import { TopBar } from './TopBar';
import { SidebarNav } from './SidebarNav';
import type { LogEntry } from '../../services/logStream';
import type { StateResponse } from '../../services/projects';

/* ── Shell Context ─────────────────────────────────────── */

interface ShellContextValue {
  sidebarExpanded: boolean;
  toggleSidebar: () => void;
  selectedRunId: string | null;
  setSelectedRunId: Dispatch<SetStateAction<string | null>>;
  runLogsById: Record<string, LogEntry[]>;
  setRunLogsById: Dispatch<SetStateAction<Record<string, LogEntry[]>>>;
  runErrorsById: Record<string, string | null>;
  setRunErrorsById: Dispatch<SetStateAction<Record<string, string | null>>>;
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
  activeRunCount?: number;
  integrityMismatch?: boolean;
  currentSearch?: string;
  availableRoadmaps?: StateResponse['available_roadmaps'];
  selectedRoadmapId?: string;
  roadmapMode?: StateResponse['roadmap_mode'];
  onChangeRoadmap?: (roadmapId: string) => void;
}

const STORAGE_KEY = 'esaa-sidebar-expanded';

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
  activeRunCount = 0,
  integrityMismatch = false,
  currentSearch = '',
  availableRoadmaps = [],
  selectedRoadmapId = 'roadmap.json',
  roadmapMode = 'single',
  onChangeRoadmap,
}: AppShellProps) {
  const [sidebarExpanded, setSidebarExpanded] = useState<boolean>(readSidebarPref);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [runLogsById, setRunLogsById] = useState<Record<string, LogEntry[]>>({});
  const [runErrorsById, setRunErrorsById] = useState<Record<string, string | null>>({});
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
    setSelectedRunId(null);
    setRunLogsById({});
    setRunErrorsById({});
  }, [projectId]);

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
        selectedRunId,
        setSelectedRunId,
        runLogsById,
        setRunLogsById,
        runErrorsById,
        setRunErrorsById,
      }}
    >
      <div className={shellClass}>
        <TopBar
          projectName={projectName ?? projectId}
          integrityMismatch={integrityMismatch}
          activeRunCount={activeRunCount}
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
            activeRunCount={activeRunCount}
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
