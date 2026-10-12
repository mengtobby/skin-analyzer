import type { FrameHeader, Health, Report } from "./types";

export const frameFixture: FrameHeader = {
  type: "frame",
  frame_id: 1,
  timestamp: 1728600000,
  width: 1280,
  height: 720,
  face: {
    bbox: [100, 100, 300, 300],
    zones: [{ zone: "chin", polygon: [[100, 100], [200, 100], [150, 200]] }],
  },
  tracks: [{
    id: 7,
    label: "papule",
    confidence: 0.82,
    zone: "chin",
    bbox: [120, 120, 20, 20],
    contour: [[120, 120], [140, 120], [130, 140]],
    size_mm: 4.2,
    age: 34,
  }],
  counts: { papule: 1 },
  metrics: {
    overall: { redness: 41.2, texture: 22, oiliness: 35.5, pigmentation: 18.3 },
    zones: { chin: { redness: 50, texture: 20, oiliness: 30, pigmentation: 10 } },
  },
  perf: { fps: 24.8, latency_ms: 31.2, stages_ms: { detect: 9.5 } },
};

export const healthFixture: Health = {
  status: "ok",
  source: "camera:0",
  camera_open: true,
  frame_size: [1280, 720],
  detector: "classical-cielab",
  preprocessor: "cpu",
  onnx_providers: ["CPUExecutionProvider"],
  landmarker: "mediapipe-face-landmarker",
  error: null,
};

export const reportFixture: Report = {
  generated_at: 1728600000,
  face_detected: true,
  findings: [{
    condition: "inflammatory_acne",
    title: "Inflammatory acne",
    severity: "moderate",
    score: 0.62,
    count: 1,
    zones: ["chin"],
    evidence: "One papule tracked on chin",
  }],
  insights: [{
    condition: "inflammatory_acne",
    title: "Inflammatory acne",
    summary: "Inflamed follicles can produce raised lesions.",
    mechanisms: ["Follicular inflammation"],
    contributing_factors: ["Occlusive products"],
    zone_notes: ["Chin: monitor persistent irritation"],
    see_a_professional: "Seek advice for persistent painful lesions.",
  }],
  ingredients: [{
    id: "salicylic_acid",
    name: "Salicylic acid",
    score: 0.8,
    rationale: "Helps with clogged pores",
    cautions: ["Introduce gradually"],
  }],
  products: [{
    id: "cleanser",
    name: "Gentle cleanser",
    brand: "Example",
    category: "cleanser",
    routine: "AM/PM",
    key_actives: ["Glycerin"],
    score: 0.77,
    rationale: "Gentle cleansing",
    targets: ["inflammatory_acne"],
  }],
  warnings: ["Use strong actives on alternate nights."],
  disclaimer: "Cosmetic guidance only - not a medical diagnosis.",
};

export function encodeFrame(
  header: unknown = frameFixture,
  jpeg = [255, 216, 255, 217],
): ArrayBuffer {
  const json = new TextEncoder().encode(JSON.stringify(header));
  const buffer = new ArrayBuffer(4 + json.length + jpeg.length);
  new DataView(buffer).setUint32(0, json.length, true);
  new Uint8Array(buffer, 4, json.length).set(json);
  new Uint8Array(buffer, 4 + json.length).set(jpeg);
  return buffer;
}
