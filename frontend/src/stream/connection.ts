import type { MutableRefObject } from "react";
import type { FrameHeader, Health, Report } from "../protocol/types";
import { createMessageHandler } from "./handlers";
export type Connection = "connecting" | "connected" | "reconnecting";
interface StreamState {
  bitmapRef: MutableRefObject<ImageBitmap | null>;
  headerRef: MutableRefObject<FrameHeader | null>;
  displayHeaderRef: MutableRefObject<FrameHeader | null>;
  socketRef: MutableRefObject<WebSocket | null>;
  setHeader: (header: FrameHeader | null) => void;
  setHealth: (health: Health) => void;
  setReport: (report: Report | null) => void;
  setError: (error: string | null) => void;
  setConnection: (connection: Connection) => void;
}
export function startConnection(state: StreamState) {
  const { bitmapRef, headerRef, displayHeaderRef, socketRef, setHeader,
    setHealth, setReport, setError, setConnection } = state;
  let active = true;
  let attempt = 0;
  let generation = 0;
  let retry: ReturnType<typeof setTimeout>;
  const connect = () => {
    if (!active) return;
    const socket = new WebSocket(
      `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/stream`,
    );
    socketRef.current = socket;
    socket.binaryType = "arraybuffer";
    socket.onopen = () => { attempt = 0; setConnection("connected"); setError(null); };
    socket.onmessage = createMessageHandler({
      bitmapRef, headerRef, displayHeaderRef, setHealth, setReport, setError,
      isCurrent: () => active && socketRef.current === socket,
      nextGeneration: () => ++generation,
      isGeneration: (version) => version === generation,
    });
    socket.onerror = () => {
      if (active) setError("Stream unavailable; retrying connection.");
    };
    socket.onclose = () => {
      if (!active) return;
      ++generation;
      socketRef.current = null;
      headerRef.current = null;
      setHeader(null);
      setConnection("reconnecting");
      retry = setTimeout(connect, Math.min(1000 * 2 ** attempt++, 15000));
    };
  };
  connect();
  const publish = setInterval(() => setHeader(headerRef.current), 200);
  return () => {
    active = false;
    ++generation;
    clearTimeout(retry);
    clearInterval(publish);
    closeStream(state);
  };
}

function closeStream({ socketRef, bitmapRef, displayHeaderRef }: StreamState): void {
  socketRef.current?.close();
  bitmapRef.current?.close();
  bitmapRef.current = null;
  displayHeaderRef.current = null;
}
