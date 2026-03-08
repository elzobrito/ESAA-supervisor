import { useCallback, useEffect, useMemo, useState } from 'react';
import { Outlet, useParams, useSearchParams } from 'react-router-dom';
import { AppShell } from '../components/layout/AppShell';
import { extractErrorMessage } from '../services/api';
import { fetchProjectState, type StateResponse } from '../services/projects';
import { ProjectContext } from '../services/projectContext';

function roadmapStorageKey(projectId: string): string {
  return `esaa:selected-roadmap:${projectId}`;
}

function readStoredRoadmap(projectId: string): string | null {
  if (!projectId) return null;
  try {
    return sessionStorage.getItem(roadmapStorageKey(projectId));
  } catch {
    return null;
  }
}

function writeStoredRoadmap(projectId: string, roadmapId: string | null): void {
  if (!projectId) return;
  try {
    const key = roadmapStorageKey(projectId);
    if (!roadmapId || roadmapId === 'roadmap.json') {
      sessionStorage.removeItem(key);
      return;
    }
    sessionStorage.setItem(key, roadmapId);
  } catch {
    // ignore storage failures
  }
}

export function ProjectLayout() {
  const { projectId = '' } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const [state, setState] = useState<StateResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const urlRoadmapParam = searchParams.get('roadmap');
  const roadmapParam = urlRoadmapParam ?? readStoredRoadmap(projectId) ?? undefined;

  const reload = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await fetchProjectState(projectId, roadmapParam);
      setState(data);
      setError(null);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, [projectId, roadmapParam]);

  useEffect(() => {
    void reload();
  }, [reload]);

  useEffect(() => {
    if (!projectId) return;
    if (urlRoadmapParam) {
      writeStoredRoadmap(projectId, urlRoadmapParam);
      return;
    }
    const storedRoadmap = readStoredRoadmap(projectId);
    if (!storedRoadmap) return;
    const next = new URLSearchParams(searchParams);
    next.set('roadmap', storedRoadmap);
    setSearchParams(next, { replace: true });
  }, [projectId, searchParams, setSearchParams, urlRoadmapParam]);

  const eligibleCount = state?.eligible_task_ids.length ?? 0;
  const openIssuesCount = state?.open_issues.length ?? 0;
  const activeRunCount = state?.active_run_count ?? 0;
  const integrityMismatch = state !== null && !state.is_consistent;
  const navigationSearch = searchParams.toString();

  const ctx = useMemo(
    () => ({ state, isLoading, error, reload }),
    [state, isLoading, error, reload],
  );

  return (
    <ProjectContext.Provider value={ctx}>
      <AppShell
        projectId={projectId}
        projectName={state?.project.name}
        eligibleCount={eligibleCount}
        openIssuesCount={openIssuesCount}
        activeRunCount={activeRunCount}
        integrityMismatch={integrityMismatch}
        currentSearch={navigationSearch}
        availableRoadmaps={state?.available_roadmaps ?? []}
        selectedRoadmapId={state?.selected_roadmap_id ?? 'roadmap.json'}
        roadmapMode={state?.roadmap_mode ?? 'single'}
        onChangeRoadmap={(nextRoadmap) => {
          const next = new URLSearchParams(searchParams);
          if (!nextRoadmap || nextRoadmap === 'roadmap.json') {
            next.delete('roadmap');
            writeStoredRoadmap(projectId, null);
          } else {
            next.set('roadmap', nextRoadmap);
            writeStoredRoadmap(projectId, nextRoadmap);
          }
          setSearchParams(next, { replace: true });
        }}
      >
        <Outlet />
      </AppShell>
    </ProjectContext.Provider>
  );
}
