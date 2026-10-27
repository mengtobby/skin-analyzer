import type { ButtonHTMLAttributes, ReactNode } from "react";
import "./Primitives.css";

export type IconButtonProps = Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'aria-label'> & { label: string; variant?: 'ink' | 'glass'; icon: ReactNode };
export function IconButton({ label, variant = 'ink', icon, className = '', type = 'button', ...props }: IconButtonProps) {
  return <button {...props} type={type} aria-label={label} className={`ui-icon-button ui-icon-button--${variant} ${className}`}><span aria-hidden="true">{icon}</span></button>;
}
export type ChipProps = Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'aria-pressed'> & { pressed: boolean; onPressedChange?: (next: boolean) => void };
export function Chip({ pressed, onPressedChange, onClick, className = '', type = 'button', children, ...props }: ChipProps) {
  return <button {...props} type={type} aria-pressed={pressed} className={`ui-chip ${className}`} onClick={event => { onClick?.(event); if (!event.defaultPrevented) onPressedChange?.(!pressed); }}>{children}</button>;
}
export function ChipGroup({ label, children }: { label: string; children: ReactNode }) {
  return <div role="group" aria-label={label} className="ui-chip-group">{children}</div>;
}
export type ScoreRingProps = { value: number | null; label: string; size?: number; decorative?: boolean; showValue?: boolean };
export function ScoreRing({ value, label, size = 112, decorative = false, showValue = true }: ScoreRingProps) {
  const score = value !== null && Number.isFinite(value) ? Math.min(100, Math.max(0, value)) : null;
  const dimension = Number.isFinite(size) && size > 0 ? size : 112;
  return <svg className="ui-score-ring" width={dimension} height={dimension} viewBox="0 0 100 100" role={decorative ? undefined : 'img'} aria-hidden={decorative || undefined} aria-label={decorative ? undefined : score === null ? `${label} unavailable` : `${label} ${score} out of 100`}>
    <circle className="ui-score-ring__track" cx="50" cy="50" r="42" />
    {score !== null && <circle className="ui-score-ring__arc" cx="50" cy="50" r="42" pathLength="100" strokeDasharray={`${score} 100`} transform="rotate(-90 50 50)" />}
    {showValue && <text x="50" y="50" dominantBaseline="central" textAnchor="middle">{score === null ? '\u2014' : `${score}%`}</text>}
  </svg>;
}
export type FloatingBadgeProps = { x: number; y: number; icon?: ReactNode; children: ReactNode; className?: string };
export function FloatingBadge({ x, y, icon, children, className = '' }: FloatingBadgeProps) {
  const position = (value: number) => `${Number.isFinite(value) ? Math.max(0, Math.min(100, value)) : 0}%`;
  return <span className={`ui-floating-badge ${className}`} style={{ left: position(x), top: position(y) }}>{icon && <span className="ui-floating-badge__icon" aria-hidden="true">{icon}</span>}{children}</span>;
}
