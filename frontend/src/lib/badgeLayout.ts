export type BadgePlacement = { id: string | number; anchorX: number; anchorY: number; x: number; y: number; side: 'left' | 'right' };

/** Coordinates describe badge centres vertically and their inner edges horizontally. */
export function layoutBadges(anchors: { id: string | number; x: number; y: number }[], face: [number, number, number, number], frame: { width: number; height: number }, opts: { gap?: number; badgeHeight?: number } = {}): BadgePlacement[] {
  if (![frame.width, frame.height, ...face].every(Number.isFinite) || frame.width <= 0 || frame.height <= 0 || face[2] <= 0 || face[3] <= 0) return [];
  const gap = opts.gap !== undefined && Number.isFinite(opts.gap) ? Math.max(0, opts.gap) : 12;
  const height = opts.badgeHeight !== undefined && Number.isFinite(opts.badgeHeight) ? Math.max(1, opts.badgeHeight) : 44;
  const half = Math.min(height / 2, frame.height / 2);
  const clamp = (value: number, low: number, high: number) => Math.min(high, Math.max(low, value));
  const sides: Record<'left' | 'right', BadgePlacement[]> = { left: [], right: [] };
  const capacity = Math.max(1, Math.floor((frame.height + gap) / (height + gap)));
  const placements = anchors.filter(anchor => Number.isFinite(anchor.x) && Number.isFinite(anchor.y)).map(anchor => {
    let side: 'left' | 'right' = anchor.x < face[0] + face[2] / 2 ? 'left' : 'right';
    const other = side === 'left' ? 'right' : 'left';
    if (sides[side].length >= capacity && sides[other].length < sides[side].length) side = other;
    const placement: BadgePlacement = { id: anchor.id, anchorX: anchor.x, anchorY: anchor.y, x: clamp(side === 'left' ? face[0] - gap : face[0] + face[2] + gap, 0, frame.width), y: clamp(anchor.y, half, frame.height - half), side };
    sides[side].push(placement);
    return placement;
  });
  Object.values(sides).forEach(items => {
    items.sort((a, b) => a.y - b.y);
    // Preserve the requested spacing whenever it fits; distribute evenly on overflow.
    const spacing = items.length > 1 ? Math.min(height + gap, (frame.height - 2 * half) / (items.length - 1)) : 0;
    items.forEach((item, index) => { if (index > 0) item.y = Math.max(item.y, items[index - 1].y + spacing); });
    if (items.length) items[items.length - 1].y = Math.min(items[items.length - 1].y, frame.height - half);
    for (let i = items.length - 2; i >= 0; i--) items[i].y = Math.min(items[i].y, items[i + 1].y - spacing);
  });
  return placements;
}
