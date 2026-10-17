import { expect, it } from "vitest";
import { reportFixture } from "../protocol/fixtures";
import type { Condition, Label } from "../protocol/types";
import { insightFor, LABEL_INFO, ZONE_NAMES } from "./blemishInfo";

const mappings: [Label, Condition][] = [
  ["papule", "inflammatory_acne"], ["pustule", "inflammatory_acne"], ["nodule", "inflammatory_acne"],
  ["comedone", "comedonal_acne"], ["red_mark", "post_inflammatory_erythema"],
  ["diffuse_redness", "diffuse_redness"], ["hyperpigmentation", "hyperpigmentation"],
  ["texture_irregularity", "uneven_texture"], ["fine_lines", "dehydration_fine_lines"],
];
it.each(mappings)("maps %s with plain-language information", (label, condition) => {
  expect(LABEL_INFO[label].condition).toBe(condition);
  expect(LABEL_INFO[label].name).toBeTruthy();
  expect(LABEL_INFO[label].plural).toBeTruthy();
  expect(LABEL_INFO[label].description.length).toBeGreaterThan(30);
});
it("finds insights by condition and handles missing insights", () => {
  expect(insightFor("pustule", reportFixture)).toBe(reportFixture.insights[0]);
  expect(insightFor("comedone", reportFixture)).toBeUndefined();
  expect(insightFor("papule", { ...reportFixture, insights: [] })).toBeUndefined();
  expect(ZONE_NAMES.left_cheek).toBe("left cheek");
  expect(Object.keys(ZONE_NAMES)).toHaveLength(6);
});
