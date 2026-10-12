import type { FrameHeader, Health, Report } from "./types";

const labels = ["papule", "pustule", "red_mark", "diffuse_redness", "hyperpigmentation",
  "texture_irregularity", "fine_lines", "comedone", "nodule"];
const zones = ["forehead", "nose", "left_cheek", "right_cheek", "chin", "other"];
const conditions = ["inflammatory_acne", "comedonal_acne", "post_inflammatory_erythema",
  "diffuse_redness", "hyperpigmentation", "uneven_texture", "dehydration_fine_lines",
  "excess_sebum"];
export const object = (v: unknown): v is Record<string, unknown> =>
  typeof v === "object" && v !== null && !Array.isArray(v);
const number = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);
const text = (v: unknown): v is string => typeof v === "string";
const strings = (v: unknown): v is string[] => Array.isArray(v) && v.every(text);
const tuple = (v: unknown, n: number) => Array.isArray(v) && v.length === n && v.every(number);
const polygon = (v: unknown) => Array.isArray(v) && v.every((p) => tuple(p, 2));
const values = (v: unknown): v is Record<string, number> =>
  object(v) && Object.values(v).every(number);
const metrics = (v: unknown) => object(v) &&
  ["redness", "texture", "oiliness", "pigmentation"].every((key) => number(v[key]));
const member = (v: unknown, options: string[]) => text(v) && options.includes(v);
const list = (v: unknown, check: (item: unknown) => boolean) => Array.isArray(v) && v.every(check);

export function isFrameHeader(v: unknown): v is FrameHeader {
  if (!object(v)) return false;
  const face = v.face;
  const perf = v.perf;
  const skin = v.metrics;
  return v.type === "frame" && number(v.frame_id) && number(v.timestamp) &&
    number(v.width) && v.width > 0 && number(v.height) && v.height > 0 &&
    (face === null || (object(face) && tuple(face.bbox, 4) && list(face.zones,
      (z) => object(z) && member(z.zone, zones) && polygon(z.polygon)))) &&
    list(v.tracks, (t) => object(t) && number(t.id) && member(t.label, labels) &&
      number(t.confidence) && t.confidence >= 0 && t.confidence <= 1 &&
      member(t.zone, zones) && tuple(t.bbox, 4) && polygon(t.contour) &&
      number(t.size_mm) && number(t.age)) &&
    values(v.counts) && Object.keys(v.counts).every((key) => labels.includes(key)) &&
    (skin === null || (object(skin) && metrics(skin.overall) && object(skin.zones) &&
      Object.entries(skin.zones).every(([key, value]) => zones.includes(key) && metrics(value)))) &&
    object(perf) && number(perf.fps) && number(perf.latency_ms) && values(perf.stages_ms);
}

export function isHealth(v: unknown): v is Health {
  return object(v) && member(v.status, ["ok", "degraded"]) && text(v.source) &&
    typeof v.camera_open === "boolean" && tuple(v.frame_size, 2) && text(v.detector) &&
    text(v.preprocessor) && strings(v.onnx_providers) && text(v.landmarker) &&
    (v.error === null || text(v.error));
}

export function isReport(v: unknown): v is Report {
  return object(v) && number(v.generated_at) && typeof v.face_detected === "boolean" &&
    list(v.findings, (f) => object(f) && member(f.condition, conditions) && text(f.title) &&
      member(f.severity, ["mild", "moderate", "notable"]) && number(f.score) &&
      number(f.count) && list(f.zones, (z) => member(z, zones)) && text(f.evidence)) &&
    list(v.insights, (i) => object(i) && member(i.condition, conditions) && text(i.title) &&
      text(i.summary) && strings(i.mechanisms) && strings(i.contributing_factors) &&
      strings(i.zone_notes) && text(i.see_a_professional)) &&
    list(v.ingredients, (i) => object(i) && text(i.id) && text(i.name) && number(i.score) &&
      text(i.rationale) && strings(i.cautions)) &&
    list(v.products, (p) => object(p) && text(p.id) && text(p.name) && text(p.brand) &&
      member(p.category, ["cleanser", "toner", "serum", "treatment", "moisturizer", "sunscreen"]) &&
      member(p.routine, ["AM", "PM", "AM/PM"]) && strings(p.key_actives) && number(p.score) &&
      text(p.rationale) && list(p.targets, (c) => member(c, conditions))) &&
    strings(v.warnings) && text(v.disclaimer);
}
