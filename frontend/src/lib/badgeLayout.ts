import { useLayoutEffect, useRef, useState, type RefObject } from 'react';

export type BadgePlacement = { id: string | number; anchorX: number; anchorY: number; x: number; y: number; side: 'left' | 'right' };

/** Measure only when content or image/container dimensions change. */
export function useBadgeMeasurements(ref: RefObject<HTMLDivElement>, frame: { width: number; height: number }, labels: { id: string | number; text: string }[]) {
  const [container, setContainer] = useState({ width: 0, height: 0 });
  const [sizes, setSizes] = useState<{ widths: number[]; height: number; scale: number }>({ widths: [], height: 44, scale: 1 });
  const cache = useRef(new Map<string, { width: number; height: number }>());
  const key = JSON.stringify(labels.map(({ id, text }) => [id, text]));
  useLayoutEffect(() => {
    const area = ref.current;
    if (!area) return;
    const update = (width: number, height: number) => {
      if (!Number.isFinite(width) || !Number.isFinite(height)) return;
      setContainer(previous => previous.width === width && previous.height === height ? previous : { width, height });
    };
    const bounds = area.getBoundingClientRect();
    update(bounds.width, bounds.height);
    const observer = typeof ResizeObserver === 'undefined' ? undefined : new ResizeObserver(entries => {
      const bounds = entries.find(entry => entry.target === area)?.contentRect;
      if (bounds) update(bounds.width, bounds.height);
    });
    observer?.observe(area);
    return () => observer?.disconnect();
  }, [ref]);
  useLayoutEffect(() => { cache.current.clear(); }, [container.width, container.height]);
  // Widths measured in the fallback font are wrong once the web font swaps in.
  const [fontEpoch, setFontEpoch] = useState(0);
  useLayoutEffect(() => {
    const fonts = typeof document === 'undefined' ? undefined : document.fonts;
    if (!fonts) return;
    let active = true;
    const remeasure = () => { if (!active) return; cache.current.clear(); setFontEpoch(epoch => epoch + 1); };
    fonts.ready?.then(remeasure, () => undefined);
    fonts.addEventListener?.('loadingdone', remeasure);
    return () => { active = false; fonts.removeEventListener?.('loadingdone', remeasure); };
  }, []);
  useLayoutEffect(() => {
    const area = ref.current;
    const scale = Math.min(container.width / frame.width, container.height / frame.height);
    if (!area || !Number.isFinite(scale) || scale <= 0 || frame.width <= 0 || frame.height <= 0) return;
    const content = JSON.parse(key) as [string | number, string][];
    const badges = Array.from(area.querySelectorAll<HTMLElement>('.ui-floating-badge'));
    const measured = content.map(([, text], index) => {
      const cached = cache.current.get(text);
      if (cached) return cached;
      const badge = badges[index];
      if (!badge) return { width: 0, height: 44 };
      const rect = badge.getBoundingClientRect();
      const size = { width: Math.max(rect.width, badge.scrollWidth), height: rect.height };
      cache.current.set(text, size);
      return size;
    });
    const widths = measured.map(size => size.width / scale);
    const height = Math.max(44, ...measured.map(size => size.height)) / scale;
    setSizes(previous => previous.scale === scale && previous.height === height && previous.widths.length === widths.length && widths.every((width, index) => width === previous.widths[index]) ? previous : { widths, height, scale });
  }, [ref, key, frame.width, frame.height, container.width, container.height, fontEpoch]);
  return sizes;
}

/** Coordinates describe badge centres vertically and their inner edges horizontally. */
export function layoutBadges(anchors: { id: string | number; x: number; y: number; width?: number }[], face: [number, number, number, number], frame: { width: number; height: number }, opts: { gap?: number; badgeHeight?: number; badgeWidth?: number; margin?: number; obstacles?: [number, number, number, number][] } = {}): BadgePlacement[] {
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
  const obstacles = (opts.obstacles ?? []).filter(rect => rect.every(Number.isFinite) && rect[2] > 0 && rect[3] > 0);
  // Resolve after column spacing so it cannot move a safe badge back over a marker.
  if (obstacles.length) placements.forEach(placement => {
    const anchor = anchors.find(item => item.id === placement.id)!;
    const width = Math.min(anchor.width !== undefined && Number.isFinite(anchor.width) && anchor.width > 0 ? anchor.width : defaultWidth, frame.width - 2 * mx);
    const overlap = (candidate: BadgePlacement) => {
      const left = candidate.side === 'left' ? candidate.x - width : candidate.x;
      const padding = 4;
      return obstacles.reduce((area, [x, y, w, h]) => area +
        Math.max(0, Math.min(left + width, x + w + padding) - Math.max(left, x - padding)) *
        Math.max(0, Math.min(candidate.y + half, y + h + padding) - Math.max(candidate.y - half, y - padding)), 0);
    };
    let best = { ...placement };
    let leastOverlap = overlap(best);
    if (leastOverlap === 0) return;
    const other = placement.side === 'left' ? 'right' : 'left';
    const candidateAt = (side: 'left' | 'right', y: number): BadgePlacement => ({ ...placement, side, y,
      x: side === 'left' ? clamp(face[0] - gap, mx + width, frame.width - mx) : clamp(face[0] + face[2] + gap, mx, frame.width - mx - width),
    });
    const candidates: BadgePlacement[] = [];
    // At a frame edge, clamping can push the badge onto its anchor. Move it
    // inward first to preserve the existing column and its full measured width.
    if (placement.y !== placement.anchorY) {
      for (const direction of [-1, 1]) {
        candidates.push(candidateAt(placement.side, clamp(placement.anchorY + direction * height, my + half, frame.height - my - half)));
      }
    }
    candidates.push(candidateAt(other, placement.y));
    for (let step = 1; step <= Math.ceil(frame.height / height); step++) {
      for (const direction of [-1, 1]) {
        const y = clamp(placement.anchorY + direction * step * height, my + half, frame.height - my - half);
        candidates.push(candidateAt(placement.side, y), candidateAt(other, y));
      }
    }
    for (const candidate of candidates) {
      const area = overlap(candidate);
      if (area < leastOverlap) { best = candidate; leastOverlap = area; }
      if (area === 0) break;
    }
    Object.assign(placement, best);
  });
  return placements;
}
