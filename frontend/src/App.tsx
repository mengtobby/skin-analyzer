import { useEffect, useState } from "react";
import type { Report } from "./protocol/types";
import { SettingsPage } from "./settings/SettingsPage";
import { useSkinStream } from "./stream/useSkinStream";
import { StatusBar } from "./components/StatusBar";
import { LiveView } from "./components/LiveView";
import { MetricsPanel } from "./components/MetricsPanel";
import { InsightsPanel } from "./components/InsightsPanel";
import { RecommendationsPanel } from "./components/RecommendationsPanel";

function AppTabs({ tab, chooseTab }: { tab: string; chooseTab: (value: string) => void }) {
  return <div className="app-tabs" role="tablist" aria-label="Main navigation">
    {["dashboard", "settings"].map((value, index) => <button key={value}
      id={`${value}-tab`} role="tab" aria-selected={tab === value}
      aria-controls={`${value}-panel`} tabIndex={tab === value ? 0 : -1}
      onClick={() => chooseTab(value)} onKeyDown={(event) => {
        const next = event.key === "Home" ? "dashboard" : event.key === "End" ? "settings" :
          ["ArrowLeft", "ArrowRight"].includes(event.key) ? (index === 0 ? "settings" : "dashboard") : null;
        if (next) { event.preventDefault(); chooseTab(next); document.getElementById(`${next}-tab`)?.focus(); }
      }}>{value === "dashboard" ? "Dashboard" : "Settings"}</button>)}
  </div>;
}
function Dashboard({ stream, report, frozen }: {
  stream: ReturnType<typeof useSkinStream>; report: Report | null; frozen: boolean;
}) {
  return <>
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
  </>;
}

export default function App() {
  const stream = useSkinStream();
  const [tab, setTab] = useState(() => location.hash === "#settings" ? "settings" : "dashboard");
  useEffect(() => {
    const sync = () => setTab(location.hash === "#settings" ? "settings" : "dashboard");
    window.addEventListener("hashchange", sync);
    return () => window.removeEventListener("hashchange", sync);
  }, []);
  function chooseTab(value: string) {
    setTab(value);
    window.location.hash = value === "settings" ? "settings" : "dashboard";
  }
  const [frozen, setFrozen] = useState(false);
  const [snapshot, setSnapshot] = useState<Report | null>(null);
  const report = frozen ? snapshot : stream.report;
  function inputChanged() {
    stream.clearReport();
    setFrozen(false);
    setSnapshot(null);
  }
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
      <AppTabs tab={tab} chooseTab={chooseTab} />
      <div role="tabpanel" id="dashboard-panel" aria-labelledby="dashboard-tab" hidden={tab !== "dashboard"}>
        <Dashboard stream={stream} report={report} frozen={frozen} />
      </div>
      <div role="tabpanel" id="settings-panel" aria-labelledby="settings-tab" hidden={tab !== "settings"}>
        {tab === "settings" && <SettingsPage onInputChanged={inputChanged} />}
      </div>
    </main>
  );
}
