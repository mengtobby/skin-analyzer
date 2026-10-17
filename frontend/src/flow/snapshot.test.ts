import { afterEach, expect, it, vi } from "vitest";
import { frameFixture, reportFixture } from "../protocol/fixtures";
import { captureSnapshot } from "./snapshot";

afterEach(() => vi.restoreAllMocks());
const bitmap = {} as ImageBitmap;
it("requires bitmap, header, report and a face", () => {
  expect(captureSnapshot(null, frameFixture, reportFixture)).toBeNull();
  expect(captureSnapshot(bitmap, null, reportFixture)).toBeNull();
  expect(captureSnapshot(bitmap, frameFixture, null)).toBeNull();
  expect(captureSnapshot(bitmap, { ...frameFixture, face: null }, reportFixture)).toBeNull();
  expect(captureSnapshot(bitmap, { ...frameFixture, width: 0 }, reportFixture)).toBeNull();
});
it("draws synchronously and isolates nested header and report data", () => {
  const drawImage = vi.fn();
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({ drawImage } as unknown as CanvasRenderingContext2D);
  const header = structuredClone(frameFixture);
  const report = structuredClone(reportFixture);
  const snapshot = captureSnapshot(bitmap, header, report, 123)!;
  expect(drawImage).toHaveBeenCalledWith(bitmap, 0, 0, header.width, header.height);
  expect(snapshot.image.width).toBe(header.width);
  expect(snapshot.image.height).toBe(header.height);
  expect(snapshot.capturedAt).toBe(123);
  header.tracks[0].bbox[0] = 999;
  report.insights[0].mechanisms.push("Changed");
  expect(snapshot.header.tracks[0].bbox[0]).toBe(120);
  expect(snapshot.report.insights[0].mechanisms).toEqual(["Follicular inflammation"]);
});
it("returns null when drawing is unavailable or the bitmap is closed", () => {
  const context = vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
  expect(captureSnapshot(bitmap, frameFixture, reportFixture)).toBeNull();
  context.mockImplementation(() => { throw new Error("Closed bitmap"); });
  expect(captureSnapshot(bitmap, frameFixture, reportFixture)).toBeNull();
});
