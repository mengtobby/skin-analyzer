type Point = [number, number];
export type FaceMesh = { points: Point[]; edges: [number, number][] };

export function meshFromZones(zones: { zone: string; polygon: Point[] }[]): FaceMesh {
  const points: Point[] = [];
  const edges: [number, number][] = [];
  const seen = new Set<string>();
  const vertex = (point: Point): number => {
    const existing = points.findIndex(other => Math.hypot(point[0] - other[0], point[1] - other[1]) <= 2);
    if (existing >= 0) return existing;
    points.push([point[0], point[1]]);
    return points.length - 1;
  };
  const edge = (a: number, b: number): void => {
    if (a === b) return;
    const key = `${Math.min(a, b)}:${Math.max(a, b)}`;
    if (!seen.has(key)) { seen.add(key); edges.push([a, b]); }
  };
  const polygons = zones.map(({ polygon }) => polygon.filter(point => Number.isFinite(point[0]) && Number.isFinite(point[1]))).filter(polygon => polygon.length >= 3);
  const centers = polygons.map(polygon => {
    const vertices = polygon.map(vertex);
    vertices.forEach((index, i) => edge(index, vertices[(i + 1) % vertices.length]));
    const center: Point = [polygon.reduce((sum, point) => sum + point[0], 0) / polygon.length, polygon.reduce((sum, point) => sum + point[1], 0) / polygon.length];
    const index = vertex(center);
    vertices.forEach(corner => edge(index, corner));
    return { center, index };
  });
  // Each zone connects to its nearest neighbour; duplicate links collapse above.
  centers.forEach((item, i) => {
    const nearest = centers.map((other, j) => ({ ...other, distance: i === j ? Infinity : Math.hypot(item.center[0] - other.center[0], item.center[1] - other.center[1]) })).sort((a, b) => a.distance - b.distance)[0];
    if (nearest && Number.isFinite(nearest.distance)) edge(item.index, nearest.index);
  });
  return { points, edges };
}

export function meshFromFace(face: { bbox: [number, number, number, number]; zones: { zone: string; polygon: Point[] }[] }): FaceMesh {
  const mesh = meshFromZones(face.zones);
  const [x, y, width, height] = face.bbox;
  if (!face.bbox.every(Number.isFinite) || width <= 0 || height <= 0) return mesh;
  const zoneVertices = mesh.points.map((point, index) => ({ point, index })).filter(({ point }) =>
    face.zones.some(({ polygon }) => polygon.some(vertex => Math.hypot(vertex[0] - point[0], vertex[1] - point[1]) <= 2)));
  const offset = mesh.points.length;
  for (let i = 0; i < 18; i++) {
    const angle = i * Math.PI * 2 / 18 - Math.PI / 2;
    const point: Point = [x + width / 2 + Math.cos(angle) * width * .46, y + height / 2 + Math.sin(angle) * height * .46];
    mesh.points.push(point);
    mesh.edges.push([offset + i, offset + (i + 1) % 18]);
    const nearest = zoneVertices.reduce<typeof zoneVertices[number] | undefined>((best, candidate) =>
      !best || Math.hypot(candidate.point[0] - point[0], candidate.point[1] - point[1]) < Math.hypot(best.point[0] - point[0], best.point[1] - point[1]) ? candidate : best, undefined);
    if (nearest) mesh.edges.push([offset + i, nearest.index]);
  }
  return mesh;
}

export function drawFaceMesh(ctx: CanvasRenderingContext2D, mesh: FaceMesh, scale: number, opts: { highlightY?: number; alpha?: number } = {}): void {
  if (!Number.isFinite(scale) || scale <= 0) return;
  const alpha = opts.alpha === undefined || !Number.isFinite(opts.alpha) ? 1 : Math.max(0, Math.min(1, opts.alpha));
  ctx.save();
  ctx.globalAlpha *= alpha;
  ctx.lineWidth = 1;
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.75)';
  ctx.setLineDash([3, 4]);
  ctx.beginPath();
  mesh.edges.forEach(([a, b]) => {
    const start = mesh.points[a];
    const end = mesh.points[b];
    if (!start || !end) return;
    ctx.moveTo(start[0] * scale, start[1] * scale);
    ctx.lineTo(end[0] * scale, end[1] * scale);
  });
  ctx.stroke();
  ctx.setLineDash([]);
  mesh.points.forEach(([x, y]) => {
    const highlighted = opts.highlightY !== undefined && y <= opts.highlightY;
    ctx.shadowColor = highlighted ? 'rgba(244, 176, 140, 0.4)' : 'transparent';
    ctx.shadowBlur = highlighted ? 8 : 0;
    ctx.fillStyle = highlighted ? '#f4b08c' : 'rgba(255, 255, 255, 0.9)';
    ctx.beginPath();
    ctx.arc(x * scale, y * scale, 3, 0, Math.PI * 2);
    ctx.fill();
  });
  ctx.restore();
}
