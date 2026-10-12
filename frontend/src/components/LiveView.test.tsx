import "@testing-library/jest-dom/vitest";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { LiveView } from "./LiveView";
import { frameFixture, qualityFixture } from "../protocol/fixtures";

beforeEach(() => {
  vi.stubGlobal("requestAnimationFrame", vi.fn(() => 1));
  vi.stubGlobal("cancelAnimationFrame", vi.fn());
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

it("shows connecting and no-face states and exposes overlay and reset controls", () => {
  const sendReset = vi.fn();
  const props = {
    bitmapRef: { current: null }, headerRef: { current: null }, sendReset,
  };
  const { rerender } = render(<LiveView {...props} header={null} connection="connecting" />);
  expect(screen.getByText("Connecting to camera…")).toBeVisible();
  expect(screen.getByRole("button", { name: "Reset tracking" })).toBeDisabled();
  const header = { ...frameFixture, face: null };
  rerender(<LiveView {...props} header={header} connection="connected" />);
  expect(screen.getByText(/No face detected - centre/)).toBeVisible();
  for (const name of ["Zones", "Masks", "Boxes", "Labels"]) {
    const toggle = screen.getByRole("checkbox", { name });
    expect(toggle).toBeChecked();
    fireEvent.click(toggle);
    expect(toggle).not.toBeChecked();
  }
  fireEvent.click(screen.getByRole("button", { name: "Reset tracking" }));
  expect(sendReset).toHaveBeenCalledOnce();
});

it("draws ref-held frames at device pixel ratio and cancels its animation loop", () => {
  const ctx = {
    setTransform: vi.fn(), clearRect: vi.fn(), save: vi.fn(), translate: vi.fn(),
    drawImage: vi.fn(), restore: vi.fn(), scale: vi.fn(), beginPath: vi.fn(),
    moveTo: vi.fn(), lineTo: vi.fn(), closePath: vi.fn(), stroke: vi.fn(),
    fill: vi.fn(), fillText: vi.fn(), measureText: vi.fn(() => ({ width: 120 })),
  };
  vi.spyOn(HTMLCanvasElement.prototype, "getContext")
    .mockReturnValue(ctx as unknown as CanvasRenderingContext2D);
  let callback: FrameRequestCallback = () => undefined;
  vi.stubGlobal("requestAnimationFrame", vi.fn((next: FrameRequestCallback) => {
    callback = next;
    return 1;
  }));
  const cancel = vi.fn();
  vi.stubGlobal("cancelAnimationFrame", cancel);
  vi.stubGlobal("devicePixelRatio", 2);
  const bitmap = { close: vi.fn() } as unknown as ImageBitmap;
  const { unmount } = render(
    <LiveView
      bitmapRef={{ current: bitmap }}
      headerRef={{ current: frameFixture }}
      header={frameFixture}
      connection="connected"
      sendReset={vi.fn()}
    />,
  );
  const canvas = screen.getByLabelText("Live camera with skin detection overlays");
  Object.defineProperty(canvas, "clientWidth", { value: 960 });
  Object.defineProperty(canvas, "clientHeight", { value: 540 });
  act(() => callback(0));
  expect(canvas).toHaveAttribute("width", "1920");
  expect(canvas).toHaveAttribute("height", "1080");
  expect(ctx.setTransform).toHaveBeenCalledWith(2, 0, 0, 2, 0, 0);
  expect(ctx.drawImage).toHaveBeenCalledWith(bitmap, 0, 0, 960, 540);
  expect(ctx.scale).toHaveBeenCalledWith(0.75, 0.75);
  unmount();
  expect(cancel).toHaveBeenCalledWith(1);
});

it("shows actionable guidance for every quality issue", () => {
  const messages = {
    too_dark: "Too dark - face a window or lamp",
    too_bright: "Too bright - reduce direct light",
    uneven_light: "Uneven lighting - light your face from the front",
    too_far: "Move closer to the camera",
    turned_away: "Face the camera",
    tilted: "Level your head",
    occluded: "Clear hair or hands away from your face",
  };
  render(<LiveView bitmapRef={{ current: null }} headerRef={{ current: null }}
    header={{ ...frameFixture, quality: { ...qualityFixture, issues: Object.keys(messages) } }}
    connection="connected" sendReset={vi.fn()} />);
  Object.values(messages).forEach((message) => expect(screen.getByText(message)).toBeVisible());
  expect(screen.getByText("Quality 30%")).toBeVisible();
});
