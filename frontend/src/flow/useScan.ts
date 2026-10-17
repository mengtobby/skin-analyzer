import { useEffect, useRef, useState } from "react";
import type { useSkinStream } from "../stream/useSkinStream";
import { captureSnapshot, type AnalysisSnapshot } from "./snapshot";
import type { FrameHeader } from "../protocol/types";
export type SkinStream = ReturnType<typeof useSkinStream>;
export function useScan(stream: SkinStream, onCapture: (snapshot: AnalysisSnapshot) => void) {
  const latest = useRef({ stream, onCapture });
  latest.current = { stream, onCapture };
  const [started, setStarted] = useState<number | null>(null);
  const initialReport = useRef(stream.report);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (started === null) return;
    let badSince: number | null = null;
    let frame: { image: HTMLCanvasElement; header: FrameHeader } | null = null;
    // One reusable buffer, refreshed only when a new frame is displayed (not every poll).
    let buffer: HTMLCanvasElement | null = null;
    let copiedFrameId: number | null = null;
    const timer = window.setInterval(() => {
      const { stream: current, onCapture: finish } = latest.current;
      const elapsed = Date.now() - started;
      const header = current.headerRef.current;
      const good = current.connection === 'connected' && header?.face && header.quality?.ok;
      if (!good) badSince ??= Date.now(); else badSince = null;
      if (badSince !== null && Date.now() - badSince > 1500) {
        setError('We lost a clear view of your face. Adjust your position and try again.');
        setProgress(0); window.clearInterval(timer); setStarted(null); return;
      }
      const displayHeader = current.displayHeaderRef.current;
      const displayGood = !!displayHeader?.face && displayHeader.quality?.ok === true;
      if (good && displayGood && current.bitmapRef.current && displayHeader && displayHeader.frame_id !== copiedFrameId) {
        buffer ??= document.createElement('canvas');
        buffer.width = displayHeader.width; buffer.height = displayHeader.height;
        try {
          const ctx = buffer.getContext('2d');
          if (ctx) {
            ctx.drawImage(current.bitmapRef.current, 0, 0);
            frame = { image: buffer, header: structuredClone(displayHeader) };
            copiedFrameId = displayHeader.frame_id;
          }
        } catch { /* A replaced bitmap can be retried on the next poll. */ }
      }
      setProgress(Math.min(1, elapsed / 3000));
      const fresh = current.report && current.report !== initialReport.current;
      if (elapsed < 3000 || (!fresh && elapsed < 6000) || (!good && elapsed < 6000)) return;
      const snapshot = (good && displayGood && captureSnapshot(current.bitmapRef.current, current.displayHeaderRef.current, current.report)) ||
        (frame && captureSnapshot(frame.image as unknown as ImageBitmap, frame.header, current.report));
      window.clearInterval(timer);
      setStarted(null);
      if (snapshot) finish(snapshot);
      else { setProgress(0); setError('We could not finish your analysis. Please hold still and try again.'); }
    }, 100);
    return () => window.clearInterval(timer);
  }, [started]);
  return { scanning: started !== null, progress, error,
    start: () => { initialReport.current = stream.report; setError(null); setProgress(0); setStarted(Date.now()); },
    cancel: () => { setStarted(null); setProgress(0); } };
}
