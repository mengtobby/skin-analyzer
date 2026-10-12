import { useId, useState } from "react";
import type { Ingredient } from "../protocol/types";
import { percent } from "../lib/format";

interface IngredientChipProps {
  ingredient: Ingredient;
}

export function IngredientChip({ ingredient }: IngredientChipProps) {
  const [open, setOpen] = useState(false);
  const id = useId();
  return (
    <div className="ingredient-disclosure">
      <button
        className="chip ingredient"
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((current) => !current)}
        title={[ingredient.rationale, ...ingredient.cautions].join("\n")}
      >
        {ingredient.name} <span className="mono">{percent(ingredient.score)}</span>
      </button>
      <div id={id} hidden={!open}>
        <p>{ingredient.rationale}</p>
        {ingredient.cautions.length > 0 && (
          <>
            <h3>Cautions</h3>
            <ul>
              {ingredient.cautions.map((caution, i) => (
                <li key={i}>{caution}</li>
              ))}
            </ul>
          </>
        )}
      </div>
    </div>
  );
}
