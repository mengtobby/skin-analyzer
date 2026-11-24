import type { Connection } from "./connection";
export interface CameraStatus { label: string; tone: "success" | "warning" | "neutral" }

export function cameraStatus(connection: Connection, stalled: boolean): CameraStatus {
  if (connection === "connecting") return { label: "Connecting", tone: "neutral" };
  if (connection === "reconnecting") return { label: "Reconnecting", tone: "neutral" };
  return stalled ? { label: "No camera frames", tone: "warning" } : { label: "Camera connected", tone: "success" };
}
