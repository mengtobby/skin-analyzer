import { object } from "../protocol/validate";

export type SourceView = { kind: "camera" | "url" | "file"; spec: string; camera_index: number | null };
export type CameraOption = { index: number; width: number; height: number };
export type SourceRequest = { kind: "camera"; camera_index: number } | { kind: "url"; url: string };

const integer = (v: unknown): v is number => typeof v === "number" && Number.isInteger(v) && v >= 0;
const isSource = (v: unknown): v is SourceView => object(v) &&
  ["camera", "url", "file"].includes(String(v.kind)) && typeof v.spec === "string" &&
  v.spec.startsWith(`${v.kind}:`) &&
  (v.kind === "camera" ? integer(v.camera_index) && v.spec === `camera:${v.camera_index}` : v.camera_index === null);
const isCamera = (v: unknown): v is CameraOption => object(v) && integer(v.index) &&
  integer(v.width) && v.width > 0 && integer(v.height) && v.height > 0;

async function request<T>(path: string, validate: (v: unknown) => v is T, body?: SourceRequest): Promise<T> {
  let response: Response;
  let envelope: unknown;
  try {
    response = await fetch(path, body ? {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    } : undefined);
    envelope = await response.json();
  } catch { throw new Error("Settings service unavailable"); }
  if (object(envelope) && typeof envelope.error === "string" && envelope.error) {
    throw new Error(envelope.error);
  }
  if (!response.ok || !object(envelope) || envelope.success !== true || envelope.error !== null || !validate(envelope.data)) {
    throw new Error("Settings service unavailable");
  }
  return envelope.data;
}

export const getSettings = (): Promise<SourceView> => request("/api/settings", isSource);
export const getCameras = (): Promise<CameraOption[]> => request("/api/settings/cameras",
  (v): v is CameraOption[] => Array.isArray(v) && v.every(isCamera));
export const setSource = (source: SourceRequest): Promise<SourceView> =>
  request("/api/settings/source", isSource, source);

export function sourceLabel(source: SourceView): string {
  if (source.kind === "camera") return `Camera ${source.camera_index}`;
  if (source.kind === "file") return "Video file";
  // Defensively redact even if an upstream service accidentally returns credentials.
  try {
    const url = new URL(source.spec.replace(/^url:/, ""));
    url.username = ""; url.password = ""; url.search = ""; url.hash = "";
    return `Phone / network stream (url:${url.toString()})`;
  } catch { return "Phone / network stream"; }
}
