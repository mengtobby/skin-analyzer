import { value } from "../lib/format";
import { Sparkline } from "./Sparkline";

interface MetricRowProps {
  name: string;
  metric: number | undefined;
  history: readonly number[];
}

export function MetricRow({ name, metric, history }: MetricRowProps) {
  return (
    <div className="metric-row">
      <div className="metric-name">{name}</div>
      <span className="metric-value mono">{value(metric)}</span>
      <meter min={0} max={100} value={metric ?? 0} aria-label={`${name} score`} />
      <Sparkline samples={history} label={`${name}, last 60 samples`} />
    </div>
  );
}
