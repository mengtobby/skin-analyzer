export const SCORES = [
  ["redness", "Redness", "Visible red tones"], ["texture", "Texture", "Surface unevenness"],
  ["oiliness", "Oiliness", "Visible surface shine"], ["pigmentation", "Pigmentation", "Uneven dark tones"],
] as const;

/** Clamped, rounded 0-100 score, or null when missing or not finite. */
export function scoreValue(raw: number | undefined): number | null {
  return raw !== undefined && Number.isFinite(raw) ? Math.round(Math.max(0, Math.min(100, raw))) : null;
}
