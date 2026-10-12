export const HISTORY_LENGTH = 60;

export function appendSample(history: readonly number[], sample: number): number[] {
  if (!Number.isFinite(sample)) return history.slice(-HISTORY_LENGTH);
  return [...history, sample].slice(-HISTORY_LENGTH);
}
