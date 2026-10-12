"""Rank ingredient and product options and explain routine cautions."""
from __future__ import annotations

from collections import Counter
from itertools import combinations
from typing import Sequence

from .kb import KnowledgeBase, Product
from .models import Finding, IngredientRecommendation, ProductRecommendation

ACIDS = frozenset({"salicylic_acid", "glycolic_acid", "lactic_acid"})
RETINOIDS = frozenset({"adapalene", "retinol"})


def _ingredients(findings: Sequence[Finding], kb: KnowledgeBase
                 ) -> tuple[IngredientRecommendation, ...]:
    scores: Counter[str] = Counter()
    reasons: dict[str, list[str]] = {}
    for finding in findings:
        for target in kb.conditions[finding.condition].ingredient_targets:
            scores[target.id] += finding.score * target.weight
            reasons.setdefault(target.id, []).append(f"{finding.title}: {target.rationale}")
    maximum = max(1.0, max(scores.values(), default=0.0))
    ranked = sorted(scores, key=lambda key: (-scores[key], key))[:6]
    return tuple(IngredientRecommendation(
        key, kb.ingredients[key].name, scores[key] / maximum,
        "; ".join(reasons[key]), tuple(kb.ingredients[key].cautions),
    ) for key in ranked if scores[key] > 0)


def _product(product: Product, scores: dict[str, float], findings: Sequence[Finding],
             kb: KnowledgeBase) -> ProductRecommendation:
    active_scores = sorted((scores.get(a, 0.0) for a in product.actives), reverse=True)
    score = sum(s * w for s, w in zip(active_scores, (1.0, 0.5, 0.25)))
    targets = tuple(f.condition for f in findings if any(
        t.id in product.actives and t.id in scores
        for t in kb.conditions[f.condition].ingredient_targets))
    names = ", ".join(kb.conditions[t].title for t in targets)
    rationale = f"Ingredient options targeting {names}." if names else (
        "Gentle routine maintenance and daily barrier care." if product.category != "sunscreen"
        else "Daily sun protection for maintenance and to limit UV-related discoloration."
    )
    return ProductRecommendation(product.id, product.name, product.brand, product.category,
                                 product.routine, tuple(product.key_actives), score,
                                 rationale, targets)


def _select(findings: Sequence[Finding], scores: dict[str, float], kb: KnowledgeBase
            ) -> tuple[ProductRecommendation, ...]:
    ranked = sorted((_product(p, scores, findings, kb) for p in kb.products.values()),
                    key=lambda p: (-p.score, p.id))
    if not findings:
        return tuple(next(p for p in ranked if p.category == category and
                          not (set(kb.products[p.id].actives) & (ACIDS | RETINOIDS)))
                     for category in ("cleanser", "moisturizer", "sunscreen"))
    selected: list[ProductRecommendation] = []
    counts: Counter[str] = Counter()
    for product in ranked:
        if product.score > 0 and counts[product.category] < 2:
            selected.append(product)
            counts[product.category] += 1
        if len(selected) == 6:
            break
    actives = set(scores) | {a for p in selected for a in kb.products[p.id].actives}
    sun_needed = bool(actives & (ACIDS | RETINOIDS)) or any(
        f.condition in {"hyperpigmentation", "post_inflammatory_erythema"} for f in findings)
    if sun_needed and not any(p.category == "sunscreen" for p in selected):
        sunscreen = next(p for p in ranked if p.category == "sunscreen")
        selected = selected[:5] + [sunscreen]
    return tuple(sorted(selected, key=lambda p: (-p.score, p.id)))


def _warnings(products: Sequence[ProductRecommendation], kb: KnowledgeBase
              ) -> tuple[str, ...]:
    actives = {a for p in products for a in kb.products[p.id].actives}
    warnings: list[str] = []
    if "benzoyl_peroxide" in actives and actives & RETINOIDS:
        warnings.append("Benzoyl peroxide and retinoids: use on alternate nights to limit "
                        "irritation; prescribed combination products may be used as directed.")
    if len(actives & ACIDS) > 1:
        warnings.append("Multiple exfoliating acids: do not layer; choose one and introduce slowly.")
    if actives & RETINOIDS:
        warnings.append("Retinoids: avoid in pregnancy or when planning pregnancy.")
    if {"vitamin_c", "benzoyl_peroxide"} <= actives:
        warnings.append("Vitamin C and benzoyl peroxide: use at separate times.")
    for left, right in combinations(sorted(actives), 2):
        conflict = (right in kb.ingredients[left].conflicts or
                    left in kb.ingredients[right].conflicts)
        covered = ({left, right} <= ACIDS or
                   ("benzoyl_peroxide" in {left, right} and
                    bool({left, right} & (RETINOIDS | {"vitamin_c"}))))
        if conflict and not covered:
            warnings.append(f"{kb.ingredients[left].name} and {kb.ingredients[right].name}: "
                            "introduce separately and monitor irritation.")
    return tuple(dict.fromkeys(warnings))


def recommend(findings: Sequence[Finding], kb: KnowledgeBase
              ) -> tuple[tuple[IngredientRecommendation, ...],
                         tuple[ProductRecommendation, ...], tuple[str, ...]]:
    ingredients = _ingredients(findings, kb)
    products = _select(findings, {i.id: i.score for i in ingredients}, kb)
    return ingredients, products, _warnings(products, kb)
