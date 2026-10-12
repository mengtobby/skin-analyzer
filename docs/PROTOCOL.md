# Backend ⇄ Frontend Protocol (contract)

All coordinates are **pixels in the transmitted (already mirrored) JPEG frame**.
Enum strings are the `.value`s from `backend/skin_analyzer/domain.py`.

- Zones: `forehead | nose | left_cheek | right_cheek | chin | other`
- Labels: `papule | pustule | red_mark | diffuse_redness | hyperpigmentation | texture_irregularity | fine_lines | comedone | nodule`
- Condition ids (knowledge layer): `inflammatory_acne | comedonal_acne | post_inflammatory_erythema | diffuse_redness | hyperpigmentation | uneven_texture | dehydration_fine_lines | excess_sebum`

## REST (JSON envelope)

Every REST response is `{"success": bool, "data": <payload|null>, "error": <string|null>}`.

| Method | Path          | `data`                                   |
|--------|---------------|-------------------------------------------|
| GET    | `/api/health` | `Health`                                  |
| GET    | `/api/report` | `Report` (latest; `null` before the first) |
| POST   | `/api/reset`  | `{"reset": true}` — clears tracks/smoothing |

```jsonc
// Health
{
  "status": "ok",                      // "ok" | "degraded" (camera not delivering)
  "source": "camera:0",
  "camera_open": true,
  "frame_size": [1280, 720],
  "detector": "classical-cielab",
  "preprocessor": "cpu",
  "onnx_providers": ["DmlExecutionProvider", "CPUExecutionProvider"],
  "landmarker": "mediapipe-face-landmarker",
  "error": null                        // last pipeline error message, if any
}
```

## WebSocket `/ws/stream`

### Server → client, binary: one message per processed frame

```
bytes 0..3        uint32 little-endian N = header length
bytes 4..4+N      UTF-8 JSON FrameHeader
bytes 4+N..end    JPEG of the display frame (may be empty only if encoding failed)
```

```jsonc
// FrameHeader
{
  "type": "frame",
  "frame_id": 1234,
  "timestamp": 1728600000.123,          // seconds (unix)
  "width": 1280, "height": 720,
  "face": null | {
    "bbox": [x, y, w, h],
    "zones": [ {"zone": "forehead", "polygon": [[x, y], ...]}, ... ]
  },
  "tracks": [
    {
      "id": 7, "label": "papule", "confidence": 0.82, "zone": "left_cheek",
      "bbox": [x, y, w, h], "contour": [[x, y], ...], "size_mm": 4.2, "age": 34
    }
  ],
  "counts": {"papule": 2, "hyperpigmentation": 1},   // confirmed tracks per label
  "metrics": null | {
    "overall": {"redness": 41.2, "texture": 22.0, "oiliness": 35.5, "pigmentation": 18.3},
    "zones":   {"forehead": {"redness": ..., "texture": ..., "oiliness": ..., "pigmentation": ...}, ...}
  },
  "perf": {
    "fps": 24.8, "latency_ms": 31.2,
    "stages_ms": {"landmarks": 8.1, "preprocess": 3.2, "detect": 9.5, "track": 0.3, "metrics": 2.0, "encode": 4.4}
  }
}
```

### Server → client, text (JSON)

- On connect: `{"type": "status", "data": Health}`
- About once per second (and only when it changed): `{"type": "report", "data": Report}`

### Client → server, text (JSON)

- `{"type": "reset"}` — same as `POST /api/reset`.

## Report

```jsonc
{
  "generated_at": 1728600000.0,
  "face_detected": true,
  "findings": [
    {"condition": "inflammatory_acne", "title": "Inflammatory acne", "severity": "moderate",
     "score": 0.62, "count": 3, "zones": ["chin", "left_cheek"],
     "evidence": "3 inflamed lesions tracked (2 papules, 1 pustule) on chin, left cheek"}
  ],
  "insights": [
    {"condition": "inflammatory_acne", "title": "Inflammatory acne",
     "summary": "…", "mechanisms": ["…"], "contributing_factors": ["…"],
     "zone_notes": ["Chin/jawline: …"], "see_a_professional": "…"}
  ],
  "ingredients": [
    {"id": "salicylic_acid", "name": "Salicylic acid (BHA)", "score": 0.8,
     "rationale": "…", "cautions": ["…"]}
  ],
  "products": [
    {"id": "…", "name": "…", "brand": "…", "category": "cleanser|toner|serum|treatment|moisturizer|sunscreen",
     "routine": "AM|PM|AM/PM", "key_actives": ["Salicylic acid 2%"], "score": 0.77,
     "rationale": "…", "targets": ["inflammatory_acne"]}
  ],
  "warnings": ["Benzoyl peroxide and retinoids: use on alternate nights."],
  "disclaimer": "Cosmetic guidance only — not a medical diagnosis. …"
}
```

`severity` ∈ `mild | moderate | notable`. `findings`, `insights` are sorted by score desc;
`insights[i].condition` corresponds to a finding. `products` are at most 6, `ingredients` at most 6.
