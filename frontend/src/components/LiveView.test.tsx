import "@testing-library/jest-dom/vitest";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { LiveView } from "./LiveView";
import { drawFaceMesh } from "../overlay/mesh";
import { LABEL_INFO } from "../lib/blemishInfo";
vi.mock("../overlay/mesh", async importOriginal => ({ ...await importOriginal<typeof import("../overlay/mesh")>(), drawFaceMesh: vi.fn() }));
import { frameFixture } from "../protocol/fixtures";

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
  expect(screen.getByRole("heading", { name: "Live analysis" })).toBeVisible();
  expect(screen.queryByText("Awaiting frames")).not.toBeInTheDocument();
  const wrapper = screen.getByLabelText("Live camera with skin detection overlays").parentElement;
  expect(wrapper).not.toHaveAttribute("data-frame-id");
  expect(screen.getByText("Connecting to camera...")).toBeVisible();
  expect(screen.getByRole("button", { name: "Reset tracking" })).toBeDisabled();
  const header = { ...frameFixture, face: null };
  rerender(<LiveView {...props} header={header} connection="connected" />);
  expect(screen.queryByText(/^Frame \d+$/)).not.toBeInTheDocument();
  expect(wrapper).toHaveAttribute("data-frame-id", String(header.frame_id));
  rerender(<LiveView {...props} header={{ ...header, frame_id: header.frame_id + 1 }} connection="connected" />);
  expect(wrapper).toHaveAttribute("data-frame-id", String(header.frame_id + 1));
  expect(screen.getByText(/No face detected - centre/)).toBeVisible();
  const toggle = screen.getByRole("checkbox", { name: "Show detection overlay" });
  expect(toggle).not.toBeChecked();
  fireEvent.click(toggle);
  expect(toggle).toBeChecked();
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
  const { unmount, rerender } = render(
    <LiveView
      bitmapRef={{ current: bitmap }}
      headerRef={{ current: frameFixture }}
      header={frameFixture}
      connection="connected"
      sendReset={vi.fn()}
    />,
  );
  fireEvent.click(screen.getByRole("checkbox", { name: "Show detection overlay" }));
  const canvas = screen.getByLabelText("Live camera with skin detection overlays");
  Object.defineProperty(canvas, "clientWidth", { value: 960 });
  Object.defineProperty(canvas, "clientHeight", { value: 540 });
  act(() => callback(0));
  expect(canvas).toHaveAttribute("width", "1920");
  expect(canvas).toHaveAttribute("height", "1080");
  expect(ctx.setTransform).toHaveBeenCalledWith(2, 0, 0, 2, 0, 0);
  expect(ctx.drawImage).toHaveBeenCalledWith(bitmap, 0, 0, 960, 540);
  expect(ctx.scale).toHaveBeenCalledWith(0.75, 0.75);
  expect(drawFaceMesh).toHaveBeenCalledWith(ctx, expect.objectContaining({ points: expect.any(Array) }), 0.75, { highlightY: undefined });
  expect(screen.getByText(`${LABEL_INFO.papule.plural} 1`)).toBeVisible();
  vi.mocked(drawFaceMesh).mockClear();
  rerender(<LiveView bitmapRef={{ current: bitmap }} headerRef={{ current: { ...frameFixture, face: null } }} header={{ ...frameFixture, face: null }} connection="connected" sendReset={vi.fn()} />);
  act(() => callback(0));
  expect(drawFaceMesh).not.toHaveBeenCalled();
  expect(screen.queryByText(`${LABEL_INFO.papule.plural} 1`)).not.toBeInTheDocument();
  unmount();
  expect(cancel).toHaveBeenCalledWith(1);
});

it('exposes the canvas as a named image and hides duplicate overlay guidance', () => {
  render(<LiveView bitmapRef={{ current: null }} headerRef={{ current: null }}
    header={{ ...frameFixture, face: null }} connection="connected" sendReset={vi.fn()} />);
  expect(screen.getByRole('img', { name: 'Live camera with skin detection overlays' })).toBeVisible();
  expect(screen.getByText(/No face detected/)).toHaveAttribute('aria-hidden', 'true');
  expect(screen.queryByRole('status')).not.toBeInTheDocument();
});

it.each([false, true])('sweeps mesh tint and respects reduced motion (%s)', reducedMotion => {
  const gradient = { addColorStop: vi.fn() };
  const ctx = { setTransform: vi.fn(), clearRect: vi.fn(), save: vi.fn(), translate: vi.fn(), drawImage: vi.fn(), restore: vi.fn(), createLinearGradient: vi.fn(() => gradient), fillRect: vi.fn() };
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(ctx as unknown as CanvasRenderingContext2D);
  vi.stubGlobal('matchMedia', vi.fn(() => ({ matches: reducedMotion })));
  let callback: FrameRequestCallback = () => undefined;
  vi.stubGlobal('requestAnimationFrame', vi.fn((next: FrameRequestCallback) => { callback = next; return 1; }));
  const header = { ...frameFixture, tracks: [...frameFixture.tracks, { ...frameFixture.tracks[0], id: 8 }] };
  render(<LiveView bitmapRef={{ current: {} as ImageBitmap }} headerRef={{ current: header }} header={header} connection="connected" sendReset={vi.fn()} scanProgress={0.5} />);
  const canvas = screen.getByRole('img');
  Object.defineProperty(canvas, 'clientWidth', { value: 1280 });
  Object.defineProperty(canvas, 'clientHeight', { value: 720 });
  act(() => callback(0));
  expect(drawFaceMesh).toHaveBeenLastCalledWith(ctx, expect.any(Object), 1, { highlightY: 250 });
  expect(screen.getByText(`${LABEL_INFO.papule.plural} 2`)).toBeVisible();
  expect(ctx.fillRect).toHaveBeenCalledTimes(reducedMotion ? 0 : 1);
  expect(screen.getByRole('checkbox', { name: 'Show detection overlay' })).not.toBeChecked();
});
