import type { CaptureQuality } from "../protocol/types";
const guidance: Record<string, string> = {
  too_dark: "Too dark - face a window or lamp",
  too_bright: "Too bright - reduce direct light",
  uneven_light: "Uneven lighting - light your face from the front",
  too_far: "Move closer to the camera",
  turned_away: "Face the camera",
  tilted: "Level your head",
  occluded: "Clear hair or hands away from your face",
};
export function QualityBanner({ quality }: { quality: CaptureQuality }) {
  return <div className="quality-banner" role="status">
    <strong>Improve capture conditions</strong>
    <span className="quality-score mono">Quality {Math.round(quality.score * 100)}%</span>
    <ul>{[...new Set(quality.issues)].map((issue) =>
      <li key={issue}>{guidance[issue] ?? "Centre your face in even, diffuse light"}</li>)}</ul>
  </div>;
}
