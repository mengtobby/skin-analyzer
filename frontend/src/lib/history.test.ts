import { describe, expect, it } from "vitest";
import { appendSample } from "./history";

describe("appendSample", () => {
  it("does not mutate frozen input and caps the history at 60", () => {
    const original = Object.freeze(Array.from({ length: 60 }, (_, i) => i));
    const next = appendSample(original, 60);
    expect(original[0]).toBe(0);
    expect(original).toHaveLength(60);
    expect(next).toHaveLength(60);
    expect(next[0]).toBe(1);
    expect(next[59]).toBe(60);
    expect(next).not.toBe(original);
  });

  it("starts empty histories and ignores nonfinite samples", () => {
    expect(appendSample([], 2)).toEqual([2]);
    const input = [1];
    expect(appendSample(input, NaN)).toEqual([1]);
    expect(appendSample(input, Infinity)).not.toBe(input);
  });
});
