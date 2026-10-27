import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { Badge, Card, HomeIcon, Chip, ChipGroup, IconButton, ScoreRing, FloatingBadge } from "./index";
import { FloatingBadge as LinkedFloatingBadge } from './FloatingBadge';
import { readFileSync } from 'node:fs';
import { URL as NodeURL } from 'node:url';

afterEach(cleanup);
it('keeps stepper progress thin with softer tracks and peach current markers', () => {
  const css = readFileSync(new NodeURL('./Stepper.css', import.meta.url), 'utf8');
  expect(css).toMatch(/\.ui-stepper__segment \{[^}]*height: 4px;[^}]*color-mix\(in srgb, var\(--border\) 55%, transparent\)/);
  expect(css).toMatch(/\.ui-stepper__segment > span \{[^}]*background: var\(--ink\); opacity: \.85;/);
  expect(css).toMatch(/\.ui-stepper__marker > span \{[^}]*background: var\(--peach\)/);
});
it("renders a section with title, action and forwarded attributes", () => {
  render(<Card title={<span>Overview</span>} action={<button>Details</button>} className="custom" aria-label="Summary"><p>Analysis ready</p></Card>);
  const card = screen.getByRole("region", { name: "Summary" });
  expect(card.tagName).toBe("SECTION");
  expect(card).toHaveClass("ui-card", "custom");
  expect(screen.getByRole("heading", { name: "Overview", level: 2 })).toBeVisible();
  expect(screen.getByRole("button", { name: "Details" })).toBeVisible();
  expect(card).toHaveTextContent("Analysis ready");
});
it.each(["neutral", "accent", "success", "warning"] as const)("renders a %s badge", tone => {
  render(<Badge tone={tone}>Rx</Badge>);
  expect(screen.getByText("Rx")).toHaveClass(`ui-badge--${tone}`);
});
it("hides decorative icons and exposes titled icons", () => {
  const { container, rerender } = render(<HomeIcon />);
  expect(container.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
  rerender(<HomeIcon title="Home" className="custom-icon" />);
  expect(screen.getByRole("img", { name: "Home" })).toHaveClass("custom-icon");
  expect(screen.getByRole("img", { name: "Home" })).not.toHaveAttribute("aria-hidden");
});

it.each([2, 3, 4] as const)("renders card heading level %s", headingLevel => {
  render(<Card title="Overview" headingLevel={headingLevel}>Content</Card>);
  expect(screen.getByRole("heading", { name: "Overview", level: headingLevel })).toBeVisible();
});

it('exposes controlled chip selection in a labelled group', () => {
  const change = vi.fn();
  const { rerender } = render(<ChipGroup label="Metrics"><Chip pressed={false} onPressedChange={change}>All</Chip></ChipGroup>);
  expect(screen.getByRole('group', { name: 'Metrics' })).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: 'All' }));
  expect(change).toHaveBeenCalledWith(true);
  rerender(<Chip pressed onPressedChange={change}>All</Chip>);
  expect(screen.getByRole('button')).toHaveAttribute('aria-pressed', 'true');
  fireEvent.click(screen.getByRole('button'));
  expect(change).toHaveBeenLastCalledWith(false);
});
it('allows a chip click handler to prevent selection', () => {
  const change = vi.fn();
  render(<Chip pressed={false} onPressedChange={change} onClick={event => event.preventDefault()}>All</Chip>);
  fireEvent.click(screen.getByRole('button'));
  expect(change).not.toHaveBeenCalled();
});
it('names score rings and renders an empty track for unavailable data', () => {
  const { rerender } = render(<ScoreRing label="Redness" value={26} />);
  expect(screen.getByRole('img', { name: 'Redness 26 out of 100' })).toHaveTextContent('26');
  rerender(<ScoreRing label="Redness" value={null} />);
  expect(screen.getByRole('img', { name: 'Redness unavailable' })).toHaveTextContent('\u2014');
  expect(document.querySelector('.ui-score-ring__arc')).toBeNull();
  rerender(<ScoreRing label="Redness" value={150} decorative />);
  expect(screen.queryByRole('img')).not.toBeInTheDocument();
  expect(document.querySelector('.ui-score-ring')).toHaveTextContent('100');
});
it('renders dark badges, labelled icon buttons and positioned floating badges', () => {
  render(<><Badge tone="dark" icon={<HomeIcon />}>Ready</Badge><IconButton label="Continue" icon={<HomeIcon />} /><FloatingBadge x={25} y={60} icon={<HomeIcon />}>26</FloatingBadge></>);
  expect(screen.getByText('Ready')).toHaveClass('ui-badge--dark');
  expect(screen.getByRole('button', { name: 'Continue' })).toHaveClass('ui-icon-button--ink');
  expect(screen.getByText('26')).toHaveStyle({ left: '25%', top: '60%' });
});
it('renders a solid card variant', () => {
  render(<Card variant="solid">Content</Card>);
  expect(screen.getByText('Content')).toHaveClass('ui-card--solid');
});

it('draws a decorative leader and dot in the same container coordinates', () => {
  const { container, rerender } = render(<LinkedFloatingBadge x={20} y={40} side="left" leader={{ x: 45, y: 60 }}>26</LinkedFloatingBadge>);
  expect(screen.getByText('26')).toHaveClass('ui-floating-badge--left');
  expect(screen.getByText('26')).toHaveStyle({ left: '20%', top: '40%' });
  const svg = container.querySelector('svg');
  expect(svg).toHaveAttribute('aria-hidden', 'true');
  expect(svg).toHaveAttribute('focusable', 'false');
  expect(svg?.querySelector('line')).toHaveAttribute('x1', '20%');
  expect(svg?.querySelector('line')).toHaveAttribute('y1', '40%');
  expect(svg?.querySelector('line')).toHaveAttribute('x2', '45%');
  expect(svg?.querySelector('line')).toHaveAttribute('y2', '60%');
  expect(svg?.querySelector('circle')).toHaveAttribute('r', '3');
  expect(svg?.querySelector('circle')).toHaveAttribute('cx', '45%');
  expect(svg?.querySelector('circle')).toHaveAttribute('cy', '60%');
  rerender(<LinkedFloatingBadge x={130} y={NaN} side="right">26</LinkedFloatingBadge>);
  expect(container.querySelector('svg')).toBeNull();
  expect(screen.getByText('26')).toHaveClass('ui-floating-badge--right');
  expect(screen.getByText('26')).toHaveStyle({ left: '100%', top: '0%' });
  rerender(<LinkedFloatingBadge x={20} y={40} leader={{ x: Infinity, y: 60 }}>26</LinkedFloatingBadge>);
  expect(container.querySelector('svg')).toBeNull();
});

it('omits all SVG text when the decorative score value is disabled', () => {
  const { container, rerender } = render(<ScoreRing value={41} label="Redness" decorative showValue={false} />);
  expect(container.querySelector('svg')).toHaveAttribute('aria-hidden', 'true');
  expect(container.querySelector('text')).toBeNull();
  rerender(<ScoreRing value={null} label="Redness" decorative showValue={false} />);
  expect(container.querySelector('text')).toBeNull();
  const css = readFileSync(new NodeURL('./Primitives.css', import.meta.url), 'utf8');
  expect(css).toMatch(/__track\s*\{\s*stroke: var\(--ring-track\)/);
  expect(css).toMatch(/__arc\s*\{\s*stroke: var\(--apricot\); stroke-linecap: round/);
});
