import { useId, useState } from "react";
import type { AnalysisSnapshot } from "./snapshot";
import { Button, RefreshIcon, ChevronRightIcon } from "../ui";
import { BlemishMap } from "./BlemishMap";
import { BlemishDetail } from "./BlemishDetail";
import { BlemishList } from "./BlemishList";
import { SkinScores } from "./SkinScores";
import { areaName } from "../lib/blemishInfo";
import "./results.css";

export function ResultsPage({ snapshot, onContinue, onRetake }: {
  snapshot: AnalysisSnapshot; onContinue: () => void; onRetake: () => void;
}) {
  const [selected, setSelected] = useState<number | undefined>(snapshot.header.tracks[0]?.id);
  const track = snapshot.header.tracks.find(item => item.id === selected) ?? snapshot.header.tracks[0];
  const detailId = useId();
  const [announcement, setAnnouncement] = useState("");
  function selectArea(id: number) {
    if (id === track?.id) return;
    const next = snapshot.header.tracks.find(item => item.id === id);
    if (!next) return;
    const group = snapshot.header.tracks.filter(item => item.label === next.label);
    setSelected(id);
    setAnnouncement(`Showing ${areaName(next, group.findIndex(item => item.id === id))}`);
  }
  const count = snapshot.header.tracks.length;
  return <div className="analysis-results">
    <div className="sr-only" role="status" aria-live="polite" aria-atomic="true">{announcement}</div>
    <header className="result-heading"><h1>Your results</h1><p>{count} {count === 1 ? "area" : "areas"} to look at. Select an area to learn more.</p></header>
    <div className="results-layout"><div>
      <BlemishMap snapshot={snapshot} selected={track?.id} onSelect={selectArea} detailId={detailId} />
      <BlemishList tracks={snapshot.header.tracks} selected={track?.id} onSelect={selectArea} detailId={detailId} />
    </div><BlemishDetail id={detailId} track={track} report={snapshot.report} /></div>
    <section><h2>Your skin at a glance</h2><p className="result-muted">Appearance scores from this capture. Higher values mean more visible signs.</p>
      <SkinScores metrics={snapshot.header.metrics} /></section>
    <footer className="result-actions"><Button variant="secondary" icon={<RefreshIcon />} onClick={onRetake}>Retake</Button>
      <Button icon={<ChevronRightIcon />} onClick={onContinue}>See treatments</Button></footer>
  </div>;
}
