import "@testing-library/jest-dom/vitest";
import { useEffect } from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { frameFixture, reportFixture } from "./protocol/fixtures";
import type { Report } from "./protocol/types";
import App from "./App";

const state = vi.hoisted(() => ({ report: null as Report | null, mounts: 0 }));
vi.mock("./stream/useSkinStream", () => ({
  useSkinStream: () => {
    useEffect(() => { state.mounts += 1; }, []);
    return ({
    bitmapRef: { current: null },
    headerRef: { current: frameFixture },
    displayHeaderRef: { current: frameFixture },
    header: frameFixture,
    report: state.report,
    health: null,
    connection: "connected",
    error: null,
    sendReset: vi.fn(),
  }); },
}));
vi.mock("./components/StatusBar", () => ({ StatusBar: () => <div>Pipeline status</div> }));
vi.mock("./components/LiveView", () => ({ LiveView: () => <div>Camera view</div> }));

vi.mock("./settings/SettingsPage", () => ({ SettingsPage: () => <div>Camera input settings</div> }));
afterEach(() => { cleanup(); window.history.replaceState(null, "", "/"); });

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

it("switches tabs with arrow keys and preserves dashboard content", () => {
  render(<App />);
  const mounts = state.mounts;
  const dashboard = screen.getByRole("tab", { name: "Dashboard" });
  fireEvent.keyDown(dashboard, { key: "ArrowRight" });
  const settings = screen.getByRole("tab", { name: "Settings" });
  expect(settings).toHaveFocus();
  expect(settings).toHaveAttribute("aria-selected", "true");
  expect(window.location.hash).toBe("#settings");
  expect(screen.getByRole("tabpanel", { name: "Settings" })).toHaveTextContent("Camera input settings");
  expect(screen.getByText("Camera view")).not.toBeVisible();
  fireEvent.keyDown(settings, { key: "ArrowLeft" });
  expect(dashboard).toHaveFocus();
  expect(screen.getByText("Camera view")).toBeVisible();
  expect(state.mounts).toBe(mounts);
});

it("opens settings from the hash and responds to hash navigation", () => {
  window.history.replaceState(null, "", "/#settings");
  render(<App />);
  expect(screen.getByRole("tab", { name: "Settings" })).toHaveAttribute("aria-selected", "true");
  window.history.replaceState(null, "", "/");
  fireEvent(window, new Event("hashchange"));
  expect(screen.getByRole("tab", { name: "Dashboard" })).toHaveAttribute("aria-selected", "true");
});
