"""Immutable report values matching the public telemetry protocol."""
from __future__ import annotations

from dataclasses import dataclass

from ..domain import FaceZone


@dataclass(frozen=True)
class Finding:
    condition: str
    title: str
    severity: str
    score: float
    count: int
    zones: tuple[FaceZone, ...]
    evidence: str


@dataclass(frozen=True)
class Insight:
    condition: str
    title: str
    summary: str
    mechanisms: tuple[str, ...]
    contributing_factors: tuple[str, ...]
    zone_notes: tuple[str, ...]
    see_a_professional: str


@dataclass(frozen=True)
class IngredientRecommendation:
    id: str
    name: str
    score: float
    rationale: str
    cautions: tuple[str, ...]


@dataclass(frozen=True)
class ProductRecommendation:
    id: str
    name: str
    brand: str
    category: str
    routine: str
    key_actives: tuple[str, ...]
    score: float
    rationale: str
    targets: tuple[str, ...]


@dataclass(frozen=True)
class Report:
    generated_at: float
    face_detected: bool
    findings: tuple[Finding, ...]
    insights: tuple[Insight, ...]
    ingredients: tuple[IngredientRecommendation, ...]
    products: tuple[ProductRecommendation, ...]
    warnings: tuple[str, ...]
    disclaimer: str
