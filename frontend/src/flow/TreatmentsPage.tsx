import type { Ingredient, Product } from "../protocol/types";
import type { AnalysisSnapshot } from "./snapshot";
import { Badge, Button, Card, ArrowLeftIcon, InfoIcon, RefreshIcon, SunIcon, MoonIcon } from "../ui";
import "./results.css";

/** The knowledge base joins one sentence per condition with "; " (e.g. "A: x; y.; B: z."),
 * so split only after a full stop; semicolons inside a sentence stay. */
function splitRationale(text: string): string[] {
  return text.split(/(?<=\.);\s*/).map(reason => reason.trim()).filter(Boolean);
}

/** Cautions every ingredient carries are shown once instead of on each card. */
function sharedCautions(ingredients: Ingredient[]): string[] {
  if (ingredients.length < 2) return [];
  return ingredients[0].cautions.filter(caution => ingredients.every(item => item.cautions.includes(caution)));
}

function IngredientCard({ ingredient, shared }: { ingredient: Ingredient; shared: string[] }) {
  const score = Math.round(Math.max(0, Math.min(1, ingredient.score)) * 100);
  const reasons = splitRationale(ingredient.rationale);
  const cautions = ingredient.cautions.filter(caution => !shared.includes(caution));
  return <Card title={ingredient.name} headingLevel={3}>
    {reasons.length > 1
      ? <ul className="ingredient-reasons">{reasons.map((reason, i) => <li key={i}>{reason}</li>)}</ul>
      : <p>{reasons[0] ?? ingredient.rationale}</p>}
    <div className="ingredient-score"><span>Recommendation match</span><span>{score}%</span></div>
    <progress max={100} value={score} aria-label={`${ingredient.name} recommendation match`} />
    {cautions.map((caution, i) => <p key={i} className="treatment-caution">{caution}</p>)}
  </Card>;
}

function RoutineProduct({ product }: { product: Product }) {
  return <Card className="routine-product"><p className="result-muted">{product.brand}</p>
    <h4>{product.name}</h4><Badge>{product.category}</Badge>
    <ul className="active-chips" aria-label="Key actives">{product.key_actives.map((active, i) => <li key={i}><Badge>{active}</Badge></li>)}</ul>
    <p>{product.rationale}</p></Card>;
}

function Routine({ products, morning }: { products: Product[]; morning: boolean }) {
  const items = products.filter(product => product.routine === (morning ? "AM" : "PM") || product.routine === "AM/PM");
  const name = morning ? "Morning" : "Evening";
  return <section aria-label={`${name} routine`}><h3 className="result-inline">{morning ? <SunIcon /> : <MoonIcon />}{name}</h3>
    <div className="routine-stack">{items.map(product => <RoutineProduct key={product.id} product={product} />)}</div>
    {!items.length && <p className="result-muted">No products suggested for this routine.</p>}</section>;
}

export function TreatmentsPage({ snapshot, onBack, onRestart }: {
  snapshot: AnalysisSnapshot; onBack: () => void; onRestart: () => void;
}) {
  const { report } = snapshot;
  const empty = !report.ingredients.length && !report.products.length;
  const shared = sharedCautions(report.ingredients);
  return <div className="analysis-results treatments-page">
    <header className="result-heading"><h1>Recommended treatments</h1><p>Cosmetic care suggestions to help you plan your next steps.</p></header>
    {empty && <Card title="No recommendations yet"><p>This capture did not produce ingredient or product suggestions. You can start a new analysis when you are ready.</p></Card>}
    {!!report.ingredients.length && <section><h2>Key ingredients</h2>
      {shared.map((caution, i) => <p key={i} className="treatment-note"><InfoIcon />{caution}</p>)}
      <div className="ingredient-grid">
      {report.ingredients.map(ingredient => <IngredientCard key={ingredient.id} ingredient={ingredient} shared={shared} />)}</div></section>}
    {!!report.products.length && <section><h2>Suggested routine</h2><div className="treatment-routines">
      <Routine products={report.products} morning /><Routine products={report.products} morning={false} /></div></section>}
    {!!report.warnings.length && <aside className="result-callout" aria-label="Routine warnings"><h2>A little care goes a long way</h2>
      <ul>{report.warnings.map((warning, i) => <li key={i}>{warning}</li>)}</ul></aside>}
    <aside className="result-disclaimer" aria-label="Disclaimer">{report.disclaimer}</aside>
    <footer className="result-actions"><Button variant="secondary" icon={<ArrowLeftIcon />} onClick={onBack}>Back to results</Button>
      <Button icon={<RefreshIcon />} onClick={onRestart}>Start a new analysis</Button></footer>
  </div>;
}
