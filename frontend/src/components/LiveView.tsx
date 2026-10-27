import { useEffect, useRef, useState, type MutableRefObject } from "react";
import type { FrameHeader } from "../protocol/types";
import { drawOverlay } from "../overlay/draw";
import type { Connection } from "../stream/useSkinStream";
import { drawFaceMesh, meshFromZones } from "../overlay/mesh";
import { LABEL_INFO } from "../lib/blemishInfo";
import type { Label } from "../protocol/types";
import { Button, FloatingBadge, ScanFaceIcon } from "../ui";
interface LiveViewProps {
  bitmapRef: MutableRefObject<ImageBitmap | null>;
  headerRef: MutableRefObject<FrameHeader | null>;
  header: FrameHeader | null;
  connection: Connection;
  sendReset: () => void;
  scanProgress?: number;
}
function drawFrame(canvas: HTMLCanvasElement | null, bitmap: ImageBitmap | null, header: FrameHeader | null, overlay: boolean, scanProgress?: number) {
  const ctx = canvas?.getContext('2d');
  if (!canvas || !ctx) return;
  const width = canvas.clientWidth, height = canvas.clientHeight;
  const dpr = window.devicePixelRatio || 1;
  const pixelWidth = Math.round(width * dpr), pixelHeight = Math.round(height * dpr);
  if (canvas.width !== pixelWidth || canvas.height !== pixelHeight) {
    canvas.width = pixelWidth; canvas.height = pixelHeight;
  }
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, width, height);
  if (!bitmap || !header) return;
  const scale = Math.min(width / header.width, height / header.height);
  ctx.save();
  ctx.translate((width - header.width * scale) / 2, (height - header.height * scale) / 2);
  ctx.drawImage(bitmap, 0, 0, header.width * scale, header.height * scale);
  if (overlay) drawOverlay(ctx, header, scale, { zones: true, masks: true, boxes: true, labels: true });
  if (header.face) {
    const [x, y, w, h] = header.face.bbox;
    const highlightY = scanProgress === undefined || !Number.isFinite(scanProgress) ? undefined : y + h * Math.max(0, Math.min(1, scanProgress));
    drawFaceMesh(ctx, meshFromZones(header.face.zones), scale, { highlightY });
    if (highlightY !== undefined && !window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) {
      const band = ctx.createLinearGradient(0, (highlightY - 18) * scale, 0, (highlightY + 18) * scale);
      band.addColorStop(0, 'rgba(244,176,140,0)');
      band.addColorStop(0.5, 'rgba(244,176,140,0.3)');
      band.addColorStop(1, 'rgba(244,176,140,0)');
      ctx.fillStyle = band;
      ctx.fillRect(x * scale, (highlightY - 18) * scale, w * scale, 36 * scale);
    }
  }
  ctx.restore();
}
export function LiveView({ bitmapRef, headerRef, header, connection, sendReset, scanProgress }: LiveViewProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [overlay, setOverlay] = useState(false);
  useEffect(() => {
    let frame = 0;
    const draw = () => {
      drawFrame(canvasRef.current, bitmapRef.current, headerRef.current, overlay, scanProgress);
      frame = requestAnimationFrame(draw);
    };
    frame = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(frame);
  }, [bitmapRef, headerRef, overlay, scanProgress]);
  const frameAspect = header && header.width > 0 && header.height > 0 ? header.width / header.height : 16 / 9;
  const labels = header?.face && connection === 'connected'
    ? Object.values(header.tracks.reduce<Partial<Record<Label, { label: Label; count: number; zone: string }>>>((groups, track) => {
      const group = groups[track.label];
      if (group) group.count += 1;
      else groups[track.label] = { label: track.label, count: 1, zone: track.zone };
      return groups;
    }, {})).sort((a, b) => b.count - a.count || a.label.localeCompare(b.label)).slice(0, 3) : [];
  return <section className="panel live-panel" aria-labelledby="live-title">
    <div className="panel-heading"><h2 id="live-title">Live analysis</h2></div>
    <div className="canvas-wrap" data-frame-id={header?.frame_id}>
      <canvas ref={canvasRef} role="img" aria-label="Live camera with skin detection overlays" />
      <div className="live-badges" style={{ width: `${Math.min(100, frameAspect / (16 / 9) * 100)}%`, height: `${Math.min(100, (16 / 9) / frameAspect * 100)}%` }}>{labels.map((item, index) => {
        const polygon = header?.face?.zones.find(zone => zone.zone === item.zone)?.polygon ?? [];
        const x = polygon.length ? polygon.reduce((sum, point) => sum + point[0], 0) / polygon.length / header!.width * 100 : 50;
        const y = polygon.length ? polygon.reduce((sum, point) => sum + point[1], 0) / polygon.length / header!.height * 100 : 25 + index * 25;
        return <FloatingBadge key={item.label} x={Math.max(18, Math.min(82, x))} y={Math.max(12, Math.min(88, y + index * 12))} icon={<ScanFaceIcon />}>{LABEL_INFO[item.label].plural} {item.count}</FloatingBadge>;
      })}</div>
      {(!header || !header.face || connection !== 'connected') && <p className="empty-camera" aria-hidden="true">
        {!header || connection !== 'connected' ? 'Connecting to camera...' : 'No face detected - centre your face in even, diffuse light'}
      </p>}
    </div>
    <div className="controls"><label><input type="checkbox" checked={overlay}
      onChange={event => setOverlay(event.target.checked)} />Show detection overlay</label>
      <Button variant="ghost" onClick={sendReset} disabled={connection !== 'connected'}>Reset tracking</Button>
    </div>
  </section>;
}
