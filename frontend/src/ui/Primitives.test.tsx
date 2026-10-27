import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { Badge, Card, HomeIcon, Chip, ChipGroup, IconButton, ScoreRing, FloatingBadge } from "./index";

afterEach(cleanup);
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
