import type { MutableRefObject } from "react";
import { decodeFrameMessage } from "../protocol/decode";
import type { FrameHeader, Health, Report } from "../protocol/types";
import { isHealth, isReport, object } from "../protocol/validate";

interface HandlerState {
  bitmapRef: MutableRefObject<ImageBitmap | null>;
  headerRef: MutableRefObject<FrameHeader | null>;
  displayHeaderRef: MutableRefObject<FrameHeader | null>;
  setHealth: (health: Health) => void;
  setReport: (report: Report | null) => void;
  setError: (error: string | null) => void;
  isCurrent: () => boolean;
  nextGeneration: () => number;
  isGeneration: (version: number) => boolean;
}

async function handleFrame(data: ArrayBuffer, state: HandlerState): Promise<boolean> {
  const { bitmapRef, headerRef, displayHeaderRef, setError, isCurrent,
    nextGeneration, isGeneration } = state;
  const { header: next, jpeg } = decodeFrameMessage(data);
  const version = nextGeneration();
  headerRef.current = next;
  if (jpeg.length === 0) {
    bitmapRef.current?.close();
    bitmapRef.current = null;
    displayHeaderRef.current = null;
    setError("Camera frame encoding failed; waiting for the next frame.");
    return false;
  }
  const bitmap = await createImageBitmap(new Blob([jpeg], { type: "image/jpeg" }));
  if (!isCurrent() || !isGeneration(version)) {
    bitmap.close();
    return false;
  }
  bitmapRef.current?.close();
  bitmapRef.current = bitmap;
  displayHeaderRef.current = next;
  return true;
}

export function createMessageHandler(state: HandlerState) {
  const { isCurrent, setError, setHealth, setReport } = state;
  return async (event: MessageEvent<unknown>) => {
    if (!isCurrent()) return;
    try {
      if (event.data instanceof ArrayBuffer) {
        if (!await handleFrame(event.data, state)) return;
      } else if (typeof event.data === "string") {
        const message: unknown = JSON.parse(event.data);
        if (!object(message)) throw new Error("Invalid stream message");
        if (message.type === "status" && isHealth(message.data)) setHealth(message.data);
        else if (message.type === "report" && (message.data === null || isReport(message.data))) {
          setReport(message.data);
        } else throw new Error("Invalid stream message");
      } else throw new Error("Unsupported stream message");
      if (isCurrent()) setError(null);
    } catch (cause) {
      if (isCurrent()) setError(cause instanceof Error ? cause.message : "Frame decoding failed");
    }
  };
}
