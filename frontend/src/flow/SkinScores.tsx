import type { SkinMetrics } from "../protocol/types";
import { Card, ScoreRing } from "../ui";

const scores = [
  ["redness", "Redness", "Visible red tones"], ["texture", "Texture", "Surface unevenness"],
  ["oiliness", "Oiliness", "Visible surface shine"], ["pigmentation", "Pigmentation", "Uneven dark tones"],
] as const;

export function SkinScores({ metrics }: { metrics: SkinMetrics | null }) {
  return <section aria-label="Overall skin scores" className="skin-scores">
    {scores.map(([key, name, meaning]) => {
      const raw = metrics?.overall[key];
      const score = raw !== undefined && Number.isFinite(raw) ? Math.round(Math.max(0, Math.min(100, raw))) : null;
      return <Card key={key}><ScoreRing value={score} label={name} decorative showValue={false} /><h3>{name}</h3>
        <p className="skin-score-value">{score ?? "\u2014"}<span> / 100</span></p>
        <p className="result-muted">{score === null ? "Score unavailable" : meaning}</p></Card>;
    })}
  </section>;
}
