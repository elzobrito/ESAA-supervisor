interface TaskStatusBadgeProps {
  status: string;
}

export function TaskStatusBadge({ status }: TaskStatusBadgeProps) {
  return <span className={`status-badge ${status}`}>{status}</span>;
}
