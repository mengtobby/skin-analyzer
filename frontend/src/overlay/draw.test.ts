import { describe, expect, it, vi } from "vitest";
import { drawOverlay, LABEL_COLORS } from "./draw";
import { frameFixture } from "../protocol/fixtures";

function context() {
  return {
    save: vi.fn(), restore: vi.fn(), scale: vi.fn(), beginPath: vi.fn(),
    moveTo: vi.fn(), lineTo: vi.fn(), closePath: vi.fn(), stroke: vi.fn(),
    fill: vi.fn(), fillText: vi.fn(), globalAlpha: 1, strokeStyle: "", fillStyle: "",
  };
}

describe("drawOverlay", () => {
  it("strokes one path per contour and draws track id, label and confidence", () => {
    const ctx = context();
    const header = {
      ...frameFixture,
      tracks: [...frameFixture.tracks, { ...frameFixture.tracks[0], id: 8 }],
    };
    drawOverlay(ctx as unknown as CanvasRenderingContext2D, header, 0.5, {
      zones: false, masks: true, boxes: false, labels: true,
    });
    expect(ctx.stroke).toHaveBeenCalledTimes(2);
    expect(ctx.fill).toHaveBeenCalledTimes(2);
    expect(ctx.fillText).toHaveBeenCalledWith("#7 papule 82%", 120, 110);
    expect(ctx.fillStyle).toBe(LABEL_COLORS.papule);
    expect(ctx.scale).toHaveBeenCalledWith(0.5, 0.5);
    expect(ctx.globalAlpha).toBe(1);
    expect(ctx.restore).toHaveBeenCalledOnce();
  });

  it("respects every toggle independently", () => {
    for (const enabled of ["zones", "masks", "boxes", "labels", "none"]) {
      const ctx = context();
      drawOverlay(ctx as unknown as CanvasRenderingContext2D, frameFixture, 1, {
        zones: enabled === "zones", masks: enabled === "masks",
        boxes: enabled === "boxes", labels: enabled === "labels",
      });
      const strokes = ["zones", "masks", "boxes"].includes(enabled) ? 1 : 0;
      expect(ctx.stroke).toHaveBeenCalledTimes(strokes);
      expect(ctx.fill).toHaveBeenCalledTimes(enabled === "masks" ? 1 : 0);
      expect(ctx.fillText).toHaveBeenCalledTimes(["zones", "labels"].includes(enabled) ? 1 : 0);
    }
  });
});
