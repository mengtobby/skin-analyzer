interface SparklineProps {
  samples: readonly number[];
  label: string;
}

export function Sparkline({ samples, label }: SparklineProps) {
  const points = samples
    .map((sample, i) => {
      const x = (i / Math.max(1, samples.length - 1)) * 120;
      const y = 30 - Math.min(100, Math.max(0, sample)) * 0.28;
      return `${x},${y}`;
    })
    .join(" ");
  return (
    <svg className="sparkline" viewBox="0 0 120 32" role="img" aria-label={label}>
      <path d="M0 30H120" stroke="var(--border)" />
      <polyline points={points} fill="none" stroke="var(--accent)" strokeWidth="1.5" />
    </svg>
  );
}
