import type { ReactNode } from "react";
import "./Badge.css";

export type BadgeProps = { tone?: "neutral" | "accent" | "success" | "warning" | "dark"; icon?: ReactNode; children: ReactNode };
export function Badge({ tone = "neutral", icon, children }: BadgeProps) {
  return <span className={`ui-badge ui-badge--${tone}`}>{icon && <span className="ui-badge__icon" aria-hidden="true">{icon}</span>}{children}</span>;
}
