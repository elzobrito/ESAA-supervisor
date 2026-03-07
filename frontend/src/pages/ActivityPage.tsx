import { ActivityTimeline } from '../components/activity/ActivityTimeline';
import { useProject } from '../services/projectContext';

export function ActivityPage() {
  const { state, isLoading, error } = useProject();

  if (isLoading) return <div className="state-loading">Carregando atividade...</div>;
  if (error || !state) return <div className="state-error">{error || 'Projeto indisponível.'}</div>;

  return (
    <section className="activity-page">
      <h1 className="page-title">Atividade</h1>
      <p className="page-subtitle">
        Timeline operacional com leitura rápida, diferenciação semântica e inspeção detalhada de payload.
      </p>
      <ActivityTimeline events={state.activity} />
    </section>
  );
}
