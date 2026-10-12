import type { Ingredient } from "../protocol/types";
import { IngredientChip } from "./IngredientChip";

interface IngredientChipsProps {
  ingredients: Ingredient[];
}

export function IngredientChips({ ingredients }: IngredientChipsProps) {
  return (
    <div className="chips">
      {ingredients.map((ingredient) => (
        <IngredientChip ingredient={ingredient} key={ingredient.id} />
      ))}
    </div>
  );
}
