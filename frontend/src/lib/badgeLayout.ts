import { useLayoutEffect, useState, type RefObject } from 'react';

export type BadgePlacement = { id: string | number; anchorX: number; anchorY: number; x: number; y: number; side: 'left' | 'right' };

/** Measure in image pixels; constrain wrapping before measuring to fit narrow frames. */
export function useBadgeMeasurements(ref: RefObject<HTMLDivElement>, frame: { width: number; height: number }) {
  const [sizes, setSizes] = useState<{ widths: number[]; height: number; scale: number }>({ widths: [], height: 44, scale: 1 });
  useLayoutEffect(() => {
    const area = ref.current;
    if (!area || frame.width <= 0 || frame.height <= 0) return;
    const badges = Array.from(area.querySelectorAll<HTMLElement>('.ui-floating-badge'));
    const measure = () => {
      const bounds = area.getBoundingClientRect();
      const scale = Math.min(bounds.width / frame.width, bounds.height / frame.height);
      if (!Number.isFinite(scale) || scale <= 0) return;
      badges.forEach(badge => {
        badge.style.maxWidth = `${Math.max(1, bounds.width - 16)}px`;
        badge.style.boxSizing = 'border-box';
        badge.style.whiteSpace = 'normal';
        badge.style.overflowWrap = 'anywhere';
      });
      const rects = badges.map(badge => badge.getBoundingClientRect());
      const widths = rects.map(rect => rect.width / scale);
      const height = Math.max(44, ...rects.map(rect => rect.height)) / scale;
      setSizes(previous => previous.scale === scale && previous.height === height && previous.widths.length === widths.length && widths.every((width, index) => width === previous.widths[index]) ? previous : { widths, height, scale });
    };
    measure();
    const observer = typeof ResizeObserver === 'undefined' ? undefined : new ResizeObserver(measure);
    observer?.observe(area);
    badges.forEach(badge => observer?.observe(badge));
    window.addEventListener('resize', measure);
    return () => { observer?.disconnect(); window.removeEventListener('resize', measure); };
  });
  return sizes;
}

/** Coordinates describe badge centres vertically and their inner edges horizontally. */
export function layoutBadges(anchors: { id: string | number; x: number; y: number; width?: number }[], face: [number, number, number, number], frame: { width: number; height: number }, opts: { gap?: number; badgeHeight?: number; badgeWidth?: number; margin?: number } = {}): BadgePlacement[] {
  if (![frame.width, frame.height, ...face].every(Number.isFinite) || frame.width <= 0 || frame.height <= 0 || face[2] <= 0 || face[3] <= 0) return [];
  const gap = opts.gap !== undefined && Number.isFinite(opts.gap) ? Math.max(0, opts.gap) : 12;
  const height = opts.badgeHeight !== undefined && Number.isFinite(opts.badgeHeight) ? Math.max(1, opts.badgeHeight) : 44;
  const margin = opts.margin !== undefined && Number.isFinite(opts.margin) ? Math.max(0, opts.margin) : 8;
  const mx = Math.min(margin, frame.width / 2), my = Math.min(margin, frame.height / 2);
  const defaultWidth = opts.badgeWidth !== undefined && Number.isFinite(opts.badgeWidth) && opts.badgeWidth > 0 ? opts.badgeWidth : 80;
  const half = Math.min(height / 2, (frame.height - 2 * my) / 2);
  const clamp = (value: number, low: number, high: number) => Math.min(high, Math.max(low, value));
  const sides: Record<'left' | 'right', BadgePlacement[]> = { left: [], right: [] };
  const capacity = Math.max(1, Math.floor((frame.height - 2 * my + gap) / (height + gap)));
  const placements = anchors.filter(anchor => Number.isFinite(anchor.x) && Number.isFinite(anchor.y)).map(anchor => {
    let side: 'left' | 'right' = anchor.x < face[0] + face[2] / 2 ? 'left' : 'right';
    const other = side === 'left' ? 'right' : 'left';
    const width = Math.min(anchor.width !== undefined && Number.isFinite(anchor.width) && anchor.width > 0 ? anchor.width : defaultWidth, frame.width - 2 * mx);
    const fits = (candidate: 'left' | 'right') => candidate === 'left' ? face[0] - gap - width >= mx : face[0] + face[2] + gap + width <= frame.width - mx;
    if ((!fits(side) && fits(other)) || (fits(other) && sides[side].length >= capacity && sides[other].length < sides[side].length)) side = other;
    const placement: BadgePlacement = { id: anchor.id, anchorX: anchor.x, anchorY: anchor.y, x: side === 'left' ? clamp(face[0] - gap, mx + width, frame.width - mx) : clamp(face[0] + face[2] + gap, mx, frame.width - mx - width), y: clamp(anchor.y, my + half, frame.height - my - half), side };
    sides[side].push(placement);
    return placement;
  });
  Object.values(sides).forEach(items => {
    items.sort((a, b) => a.y - b.y);
    // Preserve the requested spacing whenever it fits; distribute evenly on overflow.
    const spacing = items.length > 1 ? Math.min(height + gap, (frame.height - 2 * my - 2 * half) / (items.length - 1)) : 0;
    items.forEach((item, index) => { if (index > 0) item.y = Math.max(item.y, items[index - 1].y + spacing); });
    if (items.length) items[items.length - 1].y = Math.min(items[items.length - 1].y, frame.height - my - half);
    for (let i = items.length - 2; i >= 0; i--) items[i].y = Math.min(items[i].y, items[i + 1].y - spacing);
  });
  return placements;
}
