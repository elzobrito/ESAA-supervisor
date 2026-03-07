import { createContext, useContext } from 'react';
import type { StateResponse } from './projects';

export interface ProjectContextValue {
  state: StateResponse | null;
  isLoading: boolean;
  error: string | null;
  reload: () => Promise<void>;
}

export const ProjectContext = createContext<ProjectContextValue | null>(null);

export function useProject(): ProjectContextValue {
  const ctx = useContext(ProjectContext);
  if (!ctx) throw new Error('useProject must be used inside ProjectLayout');
  return ctx;
}
