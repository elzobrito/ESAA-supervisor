import { KpiCard } from '../components/dashboard/KpiCard';
import { NextEligibleTasksCard } from '../components/dashboard/NextEligibleTasksCard';
import { OpenProblemsCard } from '../components/dashboard/OpenProblemsCard';
import { OverviewCharts } from '../components/dashboard/OverviewCharts';
import { RecentActivitySummary } from '../components/dashboard/RecentActivitySummary';
import { useProject } from '../services/projectContext';

export function OverviewPage() {
  const { state, isLoading, error } = useProject();

  if (isLoading) return <div className="state-loading">Carregando visão geral...</div>;
  if (error || !state) return <div className="state-error">{error || 'Projeto indisponível.'}</div>;

  const done = state.tasks.filter((task) => task.status === 'done').length;
  const inProgress = state.tasks.filter((task) => task.status === 'in_progress').length;
  const blocked = state.tasks.filter((task) => !task.is_eligible && task.status !== 'done').length;

  return (
    <section>
      <h1 className="page-title">Visão Geral</h1>
      <p className="page-subtitle">Leitura executiva do projeto, integridade e próximos passos.</p>

      <div className="kpi-grid">
        <KpiCard label="Tasks Done" value={done} variant="success" />
        <KpiCard label="Em andamento" value={inProgress} variant="live" />
        <KpiCard label="Bloqueadas" value={blocked} variant={blocked > 0 ? 'warning' : 'neutral'} />
        <KpiCard label="Issues abertas" value={state.open_issues.length} variant={state.open_issues.length > 0 ? 'error' : 'neutral'} />
        <KpiCard label="Integridade" value={state.is_consistent ? 'OK' : 'Mismatch'} variant={state.is_consistent ? 'success' : 'error'} />
      </div>

      <OverviewCharts tasks={state.tasks} activity={state.activity} />

      <div className="overview-panels">
        <NextEligibleTasksCard tasks={state.tasks} />
        <OpenProblemsCard issues={state.open_issues} />
        <RecentActivitySummary activity={state.activity} />
      </div>
    </section>
  );
}
