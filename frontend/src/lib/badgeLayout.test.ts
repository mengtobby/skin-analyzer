import { expect, it } from 'vitest';
import { layoutBadges } from './badgeLayout';

it('places inner edges beside the face and preserves anchors and input order', () => {
  expect(layoutBadges([{ id: 'a', x: 150, y: 80 }, { id: 2, x: 250, y: 150 }], [100, 20, 200, 200], { width: 500, height: 300 }, { gap: 10 })).toEqual([
    { id: 'a', anchorX: 150, anchorY: 80, x: 90, y: 80, side: 'left' },
    { id: 2, anchorX: 250, anchorY: 150, x: 310, y: 150, side: 'right' },
  ]);
});

it('resolves collisions near the bottom while keeping each badge inside the frame', () => {
  const result = layoutBadges([190, 192, 194].map((y, id) => ({ id, x: 120, y })), [100, 0, 200, 200], { width: 400, height: 200 }, { gap: 10, badgeHeight: 40 });
  expect(result.map(item => item.y)).toEqual([80, 130, 180]);
  expect(result.every(item => item.side === 'left')).toBe(true);
});

it('switches sides when one column is full', () => {
  const result = layoutBadges(Array.from({ length: 4 }, (_, id) => ({ id, x: 120, y: 50 })), [100, 0, 200, 100], { width: 400, height: 100 }, { gap: 10, badgeHeight: 40 });
  expect(result.map(item => item.side)).toEqual(['left', 'left', 'right', 'right']);
  expect(result[1].y - result[0].y).toBeGreaterThanOrEqual(50);
  expect(result[3].y - result[2].y).toBeGreaterThanOrEqual(50);
});

it('clamps inner edges and vertical extents and filters invalid anchors', () => {
  const result = layoutBadges([{ id: 1, x: 0, y: -100 }, { id: 2, x: 500, y: 600 }, { id: 3, x: NaN, y: 0 }], [0, 0, 400, 200], { width: 400, height: 200 }, { badgeHeight: 40 });
  expect(result.map(({ x, y }) => [x, y])).toEqual([[0, 20], [400, 180]]);
});

it.each([{ width: 0, height: 100 }, { width: 100, height: 0 }, { width: Infinity, height: 100 }, { width: 100, height: NaN }, { width: -1, height: 10 }])('rejects invalid or zero-size frames %j', frame => {
  expect(layoutBadges([{ id: 1, x: 10, y: 20 }], [0, 0, 30, 30], frame)).toEqual([]);
});
