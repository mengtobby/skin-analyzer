"""Training-free skin feature detector working in CIELAB on the canonical face canvas.

Each feature is found as a local *contrast* against the face's own baseline rather than
an absolute colour, so it adapts to skin tone and lighting:

* inflammation  -> a* (red-green) above a masked local baseline
* pustule head  -> bright, yellow-shifted core (L*, b*) inside an inflamed lesion
* pigmentation  -> L* below baseline without elevated a*
* texture       -> high-pass L* energy relative to the face median
* fine lines    -> Hessian ridge response (dark, thin, elongated valleys)

Thresholds are multiples of a robust (MAD) noise estimate with absolute floors.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from ..domain import ZONE_IDS, Detection, DetectionClass, FaceZone
from .base import MM_PER_UNIT, DetectorInput, component_to_detection


# Reject diffuse flush or shadow whose hysteresis extent dwarfs any lesion.
MAX_EXTENT_FACTOR = 3.0


@dataclass(frozen=True)
class ClassicalParams:
    denoise_sigma: float = 1.0
    local_sigma_units: float = 0.10
    broad_sigma_units: float = 0.30
    boundary_units: float = 0.035
    # Calibrated on real 1280x720 webcam frames in even frontal light (local noise:
    # sigma L* ~2.0, sigma a* ~1.1) against synthetic lesions injected into those frames:
    # ~0.7 raw false detections/frame on clear skin; recall 100% for +9 a* red lesions,
    # 98% for -10 L* / 68% for -8 L* pigmented spots (2.5 mm radius).
    red_k: float = 3.5
    red_floor: float = 5.0
    papule_k: float = 4.5
    papule_floor: float = 8.0
    pustule_l_floor: float = 5.0
    patch_k: float = 4.0  # cheeks are physiologically 3-5 a* redder than the forehead
    patch_floor: float = 6.0
    dark_k: float = 3.5
    dark_floor: float = 6.0
    lesion_diam_units: tuple[float, float] = (0.02, 0.10)
    patch_diam_units: tuple[float, float] = (0.12, 0.45)
    pigment_diam_units: tuple[float, float] = (0.03, 0.20)
    texture_ratio: float = 5.0
    texture_min_diam_units: float = 0.18
    ridge_k: float = 8.0
    line_min_len_units: float = 0.12
    line_min_aspect: float = 5.5
    hysteresis_ratio: float = 0.5  # region growth threshold as a fraction of the seed threshold
    max_per_class: int = 20
    enabled: frozenset[DetectionClass] = frozenset(DetectionClass)


def _robust_sigma(values: np.ndarray) -> float:
    if values.size < 10:
        return 1.0
    med = np.median(values)
    return float(1.4826 * np.median(np.abs(values - med))) + 1e-6


def masked_blur(img: np.ndarray, mask: np.ndarray, sigma_px: float) -> np.ndarray:
    """Normalised-convolution Gaussian: average of ``img`` over ``mask`` only.

    Computed at reduced resolution for large sigmas (keeps it ~O(1ms)).
    """
    h, w = img.shape[:2]
    factor = int(max(1, min(8, sigma_px // 4)))
    m = mask.astype(np.float32)
    x = img.astype(np.float32) * m
    if factor > 1:
        size = (max(1, w // factor), max(1, h // factor))
        x = cv2.resize(x, size, interpolation=cv2.INTER_AREA)
        m = cv2.resize(m, size, interpolation=cv2.INTER_AREA)
    s = sigma_px / factor
    num = cv2.GaussianBlur(x, (0, 0), s)
    den = cv2.GaussianBlur(m, (0, 0), s)
    out = num / np.maximum(den, 1e-4)
    if factor > 1:
        out = cv2.resize(out, (w, h), interpolation=cv2.INTER_LINEAR)
    return out


def hysteresis(strong: np.ndarray, weak: np.ndarray) -> np.ndarray:
    """Keep the connected regions of ``weak`` that contain at least one ``strong`` pixel.

    Strict seeds control false positives; growing to the weak threshold recovers a
    soft-edged spot's true extent, so size filters see its real size.
    """
    count, labels = cv2.connectedComponents(weak.astype(np.uint8), connectivity=8)
    seeded = np.zeros(count, bool)
    seeded[labels[strong & weak]] = True
    seeded[0] = False
    return seeded[labels]


def _diameter_units(area_px: float, ppu: float) -> float:
    return 2.0 * np.sqrt(area_px / np.pi) / ppu


def _confidence(peak: float, threshold: float) -> float:
    return float(np.clip(1.0 - np.exp(-1.5 * (peak / max(threshold, 1e-6))), 0.3, 0.99))


class ClassicalDetector:
    name = "classical-cielab"

    def __init__(self, params: ClassicalParams | None = None) -> None:
        self.p = params or ClassicalParams()

    def detect(self, inp: DetectorInput) -> list[Detection]:
        ppu = inp.region.canvas.px_per_unit
        skin = inp.zone_map > 0
        if skin.sum() < 500:
            return []
        lab = cv2.GaussianBlur(inp.canvas_lab, (0, 0), self.p.denoise_sigma)
        L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
        dist = cv2.distanceTransform(skin.astype(np.uint8), cv2.DIST_L2, 3)
        core = dist >= self.p.boundary_units * ppu

        local_sigma = self.p.local_sigma_units * ppu
        dL = L - masked_blur(L, skin, local_sigma)
        da = a - masked_blur(a, skin, local_sigma)
        db = b - masked_blur(b, skin, local_sigma)
        sig_a = _robust_sigma(da[core])
        sig_l = _robust_sigma(dL[core])

        ctx = _Ctx(inp, ppu, core, dL, da, db, sig_a, sig_l)
        on = self.p.enabled
        found: list[Detection] = []
        if on & {DetectionClass.PAPULE, DetectionClass.PUSTULE, DetectionClass.RED_MARK}:
            found += self._inflammatory(ctx)
        if DetectionClass.DIFFUSE_REDNESS in on:
            found += self._diffuse_redness(ctx, a, skin)
        if DetectionClass.HYPERPIGMENTATION in on:
            found += self._pigmentation(ctx)
        if DetectionClass.TEXTURE in on:
            found += self._texture(ctx, L)
        if DetectionClass.FINE_LINES in on:
            found += self._fine_lines(ctx, L)
        return [d for d in found if d.label in on]

    # -- individual feature finders -------------------------------------------------

    def _components(self, mask: np.ndarray, diam_range: tuple[float, float], ppu: float):
        n, labels, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
        for i in range(1, n):
            x, y, w, h, area = stats[i]
            d = _diameter_units(area, ppu)
            if not (diam_range[0] <= d <= diam_range[1]):
                continue
            sl = (slice(y, y + h), slice(x, x + w))
            yield labels[sl] == i, sl, (int(x), int(y)), d

    def _half_max_components(self, mask: np.ndarray, strength: np.ndarray, floor: float,
                             seed_threshold: float, diam_range: tuple[float, float], ppu: float):
        """Yield seeded spot cores, bounded in full extent and measured at their own half peak."""
        n, labels, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
        for i in range(1, n):
            x, y, w, h, area = stats[i]
            if _diameter_units(area, ppu) > MAX_EXTENT_FACTOR * diam_range[1]:
                continue
            sl = (slice(y, y + h), slice(x, x + w))
            comp = labels[sl] == i
            values = strength[sl]
            peak = float(values[comp].max())
            if peak <= seed_threshold:
                continue
            # Keep weaker neighbours visible even when the highest peak's half
            # maximum exceeds their seed. Each piece supplies its own peak below.
            split_level = max(floor, min(seed_threshold, 0.5 * peak))
            # Strict comparison excludes plateaus exactly at the split level.
            core = comp & (values > split_level)
            count, parts = cv2.connectedComponents(core.astype(np.uint8), connectivity=8)
            _, owners = cv2.distanceTransformWithLabels(
                (~core).astype(np.uint8), cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL
            )
            # Map nearest core pixels to the same 8-connected parts used above.
            part_by_owner = np.zeros(int(owners.max()) + 1, dtype=parts.dtype)
            part_by_owner[owners[core]] = parts[core]
            owners = part_by_owner[owners]
            for j in range(1, count):
                part = parts == j
                local_peak = float(values[part].max())
                if local_peak <= seed_threshold:
                    continue
                peak_at = np.unravel_index(np.argmax(np.where(part, values, -np.inf)), part.shape)
                extent = comp & (owners == owners[peak_at])
                extent &= values >= max(floor, 0.5 * local_peak)
                _, refined = cv2.connectedComponents(extent.astype(np.uint8), connectivity=8)
                piece = refined == refined[peak_at]
                d = _diameter_units(float(piece.sum()), ppu)
                if diam_range[0] <= d <= diam_range[1]:
                    yield piece, sl, (int(x), int(y)), d

    def _emit(self, ctx, comp, sl, off, label, conf, feats) -> Detection | None:
        return component_to_detection(
            comp, off, label, conf, ctx.inp.zone_map[sl], ctx.inp.region, feats
        )

    def _inflammatory(self, ctx: "_Ctx") -> list[Detection]:
        p = self.p
        thr = max(p.red_floor, p.red_k * ctx.sig_a)
        papule_thr = max(p.papule_floor, p.papule_k * ctx.sig_a)
        bright_thr = max(p.pustule_l_floor, 2.5 * ctx.sig_l)
        strong = (ctx.da > thr) & ctx.core
        weak = (ctx.da > p.hysteresis_ratio * thr) & ctx.core
        mask = cv2.morphologyEx(
            hysteresis(strong, weak).astype(np.uint8), cv2.MORPH_OPEN, np.ones((2, 2), np.uint8)
        )
        out = []
        floor = p.hysteresis_ratio * thr
        for comp, sl, off, d in self._half_max_components(mask, ctx.da, floor, thr,
                                                          p.lesion_diam_units, ctx.ppu):
            peak = float(ctx.da[sl][comp].max())
            grown = cv2.dilate(comp.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
            head = (ctx.dL[sl] > bright_thr) & (ctx.db[sl] > 1.5) & grown
            if head.sum() >= 2 and peak >= thr * 1.2:
                label = DetectionClass.PUSTULE
            elif peak >= papule_thr:
                label = DetectionClass.PAPULE
            else:
                label = DetectionClass.RED_MARK
            feats = {"peak_delta_a": peak, "diameter_mm": d * MM_PER_UNIT,
                     "mean_delta_a": float(ctx.da[sl][comp].mean())}
            det = self._emit(ctx, comp, sl, off, label, _confidence(peak, thr), feats)
            if det:
                out.append(det)
        return self._top(out)

    def _diffuse_redness(self, ctx: "_Ctx", a: np.ndarray, skin: np.ndarray) -> list[Detection]:
        p = self.p
        broad = masked_blur(a, skin, p.broad_sigma_units * ctx.ppu)
        face_mean = float(np.median(a[ctx.core]))
        excess = cv2.GaussianBlur(a, (0, 0), 3.0) - np.minimum(broad, face_mean)
        thr = max(p.patch_floor, p.patch_k * ctx.sig_a)
        mask = cv2.morphologyEx(
            ((excess > thr) & ctx.core).astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8)
        )
        out = []
        for comp, sl, off, d in self._components(mask, p.patch_diam_units, ctx.ppu):
            mean_ex = float(excess[sl][comp].mean())
            feats = {"mean_excess_a": mean_ex, "diameter_mm": d * MM_PER_UNIT}
            det = self._emit(ctx, comp, sl, off, DetectionClass.DIFFUSE_REDNESS,
                             _confidence(mean_ex, thr), feats)
            if det:
                out.append(det)
        return self._top(out)

    def _pigmentation(self, ctx: "_Ctx") -> list[Detection]:
        p = self.p
        thr = max(p.dark_floor, p.dark_k * ctx.sig_l)
        red_thr = max(p.red_floor, p.red_k * ctx.sig_a)
        brownish = (ctx.da < 0.6 * red_thr) & (ctx.db > -1.0) & ctx.core
        strong = (ctx.dL < -thr) & brownish
        weak = (ctx.dL < -p.hysteresis_ratio * thr) & brownish
        mask = cv2.morphologyEx(
            hysteresis(strong, weak).astype(np.uint8), cv2.MORPH_OPEN, np.ones((2, 2), np.uint8)
        )
        out = []
        floor = p.hysteresis_ratio * thr
        for comp, sl, off, d in self._half_max_components(mask, -ctx.dL, floor, thr,
                                                          p.pigment_diam_units, ctx.ppu):
            contours, _ = cv2.findContours(comp.astype(np.uint8), cv2.RETR_EXTERNAL,
                                           cv2.CHAIN_APPROX_NONE)
            c = max(contours, key=cv2.contourArea)
            perim = cv2.arcLength(c, True)
            circularity = 4 * np.pi * cv2.contourArea(c) / max(perim * perim, 1e-6)
            if circularity < 0.35:
                continue  # elongated dark edges are usually shadows, not spots
            depth = float(-ctx.dL[sl][comp].min())
            feats = {"delta_l": -depth, "diameter_mm": d * MM_PER_UNIT,
                     "circularity": float(circularity)}
            det = self._emit(ctx, comp, sl, off, DetectionClass.HYPERPIGMENTATION,
                             _confidence(depth, thr), feats)
            if det:
                out.append(det)
        return self._top(out)

    def _texture(self, ctx: "_Ctx", L: np.ndarray) -> list[Detection]:
        p = self.p
        hp = L - cv2.GaussianBlur(L, (0, 0), 3.0)
        energy = masked_blur(hp * hp, ctx.core, 8.0)
        med = float(np.median(energy[ctx.core])) + 1e-3
        mask = (energy > p.texture_ratio * med) & ctx.core
        out = []
        for comp, sl, off, d in self._components(mask, (p.texture_min_diam_units, 1.0), ctx.ppu):
            ratio = float(energy[sl][comp].mean() / med)
            feats = {"energy_ratio": ratio, "diameter_mm": d * MM_PER_UNIT}
            det = self._emit(ctx, comp, sl, off, DetectionClass.TEXTURE,
                             _confidence(ratio, p.texture_ratio), feats)
            if det:
                out.append(det)
        return self._top(out)

    def _fine_lines(self, ctx: "_Ctx", L: np.ndarray) -> list[Detection]:
        p = self.p
        g = cv2.GaussianBlur(L, (0, 0), 1.5)
        lxx = cv2.Sobel(g, cv2.CV_32F, 2, 0, ksize=3)
        lyy = cv2.Sobel(g, cv2.CV_32F, 0, 2, ksize=3)
        lxy = cv2.Sobel(g, cv2.CV_32F, 1, 1, ksize=3)
        ridge = (lxx + lyy) / 2 + np.sqrt(((lxx - lyy) / 2) ** 2 + lxy**2)
        allowed = np.isin(ctx.inp.zone_map, [ZONE_IDS[FaceZone.FOREHEAD],
                                             ZONE_IDS[FaceZone.LEFT_CHEEK],
                                             ZONE_IDS[FaceZone.RIGHT_CHEEK]]) & ctx.core
        if allowed.sum() < 100:
            return []
        vals = ridge[allowed]
        thr = float(np.median(vals)) + p.ridge_k * _robust_sigma(vals)
        mask = (ridge > thr) & allowed
        n, labels, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
        out = []
        for i in range(1, n):
            x, y, w, h, area = stats[i]
            if area < 6:
                continue
            sl = (slice(y, y + h), slice(x, x + w))
            comp = labels[sl] == i
            pts = np.column_stack(np.nonzero(comp)[::-1]).astype(np.float32)
            (_, _), (rw, rh), _ = cv2.minAreaRect(pts)
            length, width = max(rw, rh), max(min(rw, rh), 1.0)
            if length / ctx.ppu < p.line_min_len_units or length / width < p.line_min_aspect:
                continue
            strength = float(ridge[sl][comp].mean())
            feats = {"length_mm": float(length / ctx.ppu * MM_PER_UNIT),
                     "aspect": float(length / width)}
            det = self._emit(ctx, comp, sl, (int(x), int(y)), DetectionClass.FINE_LINES,
                             _confidence(strength, thr), feats)
            if det:
                out.append(det)
        return self._top(out)

    def _top(self, dets: list[Detection]) -> list[Detection]:
        return sorted(dets, key=lambda d: d.confidence, reverse=True)[: self.p.max_per_class]


@dataclass(frozen=True)
class _Ctx:
    inp: DetectorInput
    ppu: float
    core: np.ndarray
    dL: np.ndarray
    da: np.ndarray
    db: np.ndarray
    sig_a: float
    sig_l: float
