export function value(value: number | undefined, suffix = ""): string {
  return value === undefined ? "--" : `${value.toFixed(1)}${suffix}`;
}

export function humanize(value: string): string {
  return value.replace(/_/g, " ");
}

export function percent(score: number): string {
  return `${Math.round(score * 100)}%`;
}
