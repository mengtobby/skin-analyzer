import { useEffect, useRef, useState, type CSSProperties } from "react";
import type { AnalysisSnapshot } from "./snapshot";
import { LABEL_COLORS } from "../overlay/draw";
import type { Track } from "../protocol/types";
import { meshFromFace } from "../overlay/mesh";
import { SparkleIcon } from "../ui";
import { FloatingBadge } from "../ui/FloatingBadge";
import { layoutBadges, useBadgeMeasurements } from "../lib/badgeLayout";
import { areaName } from "../lib/blemishInfo";

export function BlemishMap({ snapshot, selected, onSelect, detailId, tracks = snapshot.header.tracks }: {
  tracks?: Track[]; detailId: string; snapshot: AnalysisSnapshot; selected: number | undefined; onSelect: (id: number) => void;
}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const mapRef = useRef<HTMLDivElement>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    try {
      const context = canvas.current?.getContext("2d");
      if (!context) { setFailed(true); return; }
      context.drawImage(snapshot.image, 0, 0);
      setFailed(false);
    } catch { setFailed(true); }
  }, [snapshot]);
  const track = tracks.find(item => item.id === selected);
  const face = snapshot.header.face;
  const mesh = face ? meshFromFace(face) : { points: [], edges: [] };
  const badgeText = track ? `${areaName(track, snapshot.header.tracks.slice(0, snapshot.header.tracks.indexOf(track)).filter(item => item.label === track.label).length)} ${Math.round(track.confidence * 100)}%` : '';
  const badgeSizes = useBadgeMeasurements(mapRef, snapshot, track ? [{ id: track.id, text: badgeText }] : []);
  const placement = track && face ? layoutBadges([{ id: track.id, x: track.bbox[0] + track.bbox[2] / 2, y: track.bbox[1] + track.bbox[3] / 2,
    width: badgeSizes.widths[0] || (60 + badgeText.length * 8) / badgeSizes.scale,
  }], face.bbox, snapshot, { badgeHeight: badgeSizes.height, margin: 8 / badgeSizes.scale })[0] : undefined;
  return <div ref={mapRef} className="blemish-map" style={{ aspectRatio: `${snapshot.width}/${snapshot.height}`,
    "--badge-space": placement ? `${(placement.side === "left" ? placement.x : snapshot.width - placement.x) / snapshot.width * 100}%` : undefined } as CSSProperties}>
    <canvas ref={canvas} width={snapshot.width} height={snapshot.height} role="img" aria-label={`Captured photo with ${tracks.length} marked areas`} />
    {failed && <p className="map-error" role="status">The captured image could not be displayed. Explore the areas below.</p>}
    <svg className="blemish-contour" viewBox={`0 0 ${snapshot.width} ${snapshot.height}`} aria-hidden="true">
      <g className="scan-mesh">{mesh.edges.map(([a, b], index) => <line key={index} x1={mesh.points[a][0]} y1={mesh.points[a][1]} x2={mesh.points[b][0]} y2={mesh.points[b][1]} />)}{mesh.points.map(([x, y], index) => <circle key={index} cx={x} cy={y} r="3" />)}</g>
      {track && track.contour.length > 0 && <polygon points={track.contour.map(point => point.join(",")).join(" ")}
        fill="none" stroke={LABEL_COLORS[track.label]} strokeWidth="2" vectorEffect="non-scaling-stroke" />}
    </svg>
    {tracks.map((item) => <button key={item.id} type="button" className="blemish-marker"
      style={{ left: `${(item.bbox[0] + item.bbox[2] / 2) / snapshot.width * 100}%`,
        top: `${(item.bbox[1] + item.bbox[3] / 2) / snapshot.height * 100}%`, color: LABEL_COLORS[item.label] }}
      aria-label={`${areaName(item, snapshot.header.tracks.slice(0, snapshot.header.tracks.indexOf(item)).filter(previous => previous.label === item.label).length)}, details`}
      aria-controls={detailId} aria-pressed={selected === item.id} onClick={() => onSelect(item.id)}><span /></button>)}
    {track && placement && <FloatingBadge className="selected-area-badge" x={placement.x / snapshot.width * 100} y={placement.y / snapshot.height * 100} side={placement.side} leader={{ x: placement.anchorX / snapshot.width * 100, y: placement.anchorY / snapshot.height * 100 }} icon={<SparkleIcon />}><span>{areaName(track, snapshot.header.tracks.slice(0, snapshot.header.tracks.indexOf(track)).filter(item => item.label === track.label).length)}</span><span>{Math.round(track.confidence * 100)}%</span></FloatingBadge>}
  </div>;
}
