import type { ReactNode } from "react";
import "./AppShell.css";

export type AppShellProps = {
  nav: { id: string; label: string; href: string; icon: ReactNode }[];
  active: string;
  right?: ReactNode;
  children: ReactNode;
};

export function AppShell({ nav, active, right, children }: AppShellProps) {
  return <div className="ui-shell">
    <header className="ui-shell__header">
      <a className="ui-shell__wordmark" href="#" aria-label="Skin Analyzer home"><span>skin</span>analyzer</a>
      <nav className="ui-shell__nav" aria-label="Main navigation">{nav.map(item =>
        <a key={item.id} href={item.href} aria-label={item.label} aria-current={item.id === active ? "page" : undefined}>
          <span className="ui-shell__icon" aria-hidden="true">{item.icon}</span><span className="ui-shell__label">{item.label}</span>
        </a>)}</nav>
      {right != null && <div className="ui-shell__right">{right}</div>}
    </header>
    <main className="ui-shell__main">{children}</main>
  </div>;
}
