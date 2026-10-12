import { useState } from "react";
import type { Report } from "./protocol/types";
import { useSkinStream } from "./stream/useSkinStream";
import { StatusBar } from "./components/StatusBar";
import { LiveView } from "./components/LiveView";
import { MetricsPanel } from "./components/MetricsPanel";
import { InsightsPanel } from "./components/InsightsPanel";
import { RecommendationsPanel } from "./components/RecommendationsPanel";

export default function App() {
  const stream = useSkinStream();
  const [frozen, setFrozen] = useState(false);
  const [snapshot, setSnapshot] = useState<Report | null>(null);
  const report = frozen ? snapshot : stream.report;
  return (
    <main>
      <header className="app-header">
        <div>
          <h1>Skin Analyzer</h1>
          <p className="muted">Live skin telemetry &amp; personalised cosmetic guidance</p>
        </div>
        <label className="freeze-control">
          <input
            type="checkbox"
            checked={frozen}
            disabled={!stream.report}
            onChange={(event) => {
              setSnapshot(stream.report);
              setFrozen(event.target.checked);
            }}
          />
          Freeze report
        </label>
      </header>
      <StatusBar connection={stream.connection} header={stream.header} health={stream.health} />
      {stream.error && <p className="callout" role="alert">{stream.error}</p>}
      {frozen && <p className="muted" role="status">Report frozen. Live telemetry continues.</p>}
      <div className="dashboard-grid">
        <LiveView {...stream} headerRef={stream.displayHeaderRef} />
        <MetricsPanel header={stream.header} />
        <InsightsPanel report={report} />
        <RecommendationsPanel report={report} />
      </div>
      <footer>{report?.disclaimer ?? "Awaiting report disclaimer."}</footer>
    </main>
  );
}
