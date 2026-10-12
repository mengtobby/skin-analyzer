"""Knowledge engine contract and boundary tests."""
import json
from dataclasses import replace
from pathlib import Path

import pytest

from skin_analyzer.domain import DetectionClass, FaceZone, SkinMetrics, Track, ZoneMetrics
from skin_analyzer.knowledge import KnowledgeBase, generate_report, report_to_dict
from skin_analyzer.knowledge.recommender import _product, _warnings


@pytest.fixture
def kb() -> KnowledgeBase:
    return KnowledgeBase.load()


def track(label: DetectionClass = DetectionClass.PAPULE,
          zone: FaceZone = FaceZone.CHIN, confirmed: bool = True) -> Track:
    return Track(1, label, 0.9, (0, 0, 4, 4), (), zone, (0.0, 0.0),
                 2.0, 5, 5, 0, confirmed)


def metrics(**values: float) -> SkinMetrics:
    fields = dict(redness=0.0, texture=0.0, oiliness=0.0, pigmentation=0.0)
    fields.update(values)
    return SkinMetrics(ZoneMetrics(**fields), {})


def test_acne_report(kb: KnowledgeBase) -> None:
    report = generate_report([replace(track(), track_id=i) for i in range(3)],
                             metrics(), kb, now=100.0)
    finding = report.findings[0]
    assert finding.condition == "inflammatory_acne"
    assert finding.severity in {"moderate", "notable"}
    assert finding.count == 3 and finding.zones == (FaceZone.CHIN,)
    assert finding.evidence == "3 inflamed lesions tracked (3 papules) on chin"
    assert "Chin/jawline" in report.insights[0].zone_notes[0]
    assert {i.id for i in report.ingredients} & {"salicylic_acid", "benzoyl_peroxide"}
    assert any(p.category == "treatment" for p in report.products)
    assert any("alternate nights" in w for w in report.warnings)
    assert any("pregnancy" in w for w in report.warnings)


def test_mixed_lesion_evidence(kb: KnowledgeBase) -> None:
    tracks = [track(), replace(track(), track_id=2),
              replace(track(DetectionClass.PUSTULE, FaceZone.LEFT_CHEEK), track_id=3)]
    report = generate_report(tracks, None, kb)
    assert report.findings[0].evidence == (
        "3 inflamed lesions tracked (2 papules, 1 pustule) on left cheek, chin"
    )


def test_evidence_zones_follow_anatomical_order(kb: KnowledgeBase) -> None:
    tracks = [track(), replace(track(zone=FaceZone.FOREHEAD), track_id=2)]
    finding = generate_report(tracks, None, kb).findings[0]
    assert finding.zones == (FaceZone.FOREHEAD, FaceZone.CHIN)
    assert finding.evidence == (
        "2 inflamed lesions tracked (2 papules) on forehead, chin"
    )


def test_lesion_evidence_excludes_metric_only_zones(kb: KnowledgeBase) -> None:
    m = SkinMetrics(ZoneMetrics(61, 0, 0, 0), {
        FaceZone.FOREHEAD: ZoneMetrics(80, 0, 0, 0),
    })
    tracks = [track(DetectionClass.DIFFUSE_REDNESS, FaceZone.NOSE),
              replace(track(DetectionClass.DIFFUSE_REDNESS, FaceZone.CHIN,
                            confirmed=False), track_id=2),
              replace(track(zone=FaceZone.LEFT_CHEEK), track_id=3)]
    report = generate_report(tracks, m, kb)
    finding = next(f for f in report.findings if f.condition == "diffuse_redness")
    assert finding.count == 1
    assert finding.zones == (FaceZone.FOREHEAD, FaceZone.NOSE)
    assert finding.evidence == (
        "1 area of diffuse redness tracked on nose; "
        "Redness index 61/100 across the face"
    )


@pytest.mark.parametrize("label,description", [
    (DetectionClass.PAPULE, "1 inflamed lesion tracked (1 papule)"),
    (DetectionClass.PUSTULE, "1 inflamed lesion tracked (1 pustule)"),
    (DetectionClass.NODULE, "1 inflamed lesion tracked (1 nodule)"),
    (DetectionClass.COMEDONE, "1 comedone tracked"),
    (DetectionClass.RED_MARK, "1 red mark tracked"),
    (DetectionClass.DIFFUSE_REDNESS, "1 area of diffuse redness tracked"),
    (DetectionClass.HYPERPIGMENTATION, "1 area of hyperpigmentation tracked"),
    (DetectionClass.TEXTURE, "1 texture irregularity tracked"),
    (DetectionClass.FINE_LINES, "1 area with fine lines tracked"),
])
def test_singular_evidence(label: DetectionClass, description: str,
                           kb: KnowledgeBase) -> None:
    report = generate_report([track(label, FaceZone.LEFT_CHEEK)], None, kb)
    assert report.findings[0].evidence == f"{description} on left cheek"


def test_metric_evidence(kb: KnowledgeBase) -> None:
    report = generate_report([], metrics(redness=61), kb)
    assert report.findings[0].evidence == "Redness index 61/100 across the face"


@pytest.mark.parametrize("tracks", [[], [track()]])
def test_exact_disclaimer(tracks: list[Track], kb: KnowledgeBase) -> None:
    report = report_to_dict(generate_report(tracks, None, kb))
    assert report["disclaimer"] == (
        "Cosmetic guidance only — not a medical diagnosis. Camera-based analysis is "
        "approximate; consult a dermatologist for persistent, painful or changing lesions. "
        "Products are examples of formulations containing the suggested ingredients, "
        "not endorsements."
    )


def test_baseline_and_unconfirmed(kb: KnowledgeBase) -> None:
    report = generate_report([track(confirmed=False)], metrics(), kb)
    assert not report.findings and not report.insights and not report.ingredients
    assert {p.category for p in report.products} == {"cleanser", "moisturizer", "sunscreen"}
    assert all("maintenance" in p.rationale for p in report.products)
    assert not report.warnings


@pytest.mark.parametrize("label", list(DetectionClass))
def test_all_labels_have_findings(label: DetectionClass, kb: KnowledgeBase) -> None:
    report = generate_report([track(label)], None, kb)
    assert len(report.findings) == len(report.insights) == 1


@pytest.mark.parametrize("field,condition,threshold", [
    ("redness", "diffuse_redness", 55),
    ("pigmentation", "hyperpigmentation", 55),
    ("texture", "uneven_texture", 50),
    ("oiliness", "excess_sebum", 40),
])
def test_metric_thresholds(field: str, condition: str, threshold: float,
                           kb: KnowledgeBase) -> None:
    assert not generate_report([], metrics(**{field: threshold - 0.01}), kb).findings
    report = generate_report([], metrics(**{field: threshold}), kb)
    assert report.findings[0].condition == condition
    if condition == "hyperpigmentation":
        assert any(p.category == "sunscreen" for p in report.products)


def test_tzone_maximum(kb: KnowledgeBase) -> None:
    m = SkinMetrics(ZoneMetrics(0, 0, 90, 0), {
        FaceZone.CHIN: ZoneMetrics(0, 0, 39, 0),
        FaceZone.LEFT_CHEEK: ZoneMetrics(0, 0, 95, 0),
    })
    assert not generate_report([], m, kb).findings
    m = replace(m, zones={FaceZone.NOSE: ZoneMetrics(0, 0, 40, 0)})
    assert generate_report([], m, kb).findings[0].zones == (FaceZone.NOSE,)


def test_wire_shape(kb: KnowledgeBase) -> None:
    tracks = [track(label, FaceZone.LEFT_CHEEK) for label in DetectionClass]
    report = report_to_dict(generate_report(tracks, metrics(oiliness=80), kb, now=123.0))
    assert set(report) == {"generated_at", "face_detected", "findings", "insights",
                           "ingredients", "products", "warnings", "disclaimer"}
    assert len(report["ingredients"]) <= 6 and len(report["products"]) <= 6
    assert report["findings"][0]["zones"] == ["left_cheek"]
    assert set(report["products"][0]) == {"id", "name", "brand", "category", "routine",
                                          "key_actives", "score", "rationale", "targets"}
    assert all(sum(p["category"] == c for p in report["products"]) <= 2
               for c in {p["category"] for p in report["products"]})
    assert len(report["warnings"]) == len(set(report["warnings"]))
    json.dumps(report, allow_nan=False)


def test_invalid_references(monkeypatch: pytest.MonkeyPatch) -> None:
    directory = Path(__file__).parents[1] / "skin_analyzer" / "knowledge" / "data"
    contents = {p.name: p.read_text(encoding="utf-8") for p in directory.glob("*.json")}
    rows = json.loads(contents["conditions.json"])
    rows[0]["ingredient_targets"][0]["id"] = "unknown_active"
    contents["conditions.json"] = json.dumps(rows)
    def read_data(path: Path, encoding: str = "utf-8") -> str:
        return contents[path.name]
    monkeypatch.setattr(Path, "read_text", read_data)
    with pytest.raises(ValueError, match="Unknown ingredient id 'unknown_active'"):
        KnowledgeBase.load(Path("invalid-data"))


def test_invalid_input(kb: KnowledgeBase) -> None:
    with pytest.raises(ValueError, match="confidence"):
        generate_report([replace(track(), confidence=float("nan"))], None, kb)
    with pytest.raises(ValueError, match="metric"):
        generate_report([], metrics(redness=101), kb)
    with pytest.raises(ValueError, match="timestamp"):
        generate_report([], None, kb, now=float("inf"))
    assert not generate_report([track()], metrics(redness=90), kb,
                               face_detected=False).findings


def test_active_warnings(kb: KnowledgeBase) -> None:
    ids = ("effaclar_duo_us", "differin", "timeless_c", "pc_bha", "ordinary_glycolic")
    products = tuple(_product(kb.products[key], {}, (), kb) for key in ids)
    warnings = _warnings(products, kb)
    assert len(warnings) == 4
    assert any("alternate nights" in w for w in warnings)
    assert any("do not layer" in w for w in warnings)
    assert any("pregnancy" in w for w in warnings)
    assert any("Vitamin C" in w and "separate times" in w for w in warnings)


@pytest.mark.parametrize("change,message", [
    ("condition", "Unknown condition"),
    ("product", "Unknown ingredient"),
    ("weight", "Invalid knowledge data"),
])
def test_invalid_schema(change: str, message: str, monkeypatch: pytest.MonkeyPatch) -> None:
    directory = Path(__file__).parents[1] / "skin_analyzer" / "knowledge" / "data"
    rows = {p.name: json.loads(p.read_text(encoding="utf-8"))
            for p in directory.glob("*.json")}
    if change == "condition":
        rows["conditions.json"][0]["id"] = "unknown_condition"
    elif change == "product":
        rows["products.json"][0]["actives"] = ["unknown_ingredient"]
    else:
        rows["conditions.json"][0]["ingredient_targets"][0]["weight"] = 1.1
    def read_data(path: Path, encoding: str = "utf-8") -> str:
        return json.dumps(rows[path.name])
    monkeypatch.setattr(Path, "read_text", read_data)
    with pytest.raises(ValueError, match=message):
        KnowledgeBase.load(Path("invalid-data"))
