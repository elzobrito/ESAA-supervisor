import { useCallback, useEffect, useMemo, useState } from 'react';
import { Outlet, useParams, useSearchParams } from 'react-router-dom';
import { AppShell } from '../components/layout/AppShell';
import { fetchProjectState, type StateResponse } from '../services/projects';
import { ProjectContext } from '../services/projectContext';

export function ProjectLayout() {
  const { projectId = '' } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const [state, setState] = useState<StateResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const roadmapParam = searchParams.get('roadmap') ?? undefined;

  const reload = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await fetchProjectState(projectId, roadmapParam);
      setState(data);
      setError(null);
    } catch (err) {
      setError(String(err));
    } finally {
      setIsLoading(false);
    }
  }, [projectId, roadmapParam]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const eligibleCount = state?.eligible_task_ids.length ?? 0;
  const openIssuesCount = state?.open_issues.length ?? 0;
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
        integrityMismatch={integrityMismatch}
        currentSearch={navigationSearch}
        availableRoadmaps={state?.available_roadmaps ?? []}
        selectedRoadmapId={state?.selected_roadmap_id ?? 'roadmap.json'}
        roadmapMode={state?.roadmap_mode ?? 'single'}
        onChangeRoadmap={(nextRoadmap) => {
          const next = new URLSearchParams(searchParams);
          if (!nextRoadmap || nextRoadmap === 'roadmap.json') {
            next.delete('roadmap');
          } else {
            next.set('roadmap', nextRoadmap);
          }
          setSearchParams(next, { replace: true });
        }}
      >
        <Outlet />
      </AppShell>
    </ProjectContext.Provider>
  );
}
