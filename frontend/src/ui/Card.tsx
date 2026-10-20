import type { HTMLAttributes, ReactNode } from "react";
import "./Card.css";

export type CardProps = { title?: ReactNode; headingLevel?: 2 | 3 | 4; action?: ReactNode; className?: string; children: ReactNode } & Omit<HTMLAttributes<HTMLElement>, "title">;

export function Card({ title, headingLevel = 2, action, className = "", children, ...props }: CardProps) {
  const Heading = `h${headingLevel}` as 'h2' | 'h3' | 'h4';
  return <section {...props} className={`ui-card ${className}`}>
    {(title != null || action != null) && <header className="ui-card__header">
      {title != null && <Heading>{title}</Heading>}{action}
    </header>}
    {children}
  </section>;
}
