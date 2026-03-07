interface KpiCardProps {
  label: string;
  value: string | number;
  context?: string;
  variant?: 'default' | 'success' | 'warning' | 'error' | 'accent' | 'neutral' | 'live';
}

export function KpiCard({ label, value, context, variant = 'default' }: KpiCardProps) {
  const cls = variant === 'default' ? 'kpi-card' : `kpi-card kpi-${variant}`;
  return (
    <div className={cls}>
      <span className="kpi-label">{label}</span>
      <span className="kpi-value">{value}</span>
      {context && <span className="kpi-context">{context}</span>}
    </div>
  );
}
