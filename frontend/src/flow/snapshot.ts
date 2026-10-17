import type { FrameHeader, Report } from "../protocol/types";

export interface AnalysisSnapshot {
  image: HTMLCanvasElement;
  width: number;
  height: number;
  header: FrameHeader;
  report: Report;
  capturedAt: number;
}

export function captureSnapshot(bitmap: ImageBitmap | null, header: FrameHeader | null,
  report: Report | null, now = Date.now()): AnalysisSnapshot | null {
  if (!bitmap || !header?.face || !report || !Number.isInteger(header.width) ||
    !Number.isInteger(header.height) || header.width <= 0 || header.height <= 0) return null;
  const image = document.createElement("canvas");
  image.width = header.width;
  image.height = header.height;
  try {
    const context = image.getContext("2d");
    if (!context) return null;
    context.drawImage(bitmap, 0, 0, header.width, header.height);
    return { image, width: header.width, height: header.height,
      header: structuredClone(header), report: structuredClone(report), capturedAt: now };
  } catch {
    return null;
  }
}
