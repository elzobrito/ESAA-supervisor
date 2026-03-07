import { PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import { useShell } from './AppShell';

interface SidebarToggleProps {
  onToggle: () => void;
}

export function SidebarToggle({ onToggle }: SidebarToggleProps) {
  const { sidebarExpanded } = useShell();
  const Icon = sidebarExpanded ? PanelLeftClose : PanelLeftOpen;

  return (
    <button
      className="sidebar-toggle-btn"
      onClick={onToggle}
      aria-label={sidebarExpanded ? 'Recolher menu' : 'Expandir menu'}
      title={sidebarExpanded ? 'Recolher menu' : 'Expandir menu'}
    >
      <Icon size={18} />
    </button>
  );
}
