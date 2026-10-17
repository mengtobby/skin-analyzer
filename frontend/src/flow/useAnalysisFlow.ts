import { useEffect, useState } from "react";
import type { AnalysisSnapshot } from "./snapshot";
export type Route = 'start'|'camera'|'results'|'treatments'|'settings';
const routes: Route[] = ['start', 'camera', 'results', 'treatments', 'settings'];
function readRoute(): Route {
  const value = location.hash.slice(1) as Route;
  return routes.includes(value) ? value : 'start';
}
export function useAnalysisFlow(): {route: Route; go: (route: Route) => void; snapshot: AnalysisSnapshot | null; setSnapshot: (s: AnalysisSnapshot | null) => void; restart: () => void} {
  const [requested, setRoute] = useState<Route>(readRoute);
  const [snapshot, setSnapshot] = useState<AnalysisSnapshot | null>(null);
  const route = !snapshot && (requested === 'results' || requested === 'treatments') ? 'start' : requested;
  useEffect(() => {
    const sync = () => setRoute(readRoute());
    window.addEventListener('hashchange', sync);
    return () => window.removeEventListener('hashchange', sync);
  }, []);
  useEffect(() => { if (route !== requested) { location.hash = route; setRoute(route); } }, [route, requested]);
  const go = (next: Route) => { location.hash = next; setRoute(next); };
  const restart = () => {
    setSnapshot(null);
    window.dispatchEvent(new Event('analysis-restart'));
    go('start');
  };
  return { route, go, snapshot, setSnapshot, restart };
}
