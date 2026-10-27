import { expect, it, vi } from 'vitest';
import { drawFaceMesh, meshFromZones } from './mesh';

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
  const ctx = { save: vi.fn(), restore: vi.fn(), globalAlpha: 1, lineWidth: 0, strokeStyle: '', fillStyle: '', setLineDash: vi.fn(), beginPath: vi.fn(), moveTo: vi.fn(), lineTo: vi.fn(), stroke: vi.fn(), arc: vi.fn(), fill: vi.fn(() => fills.push(ctx.fillStyle)) };
  drawFaceMesh(ctx as unknown as CanvasRenderingContext2D, { points: [[1, 2], [3, 8]], edges: [[0, 1]] }, 2, { highlightY: 4, alpha: .5 });
  expect(ctx.setLineDash).toHaveBeenNthCalledWith(1, [2, 4]);
  expect(ctx.moveTo).toHaveBeenCalledWith(2, 4);
  expect(ctx.lineTo).toHaveBeenCalledWith(6, 16);
  expect(ctx.arc).toHaveBeenCalledWith(2, 4, 2.5, 0, Math.PI * 2);
  expect(fills).toEqual(['#f4b08c', 'rgba(255, 255, 255, 0.9)']);
  expect(ctx.globalAlpha).toBe(.5);
  expect(ctx.restore).toHaveBeenCalledOnce();
  ctx.save.mockClear();
  drawFaceMesh(ctx as unknown as CanvasRenderingContext2D, { points: [], edges: [] }, NaN);
  expect(ctx.save).not.toHaveBeenCalled();
});
