import { useEffect, useRef, useState } from "react";
import type { FrameHeader, Label, SkinMetrics, ZoneMetrics } from "../protocol/types";
import { appendSample } from "../lib/history";
import { MetricRow } from "./MetricRow";
import { METRIC_KEYS, ZoneTable } from "./ZoneTable";
import { CountsList } from "./CountsList";

interface MetricsPanelProps {
  header?: FrameHeader | null;
  metrics?: SkinMetrics | null;
  counts?: Partial<Record<Label, number>>;
}
type Histories = Record<keyof ZoneMetrics, number[]>;

export function MetricsPanel({ header, metrics, counts }: MetricsPanelProps) {
  const current = metrics ?? header?.metrics ?? null;
  const previous = useRef<SkinMetrics | null>(null);
  const [history, setHistory] = useState<Histories>({
    redness: [], texture: [], oiliness: [], pigmentation: [],
  });
  useEffect(() => {
    if (!current || current === previous.current) return;
    previous.current = current;
    setHistory((old) => ({
      redness: appendSample(old.redness, current.overall.redness),
      texture: appendSample(old.texture, current.overall.texture),
      oiliness: appendSample(old.oiliness, current.overall.oiliness),
      pigmentation: appendSample(old.pigmentation, current.overall.pigmentation),
    }));
  }, [current]);
  return (
    <section className="panel" aria-labelledby="metrics-title">
      <div className="panel-heading">
        <h2 id="metrics-title">Skin telemetry</h2>
        <span className="muted">Relative score / 100</span>
      </div>
      <div className="metric-list">
        {METRIC_KEYS.map((key) => (
          <MetricRow key={key} name={key} metric={current?.overall[key]} history={history[key]} />
        ))}
      </div>
      <ZoneTable metrics={current} />
      <CountsList counts={counts ?? header?.counts ?? {}} />
    </section>
  );
}
