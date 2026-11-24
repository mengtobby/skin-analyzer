import { useEffect, useRef, useState } from "react";
import { startConnection, type Connection } from "./connection";
export type { Connection } from "./connection";
import type { FrameHeader, Health, Report } from "../protocol/types";

/** A connected stream with no new frame for this long is reported as stalled
 * (camera covered, unplugged or taken by another app; phone stream paused). */
export const STALL_MS = 3000;

export function useSkinStream() {
  const bitmapRef = useRef<ImageBitmap | null>(null);
  const headerRef = useRef<FrameHeader | null>(null);
  const displayHeaderRef = useRef<FrameHeader | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const [header, setHeader] = useState<FrameHeader | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [connection, setConnection] = useState<Connection>("connecting");
  const [error, setError] = useState<string | null>(null);
  const [stalled, setStalled] = useState(false);

  useEffect(() => startConnection({
    bitmapRef, headerRef, displayHeaderRef, socketRef, setHeader,
    setHealth, setReport, setError, setConnection,
  }), []);

  // `header` only changes identity when a new frame arrives, so this restarts per frame.
  useEffect(() => {
    setStalled(false);
    if (connection !== "connected") return;
    const timer = setTimeout(() => setStalled(true), STALL_MS);
    return () => clearTimeout(timer);
  }, [header, connection]);

  const sendReset = () => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: "reset" }));
    } else setError("Tracking reset requires a connected stream.");
  };
  // Optimistic local clear: the server also broadcasts {type: "report", data: null} after a
  // reset or input switch, but this window drops the old findings without waiting for it.
  const clearReport = () => setReport(null);
  return {
    bitmapRef, headerRef, displayHeaderRef, header, report, health, connection, stalled, error, sendReset,
    clearReport,
  };
}
