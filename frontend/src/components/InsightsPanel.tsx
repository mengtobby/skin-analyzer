import type { Report } from "../protocol/types";
import { InsightCard } from "./InsightCard";

interface InsightsPanelProps {
  report: Report | null;
}

export function InsightsPanel({ report }: InsightsPanelProps) {
  return (
    <section className="panel full-width" aria-labelledby="insights-title">
      <div className="panel-heading">
        <h2 id="insights-title">Insights</h2>
        <span className="muted">Evidence from your live session</span>
      </div>
      {report?.findings.length ? report.findings.map((finding) => (
        <InsightCard
          key={finding.condition}
          finding={finding}
          insight={report.insights.find((insight) => insight.condition === finding.condition)}
        />
      )) : <p className="muted">No findings yet. Keep your face centred while analysis settles.</p>}
    </section>
  );
}
