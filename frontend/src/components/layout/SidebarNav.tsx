import {
  Activity,
  AlertTriangle,
  BookOpen,
  LayoutDashboard,
  ListChecks,
  Package,
  Play,
  ShieldCheck,
} from 'lucide-react';
import { NavLink, useParams } from 'react-router-dom';

interface SidebarNavProps {
  expanded: boolean;
  projectId: string;
  eligibleCount: number;
  openIssuesCount: number;
  hasActiveRun: boolean;
  integrityMismatch: boolean;
  currentSearch: string;
}

interface NavItem {
  to: string;
  icon: React.ElementType;
  label: string;
  badge?: number | string | null;
  badgeVariant?: 'default' | 'warn' | 'error' | 'live';
}

export function SidebarNav({
  expanded,
  projectId,
  eligibleCount,
  openIssuesCount,
  hasActiveRun,
  integrityMismatch,
  currentSearch,
}: SidebarNavProps) {
  const base = `/projects/${projectId}`;

  const items: NavItem[] = [
    {
      to: base,
      icon: LayoutDashboard,
      label: 'Visão Geral',
    },
    {
      to: `${base}/tasks`,
      icon: ListChecks,
      label: 'Tarefas',
      badge: eligibleCount > 0 ? eligibleCount : null,
    },
    {
      to: `${base}/runs`,
      icon: Play,
      label: 'Execução',
      badge: hasActiveRun ? 'AO VIVO' : null,
      badgeVariant: 'live',
    },
    {
      to: `${base}/activity`,
      icon: Activity,
      label: 'Atividade',
    },
    {
      to: `${base}/artifacts`,
      icon: Package,
      label: 'Artefatos',
      badge: integrityMismatch ? '!' : null,
      badgeVariant: 'warn',
    },
    {
      to: `${base}/integrity`,
      icon: ShieldCheck,
      label: 'Integridade',
      badge: integrityMismatch ? '!' : null,
      badgeVariant: 'warn',
    },
    {
      to: `${base}/issues`,
      icon: AlertTriangle,
      label: 'Problemas',
      badge: openIssuesCount > 0 ? openIssuesCount : null,
      badgeVariant: 'error',
    },
    {
      to: `${base}/lessons`,
      icon: BookOpen,
      label: 'Lições',
    },
  ];

  return (
    <nav className="sidebar-nav" aria-label="Navegação principal">
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={{ pathname: item.to, search: currentSearch ? `?${currentSearch}` : '' }}
          end={item.to === base}
          className={({ isActive }) =>
            `sidebar-nav-item${isActive ? ' active' : ''}`
          }
          title={!expanded ? item.label : undefined}
        >
          <item.icon className="sidebar-nav-item-icon" size={18} />
          <span className="sidebar-nav-item-label">{item.label}</span>
          {item.badge != null && (
            <span
              className={[
                'sidebar-nav-badge',
                item.badgeVariant === 'warn' ? 'badge-warn' : '',
                item.badgeVariant === 'error' ? 'badge-error' : '',
              ]
                .filter(Boolean)
                .join(' ')}
            >
              {item.badge}
            </span>
          )}
        </NavLink>
      ))}
    </nav>
  );
}
