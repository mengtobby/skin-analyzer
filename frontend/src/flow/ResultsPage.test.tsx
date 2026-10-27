import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { frameFixture, reportFixture } from "../protocol/fixtures";
import { LABEL_INFO } from "../lib/blemishInfo";
import type { AnalysisSnapshot } from "./snapshot";
import { ResultsPage } from "./ResultsPage";
import { readFileSync } from "node:fs";
import { URL as NodeURL } from "node:url";

const resultsCss = readFileSync(new NodeURL("./results.css", import.meta.url), "utf-8");

function snapshot(): AnalysisSnapshot {
  const header = structuredClone(frameFixture);
  header.tracks.push({ ...header.tracks[0], id: 8, label: "comedone", zone: "left_cheek", bbox: [620, 340, 40, 40] });
  return { image: document.createElement("canvas"), width: 1280, height: 720, header,
    report: structuredClone(reportFixture), capturedAt: 1 };
}
beforeEach(() => {
  vi.spyOn(HTMLCanvasElement.prototype, "getContext")
    .mockReturnValue({ drawImage: vi.fn() } as unknown as CanvasRenderingContext2D);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });
it("positions every marker proportionally and shares selection with the grouped list", () => {
  render(<ResultsPage snapshot={snapshot()} onContinue={vi.fn()} onRetake={vi.fn()} />);
  const first = screen.getByRole("button", { name: "Papule 1, chin, details" });
  const second = screen.getByRole("button", { name: "Comedone 1, left cheek, details" });
  expect(screen.getByRole("status")).toBeEmptyDOMElement();
  expect(screen.getByRole("status")).toHaveAttribute("aria-live", "polite");
  expect(screen.getByRole("heading", { name: "All areas", level: 2 })).toBeInTheDocument();
  expect(screen.getByRole("img", { name: "Captured photo with 2 marked areas" })).toBeInTheDocument();
  const detail = screen.getByRole("region", { name: "Selected area details" });
  expect(first).toHaveAttribute("aria-controls", detail.id);
  expect(screen.getByRole("button", { name: "Papule 1, chin" })).toHaveAttribute("aria-controls", detail.id);
  expect(first).toHaveAttribute("aria-pressed", "true");
  expect(second).toHaveStyle({ left: "50%", top: "50%" });
  expect(first.style.left).toBe(`${130 / 1280 * 100}%`);
  expect(screen.getByText("Follicular inflammation")).toBeVisible();
  expect(screen.getByText("Occlusive products")).toBeVisible();
  expect(screen.getByText("Chin: monitor persistent irritation")).toBeVisible();
  expect(screen.getByText("4.2 mm")).toBeVisible();
  expect(within(detail).getByText("82%")).toBeVisible();
  fireEvent.click(second);
  expect(screen.getByRole("status")).toHaveTextContent("Showing Comedone 1, left cheek");
  expect(second).toHaveAttribute("aria-pressed", "true");
  expect(first).toHaveAttribute("aria-pressed", "false");
  expect(screen.getByText(LABEL_INFO.comedone.description)).toBeVisible();
  expect(screen.getByText(/There is no additional explanation/)).toBeVisible();
  expect(screen.getByRole("button", { name: "Comedone 1, left cheek" })).toHaveAttribute("aria-pressed", "true");
  fireEvent.click(screen.getByRole("button", { name: "Papule 1, chin" }));
  expect(first).toHaveAttribute("aria-pressed", "true");
  expect(screen.getByRole("status")).toHaveTextContent("Showing Papule 1, chin");
  expect(screen.getByText(LABEL_INFO.papule.description)).toBeVisible();
  expect(screen.getByText("Seek advice for persistent painful lesions.")).toBeVisible();
  expect(within(screen.getByRole("region", { name: "Overall skin scores" })).getAllByRole("heading")).toHaveLength(4);
  expect(screen.getByRole("heading", { name: "Redness" }).closest("section")).toHaveTextContent("41 / 100");
  expect(screen.getByRole("heading", { name: "Redness" }).closest("section")).not.toHaveAttribute("aria-label");
});
it("shows an empty state and scores, and invokes both actions", () => {
  const data = snapshot(); data.header.tracks = [];
  const onContinue = vi.fn(), onRetake = vi.fn();
  render(<ResultsPage snapshot={data} onContinue={onContinue} onRetake={onRetake} />);
  expect(screen.getByText("No blemishes stood out")).toBeVisible();
  expect(screen.getByRole("heading", { name: "Pigmentation" }).closest("section")).toHaveTextContent("18 / 100");
  fireEvent.click(screen.getByRole("button", { name: "Retake" }));
  fireEvent.click(screen.getByRole("button", { name: "See treatments" }));
  expect(onContinue).toHaveBeenCalledOnce(); expect(onRetake).toHaveBeenCalledOnce();
});
it("handles unavailable scores and image rendering failure", () => {
  vi.mocked(HTMLCanvasElement.prototype.getContext).mockReturnValue(null);
  const data = snapshot(); data.header.metrics = null;
  render(<ResultsPage snapshot={data} onContinue={vi.fn()} onRetake={vi.fn()} />);
  expect(screen.getAllByText("Score unavailable")).toHaveLength(4);
  const scores = screen.getByRole("region", { name: "Overall skin scores" });
  for (const heading of within(scores).getAllByRole("heading")) {
    const tile = heading.closest("section")!;
    expect(tile.querySelector(".skin-score-value")?.textContent).toBe("\u2014 / 100");
  }
  expect(screen.getAllByRole("status")[1]).toHaveTextContent("could not be displayed");
});

it("numbers repeated types consistently across markers and list items", () => {
  const data = snapshot();
  data.header.tracks.push({ ...data.header.tracks[0], id: 9 });
  render(<ResultsPage snapshot={data} onContinue={vi.fn()} onRetake={vi.fn()} />);
  const marker = screen.getByRole("button", { name: "Papule 2, chin, details" });
  fireEvent.click(screen.getByRole("button", { name: "Papule 2, chin" }));
  expect(marker).toHaveAttribute("aria-pressed", "true");
  expect(screen.getByRole("status")).toHaveTextContent("Showing Papule 2, chin");
});

it("limits marker motion and keeps a static size cue for selection", () => {
  expect(resultsCss).toMatch(/animation-iteration-count:\s*2/);
  expect(resultsCss).not.toMatch(/blemish-pulse[^;]*infinite/);
  expect(resultsCss).toMatch(/\[aria-pressed="true"\] span\s*\{[^}]*transform:\s*scale\(1\.25\)/);
  expect(resultsCss).toMatch(/prefers-reduced-motion:\s*reduce[^}]*animation:\s*none/);
});


it("filters markers and list groups, selects a visible area, and restores all areas", () => {
  render(<ResultsPage snapshot={snapshot()} onContinue={vi.fn()} onRetake={vi.fn()} />);
  const filters = within(screen.getByRole("group", { name: "Filter areas" }));
  expect(filters.getByRole("button", { name: "All" })).toHaveAttribute("aria-pressed", "true");
  fireEvent.click(filters.getByRole("button", { name: LABEL_INFO.comedone.plural }));
  expect(screen.getByRole("img", { name: "Captured photo with 1 marked areas" })).toBeVisible();
  expect(screen.queryByRole("button", { name: "Papule 1, chin, details" })).toBeNull();
  expect(screen.queryByRole("button", { name: "Papule 1, chin" })).toBeNull();
  expect(screen.queryByRole("heading", { name: /Papules/ })).toBeNull();
  expect(screen.getByRole("button", { name: "Comedone 1, left cheek, details" })).toHaveAttribute("aria-pressed", "true");
  expect(screen.getByRole("button", { name: "Comedone 1, left cheek" })).toHaveAttribute("aria-pressed", "true");
  fireEvent.click(filters.getByRole("button", { name: "All" }));
  expect(screen.getByRole("button", { name: "Papule 1, chin, details" })).toBeVisible();
  expect(screen.getByRole("heading", { name: "Papules (1)" })).toBeVisible();
  expect(screen.getByRole("button", { name: "Comedone 1, left cheek, details" })).toHaveAttribute("aria-pressed", "true");
});

it("shows the selected marker's real name and confidence in a floating badge", () => {
  const data = snapshot();
  data.header.tracks[1].confidence = 0.67;
  const { container } = render(<ResultsPage snapshot={data} onContinue={vi.fn()} onRetake={vi.fn()} />);
  const badge = container.querySelector(".selected-area-badge")!;
  expect(badge).toHaveTextContent("Papule 1, chin");
  expect(badge).toHaveTextContent("82%");
  fireEvent.click(screen.getByRole("button", { name: "Comedone 1, left cheek, details" }));
  expect(badge).toHaveTextContent("Comedone 1, left cheek");
  expect(badge).toHaveTextContent("67%");
  expect(within(screen.getByRole("region", { name: "Overall skin scores" })).queryByRole("img")).toBeNull();
  expect(screen.getByRole("heading", { name: "Redness" }).parentElement).toHaveTextContent("41 / 100");
});

it("renders the captured zone mesh beneath the interactive markers", () => {
  const data = snapshot();
  data.header.face = { bbox: [0, 0, 100, 100], zones: [{ zone: "chin", polygon: [[10, 10], [80, 10], [45, 80]] }] };
  const { container } = render(<ResultsPage snapshot={data} onContinue={vi.fn()} onRetake={vi.fn()} />);
  const mesh = container.querySelector(".scan-mesh")!;
  expect(mesh.closest("svg")).toHaveAttribute("aria-hidden", "true");
  expect(mesh.querySelectorAll("circle")).toHaveLength(22);
  expect(mesh.querySelectorAll("line")).toHaveLength(42);
  expect(resultsCss).toMatch(/\.scan-mesh line\s*\{[^}]*stroke-opacity: \.75;[^}]*stroke-dasharray: 3 4;/);
  expect(screen.getAllByRole("button", { name: /, details$/ })).toHaveLength(2);
});

it("keeps the type heading plain and actions in visual DOM order", () => {
  const { container } = render(<ResultsPage snapshot={snapshot()} onContinue={vi.fn()} onRetake={vi.fn()} />);
  const heading = screen.getByRole("heading", { name: "Papule", level: 2 });
  expect(heading).toHaveTextContent(/^Papule$/);
  expect(heading.querySelector(".ui-badge")).toBeNull();
  expect(container.querySelector(".result-actions")?.firstElementChild).toHaveTextContent("See treatments");
  expect(resultsCss).not.toMatch(/\border\s*:/);
});

it("places the selected badge outside the face with a leader to its marker", () => {
  const data = snapshot();
  data.header.face = { bbox: [300, 100, 600, 500], zones: [] };
  const { container } = render(<ResultsPage snapshot={data} onContinue={vi.fn()} onRetake={vi.fn()} />);
  const badge = container.querySelector<HTMLElement>(".selected-area-badge")!;
  expect(badge).toHaveClass("ui-floating-badge--left");
  expect(container.querySelector<HTMLElement>(".blemish-map")?.style.getPropertyValue("--badge-space")).toBe(`${288 / 1280 * 100}%`);
  expect(parseFloat(badge.style.left) / 100 * data.width).toBeLessThan(300);
  const leader = container.querySelector(".ui-floating-badge__leader line")!;
  expect(leader).toHaveAttribute("x2", `${130 / 1280 * 100}%`);
  fireEvent.click(screen.getByRole("button", { name: "Comedone 1, left cheek, details" }));
  expect(badge).toHaveClass("ui-floating-badge--right");
  expect(parseFloat(badge.style.left) / 100 * data.width).toBeGreaterThan(900);
});

it("hides Type, flattens measurements, and renders each score value only once", () => {
  const { container } = render(<ResultsPage snapshot={snapshot()} onContinue={vi.fn()} onRetake={vi.fn()} />);
  const detail = screen.getByRole("region", { name: "Selected area details" });
  expect(within(detail).getByText("Type")).toHaveClass("sr-only");
  const measurements = container.querySelector(".blemish-measurements")!;
  expect(measurements.querySelector(".ui-card")).toBeNull();
  expect(resultsCss).toMatch(/\.blemish-measurements > div\s*\{\s*flex: 1;\s*\}/);
  expect(resultsCss).toMatch(/\.analysis-results li::marker\s*\{\s*color: var\(--apricot\)/);
  const scores = screen.getByRole("region", { name: "Overall skin scores" });
  for (const heading of within(scores).getAllByRole("heading")) {
    const tile = heading.closest("section")!;
    expect(tile.querySelectorAll(".skin-score-value")).toHaveLength(1);
    expect(tile.textContent?.match(/\/ 100/g)).toHaveLength(1);
    expect(tile.querySelector("svg text")).toBeNull();
  }
});
