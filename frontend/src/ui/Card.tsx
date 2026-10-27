import type { HTMLAttributes, ReactNode } from "react";
import "./Card.css";

export type CardProps = { variant?: "glass" | "solid"; title?: ReactNode; headingLevel?: 2 | 3 | 4; action?: ReactNode; className?: string; children: ReactNode } & Omit<HTMLAttributes<HTMLElement>, "title">;

export function Card({ variant = "glass", title, headingLevel = 2, action, className = "", children, ...props }: CardProps) {
  const Heading = `h${headingLevel}` as 'h2' | 'h3' | 'h4';
  return <section {...props} className={`ui-card ui-card--${variant} ${className}`}>
    {(title != null || action != null) && <header className="ui-card__header">
      {title != null && <Heading>{title}</Heading>}{action}
    </header>}
    {children}
  </section>;
}
