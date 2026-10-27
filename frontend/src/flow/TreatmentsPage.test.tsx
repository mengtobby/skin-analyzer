import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { frameFixture, reportFixture } from "../protocol/fixtures";
import type { AnalysisSnapshot } from "./snapshot";
import { TreatmentsPage } from "./TreatmentsPage";
import { readFileSync } from "node:fs";
import { URL as NodeURL } from "node:url";

afterEach(cleanup);
function snapshot(): AnalysisSnapshot {
  return { image: document.createElement("canvas"), width: 1280, height: 720,
    header: structuredClone(frameFixture), report: structuredClone(reportFixture), capturedAt: 1 };
}
it("groups AM and PM products, placing shared products in both routines", () => {
  const data = snapshot();
  data.report.products.push({ ...data.report.products[0], id: "day", name: "Day care", routine: "AM" },
    { ...data.report.products[0], id: "night", name: "Night care", routine: "PM" });
  render(<TreatmentsPage snapshot={data} onBack={vi.fn()} onRestart={vi.fn()} />);
  expect(screen.getByRole("heading", { name: data.report.ingredients[0].name, level: 3 })).toBeVisible();
  const morning = within(screen.getByRole("region", { name: "Morning routine" }));
  const evening = within(screen.getByRole("region", { name: "Evening routine" }));
  expect(morning.getByRole("heading", { name: "Day care", level: 4 })).toBeVisible();
  expect(morning.queryByText("Night care")).toBeNull();
  expect(evening.getByText("Night care")).toBeVisible();
  expect(evening.queryByText("Day care")).toBeNull();
  expect(morning.getByText("Gentle cleanser")).toBeVisible();
  expect(evening.getByText("Gentle cleanser")).toBeVisible();
  expect(morning.getAllByText("Glycerin")).toHaveLength(2);
  expect(screen.getByText("Introduce gradually")).toBeVisible();
  expect(screen.getByRole("progressbar")).toHaveAttribute("value", "80");
  expect(screen.getByLabelText("Routine warnings")).toHaveTextContent(data.report.warnings[0]);
  expect(screen.getByLabelText("Disclaimer")).toHaveTextContent(data.report.disclaimer);
});
it("renders an empty state, retains disclaimer, and invokes actions", () => {
  const data = snapshot(); data.report.ingredients = []; data.report.products = [];
  const onBack = vi.fn(), onRestart = vi.fn();
  render(<TreatmentsPage snapshot={data} onBack={onBack} onRestart={onRestart} />);
  expect(screen.getByText("No recommendations yet")).toBeVisible();
  expect(screen.getByLabelText("Disclaimer")).toHaveTextContent(data.report.disclaimer);
  fireEvent.click(screen.getByRole("button", { name: "Back to results" }));
  fireEvent.click(screen.getByRole("button", { name: "Start a new analysis" }));
  expect(onBack).toHaveBeenCalledOnce(); expect(onRestart).toHaveBeenCalledOnce();
});
it("explains an empty routine when only morning products are suggested", () => {
  const data = snapshot(); data.report.products[0].routine = "AM";
  render(<TreatmentsPage snapshot={data} onBack={vi.fn()} onRestart={vi.fn()} />);
  expect(within(screen.getByRole("region", { name: "Evening routine" })).getByText("No products suggested for this routine.")).toBeVisible();
});

it("lists multi-condition rationales separately and shows shared cautions once", () => {
  const s = snapshot();
  const general = "Introduce one new active at a time and stop if persistent irritation occurs.";
  s.report.ingredients = [
    { id: "azelaic", name: "Azelaic acid", score: 0.9, cautions: ["Temporary stinging can occur.", general],
      rationale: "Post-inflammatory erythema: May support marks; redness varies.; Inflammatory acne: Supports acne." },
    { id: "niacinamide", name: "Niacinamide", score: 0.7, cautions: [general],
      rationale: "Hyperpigmentation: May reduce uneven pigmentation." },
  ];
  render(<TreatmentsPage snapshot={s} onBack={vi.fn()} onRestart={vi.fn()} />);
  const azelaic = screen.getByRole("heading", { name: "Azelaic acid" }).closest("section")!;
  const reasons = within(azelaic).getAllByRole("listitem").map((item) => item.textContent);
  expect(reasons).toEqual(["Post-inflammatory erythema: May support marks; redness varies.", "Inflammatory acne: Supports acne."]);
  expect(screen.queryByText(/\.;/)).toBeNull();
  expect(screen.getAllByText(general)).toHaveLength(1);
  expect(within(azelaic).getByText("Temporary stinging can occur.")).toBeVisible();
});

it("keeps the ingredient match accessible alongside its donut gauge", () => {
  const data = snapshot();
  const { container } = render(<TreatmentsPage snapshot={data} onBack={vi.fn()} onRestart={vi.fn()} />);
  expect(screen.getByRole("progressbar", { name: data.report.ingredients[0].name + " recommendation match" })).toHaveAttribute("value", "80");
  expect(container.querySelector(".ingredient-score .ui-score-ring")).toHaveAttribute("aria-hidden", "true");
});

it("shows a single percentage inside the ring and keeps native progress at one pixel", () => {
  const data = snapshot();
  const { container } = render(<TreatmentsPage snapshot={data} onBack={vi.fn()} onRestart={vi.fn()} />);
  const progress = screen.getByRole("progressbar", { name: data.report.ingredients[0].name + " recommendation match" });
  expect(progress).toHaveClass("sr-only");
  expect(container.querySelector(".ingredient-header .ui-score-ring text")).toHaveTextContent(/^80%$/);
  expect(container.querySelector(".ingredient-score")?.children).toHaveLength(2);
  const css = readFileSync(new NodeURL("./results.css", import.meta.url), "utf-8");
  expect(css).not.toMatch(/\.analysis-results progress\s*\{/);
  expect(css).toMatch(/progress:not\(\.sr-only\)\s*\{/);
  expect(css).toMatch(/progress\.sr-only\s*\{\s*width: 1px; height: 1px;/);
  expect(container.querySelectorAll(".ingredient-header .ui-score-ring text")).toHaveLength(data.report.ingredients.length);
  expect(css).toMatch(/\.analysis-results \.ingredient-header h3\s*\{\s*margin: 0; font-size: 1\.25rem; font-weight: 600;/);
  expect(screen.getByRole("heading", { name: data.report.ingredients[0].name }).closest("header")?.querySelector(".ui-score-ring")).toBeInTheDocument();
});


it("uses the same reason list for single and multiple rationales", () => {
  const data = snapshot();
  render(<TreatmentsPage snapshot={data} onBack={vi.fn()} onRestart={vi.fn()} />);
  const card = screen.getByRole("heading", { name: data.report.ingredients[0].name }).closest("section")!;
  expect(card.querySelector(".ingredient-reasons > li")).toHaveTextContent(data.report.ingredients[0].rationale);
});
