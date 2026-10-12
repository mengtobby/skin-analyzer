import { useEffect, useRef, useState } from "react";
import { decodeFrameMessage } from "../protocol/decode";
import type { FrameHeader, Health, Report } from "../protocol/types";
import { isHealth, isReport, object } from "../protocol/validate";

export type Connection = "connecting" | "connected" | "reconnecting";

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

  useEffect(() => {
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
      socket.onopen = () => {
        attempt = 0;
        setConnection("connected");
        setError(null);
      };
      socket.onmessage = async (event: MessageEvent<unknown>) => {
        if (!active || socketRef.current !== socket) return;
        try {
          if (event.data instanceof ArrayBuffer) {
            const { header: next, jpeg } = decodeFrameMessage(event.data);
            const version = ++generation;
            headerRef.current = next;
            if (jpeg.length === 0) {
              bitmapRef.current?.close();
              bitmapRef.current = null;
              displayHeaderRef.current = null;
              setError("Camera frame encoding failed; waiting for the next frame.");
              return;
            }
            const bitmap = await createImageBitmap(new Blob([jpeg], { type: "image/jpeg" }));
            if (!active || socketRef.current !== socket || version !== generation) {
              bitmap.close();
              return;
            }
            bitmapRef.current?.close();
            bitmapRef.current = bitmap;
            displayHeaderRef.current = next;
          } else if (typeof event.data === "string") {
            const message: unknown = JSON.parse(event.data);
            if (!object(message)) throw new Error("Invalid stream message");
            if (message.type === "status" && isHealth(message.data)) setHealth(message.data);
            else if (message.type === "report" && isReport(message.data)) setReport(message.data);
            else throw new Error("Invalid stream message");
          } else throw new Error("Unsupported stream message");
        } catch (cause) {
          if (active) setError(cause instanceof Error ? cause.message : "Frame decoding failed");
        }
      };
      socket.onerror = () => {
        if (active) setError("Stream unavailable; retrying connection.");
      };
      socket.onclose = () => {
        if (!active) return;
        ++generation;
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
      socketRef.current?.close();
      bitmapRef.current?.close();
      bitmapRef.current = null;
      displayHeaderRef.current = null;
    };
  }, []);

  const sendReset = () => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: "reset" }));
    } else setError("Tracking reset requires a connected stream.");
  };
  return {
    bitmapRef, headerRef, displayHeaderRef, header, report, health, connection, error, sendReset,
  };
}
