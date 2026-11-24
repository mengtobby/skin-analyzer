import type { SkinMetrics, ZoneMetrics } from "../protocol/types";
import { Card, ScoreRing } from "../ui";
import { SCORES, scoreValue } from "./scores";


/** Oiliness only measures specular shine, which diffuse light never produces, so a zero
 * says nothing about dry skin; describe what was actually observed. */
function meaningFor(key: keyof ZoneMetrics, score: number, meaning: string): string {
  return key === "oiliness" && score === 0 ? "No shine visible in this light" : meaning;
}

export function SkinScores({ metrics }: { metrics: SkinMetrics | null }) {
  return <section aria-label="Overall skin scores" className="skin-scores">
    {SCORES.map(([key, name, meaning]) => {
      const score = scoreValue(metrics?.overall[key]);
      return <Card key={key}><ScoreRing value={score} label={name} decorative showValue={false} /><h3>{name}</h3>
        <p className="skin-score-value">{score ?? "—"}<span> / 100</span></p>
        <p className="result-muted">{score === null ? "Score unavailable" : meaningFor(key, score, meaning)}</p></Card>;
    })}
  </section>;
}
