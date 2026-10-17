import type { HTMLAttributes, ReactNode } from "react";
import "./Card.css";

export type CardProps = { title?: ReactNode; action?: ReactNode; className?: string; children: ReactNode } & Omit<HTMLAttributes<HTMLElement>, "title">;

export function Card({ title, action, className = "", children, ...props }: CardProps) {
  return <section {...props} className={`ui-card ${className}`}>
    {(title != null || action != null) && <header className="ui-card__header">
      {title != null && <h2>{title}</h2>}{action}
    </header>}
    {children}
  </section>;
}
