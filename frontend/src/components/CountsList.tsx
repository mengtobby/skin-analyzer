import type { Label } from "../protocol/types";
import { LABEL_COLORS } from "../overlay/draw";
import { humanize } from "../lib/format";

interface CountsListProps {
  counts: Partial<Record<Label, number>>;
}

export function CountsList({ counts }: CountsListProps) {
  return (
    <div>
      <h3>Confirmed detections</h3>
      <ul className="counts-list">
        {(Object.keys(LABEL_COLORS) as Label[]).map((label) => (
          <li key={label}>
            <span className="swatch" style={{ background: LABEL_COLORS[label] }} />
            <span>{humanize(label)}</span>
            <strong className="mono">{counts[label] ?? 0}</strong>
          </li>
        ))}
      </ul>
    </div>
  );
}
