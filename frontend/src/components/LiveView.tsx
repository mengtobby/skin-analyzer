import { useEffect, useRef, useState, type MutableRefObject } from "react";
import type { FrameHeader } from "../protocol/types";
import { drawOverlay, type OverlayToggles } from "../overlay/draw";
import type { Connection } from "../stream/useSkinStream";

interface LiveViewProps {
  bitmapRef: MutableRefObject<ImageBitmap | null>;
  headerRef: MutableRefObject<FrameHeader | null>;
  header: FrameHeader | null;
  connection: Connection;
  sendReset: () => void;
}

export function LiveView({ bitmapRef, headerRef, header, connection, sendReset }: LiveViewProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [toggles, setToggles] = useState<OverlayToggles>({
    zones: true, masks: true, boxes: true, labels: true,
  });
  useEffect(() => {
    let frame = 0;
    const draw = () => {
      const canvas = canvasRef.current;
      const ctx = canvas?.getContext("2d");
      if (canvas && ctx) {
        const width = canvas.clientWidth;
        const height = canvas.clientHeight;
        const dpr = window.devicePixelRatio || 1;
        const pixelWidth = Math.round(width * dpr);
        const pixelHeight = Math.round(height * dpr);
        if (canvas.width !== pixelWidth || canvas.height !== pixelHeight) {
          canvas.width = pixelWidth;
          canvas.height = pixelHeight;
        }
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        ctx.clearRect(0, 0, width, height);
        const bitmap = bitmapRef.current;
        const latest = headerRef.current;
        if (bitmap && latest) {
          const scale = Math.min(width / latest.width, height / latest.height);
          ctx.save();
          ctx.translate((width - latest.width * scale) / 2, (height - latest.height * scale) / 2);
          ctx.drawImage(bitmap, 0, 0, latest.width * scale, latest.height * scale);
          drawOverlay(ctx, latest, scale, toggles);
          ctx.restore();
        }
      }
      frame = requestAnimationFrame(draw);
    };
    frame = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(frame);
  }, [bitmapRef, headerRef, toggles]);

  return (
    <section className="panel live-panel" aria-labelledby="live-title">
      <div className="panel-heading">
        <h2 id="live-title">Live analysis</h2>
        <span className="mono">{header ? `Frame ${header.frame_id}` : "Awaiting frames"}</span>
      </div>
      <div className="canvas-wrap">
        <canvas ref={canvasRef} aria-label="Live camera with skin detection overlays" />
        {(!header || !header.face || connection !== "connected") && (
          <p className="empty-camera" role="status">
            {!header || connection !== "connected"
              ? "Connecting to camera…"
              : "No face detected - centre your face in even, diffuse light"}
          </p>
        )}
      </div>
      <div className="controls">
        {(Object.keys(toggles) as (keyof OverlayToggles)[]).map((key) => (
          <label key={key}>
            <input
              type="checkbox"
              checked={toggles[key]}
              onChange={() => setToggles((current) => ({ ...current, [key]: !current[key] }))}
            />
            {key[0].toUpperCase() + key.slice(1)}
          </label>
        ))}
        <button onClick={sendReset} disabled={connection !== "connected"}>
          Reset tracking
        </button>
      </div>
    </section>
  );
}
