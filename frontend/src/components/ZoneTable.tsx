import type { SkinMetrics, ZoneMetrics } from "../protocol/types";
import { humanize, value } from "../lib/format";

export const METRIC_KEYS: (keyof ZoneMetrics)[] = [
  "redness", "texture", "oiliness", "pigmentation",
];
interface ZoneTableProps {
  metrics: SkinMetrics | null;
}

export function ZoneTable({ metrics }: ZoneTableProps) {
  return (
    <div className="table-scroll">
      <table>
        <caption>Per-zone scores / 100</caption>
        <thead>
          <tr>
            <th scope="col">Zone</th>
            {METRIC_KEYS.map((key) => (
              <th scope="col" key={key}>
                {key}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Object.entries(metrics?.zones ?? {}).map(([zone, scores]) => (
            <tr key={zone}>
              <th scope="row">{humanize(zone)}</th>
              {METRIC_KEYS.map((key) => (
                <td
                  className="mono"
                  key={key}
                  style={{ backgroundColor: `rgba(62, 230, 193, ${scores[key] / 500})` }}
                >
                  {value(scores[key])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {!metrics && <p className="muted">Zone scores appear when a face is detected.</p>}
    </div>
  );
}
