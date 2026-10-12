import { expect, it } from "vitest";
import { isFrameHeader } from "./validate";
import { frameFixture, qualityFixture } from "./fixtures";
it("accepts old headers and optional quality and analyzed fields", () => {
  expect(isFrameHeader(frameFixture)).toBe(true);
  expect(isFrameHeader({ ...frameFixture, quality: null, analyzed: true })).toBe(true);
  expect(isFrameHeader({ ...frameFixture, quality: qualityFixture, analyzed: false })).toBe(true);
});
it("rejects malformed optional fields", () => {
  for (const quality of [{}, { ...qualityFixture, score: NaN },
    { ...qualityFixture, issues: [42] }, { ...qualityFixture, ok: 1 }]) {
    expect(isFrameHeader({ ...frameFixture, quality })).toBe(false);
  }
  expect(isFrameHeader({ ...frameFixture, analyzed: "false" })).toBe(false);
});
