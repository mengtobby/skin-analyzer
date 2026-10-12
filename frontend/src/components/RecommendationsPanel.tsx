import type { Report } from "../protocol/types";
import { IngredientChips } from "./IngredientChips";
import { ProductCard } from "./ProductCard";

interface RecommendationsPanelProps {
  report: Report | null;
}

export function RecommendationsPanel({ report }: RecommendationsPanelProps) {
  return (
    <section className="panel full-width" aria-labelledby="recommendations-title">
      <div className="panel-heading">
        <h2 id="recommendations-title">Recommendations</h2>
        <span className="muted">Ingredients &amp; routine</span>
      </div>
      {!report && <p className="muted">Your routine guidance will appear with the first report.</p>}
      {report && (
        <>
          <IngredientChips ingredients={report.ingredients} />
          <div className="routine-grid">
            {(["AM", "PM"] as const).map((routine) => (
              <div key={routine}>
                <h3>{routine} / {routine === "AM" ? "Morning" : "Evening"}</h3>
                {report.products.filter((p) => p.routine === routine || p.routine === "AM/PM")
                  .map((product) => <ProductCard key={product.id} product={product} />)}
                {!report.products.some((p) => p.routine === routine || p.routine === "AM/PM") && (
                  <p className="muted">No products recommended for this routine yet.</p>
                )}
              </div>
            ))}
          </div>
          {report.warnings.length > 0 && (
            <aside className="callout" aria-label="Routine warnings">
              <h3>Routine warnings</h3>
              <ul>
                {report.warnings.map((warning, i) => (
                  <li key={i}>{warning}</li>
                ))}
              </ul>
            </aside>
          )}
        </>
      )}
    </section>
  );
}
