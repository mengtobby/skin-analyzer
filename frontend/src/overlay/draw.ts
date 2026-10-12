import type { FrameHeader, Label, Point } from "../protocol/types";
import { humanize, percent } from "../lib/format";

export const LABEL_COLORS: Record<Label, string> = {
  papule: "#ff4d6d",
  pustule: "#ffb703",
  red_mark: "#f28482",
  diffuse_redness: "#e85d75",
  hyperpigmentation: "#b08968",
  texture_irregularity: "#8ecae6",
  fine_lines: "#cdb4db",
  comedone: "#adb5bd",
  nodule: "#d00000",
};
export interface OverlayToggles {
  zones: boolean;
  masks: boolean;
  boxes: boolean;
  labels: boolean;
}

function path(ctx: CanvasRenderingContext2D, points: Point[]): void {
  ctx.beginPath();
  points.forEach(([x, y], index) => {
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.closePath();
}

function brackets(ctx: CanvasRenderingContext2D, bbox: [number, number, number, number]): void {
  const [x, y, w, h] = bbox;
  const size = Math.min(10, w / 3, h / 3);
  ctx.beginPath();
  for (const [cx, cy, dx, dy] of [
    [x, y, 1, 1], [x + w, y, -1, 1], [x, y + h, 1, -1], [x + w, y + h, -1, -1],
  ]) {
    ctx.moveTo(cx + dx * size, cy);
    ctx.lineTo(cx, cy);
    ctx.lineTo(cx, cy + dy * size);
  }
  ctx.stroke();
}

export function drawOverlay(
  ctx: CanvasRenderingContext2D,
  header: FrameHeader,
  scale: number,
  toggles: OverlayToggles,
): void {
  ctx.save();
  ctx.scale(scale, scale);
  ctx.lineWidth = 1.5 / scale;
  ctx.font = `${11 / scale}px monospace`;
  if (toggles.zones) {
    ctx.strokeStyle = "#3ee6c1";
    ctx.fillStyle = "#3ee6c1";
    for (const zone of header.face?.zones ?? []) {
      if (zone.polygon.length === 0) continue;
      path(ctx, zone.polygon);
      ctx.stroke();
      const x = zone.polygon.reduce((sum, p) => sum + p[0], 0) / zone.polygon.length;
      const y = zone.polygon.reduce((sum, p) => sum + p[1], 0) / zone.polygon.length;
      ctx.fillText(humanize(zone.zone), x, y);
    }
  }
  for (const track of header.tracks) {
    ctx.strokeStyle = LABEL_COLORS[track.label];
    ctx.fillStyle = LABEL_COLORS[track.label];
    if (toggles.masks && track.contour.length > 0) {
      path(ctx, track.contour);
      ctx.globalAlpha = 0.25;
      ctx.fill();
      ctx.globalAlpha = 1;
      ctx.stroke();
    }
    if (toggles.boxes) brackets(ctx, track.bbox);
    if (toggles.labels) {
      ctx.fillText(
        `#${track.id} ${humanize(track.label)} ${percent(track.confidence)}`,
        track.bbox[0],
        Math.max(12 / scale, track.bbox[1] - 5 / scale),
      );
    }
  }
  ctx.restore();
}
