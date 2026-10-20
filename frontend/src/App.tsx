import { useEffect, useRef, useState } from "react";
import { SettingsPage } from "./settings/SettingsPage";
import { useSkinStream } from "./stream/useSkinStream";
import { AppShell, Badge, ScanFaceIcon, SettingsIcon, Stepper } from "./ui";
import { useAnalysisFlow, type Route } from "./flow/useAnalysisFlow";
import { StartPage } from "./flow/StartPage";
import { CameraPage } from "./flow/CameraPage";
import { ResultsPage } from "./flow/ResultsPage";
import { TreatmentsPage } from "./flow/TreatmentsPage";
import "./flow/flow.css";
const steps = ['Start', 'Camera', 'Results', 'Treatments'].map(label => ({ id: label.toLowerCase(), label }));
export default function App() {
  const stream = useSkinStream();
  const flow = useAnalysisFlow();
  const previousRoute = useRef(flow.route);
  useEffect(() => {
    const titles: Record<Route, string> = {
      start: 'Start – Step 1 of 4 – Skin Analyzer',
      camera: 'Camera – Step 2 of 4 – Skin Analyzer',
      results: 'Results – Step 3 of 4 – Skin Analyzer',
      treatments: 'Treatments – Step 4 of 4 – Skin Analyzer',
      settings: 'Settings – Skin Analyzer',
    };
    document.title = titles[flow.route];
    if (previousRoute.current !== flow.route) {
      const heading = document.querySelector<HTMLElement>('main h1');
      if (heading) {
        heading.tabIndex = -1;
        heading.focus();
      }
      previousRoute.current = flow.route;
    }
  }, [flow.route]);
  const [progress, setProgress] = useState(0);
  const { sendReset, clearReport } = stream;
  useEffect(() => {
    const reset = () => { sendReset(); clearReport(); setProgress(0); };
    window.addEventListener('analysis-restart', reset);
    return () => window.removeEventListener('analysis-restart', reset);
  }, [sendReset, clearReport]);
  const current = steps.findIndex(step => step.id === flow.route);
  return <AppShell nav={[
    { id: 'analyze', label: 'Analyze', href: '#start', icon: <ScanFaceIcon /> },
    { id: 'settings', label: 'Settings', href: '#settings', icon: <SettingsIcon /> },
  ]} active={flow.route === 'settings' ? 'settings' : 'analyze'} right={<Badge tone={stream.connection === 'connected' ? 'success' : 'neutral'}>{stream.connection === 'connected' ? 'Camera connected' : 'Reconnecting'}</Badge>}>
    {flow.route !== 'settings' && <Stepper steps={steps} current={current} currentProgress={flow.route === 'camera' ? Math.max(progress, 0.1) : 0.5}
      onSelect={index => flow.go(steps[index].id as Route)} />}
    {flow.route === 'start' && <StartPage onStart={() => flow.go('camera')} />}
    {flow.route === 'camera' && <CameraPage stream={stream} onProgress={setProgress} onCapture={snapshot => { flow.setSnapshot(snapshot); flow.go('results'); }} />}
    {flow.route === 'results' && flow.snapshot && <ResultsPage snapshot={flow.snapshot} onContinue={() => flow.go('treatments')} onRetake={() => flow.go('camera')} />}
    {flow.route === 'treatments' && flow.snapshot && <TreatmentsPage snapshot={flow.snapshot} onBack={() => flow.go('results')} onRestart={flow.restart} />}
    {flow.route === 'settings' && <SettingsPage onInputChanged={() => { flow.setSnapshot(null); stream.clearReport(); }} />}
  </AppShell>;
}
