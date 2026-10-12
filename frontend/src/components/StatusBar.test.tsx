import "@testing-library/jest-dom/vitest";
import { act, cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { StatusBar } from "./StatusBar";
import { frameFixture, healthFixture } from "../protocol/fixtures";

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

it("polls health every five seconds and shows provider chips and performance", async () => {
  vi.useFakeTimers();
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true, json: async () => ({ success: true, data: healthFixture, error: null }),
  });
  vi.stubGlobal("fetch", fetchMock);
  await act(async () => {
    render(<StatusBar connection="connected" header={frameFixture} health={null} />);
  });
  expect(screen.getByText("24.8 fps")).toBeVisible();
  expect(screen.getByText("31.2 ms latency")).toBeVisible();
  expect(screen.getByText("Detector: classical-cielab")).toBeVisible();
  expect(screen.getByText("Preprocessor: cpu")).toBeVisible();
  expect(screen.getByText("ONNX: CPUExecutionProvider")).toBeVisible();
  await act(async () => { vi.advanceTimersByTime(5000); });
  expect(fetchMock).toHaveBeenCalledTimes(2);
  cleanup();
  await act(async () => { vi.advanceTimersByTime(5000); });
  expect(fetchMock).toHaveBeenCalledTimes(2);
});

it("shows a failed health request without removing status information", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("Health unavailable")));
  await act(async () => {
    render(<StatusBar connection="reconnecting" header={null} health={healthFixture} />);
  });
  expect(screen.getByRole("status")).toHaveTextContent("Health unavailable");
  expect(screen.getByText("reconnecting")).toBeVisible();
});

it("hides stale performance after disconnect", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
    ok: true, json: async () => ({ success: true, data: healthFixture }),
  }));
  const { rerender } = render(<StatusBar connection="connected" header={frameFixture} health={null} />);
  await act(async () => {});
  rerender(<StatusBar connection="reconnecting" header={frameFixture} health={null} />);
  expect(screen.getByText("-- fps")).toBeVisible();
  expect(screen.getByText("-- ms latency")).toBeVisible();
});
