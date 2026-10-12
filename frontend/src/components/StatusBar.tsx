import { useEffect, useState } from "react";
import type { FrameHeader, Health } from "../protocol/types";
import type { Connection } from "../stream/useSkinStream";
import { isHealth, object } from "../protocol/validate";
import { value } from "../lib/format";

interface StatusBarProps {
  connection: Connection;
  header: FrameHeader | null;
  health: Health | null;
}

export function StatusBar({ connection, header, health }: StatusBarProps) {
  const [polled, setPolled] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    let pending = false;
    const poll = async () => {
      if (pending) return;
      pending = true;
      try {
        const response = await fetch("/api/health", { signal: controller.signal });
        if (!response.ok) throw new Error(`Health check failed (${response.status})`);
        const envelope: unknown = await response.json();
        if (!object(envelope) || envelope.success !== true || !isHealth(envelope.data)) {
          throw new Error("Invalid health response");
        }
        setPolled(envelope.data);
        setError(null);
      } catch (cause) {
        if (!controller.signal.aborted) {
          setError(cause instanceof Error ? cause.message : "Health check unavailable");
        }
      } finally {
        pending = false;
      }
    };
    void poll();
    const timer = setInterval(() => void poll(), 5000);
    return () => {
      controller.abort();
      clearInterval(timer);
    };
  }, []);
  const current = polled ?? health;
  return (
    <div className="status-bar" aria-label="Pipeline status">
      <span className={`connection ${connection}`}>{connection}</span>
      <span className="mono">{value(header?.perf.fps)} fps</span>
      <span className="mono">{value(header?.perf.latency_ms)} ms latency</span>
      {current && (
        <>
          <span className="chip">Detector: {current.detector}</span>
          <span className="chip">Preprocessor: {current.preprocessor}</span>
          {current.onnx_providers.map((provider) => (
            <span className="chip" key={provider}>ONNX: {provider}</span>
          ))}
          <span className="chip">Camera: {current.status}</span>
        </>
      )}
      {(error || current?.error) && <span role="status">{error || current?.error}</span>}
    </div>
  );
}
