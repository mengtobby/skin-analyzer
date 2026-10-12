import type { Product } from "../protocol/types";
import { percent } from "../lib/format";

interface ProductCardProps {
  product: Product;
}

export function ProductCard({ product }: ProductCardProps) {
  return (
    <article className="product-card">
      <div className="product-meta">
        <span>{product.brand}</span>
        <span>{product.category} / {product.routine}</span>
        <span className="mono">{percent(product.score)}</span>
      </div>
      <h4>{product.name}</h4>
      <div className="chips">
        {product.key_actives.map((active) => (
          <span className="chip" key={active}>
            {active}
          </span>
        ))}
      </div>
      <p>{product.rationale}</p>
    </article>
  );
}
