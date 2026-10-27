import { expect, it } from 'vitest';
import { layoutBadges } from './badgeLayout';

it('places inner edges beside the face and preserves anchors and input order', () => {
  expect(layoutBadges([{ id: 'a', x: 150, y: 80 }, { id: 2, x: 250, y: 150 }], [100, 20, 200, 200], { width: 500, height: 300 }, { gap: 10 })).toEqual([
    { id: 'a', anchorX: 150, anchorY: 80, x: 90, y: 80, side: 'left' },
    { id: 2, anchorX: 250, anchorY: 150, x: 310, y: 150, side: 'right' },
  ]);
});

it('tries the other side before moving vertically to avoid markers', () => {
  const [badge] = layoutBadges([{ id: 1, x: 130, y: 100, width: 100 }], [150, 0, 100, 300], { width: 500, height: 300 }, { obstacles: [[108, 78, 44, 44]] });
  expect(badge).toMatchObject({ side: 'right', y: 100, anchorX: 130, anchorY: 100 });
});

it.each([0, 1440])('moves a clamped edge badge inward without changing its column at y=%s', y => {
  const [badge] = layoutBadges([{ id: 1, x: 740, y, width: 460 }], [400, 20, 350, 1300], { width: 780, height: 1440 }, {
    badgeHeight: 120, margin: 16, obstacles: [[696, y - 44, 88, 88]],
  });
  expect(badge.side).toBe('right');
  expect(badge.x).toBeGreaterThanOrEqual(16);
  expect(badge.x + 460).toBeLessThanOrEqual(764);
  expect(Math.abs(badge.y - y)).toBeGreaterThanOrEqual(108);
  expect(badge.y - 60).toBeGreaterThanOrEqual(16);
  expect(badge.y + 60).toBeLessThanOrEqual(1424);
  expect(badge.anchorY).toBe(y);
});

it('steps above and below the anchor when both sides overlap marker targets on a phone', () => {
  const obstacles: [number, number, number, number][] = [[78, 128, 44, 44], [268, 128, 44, 44], [78, 84, 44, 44]];
  const [badge] = layoutBadges([{ id: 1, x: 100, y: 150, width: 240 }], [20, 0, 350, 300], { width: 390, height: 300 }, { badgeHeight: 44, obstacles });
  const left = badge.side === 'left' ? badge.x - 240 : badge.x;
  for (const [x, y, w, h] of obstacles) {
    expect(left + 240 <= x || left >= x + w || badge.y + 22 <= y || badge.y - 22 >= y + h).toBe(true);
  }
  expect(Math.abs(badge.y - 150)).toBeGreaterThan(44);
  expect(badge.anchorY).toBe(150);
});

it('preserves desktop placement when marker targets do not overlap', () => {
  const anchors = [{ id: 1, x: 430, y: 200, width: 180 }];
  const face: [number, number, number, number] = [300, 100, 600, 500];
  const frame = { width: 1280, height: 720 };
  expect(layoutBadges(anchors, face, frame, { obstacles: [[408, 178, 44, 44]] })).toEqual(layoutBadges(anchors, face, frame));
});

it('keeps the least-overlapping candidate when no clear position exists', () => {
  const [badge] = layoutBadges([{ id: 1, x: 20, y: 50, width: 80 }], [0, 0, 200, 100], { width: 200, height: 100 }, { obstacles: [[0, 0, 120, 100], [0, 0, 200, 100]] });
  expect(badge.side).toBe('right');
  expect(badge.x).toBe(112);
});

it('ignores invalid obstacle rectangles', () => {
  const anchors = [{ id: 1, x: 130, y: 100 }];
  const face: [number, number, number, number] = [150, 0, 100, 300];
  const frame = { width: 500, height: 300 };
  expect(layoutBadges(anchors, face, frame, { obstacles: [[NaN, 0, 20, 20], [0, 0, -1, 100]] })).toEqual(layoutBadges(anchors, face, frame));
});

it('resolves collisions near the bottom while keeping each badge inside the frame', () => {
  const result = layoutBadges([190, 192, 194].map((y, id) => ({ id, x: 120, y })), [100, 0, 200, 200], { width: 400, height: 200 }, { gap: 10, badgeHeight: 40, margin: 0 });
  expect(result.map(item => item.y)).toEqual([80, 130, 180]);
  expect(result.every(item => item.side === 'left')).toBe(true);
});

it('switches sides when one column is full', () => {
  const result = layoutBadges(Array.from({ length: 4 }, (_, id) => ({ id, x: 120, y: 50 })), [100, 0, 200, 100], { width: 400, height: 100 }, { gap: 10, badgeHeight: 40, margin: 0 });
  expect(result.map(item => item.side)).toEqual(['left', 'left', 'right', 'right']);
  expect(result[1].y - result[0].y).toBeGreaterThanOrEqual(50);
  expect(result[3].y - result[2].y).toBeGreaterThanOrEqual(50);
});

it('clamps inner edges and vertical extents and filters invalid anchors', () => {
  const result = layoutBadges([{ id: 1, x: 0, y: -100 }, { id: 2, x: 500, y: 600 }, { id: 3, x: NaN, y: 0 }], [0, 0, 400, 200], { width: 400, height: 200 }, { badgeHeight: 40 });
  expect(result.map(({ x, y }) => [x, y])).toEqual([[88, 28], [312, 172]]);
});

it('flips a wide right-edge badge into the available left column', () => {
  const [badge] = layoutBadges([{ id: 1, x: 360, y: 100, width: 180 }], [220, 20, 150, 200], { width: 390, height: 300 });
  expect(badge.side).toBe('left');
  expect(badge.x - 180).toBeGreaterThanOrEqual(8);
  expect(badge.x).toBeLessThanOrEqual(382);
});

it.each(['left', 'right'] as const)('clamps the complete %s badge when neither column has room', side => {
  const [badge] = layoutBadges([{ id: 1, x: side === 'left' ? 30 : 350, y: 300, width: 240 }], [20, 0, 350, 300], { width: 390, height: 300 }, { badgeHeight: 60 });
  expect(badge.side).toBe(side);
  expect(badge.side === 'left' ? badge.x - 240 : badge.x).toBeGreaterThanOrEqual(8);
  expect(badge.side === 'left' ? badge.x : badge.x + 240).toBeLessThanOrEqual(382);
  expect(badge.y).toBe(262);
});

it('uses the configured width for absent or invalid anchor widths', () => {
  for (const width of [undefined, NaN, -10, 0]) {
    const [badge] = layoutBadges([{ id: 1, x: 380, y: 100, width }], [220, 20, 150, 200], { width: 390, height: 300 }, { badgeWidth: 180 });
    expect(badge.side).toBe('left');
    expect(badge.x).toBe(208);
  }
});

it.each([{ width: 0, height: 100 }, { width: 100, height: 0 }, { width: Infinity, height: 100 }, { width: 100, height: NaN }, { width: -1, height: 10 }])('rejects invalid or zero-size frames %j', frame => {
  expect(layoutBadges([{ id: 1, x: 10, y: 20 }], [0, 0, 30, 30], frame)).toEqual([]);
});
