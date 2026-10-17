import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { frameFixture, reportFixture } from "../protocol/fixtures";
import type { AnalysisSnapshot } from "./snapshot";
import { TreatmentsPage } from "./TreatmentsPage";

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
  const morning = within(screen.getByRole("region", { name: "Morning routine" }));
  const evening = within(screen.getByRole("region", { name: "Evening routine" }));
  expect(morning.getByText("Day care")).toBeVisible();
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
