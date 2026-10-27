import { expect, it, vi } from 'vitest';
import { readFileSync } from 'node:fs';
import { URL as NodeURL } from 'node:url';
import { drawFaceMesh, meshFromFace, meshFromZones } from './mesh';

it('keeps five realistic fixture zones consistent with the generator', () => {
  const fixture = JSON.parse(readFileSync(new NodeURL('../../e2e/fixtures/stream-header.json', import.meta.url), 'utf8')) as { face: Parameters<typeof meshFromFace>[0] };
  const generator = readFileSync(new NodeURL('../../e2e/fixtures/make_stream_fixture.py', import.meta.url), 'utf8');
  expect(fixture.face.zones.map(({ zone }) => zone)).toEqual(['forehead', 'nose', 'left_cheek', 'right_cheek', 'chin']);
  fixture.face.zones.forEach(({ zone, polygon }) => {
    expect(generator).toContain(`"zone": "${zone}"`);
    polygon.forEach(([x, y]) => {
      expect(generator).toContain(`[${x}, ${y}]`);
      expect(x).toBeGreaterThanOrEqual(453);
      expect(x).toBeLessThanOrEqual(827);
      expect(y).toBeGreaterThanOrEqual(113);
      expect(y).toBeLessThanOrEqual(619);
    });
  });
});

it('deduplicates nearby vertices and polygon edges and connects zone centroids', () => {
  const mesh = meshFromZones([
    { zone: 'left', polygon: [[0, 0], [10, 0], [10, 10], [0, 10]] },
    { zone: 'right', polygon: [[11, 0], [20, 0], [20, 10], [11, 10]] },
  ]);
  expect(mesh.points).toHaveLength(8); // six boundary vertices and two centroids
  expect(mesh.points).toContainEqual([5, 5]);
  expect(mesh.points).toContainEqual([15.5, 5]);
  expect(mesh.edges.some(([a, b]) => mesh.points[a][0] === 5 && mesh.points[b][0] === 15.5)).toBe(true);
  expect(new Set(mesh.edges.map(([a, b]) => [a, b].sort((x, y) => x - y).join(':'))).size).toBe(mesh.edges.length);
  expect(mesh.edges).toContainEqual([0, 1]);
});
it('ignores invalid polygons and produces an empty mesh for no zones', () => {
  expect(meshFromZones([])).toEqual({ points: [], edges: [] });
  expect(meshFromZones([{ zone: 'invalid', polygon: [[NaN, 0], [0, 0], [1, 1]] }])).toEqual({ points: [], edges: [] });
});
it('draws scaled dashed edges and peach dots above the sweep with restored state', () => {
  const fills: string[] = [];
  const glows: number[] = [];
  const ctx = { save: vi.fn(), restore: vi.fn(), globalAlpha: 1, lineWidth: 0, strokeStyle: '', fillStyle: '', shadowBlur: 0, setLineDash: vi.fn(), beginPath: vi.fn(), moveTo: vi.fn(), lineTo: vi.fn(), stroke: vi.fn(), arc: vi.fn(), fill: vi.fn(() => { fills.push(ctx.fillStyle); glows.push(ctx.shadowBlur); }) };
  drawFaceMesh(ctx as unknown as CanvasRenderingContext2D, { points: [[1, 2], [3, 8]], edges: [[0, 1]] }, 2, { highlightY: 4, alpha: .5 });
  expect(ctx.setLineDash).toHaveBeenNthCalledWith(1, [3, 4]);
  expect(ctx.strokeStyle).toBe('rgba(255, 255, 255, 0.75)');
  expect(glows).toEqual([8, 0]);
  expect(ctx.moveTo).toHaveBeenCalledWith(2, 4);
  expect(ctx.lineTo).toHaveBeenCalledWith(6, 16);
  expect(ctx.arc).toHaveBeenCalledWith(2, 4, 3, 0, Math.PI * 2);
  expect(fills).toEqual(['#f4b08c', 'rgba(255, 255, 255, 0.9)']);
  expect(ctx.globalAlpha).toBe(.5);
  expect(ctx.restore).toHaveBeenCalledOnce();
  ctx.save.mockClear();
  drawFaceMesh(ctx as unknown as CanvasRenderingContext2D, { points: [], edges: [] }, NaN);
  expect(ctx.save).not.toHaveBeenCalled();
});

it('builds a closed inset 18-point oval without zones', () => {
  const mesh = meshFromFace({ bbox: [100, 50, 200, 300], zones: [] });
  expect(mesh.points).toHaveLength(18);
  expect(mesh.edges).toHaveLength(18);
  expect(mesh.edges).toContainEqual([17, 0]);
  mesh.points.forEach(([x, y]) => {
    expect(((x - 200) / 92) ** 2 + ((y - 200) / 138) ** 2).toBeCloseTo(1);
  });
});

it('preserves the zone mesh and links each oval point to the nearest zone vertex', () => {
  const zones = [{ zone: 'nose', polygon: [[40, 40], [60, 40], [50, 65]] as [number, number][] }];
  const base = meshFromZones(zones);
  const mesh = meshFromFace({ bbox: [0, 0, 100, 100], zones });
  expect(mesh.points.slice(0, base.points.length)).toEqual(base.points);
  expect(mesh.edges.slice(0, base.edges.length)).toEqual(base.edges);
  expect(mesh.points).toHaveLength(base.points.length + 18);
  expect(mesh.edges).toHaveLength(base.edges.length + 36);
  mesh.points.slice(base.points.length).forEach((point, i) => {
    const closest = zones[0].polygon.reduce((a, b) => Math.hypot(a[0] - point[0], a[1] - point[1]) <= Math.hypot(b[0] - point[0], b[1] - point[1]) ? a : b);
    expect(mesh.edges).toContainEqual([base.points.length + i, base.points.findIndex(vertex => vertex[0] === closest[0] && vertex[1] === closest[1])]);
  });
  expect(meshFromFace({ bbox: [0, 0, NaN, 10], zones })).toEqual(base);
});
