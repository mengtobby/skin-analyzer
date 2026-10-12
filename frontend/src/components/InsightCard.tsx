import { useId, useState } from "react";
import type { Finding, Insight } from "../protocol/types";
import { humanize, percent } from "../lib/format";

interface InsightCardProps {
  finding: Finding;
  insight: Insight | undefined;
}
interface TextListProps {
  items: string[];
}

function TextList({ items }: TextListProps) {
  return (
    <ul>
      {items.map((item, index) => (
        <li key={index}>{item}</li>
      ))}
    </ul>
  );
}

export function InsightCard({ finding, insight }: InsightCardProps) {
  const [expanded, setExpanded] = useState(false);
  const id = useId();
  return (
    <article className="insight-card">
      <button
        className="insight-toggle"
        aria-expanded={expanded}
        aria-controls={id}
        onClick={() => setExpanded((open) => !open)}
      >
        <span className="insight-title">{finding.title}</span>
        <span className={`chip severity-${finding.severity}`}>{finding.severity}</span>
        <span className="mono">{percent(finding.score)}</span>
        <span>{expanded ? "Collapse" : "Details"}</span>
      </button>
      <meter min={0} max={1} value={finding.score} aria-label={`${finding.title} score`} />
      <div className="chips">
        {finding.zones.map((zone) => (
          <span className="chip" key={zone}>
            {humanize(zone)}
          </span>
        ))}
      </div>
      <p className="muted">{finding.evidence}</p>
      <div id={id} hidden={!expanded}>
        {insight ? (
          <>
            <p>{insight.summary}</p>
            <h3>Why it happens</h3>
            <TextList items={insight.mechanisms} />
            <h3>Contributing factors</h3>
            <TextList items={insight.contributing_factors} />
            <h3>Zone notes</h3>
            <TextList items={insight.zone_notes} />
            {insight.see_a_professional && (
              <aside className="callout">
                <h3>When to see a dermatologist</h3>
                <p>{insight.see_a_professional}</p>
              </aside>
            )}
          </>
        ) : <p className="muted">Additional context is not available for this finding.</p>}
      </div>
    </article>
  );
}
