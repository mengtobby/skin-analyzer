"""Translate confirmed observations into cosmetic findings."""
from __future__ import annotations

from collections import Counter
from math import exp, isfinite
from time import time
from typing import Sequence

from ..domain import DetectionClass, FaceZone, SkinMetrics, Track
from .kb import KnowledgeBase
from .models import Finding, Insight, Report
from .recommender import recommend

RULES = {
    "inflammatory_acne": (("papule", "pustule", "nodule"), None, None),
    "comedonal_acne": (("comedone",), None, None),
    "post_inflammatory_erythema": (("red_mark",), "redness", None),
    "diffuse_redness": (("diffuse_redness",), "redness", 55),
    "hyperpigmentation": (("hyperpigmentation",), "pigmentation", 55),
    "uneven_texture": (("texture_irregularity",), "texture", 50),
    "dehydration_fine_lines": (("fine_lines",), None, None),
    "excess_sebum": ((), "oiliness", 40),
}
DISCLAIMER = (
    "Cosmetic guidance only - not a medical diagnosis. Camera-based analysis is "
    "approximate; consult a dermatologist for persistent, painful or changing lesions."
)


def _validate(tracks: Sequence[Track], metrics: SkinMetrics | None) -> None:
    for track in tracks:
        if not isinstance(track.label, DetectionClass) or not isinstance(track.zone, FaceZone):
            raise ValueError("Track label and zone must use domain enums")
        if not isfinite(track.confidence) or not 0 <= track.confidence <= 1:
            raise ValueError("Track confidence must be finite and between 0 and 1")
    if metrics is None:
        return
    for zone, values in metrics.zones.items():
        if not isinstance(zone, FaceZone):
            raise ValueError("Metric zones must use FaceZone")
    for values in (metrics.overall, *metrics.zones.values()):
        for value in (values.redness, values.texture, values.oiliness, values.pigmentation):
            if not isfinite(value) or not 0 <= value <= 100:
                raise ValueError("Skin metric values must be finite and between 0 and 100")


def _metric(condition: str, field: str | None,
            metrics: SkinMetrics | None) -> float:
    if metrics is None or field is None:
        return 0.0
    if condition == "excess_sebum":
        values = [m.oiliness for z, m in metrics.zones.items()
                  if z in {FaceZone.FOREHEAD, FaceZone.NOSE, FaceZone.CHIN}]
        return max(values) if values else metrics.overall.oiliness
    return float(getattr(metrics.overall, field))


def _finding(condition: str, tracks: Sequence[Track], metrics: SkinMetrics | None,
             kb: KnowledgeBase) -> Finding | None:
    labels, field, threshold = RULES[condition]
    matched = [t for t in tracks if t.confirmed and t.label.value in labels]
    value = _metric(condition, field, metrics)
    metric_trigger = threshold is not None and value >= threshold
    if not matched and not metric_trigger:
        return None
    counts = Counter(t.label.value for t in matched)
    zones = {t.zone for t in matched}
    if metric_trigger and metrics is not None:
        zones.update(z for z, m in metrics.zones.items()
                     if getattr(m, field) >= threshold and
                     (condition != "excess_sebum" or z in
                      {FaceZone.FOREHEAD, FaceZone.NOSE, FaceZone.CHIN}))
    ordered = tuple(z for z in FaceZone if z in zones)
    count = len(matched)
    confidence = sum(t.confidence for t in matched) / count if count else 0.0
    # Saturation prevents dense detections from dominating; metrics are heuristic.
    lesion_score = (1 - exp(-count / 3)) * (0.5 + 0.5 * confidence)
    score = 1 - (1 - lesion_score) * (1 - 0.6 * value / 100)
    severity = "mild" if score < 0.35 else "moderate" if score < 0.65 else "notable"
    evidence = [f"{n} {label.replace('_', ' ')}" for label, n in sorted(counts.items())]
    if field and (metric_trigger or value > 0):
        scope = "T-zone maximum" if condition == "excess_sebum" else "overall"
        evidence.append(f"{scope} {field}: {value:.1f}/100 (camera estimate)")
    location = ", ".join(z.value.replace('_', ' ') for z in ordered)
    text = "; ".join(evidence) + (f"; observed on {location}" if location else "")
    return Finding(condition, kb.conditions[condition].title, severity, score,
                   count, ordered, text)


def _insight(finding: Finding, kb: KnowledgeBase) -> Insight:
    data = kb.conditions[finding.condition]
    notes = tuple(data.zone_notes[z.value] for z in finding.zones
                  if z.value in data.zone_notes)
    return Insight(data.id, data.title, data.summary, tuple(data.mechanisms),
                   tuple(data.contributing_factors), notes, data.see_a_professional)


def generate_report(tracks: Sequence[Track], metrics: SkinMetrics | None,
                    kb: KnowledgeBase, now: float | None = None,
                    face_detected: bool = True) -> Report:
    _validate(tracks, metrics)
    timestamp = time() if now is None else float(now)
    if not isfinite(timestamp) or timestamp < 0:
        raise ValueError("Report timestamp must be finite and nonnegative")
    if not isinstance(face_detected, bool):
        raise ValueError("face_detected must be a boolean")
    findings = tuple(sorted(
        (f for c in RULES if (f := _finding(c, tracks, metrics, kb)) is not None),
        key=lambda f: (-f.score, f.condition),
    )) if face_detected else ()
    insights = tuple(_insight(f, kb) for f in findings)
    ingredients, products, warnings = recommend(findings, kb)
    return Report(timestamp, face_detected, findings, insights, ingredients,
                  products, warnings, DISCLAIMER)
