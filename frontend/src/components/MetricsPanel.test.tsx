import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { MetricsPanel } from "./MetricsPanel";
import { frameFixture } from "../protocol/fixtures";

afterEach(cleanup);

it("renders all four metrics, gauges, histories, zones and confirmed counts", () => {
  render(<MetricsPanel header={frameFixture} />);
  for (const metric of ["41.2", "22.0", "35.5", "18.3"]) {
    expect(screen.getByText(metric)).toBeVisible();
  }
  expect(screen.getAllByRole("meter")).toHaveLength(4);
  expect(screen.getAllByRole("img")).toHaveLength(4);
  expect(within(screen.getByRole("table")).getByText("chin")).toBeVisible();
  expect(screen.getByText("papule").closest("li")).toHaveTextContent("1");
});

it("shows explicit unavailable metrics before frames arrive", () => {
  render(<MetricsPanel />);
  expect(screen.getAllByText("--")).toHaveLength(4);
  expect(screen.getByText(/Zone scores appear/)).toBeVisible();
});
