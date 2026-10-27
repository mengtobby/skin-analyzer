import { meshFromZones } from "../overlay/mesh";
import type { Point } from "../protocol/types";
import { FloatingBadge, ScanFaceIcon } from "../ui";
const zones: { zone: string; polygon: Point[] }[] = [
  { zone: 'forehead', polygon: [[110, 80], [160, 55], [220, 55], [270, 80], [255, 135], [190, 150], [125, 135]] },
  { zone: 'left_cheek', polygon: [[105, 145], [155, 155], [170, 210], [145, 260], [110, 225], [95, 180]] },
  { zone: 'right_cheek', polygon: [[225, 155], [275, 145], [285, 180], [270, 225], [235, 260], [210, 210]] },
  { zone: 'nose', polygon: [[180, 155], [200, 155], [215, 220], [190, 235], [165, 220]] },
  { zone: 'chin', polygon: [[145, 270], [190, 280], [235, 270], [220, 310], [190, 325], [160, 310]] },
];
const mesh = meshFromZones(zones);
export function MeshFaceIllustration() {
  return <div className="mesh-face-card" aria-hidden="true">
    <svg viewBox="0 0 380 380" focusable="false">
      <g stroke="currentColor" strokeWidth="1" strokeDasharray="2 5" opacity=".5">{mesh.edges.map(([a, b]) => <line key={`${a}-${b}`} x1={mesh.points[a][0]} y1={mesh.points[a][1]} x2={mesh.points[b][0]} y2={mesh.points[b][1]} />)}</g>
      {mesh.points.map(([x, y], index) => <circle key={index} cx={x} cy={y} r="3" fill="currentColor" />)}
    </svg>
    <FloatingBadge x={22} y={29} icon={<ScanFaceIcon />}>Redness</FloatingBadge>
    <FloatingBadge x={78} y={45} icon={<ScanFaceIcon />}>Texture</FloatingBadge>
    <FloatingBadge x={22} y={66} icon={<ScanFaceIcon />}>Oiliness</FloatingBadge>
    <FloatingBadge x={72} y={82} icon={<ScanFaceIcon />}>Pigmentation</FloatingBadge>
  </div>;
}
