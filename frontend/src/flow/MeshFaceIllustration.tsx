import { meshFromFace } from "../overlay/mesh";
import type { Point } from "../protocol/types";
import { FloatingBadge, ScanFaceIcon } from "../ui";
const zones: { zone: string; polygon: Point[] }[] = [
  { zone: 'forehead', polygon: [[110, 80], [160, 55], [220, 55], [270, 80], [255, 135], [190, 150], [125, 135]] },
  { zone: 'left_cheek', polygon: [[105, 145], [155, 155], [170, 210], [145, 260], [110, 225], [95, 180]] },
  { zone: 'right_cheek', polygon: [[225, 155], [275, 145], [285, 180], [270, 225], [235, 260], [210, 210]] },
  { zone: 'nose', polygon: [[180, 155], [200, 155], [215, 220], [190, 235], [165, 220]] },
  { zone: 'chin', polygon: [[145, 270], [190, 280], [235, 270], [220, 310], [190, 325], [160, 310]] },
];
const mesh = meshFromFace({ bbox: [80, 30, 220, 310], zones });
const landmarks: { name: string; points: Point[] }[] = [
  { name: 'left-brow', points: [[116, 140], [128, 132], [143, 130], [157, 134]] },
  { name: 'right-brow', points: [[223, 134], [237, 130], [252, 132], [264, 140]] },
  { name: 'left-eye', points: [[118, 160], [130, 152], [144, 151], [157, 160], [144, 167], [130, 167], [118, 160]] },
  { name: 'right-eye', points: [[223, 160], [236, 151], [250, 152], [262, 160], [250, 167], [236, 167], [223, 160]] },
  { name: 'nose', points: [[190, 160], [188, 180], [184, 201], [177, 215], [190, 222], [203, 215]] },
  { name: 'lips', points: [[157, 253], [175, 244], [190, 248], [205, 244], [223, 253], [205, 263], [190, 266], [175, 263], [157, 253], [190, 254], [223, 253]] },
];
export function MeshFaceIllustration() {
  return <div className="mesh-face-card" aria-hidden="true">
    <svg viewBox="0 0 380 380" focusable="false">
      <g data-landmark="face-oval" stroke="white" strokeOpacity=".65" strokeWidth="1" strokeDasharray="2 5">{mesh.edges.map(([a, b]) => <line key={`${a}-${b}`} x1={mesh.points[a][0]} y1={mesh.points[a][1]} x2={mesh.points[b][0]} y2={mesh.points[b][1]} />)}</g>
      {mesh.points.map(([x, y], index) => <circle key={index} cx={x} cy={y} r="3" fill="var(--peach, #f4b08c)" />)}
      {landmarks.map(({ name, points }) => <g key={name} data-landmark={name}>
        <polyline points={points.map(point => point.join(',')).join(' ')} fill="none" stroke="white" strokeOpacity=".85" strokeWidth="1.5" strokeDasharray="2 3" />
        {points.map(([x, y], index) => <circle key={index} cx={x} cy={y} r="3" fill="#ffd2b7" />)}
      </g>)}
    </svg>
    <FloatingBadge x={26} y={18} icon={<ScanFaceIcon />}>Redness</FloatingBadge>
    <FloatingBadge x={74} y={28} icon={<ScanFaceIcon />}>Texture</FloatingBadge>
    <FloatingBadge x={26} y={76} icon={<ScanFaceIcon />}>Oiliness</FloatingBadge>
    <FloatingBadge x={65} y={90} icon={<ScanFaceIcon />}>Pigmentation</FloatingBadge>
  </div>;
}
