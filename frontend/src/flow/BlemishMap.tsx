import { useEffect, useRef, useState } from "react";
import type { AnalysisSnapshot } from "./snapshot";
import { LABEL_COLORS } from "../overlay/draw";
import { LABEL_INFO, ZONE_NAMES } from "../lib/blemishInfo";

export function BlemishMap({ snapshot, selected, onSelect }: {
  snapshot: AnalysisSnapshot; selected: number | undefined; onSelect: (id: number) => void;
}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    try {
      const context = canvas.current?.getContext("2d");
      if (!context) { setFailed(true); return; }
      context.drawImage(snapshot.image, 0, 0);
      setFailed(false);
    } catch { setFailed(true); }
  }, [snapshot]);
  const track = snapshot.header.tracks.find(item => item.id === selected);
  return <div className="blemish-map" style={{ aspectRatio: `${snapshot.width}/${snapshot.height}` }}>
    <canvas ref={canvas} width={snapshot.width} height={snapshot.height} role="img" aria-label="Captured skin analysis" />
    {failed && <p className="map-error" role="status">The captured image could not be displayed. Explore the areas below.</p>}
    <svg className="blemish-contour" viewBox={`0 0 ${snapshot.width} ${snapshot.height}`} aria-hidden="true">
      {track && track.contour.length > 0 && <polygon points={track.contour.map(point => point.join(",")).join(" ")}
        fill="none" stroke={LABEL_COLORS[track.label]} strokeWidth="2" vectorEffect="non-scaling-stroke" />}
    </svg>
    {snapshot.header.tracks.map(item => <button key={item.id} type="button" className="blemish-marker"
      style={{ left: `${(item.bbox[0] + item.bbox[2] / 2) / snapshot.width * 100}%`,
        top: `${(item.bbox[1] + item.bbox[3] / 2) / snapshot.height * 100}%`, color: LABEL_COLORS[item.label] }}
      aria-label={`${LABEL_INFO[item.label].name} on ${ZONE_NAMES[item.zone]}, details`}
      aria-pressed={selected === item.id} onClick={() => onSelect(item.id)}><span /></button>)}
  </div>;
}
