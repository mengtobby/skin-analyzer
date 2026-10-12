import { describe, expect, it } from "vitest";
import { decodeFrameMessage } from "./decode";
import { encodeFrame, frameFixture } from "./fixtures";

describe("decodeFrameMessage", () => {
  it("reads a little-endian header and leaves JPEG bytes intact", () => {
    const decoded = decodeFrameMessage(encodeFrame());
    expect(decoded.header).toEqual(frameFixture);
    expect([...decoded.jpeg]).toEqual([255, 216, 255, 217]);
  });

  it("allows an empty JPEG after an encoding failure", () => {
    expect(decodeFrameMessage(encodeFrame(frameFixture, [])).jpeg).toHaveLength(0);
  });

  it("rejects truncated prefixes and headers beyond the buffer", () => {
    expect(() => decodeFrameMessage(new ArrayBuffer(3))).toThrow();
    const buf = new ArrayBuffer(8);
    new DataView(buf).setUint32(0, 100, true);
    expect(() => decodeFrameMessage(buf)).toThrow("header length");
    expect(() => decodeFrameMessage(encodeFrame().slice(0, 10))).toThrow();
  });

  it("rejects invalid JSON, UTF-8, and malformed nested fields", () => {
    const json = new ArrayBuffer(5);
    new DataView(json).setUint32(0, 1, true);
    new Uint8Array(json)[4] = 123;
    expect(() => decodeFrameMessage(json)).toThrow();
    new Uint8Array(json)[4] = 255;
    expect(() => decodeFrameMessage(json)).toThrow();
    for (const change of [
      { width: 0 }, { tracks: [{}] }, { metrics: { overall: {} } },
      { face: { bbox: [0], zones: [] } }, { perf: null }, { counts: { invalid: 1 } },
    ]) {
      expect(() => decodeFrameMessage(encodeFrame({ ...frameFixture, ...change }))).toThrow();
    }
  });
});
