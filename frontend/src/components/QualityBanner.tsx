import type { CaptureQuality } from "../protocol/types";
import { qualityGuidance } from "./qualityGuidance";
export function QualityBanner({ quality }: { quality: CaptureQuality }) {
  return <div className="quality-banner">
    <strong>Improve capture conditions</strong>
    <span className="quality-score mono">Quality {Math.round(quality.score * 100)}%</span>
    <ul>{[...new Set(quality.issues)].map((issue) =>
      <li key={issue}>{qualityGuidance[issue] ?? "Centre your face in even, diffuse light"}</li>)}</ul>
  </div>;
}
