import { act, cleanup, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useSkinStream } from "./useSkinStream";
import { encodeFrame, frameFixture, healthFixture, reportFixture } from "../protocol/fixtures";

class MockSocket {
  static OPEN = 1;
  static instances: MockSocket[] = [];
  binaryType = "";
  readyState = 1;
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onmessage: ((event: { data: unknown }) => Promise<void>) | null = null;
  send = vi.fn();
  close = vi.fn(() => this.onclose?.());
  constructor(public url: string) {
    MockSocket.instances.push(this);
  }
}

beforeEach(() => {
  vi.useFakeTimers();
  MockSocket.instances = [];
  vi.stubGlobal("WebSocket", MockSocket);
  vi.stubGlobal("createImageBitmap", vi.fn().mockResolvedValue({ close: vi.fn() }));
});
afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("useSkinStream", () => {
  it("connects same-origin, throttles telemetry and closes previous images", async () => {
    const { result, unmount } = renderHook(() => useSkinStream());
    const socket = MockSocket.instances[0];
    expect(socket.url).toBe(`ws://${location.host}/ws/stream`);
    expect(socket.binaryType).toBe("arraybuffer");
    act(() => socket.onopen?.());
    expect(result.current.connection).toBe("connected");
    await act(async () => { await socket.onmessage?.({ data: encodeFrame() }); });
    const oldBitmap = result.current.bitmapRef.current!;
    expect(result.current.header).toBeNull();
    expect(result.current.headerRef.current).toEqual(frameFixture);
    act(() => { vi.advanceTimersByTime(200); });
    expect(result.current.header).toEqual(frameFixture);
    const nextBitmap = { close: vi.fn() };
    vi.mocked(createImageBitmap).mockResolvedValueOnce(nextBitmap as unknown as ImageBitmap);
    await act(async () => { await socket.onmessage?.({ data: encodeFrame() }); });
    expect(oldBitmap.close).toHaveBeenCalledOnce();
    act(() => result.current.sendReset());
    expect(socket.send).toHaveBeenCalledWith('{"type":"reset"}');
    unmount();
    expect(nextBitmap.close).toHaveBeenCalledOnce();
    expect(socket.close).toHaveBeenCalledOnce();
    act(() => { vi.advanceTimersByTime(60000); });
    expect(MockSocket.instances).toHaveLength(1);
  });

  it("accepts status and reports and reports malformed messages explicitly", async () => {
    const { result } = renderHook(() => useSkinStream());
    const socket = MockSocket.instances[0];
    await act(async () => {
      await socket.onmessage?.({ data: JSON.stringify({ type: "status", data: healthFixture }) });
      await socket.onmessage?.({ data: JSON.stringify({ type: "report", data: reportFixture }) });
    });
    expect(result.current.health).toEqual(healthFixture);
    expect(result.current.report).toEqual(reportFixture);
    await act(async () => { await socket.onmessage?.({ data: "{broken" }); });
    expect(result.current.error).toBeTruthy();
    await act(async () => { await socket.onmessage?.({ data: '{"type":"report","data":{}}' }); });
    expect(result.current.report).toEqual(reportFixture);
    expect(result.current.error).toBe("Invalid stream message");
  });

  it("reconnects with exponential delays capped at 15 seconds", () => {
    const { result } = renderHook(() => useSkinStream());
    for (const delay of [1000, 2000, 4000, 8000, 15000, 15000]) {
      const oldLength = MockSocket.instances.length;
      act(() => MockSocket.instances[oldLength - 1].onclose?.());
      expect(result.current.connection).toBe("reconnecting");
      act(() => { vi.advanceTimersByTime(delay - 1); });
      expect(MockSocket.instances).toHaveLength(oldLength);
      act(() => { vi.advanceTimersByTime(1); });
      expect(MockSocket.instances).toHaveLength(oldLength + 1);
    }
  });

  it("discards and closes out-of-order decoded bitmaps", async () => {
    let finishFirst: (bitmap: ImageBitmap) => void = () => undefined;
    vi.mocked(createImageBitmap).mockImplementationOnce(() => new Promise((resolve) => {
      finishFirst = resolve;
    }));
    const { result } = renderHook(() => useSkinStream());
    const socket = MockSocket.instances[0];
    const pending = socket.onmessage?.({ data: encodeFrame() });
    await act(async () => {
      await socket.onmessage?.({ data: encodeFrame({ ...frameFixture, frame_id: 2 }) });
    });
    const bitmap = result.current.bitmapRef.current;
    const stale = { close: vi.fn() };
    await act(async () => {
      finishFirst(stale as unknown as ImageBitmap);
      await pending;
    });
    expect(stale.close).toHaveBeenCalledOnce();
    expect(result.current.bitmapRef.current).toBe(bitmap);
    expect(result.current.headerRef.current?.frame_id).toBe(2);
    expect(result.current.displayHeaderRef.current?.frame_id).toBe(2);
  });

  it("clears the displayed image on empty JPEG while preserving telemetry", async () => {
    const { result } = renderHook(() => useSkinStream());
    const socket = MockSocket.instances[0];
    await act(async () => { await socket.onmessage?.({ data: encodeFrame() }); });
    const bitmap = result.current.bitmapRef.current!;
    await act(async () => {
      await socket.onmessage?.({ data: encodeFrame({ ...frameFixture, frame_id: 2 }, []) });
    });
    expect(bitmap.close).toHaveBeenCalledOnce();
    expect(result.current.bitmapRef.current).toBeNull();
    expect(result.current.displayHeaderRef.current).toBeNull();
    expect(result.current.headerRef.current?.frame_id).toBe(2);
  });
});

it("clears errors on the next valid frame or message and clears telemetry on close", async () => {
  const { result } = renderHook(() => useSkinStream());
  const socket = MockSocket.instances[0];
  act(() => socket.onopen?.());
  await act(async () => { await socket.onmessage?.({ data: "broken" }); });
  expect(result.current.error).toBeTruthy();
  await act(async () => { await socket.onmessage?.({ data: encodeFrame() }); });
  expect(result.current.error).toBeNull();
  await act(async () => { await socket.onmessage?.({ data: "broken" }); });
  await act(async () => {
    await socket.onmessage?.({ data: JSON.stringify({ type: "status", data: healthFixture }) });
  });
  expect(result.current.error).toBeNull();
  act(() => { vi.advanceTimersByTime(200); });
  expect(result.current.header).toEqual(frameFixture);
  act(() => socket.onclose?.());
  expect(result.current.connection).toBe("reconnecting");
  expect(result.current.header).toBeNull();
});
