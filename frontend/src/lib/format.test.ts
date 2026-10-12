import { expect, it } from "vitest";
import { humanize, percent, value } from "./format";

it("formats measurements, confidence and enum names", () => {
  expect(value(41.23)).toBe("41.2");
  expect(value(undefined)).toBe("--");
  expect(value(31.2, " ms")).toBe("31.2 ms");
  expect(percent(0.826)).toBe("83%");
  expect(humanize("post_inflammatory_erythema")).toBe("post inflammatory erythema");
});
