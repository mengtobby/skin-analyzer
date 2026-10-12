import type { FrameHeader } from "./types";
import { isFrameHeader } from "./validate";

export function decodeFrameMessage(buf: ArrayBuffer): {
  header: FrameHeader;
  jpeg: Uint8Array;
} {
  if (buf.byteLength < 4) throw new Error("Truncated frame prefix");
  const length = new DataView(buf).getUint32(0, true);
  if (length === 0 || length > buf.byteLength - 4) {
    throw new Error("Invalid frame header length");
  }
  const json = new TextDecoder("utf-8", { fatal: true }).decode(new Uint8Array(buf, 4, length));
  const header: unknown = JSON.parse(json);
  if (!isFrameHeader(header)) throw new Error("Invalid frame header");
  return { header, jpeg: new Uint8Array(buf, 4 + length) };
}
