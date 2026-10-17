import type { Report, Track } from "../protocol/types";
import { insightFor, LABEL_INFO, ZONE_NAMES } from "../lib/blemishInfo";
import { Badge, Card } from "../ui";

export function BlemishDetail({ track, report }: { track: Track | undefined; report: Report }) {
  if (!track) return <Card title="No blemishes stood out"><p>There are no individual areas to explore in this capture. You can still review your overall skin scores.</p></Card>;
  const info = LABEL_INFO[track.label];
  const insight = insightFor(track.label, report);
  return <Card className="blemish-detail" aria-label="Selected area details">
    <p className="result-muted">Type</p>
    <div className="result-inline"><h2>{info.name}</h2><Badge>{ZONE_NAMES[track.zone]}</Badge></div>
    <h3>What it is</h3><p>{info.description}</p>
    <dl className="blemish-measurements"><div><dt>Approx. size</dt><dd>{track.size_mm.toFixed(1)} mm</dd></div>
      <div><dt>Confidence</dt><dd>{Math.round(track.confidence * 100)}%</dd></div></dl>
    <h3>Why it happens</h3>
    {insight && (insight.mechanisms.length > 0 || insight.contributing_factors.length > 0) ? <>
      {insight.mechanisms.length > 0 && <ul>{insight.mechanisms.map((text, i) => <li key={i}>{text}</li>)}</ul>}
      {insight.contributing_factors.length > 0 && <><h4>Possible contributing factors</h4><ul>{insight.contributing_factors.map((text, i) => <li key={i}>{text}</li>)}</ul></>}
    </> : <p>There is no additional explanation for this area in this report. Lighting and temporary skin changes can affect its appearance.</p>}
    {!!insight?.zone_notes.length && <><h3>Where</h3><ul>{insight.zone_notes.map((note, i) => <li key={i}>{note}</li>)}</ul></>}
    {insight?.see_a_professional && <aside className="result-callout" aria-label="Professional guidance">{insight.see_a_professional}</aside>}
  </Card>;
}
