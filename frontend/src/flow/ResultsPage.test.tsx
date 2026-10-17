import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { frameFixture, reportFixture } from "../protocol/fixtures";
import { LABEL_INFO } from "../lib/blemishInfo";
import type { AnalysisSnapshot } from "./snapshot";
import { ResultsPage } from "./ResultsPage";

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
  const first = screen.getByRole("button", { name: "Papule on chin, details" });
  const second = screen.getByRole("button", { name: "Comedone on left cheek, details" });
  expect(first).toHaveAttribute("aria-pressed", "true");
  expect(second).toHaveStyle({ left: "50%", top: "50%" });
  expect(first.style.left).toBe(`${130 / 1280 * 100}%`);
  expect(screen.getByText("Follicular inflammation")).toBeVisible();
  expect(screen.getByText("Occlusive products")).toBeVisible();
  expect(screen.getByText("Chin: monitor persistent irritation")).toBeVisible();
  expect(screen.getByText("4.2 mm")).toBeVisible();
  expect(screen.getByText("82%")).toBeVisible();
  fireEvent.click(second);
  expect(second).toHaveAttribute("aria-pressed", "true");
  expect(first).toHaveAttribute("aria-pressed", "false");
  expect(screen.getByText(LABEL_INFO.comedone.description)).toBeVisible();
  expect(screen.getByText(/There is no additional explanation/)).toBeVisible();
  expect(screen.getByRole("button", { name: "Comedone 1 left cheek" })).toHaveAttribute("aria-pressed", "true");
  fireEvent.click(screen.getByRole("button", { name: "Papule 1 chin" }));
  expect(first).toHaveAttribute("aria-pressed", "true");
  expect(screen.getByText(LABEL_INFO.papule.description)).toBeVisible();
  expect(screen.getByText("Seek advice for persistent painful lesions.")).toBeVisible();
  expect(within(screen.getByRole("region", { name: "Overall skin scores" })).getAllByRole("heading")).toHaveLength(4);
  expect(screen.getByLabelText("Redness score")).toHaveTextContent("41 / 100");
});
it("shows an empty state and scores, and invokes both actions", () => {
  const data = snapshot(); data.header.tracks = [];
  const onContinue = vi.fn(), onRetake = vi.fn();
  render(<ResultsPage snapshot={data} onContinue={onContinue} onRetake={onRetake} />);
  expect(screen.getByText("No blemishes stood out")).toBeVisible();
  expect(screen.getByLabelText("Pigmentation score")).toHaveTextContent("18 / 100");
  fireEvent.click(screen.getByRole("button", { name: "Retake" }));
  fireEvent.click(screen.getByRole("button", { name: "See treatments" }));
  expect(onContinue).toHaveBeenCalledOnce(); expect(onRetake).toHaveBeenCalledOnce();
});
it("handles unavailable scores and image rendering failure", () => {
  vi.mocked(HTMLCanvasElement.prototype.getContext).mockReturnValue(null);
  const data = snapshot(); data.header.metrics = null;
  render(<ResultsPage snapshot={data} onContinue={vi.fn()} onRetake={vi.fn()} />);
  expect(screen.getAllByText("Score unavailable")).toHaveLength(4);
  expect(screen.getByRole("status")).toHaveTextContent("could not be displayed");
});
