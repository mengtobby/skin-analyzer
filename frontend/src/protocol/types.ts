export type Zone = "forehead" | "nose" | "left_cheek" | "right_cheek" | "chin" | "other";
export type Label =
  | "papule" | "pustule" | "red_mark" | "diffuse_redness" | "hyperpigmentation"
  | "texture_irregularity" | "fine_lines" | "comedone" | "nodule";
export type Condition =
  | "inflammatory_acne" | "comedonal_acne" | "post_inflammatory_erythema"
  | "diffuse_redness" | "hyperpigmentation" | "uneven_texture"
  | "dehydration_fine_lines" | "excess_sebum";
export type Point = [number, number];
export type Bbox = [number, number, number, number];
export interface Track {
  id: number;
  label: Label;
  confidence: number;
  zone: Zone;
  bbox: Bbox;
  contour: Point[];
  size_mm: number;
  age: number;
}
export interface ZoneMetrics {
  redness: number;
  texture: number;
  oiliness: number;
  pigmentation: number;
}
export interface SkinMetrics {
  overall: ZoneMetrics;
  zones: Partial<Record<Zone, ZoneMetrics>>;
}
export interface CaptureQuality {
  ok: boolean;
  score: number;
  issues: string[];
  brightness: number;
  evenness: number;
  face_size_px: number;
  yaw_deg: number;
  pitch_deg: number;
}
export interface FrameHeader {
  quality?: CaptureQuality | null;
  analyzed?: boolean;
  type: "frame";
  frame_id: number;
  timestamp: number;
  width: number;
  height: number;
  face: { bbox: Bbox; zones: { zone: Zone; polygon: Point[] }[] } | null;
  tracks: Track[];
  counts: Partial<Record<Label, number>>;
  metrics: SkinMetrics | null;
  perf: { fps: number; latency_ms: number; stages_ms: Record<string, number> };
}
export interface Health {
  status: "ok" | "degraded";
  source: string;
  camera_open: boolean;
  frame_size: Point;
  detector: string;
  preprocessor: string;
  onnx_providers: string[];
  landmarker: string;
  error: string | null;
}
export interface Finding {
  condition: Condition;
  title: string;
  severity: "mild" | "moderate" | "notable";
  score: number;
  count: number;
  zones: Zone[];
  evidence: string;
}
export interface Insight {
  condition: Condition;
  title: string;
  summary: string;
  mechanisms: string[];
  contributing_factors: string[];
  zone_notes: string[];
  see_a_professional: string;
}
export interface Ingredient {
  id: string;
  name: string;
  score: number;
  rationale: string;
  cautions: string[];
}
export interface Product {
  id: string;
  name: string;
  brand: string;
  category: "cleanser" | "toner" | "serum" | "treatment" | "moisturizer" | "sunscreen";
  routine: "AM" | "PM" | "AM/PM";
  key_actives: string[];
  score: number;
  rationale: string;
  targets: Condition[];
}
export interface Report {
  generated_at: number;
  face_detected: boolean;
  findings: Finding[];
  insights: Insight[];
  ingredients: Ingredient[];
  products: Product[];
  warnings: string[];
  disclaimer: string;
}
export interface Envelope<T> {
  success: boolean;
  data: T | null;
  error: string | null;
}
export type ServerMessage = { type: "status"; data: Health } | { type: "report"; data: Report };
