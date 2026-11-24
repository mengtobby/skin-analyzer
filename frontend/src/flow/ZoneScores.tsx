import type { SkinMetrics, Zone } from "../protocol/types";
import { ZONE_NAMES } from "../lib/blemishInfo";
import { SCORES, scoreValue } from "./scores";

const ZONE_ORDER: readonly Zone[] = ["forehead", "nose", "left_cheek", "right_cheek", "chin", "other"];

function capitalize(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/** Per-area breakdown of the overall scores, collapsed by default. */
export function ZoneScores({ metrics }: { metrics: SkinMetrics | null }) {
  const zones = ZONE_ORDER.filter(zone => metrics?.zones[zone]);
  if (!metrics || !zones.length) return null;
  const noShine = zones.some(zone => scoreValue(metrics.zones[zone]?.oiliness) === 0);
  return <details className="zone-scores">
    <summary>Scores by area</summary>
    <table aria-label="Scores by area">
      <thead><tr><th scope="col">Area</th>{SCORES.map(([key, name]) => <th key={key} scope="col">{name}</th>)}</tr></thead>
      <tbody>{zones.map(zone => <tr key={zone}><th scope="row">{capitalize(ZONE_NAMES[zone])}</th>
        {SCORES.map(([key]) => <td key={key}>{scoreValue(metrics.zones[zone]?.[key]) ?? "—"}</td>)}</tr>)}</tbody>
    </table>
    {noShine && <p className="result-muted">An oiliness of 0 means no shine was visible in this light, not that the skin is dry.</p>}
  </details>;
}
