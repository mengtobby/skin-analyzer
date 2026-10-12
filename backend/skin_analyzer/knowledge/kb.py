"""Validated local dermatology reference data; no network needed at runtime."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Annotated, Any, Mapping

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ..domain import FaceZone

logger = logging.getLogger(__name__)
Text = Annotated[str, Field(min_length=1, pattern=r"\S")]
CONDITION_IDS = frozenset({
    "inflammatory_acne", "comedonal_acne", "post_inflammatory_erythema",
    "diffuse_redness", "hyperpigmentation", "uneven_texture",
    "dehydration_fine_lines", "excess_sebum",
})


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    id: str = Field(min_length=1)


class Target(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    id: str = Field(min_length=1)
    weight: float = Field(ge=0, le=1, allow_inf_nan=False)
    rationale: str = Field(min_length=1)


class Condition(Record):
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    mechanisms: list[Text] = Field(min_length=2, max_length=4)
    contributing_factors: list[Text] = Field(min_length=2, max_length=4)
    zone_notes: dict[str, Text]
    see_a_professional: str = Field(min_length=1)
    ingredient_targets: list[Target] = Field(min_length=1)


class Ingredient(Record):
    name: str = Field(min_length=1)
    function: str = Field(min_length=1)
    cautions: list[Text] = Field(min_length=1)
    conflicts: list[Text]


class Product(Record):
    name: str = Field(min_length=1)
    brand: str = Field(min_length=1)
    category: str
    routine: str
    actives: list[Text] = Field(min_length=1)
    key_actives: list[Text] = Field(min_length=1)


def _read(path: Path, model: type[BaseModel]) -> dict[str, Any]:
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(rows, list) or not rows:
            raise ValueError("expected a nonempty array of records")
        records = [model.model_validate(row) for row in rows]
        result = {record.id: record for record in records}
        if len(result) != len(records):
            raise ValueError("duplicate ids")
        return result
    except (OSError, ValueError, ValidationError) as exc:
        raise ValueError(f"Invalid knowledge data in {path.name}: {exc}") from exc


def _references(conditions: Mapping[str, Condition],
                ingredients: Mapping[str, Ingredient],
                products: Mapping[str, Product]) -> None:
    unknown = set(conditions) - CONDITION_IDS
    if unknown:
        raise ValueError(f"Unknown condition ids: {sorted(unknown)}")
    missing = CONDITION_IDS - set(conditions)
    if missing:
        raise ValueError(f"Missing condition ids: {sorted(missing)}")
    for condition in conditions.values():
        for zone in condition.zone_notes:
            if zone not in {z.value for z in FaceZone}:
                raise ValueError(f"Unknown zone {zone!r} in {condition.id}")
        _known([t.id for t in condition.ingredient_targets], ingredients, condition.id)
    for ingredient in ingredients.values():
        _known(ingredient.conflicts, ingredients, ingredient.id)
    for product in products.values():
        _known(product.actives, ingredients, product.id)
        if product.category not in {"cleanser", "toner", "serum", "treatment",
                                    "moisturizer", "sunscreen"}:
            raise ValueError(f"Invalid category in {product.id}")
        if product.routine not in {"AM", "PM", "AM/PM"}:
            raise ValueError(f"Invalid routine in {product.id}")
    for category in ("cleanser", "moisturizer", "sunscreen"):
        if not any(p.category == category for p in products.values()):
            raise ValueError(f"Missing baseline product category: {category}")


def _known(ids: list[str], ingredients: Mapping[str, Ingredient], owner: str) -> None:
    for ingredient_id in ids:
        if ingredient_id not in ingredients:
            raise ValueError(f"Unknown ingredient id {ingredient_id!r} in {owner}")


@dataclass(frozen=True)
class KnowledgeBase:
    conditions: Mapping[str, Condition]
    ingredients: Mapping[str, Ingredient]
    products: Mapping[str, Product]

    @classmethod
    def load(cls, data_dir: Path | None = None) -> KnowledgeBase:
        directory = data_dir if data_dir is not None else Path(__file__).parent / "data"
        conditions = _read(directory / "conditions.json", Condition)
        ingredients = _read(directory / "ingredients.json", Ingredient)
        products = _read(directory / "products.json", Product)
        _references(conditions, ingredients, products)
        logger.info("Loaded %d conditions and %d products", len(conditions), len(products))
        return cls(MappingProxyType(conditions), MappingProxyType(ingredients),
                   MappingProxyType(products))
