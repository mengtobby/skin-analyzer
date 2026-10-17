import type { ReactNode } from "react";
import "./Badge.css";

export type BadgeProps = { tone?: "neutral" | "accent" | "success" | "warning"; children: ReactNode };
export function Badge({ tone = "neutral", children }: BadgeProps) {
  return <span className={`ui-badge ui-badge--${tone}`}>{children}</span>;
}
