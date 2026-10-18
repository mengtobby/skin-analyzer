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
| GET    | `/api/report` | `Report` (latest; `null` before the first or after a clear) |
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
  "analyzed": true,                  // full analysis ran this frame AND quality passed
  "quality": null | {
    "ok": true, "score": 1.0, "issues": [],
    "brightness": 65.4, "evenness": 3.2, "face_size_px": 180.0,
    "yaw_deg": 0.0, "pitch_deg": 0.0
  },
  "metrics": null | {
    "overall": {"redness": 41.2, "texture": 22.0, "oiliness": 35.5, "pigmentation": 18.3},
    "zones":   {"forehead": {"redness": ..., "texture": ..., "oiliness": ..., "pigmentation": ...}, ...}
  },
  "perf": {
    "fps": 24.8, "latency_ms": 31.2,
    "stages_ms": {"landmarks": 8.1, "preprocess": 3.2, "quality": 0.5, "detect": 9.5, "track": 0.3, "metrics": 2.0, "encode": 4.4}
  }
}
```

### Server → client, text (JSON)

- On connect: `{"type": "status", "data": Health}`
- When findings change (normally about once per second): `{"type": "report", "data": Report | null}`.
  `null` is sent immediately when the server discards its findings after a reset or
  input switch, to sessions currently showing a report; clients must clear the
  findings they display. Sessions receive no null before their first report or
  after they have already cleared it, including connections made after a clear.

### Client → server, text (JSON)

- `{"type": "reset"}` — same as `POST /api/reset`.

### Analysis cadence and capture quality

Analysis runs every second frame by default, starting at frame index 0. Landmarks
and face geometry update every frame. On skipped frames, confirmed tracks are
reprojected at their filtered canonical centres without advancing their lifecycle,
and the last quality report and smoothed metrics are reused. Unexecuted stages
have zero timing.

`analyzed` is true only on frames where the full analysis ran and quality passed.
It is false on skipped frames, on quality-rejected frames, and without a face
(where `quality` is also null).

Failed quality suppresses detection, tracker updates and metric smoothing, and
`metrics` is null until a passing analysis. The freeze is bounded:

- Tracks stay frozen (reprojected) for up to the tracker's face-lost timeout
  (1.5 s by default). After that they are hidden and aged on analysis frames, so
  they expire normally.
- On `turned_away` frames, tracks are hidden immediately, because a 2D face frame
  cannot place lesions correctly on a turned face.
- Reports keep the last passing analysis while quality fails. Once the face has
  been absent for longer than the timeout, that analysis is discarded, so a
  returning (possibly different) person never sees earlier findings.

Quality `score` is in [0, 1], rounded to two decimals. Measurements are rounded
to one decimal. `brightness` and `evenness` use CIELAB L* units; `face_size_px`
is eye-corner distance. Yaw and pitch are approximate degrees.
`issues` contains zero or more of these codes:

| Code | Meaning / capture guidance |
|------|----------------------------|
| `too_dark` | Face is too dark; move into brighter light. |
| `too_bright` | Face is overexposed; reduce direct light. |
| `uneven_light` | Lighting differs across the face; use even frontal light. |
| `too_far` | Face is too small; move closer to the camera. |
| `turned_away` | Excessive yaw; face the camera. |
| `tilted` | Excessive pitch; hold the face level toward the camera. |
| `occluded` | Too little usable skin; uncover the face. |

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

## Input settings

- `GET /api/settings` returns `data: {"source": {"kind": "camera"|"url"|"file", "spec": string, "camera_index": integer|null}}`. The spec redacts stream passwords and query strings; camera_index is null for non-camera inputs.
- `GET /api/settings/cameras` returns `data: {"cameras": [{"index": integer, "width": integer, "height": integer, "active": boolean}]}`. Probes run serially, skip the active camera, and are cached for 10 seconds. The active camera uses its current frame size.
- `POST /api/settings/source` accepts exactly `{"kind":"camera","index":0}` (integer 0–9) or `{"kind":"url","url":"http://phone:8080/video"}`. URLs must use HTTP, HTTPS or RTSP, contain no whitespace, and be at most 2048 characters. File inputs cannot be selected through this endpoint.

A successful switch returns HTTP 200 with `data: {"source": SourceView, "saved": boolean}` and discards all current findings, tracks and scores. `saved: false` means the live input changed but its preference could not be saved. Raw stream credentials are never returned. Errors use the same envelope with `success: false`, `data: null`, and a friendly `error`: 403 for an untrusted Origin (same policy as reset), 409 for another input change in progress, 422 for invalid input, and 502 when the new input could not be opened.

## Browser security and development

Every `/api/*` HTTP request and `/ws/stream` handshake with
`Sec-Fetch-Site: cross-site` is rejected before handling: HTTP 403 with
`{"success":false,"data":null,"error":"Cross-site request blocked"}`, or WebSocket
close code 1008. Missing metadata and `same-origin`, `same-site`, and `none` pass
this check; existing Host and Origin restrictions still apply. Camera enumeration
also rejects a present, untrusted Origin before any camera probe.

Vite origins `http://localhost:5173` and `http://127.0.0.1:5173` are trusted only
in development mode (`--dev`, or `SKIN_DEV=true`, `1`, or `yes`). Development is
off by default; `SKIN_DEV=false`, `0`, or `no` disables it. `start.ps1 -Dev`
passes `--dev`. Explicit extra origins remain supported.

All HTTP responses, including static files and rejections, carry:

- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: no-referrer`
- `Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self' ws: wss:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'`

`POST /api/settings/source` accepts at most 4096 body bytes, including when
Content-Length is absent or understates the body. An oversized declared or
received body returns HTTP 413 with the normal error envelope and
`Request body must be at most 4096 bytes`. Malformed JSON, including excessive
nesting, returns the friendly invalid-input HTTP 422 envelope.
