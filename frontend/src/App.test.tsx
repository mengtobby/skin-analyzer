import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { frameFixture, reportFixture } from "./protocol/fixtures";
import type { Report } from "./protocol/types";
import App from "./App";

const state = vi.hoisted(() => ({ report: null as Report | null }));
vi.mock("./stream/useSkinStream", () => ({
  useSkinStream: () => ({
    bitmapRef: { current: null },
    headerRef: { current: frameFixture },
    displayHeaderRef: { current: frameFixture },
    header: frameFixture,
    report: state.report,
    health: null,
    connection: "connected",
    error: null,
    sendReset: vi.fn(),
  }),
}));
vi.mock("./components/StatusBar", () => ({ StatusBar: () => <div>Pipeline status</div> }));
vi.mock("./components/LiveView", () => ({ LiveView: () => <div>Camera view</div> }));

afterEach(cleanup);

it("freezes only the report and restores the latest report when unfrozen", () => {
  state.report = reportFixture;
  const { rerender } = render(<App />);
  const freeze = screen.getByRole("checkbox", { name: "Freeze report" });
  fireEvent.click(freeze);
  state.report = { ...reportFixture, disclaimer: "Latest disclaimer" };
  rerender(<App />);
  expect(screen.getByText(reportFixture.disclaimer)).toBeVisible();
  expect(screen.queryByText("Latest disclaimer")).toBeNull();
  expect(screen.getByRole("status")).toHaveTextContent("Report frozen");
  fireEvent.click(freeze);
  expect(screen.getByText("Latest disclaimer")).toBeVisible();
});

it("disables freezing until the first report arrives", () => {
  state.report = null;
  render(<App />);
  expect(screen.getByRole("checkbox", { name: "Freeze report" })).toBeDisabled();
});
