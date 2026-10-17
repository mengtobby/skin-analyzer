import { useEffect, useRef, useState, type MutableRefObject } from "react";
import type { FrameHeader } from "../protocol/types";
import { drawOverlay } from "../overlay/draw";
import type { Connection } from "../stream/useSkinStream";
import { Button } from "../ui";
interface LiveViewProps {
  bitmapRef: MutableRefObject<ImageBitmap | null>;
  headerRef: MutableRefObject<FrameHeader | null>;
  header: FrameHeader | null;
  connection: Connection;
  sendReset: () => void;
}
function drawFrame(canvas: HTMLCanvasElement | null, bitmap: ImageBitmap | null, header: FrameHeader | null, overlay: boolean) {
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
  ctx.restore();
}
export function LiveView({ bitmapRef, headerRef, header, connection, sendReset }: LiveViewProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [overlay, setOverlay] = useState(false);
  useEffect(() => {
    let frame = 0;
    const draw = () => {
      drawFrame(canvasRef.current, bitmapRef.current, headerRef.current, overlay);
      frame = requestAnimationFrame(draw);
    };
    frame = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(frame);
  }, [bitmapRef, headerRef, overlay]);
  return <section className="panel live-panel" aria-labelledby="live-title">
    <div className="panel-heading"><h2 id="live-title">Live analysis</h2></div>
    <div className="canvas-wrap" data-frame-id={header?.frame_id}>
      <canvas ref={canvasRef} aria-label="Live camera with skin detection overlays" />
      {(!header || !header.face || connection !== 'connected') && <p className="empty-camera" role="status">
        {!header || connection !== 'connected' ? 'Connecting to camera...' : 'No face detected - centre your face in even, diffuse light'}
      </p>}
    </div>
    <div className="controls"><label><input type="checkbox" checked={overlay}
      onChange={event => setOverlay(event.target.checked)} />Show detection overlay</label>
      <Button variant="ghost" onClick={sendReset} disabled={connection !== 'connected'}>Reset tracking</Button>
    </div>
  </section>;
}
