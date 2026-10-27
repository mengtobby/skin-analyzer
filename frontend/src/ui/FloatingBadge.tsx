import type { ReactNode } from 'react';
import './FloatingBadge.css';

export type FloatingBadgeProps = { x: number; y: number; icon?: ReactNode; children: ReactNode; className?: string; leader?: { x: number; y: number }; side?: 'left' | 'right' };

export function FloatingBadge({ x, y, icon, children, className = '', leader, side }: FloatingBadgeProps) {
  const position = (value: number) => Number.isFinite(value) ? Math.max(0, Math.min(100, value)) : 0;
  const left = position(x);
  const top = position(y);
  return <>
    {leader && Number.isFinite(leader.x) && Number.isFinite(leader.y) && <svg className="ui-floating-badge__leader" aria-hidden="true" focusable="false">
      <line x1={`${left}%`} y1={`${top}%`} x2={`${position(leader.x)}%`} y2={`${position(leader.y)}%`} />
      <circle cx={`${position(leader.x)}%`} cy={`${position(leader.y)}%`} r="3" />
    </svg>}
    <span className={`ui-floating-badge${side ? ` ui-floating-badge--${side}` : ''} ${className}`} style={{ left: `${left}%`, top: `${top}%` }}>{icon && <span className="ui-floating-badge__icon" aria-hidden="true">{icon}</span>}{children}</span>
  </>;
}
