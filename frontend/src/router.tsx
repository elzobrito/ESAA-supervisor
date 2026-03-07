import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';

import { ProjectLayout } from './pages/ProjectLayout';
import { ProjectsPage } from './pages/ProjectsPage';
import { OverviewPage } from './pages/OverviewPage';
import { TasksPage } from './pages/TasksPage';
import { RunsPage } from './pages/RunsPage';
import { ActivityPage } from './pages/ActivityPage';
import { ArtifactsPage } from './pages/ArtifactsPage';
import { ChatPage } from './pages/ChatPage';
import { IntegrityPage } from './pages/IntegrityPage';
import { IssuesPage } from './pages/IssuesPage';
import { LessonsPage } from './pages/LessonsPage';

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/projects" replace />} />
        <Route path="/projects" element={<ProjectsPage />} />
        <Route path="/projects/:projectId" element={<ProjectLayout />}>
          <Route index element={<OverviewPage />} />
          <Route path="tasks" element={<TasksPage />} />
          <Route path="runs" element={<RunsPage />} />
          <Route path="activity" element={<ActivityPage />} />
          <Route path="chat" element={<ChatPage />} />
          <Route path="artifacts" element={<ArtifactsPage />} />
          <Route path="integrity" element={<IntegrityPage />} />
          <Route path="issues" element={<IssuesPage />} />
          <Route path="lessons" element={<LessonsPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/projects" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
