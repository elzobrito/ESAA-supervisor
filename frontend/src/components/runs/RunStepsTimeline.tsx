import type { RunState } from '../../services/runs';

interface RunStepsTimelineProps {
  run: RunState | null;
}

const STEPS = ['preflight', 'running', 'waiting_input', 'syncing', 'done'];

export function RunStepsTimeline({ run }: RunStepsTimelineProps) {
  const currentIndex = run ? STEPS.indexOf(run.status) : -1;

  return (
    <section className="run-steps-card">
      <h3 className="run-steps-title">Etapas da run</h3>
      <div className="steps-list">
        {STEPS.map((step, index) => {
          const className =
            run?.status === 'error'
              ? 'step-item step-error'
              : index < currentIndex
                ? 'step-item step-done'
                : index === currentIndex
                  ? 'step-item step-active'
                  : 'step-item';
          return (
            <div key={step} className={className}>
              {step}
            </div>
          );
        })}
      </div>
    </section>
  );
}
