import { useEffect, useRef, useState } from "react";
import { startConnection, type Connection } from "./connection";
export type { Connection } from "./connection";
import type { FrameHeader, Health, Report } from "../protocol/types";

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

  useEffect(() => startConnection({
    bitmapRef, headerRef, displayHeaderRef, socketRef, setHeader,
    setHealth, setReport, setError, setConnection,
  }), []);

  const sendReset = () => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: "reset" }));
    } else setError("Tracking reset requires a connected stream.");
  };
  // The server clears its report when the input changes but sends no update until the
  // new input produces one, so drop the previous input's findings locally.
  const clearReport = () => setReport(null);
  return {
    bitmapRef, headerRef, displayHeaderRef, header, report, health, connection, error, sendReset,
    clearReport,
  };
}
