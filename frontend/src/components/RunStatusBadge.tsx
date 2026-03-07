import React from 'react';

const STATUS_LABELS: Record<string, string> = {
  preflight: 'Preflight',
  running: 'Executando',
  syncing: 'Sincronizando',
  cancelling: 'Cancelando',
  cancelled: 'Cancelada',
  done: 'Concluído',
  error: 'Erro',
};

interface Props {
  status: string;
}

const RunStatusBadge: React.FC<Props> = ({ status }) => (
  <span className={`run-status-badge run-status-${status}`}>
    {STATUS_LABELS[status] ?? status}
  </span>
);

export default RunStatusBadge;
