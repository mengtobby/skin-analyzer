# Skin Analyzer

Real-time, on-device skin analysis from your laptop camera. The app tracks facial skin features live (inflamed lesions, red marks, pigmentation, texture, fine lines, oiliness), scores them per facial zone, explains the likely causes, and suggests ingredients and example products.

> **Cosmetic guidance only — not a medical diagnosis.** Camera-based analysis is approximate. See a dermatologist for persistent, painful or changing lesions.

Everything runs locally. No frames leave the machine.

## Quick start (Windows)

```powershell
.\start.ps1                 # sets up .venv + frontend on first run, then opens the app window
.\start.ps1 -Source camera:1   # pick another camera
.\start.ps1 -Dev            # backend + Vite dev server with hot reload (http://localhost:5173)
```

Requirements: Python 3.12, Node 20+, a webcam. On first start the MediaPipe face model (~3.7 MB) is downloaded and verified against a pinned SHA-256.

Manual setup:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r backend\requirements.txt
npm --prefix frontend ci
npm --prefix frontend run build
cd backend
..\.venv\Scripts\python -m skin_analyzer --open
```

**For good results:** face a window or lamp so the light falls evenly on your face from the front. Sit about an arm's length from the camera, look straight ahead, and keep hair off your forehead.

The app checks every analysed frame for brightness, even lighting, face size and head pose. When a frame isn't usable, analysis pauses and the live view says what to fix (for example *Too dark — face a window or lamp*), rather than reporting shadows as skin findings.

## How it works

```
camera ─► capture thread (latest frame only)
            │
            ▼
  MediaPipe Face Landmarker (478 pts) ─► One-Euro smoothing
            │
            ▼
  canonical face frame: roll-corrected, scale-normalised analysis canvas
  + anatomical zones (forehead / nose / cheeks / chin)
  − always-shaded anatomy (nostrils, nasal sidewalls, nasal root), eyes, brows, lips
            │
            ▼
  preprocessing: white balance · glare suppression · sRGB → CIELAB
  (CPU backend, or a fused CUDA kernel via CuPy)
            │
            ▼
  capture-quality gate: brightness · evenness · face size · yaw/pitch
  (failing frames pause analysis and show guidance)
            │
            ▼
  detection: classical CIELAB detector  (+ YOLOv8-seg via ONNX Runtime if a model is present)
            │
            ▼
  tracking: per-lesion Kalman filters in face coordinates (stable IDs, no jitter)
  metrics:  redness · texture · oiliness · pigmentation per zone (0–100, smoothed)
            │
            ▼
  knowledge engine: findings → root-cause insights → ingredient & product matching
            │
            ▼
  FastAPI ─ WebSocket (binary JPEG + JSON header per frame, report ~1 Hz) ─► React dashboard
```

- **Face-relative coordinates.** Tracking and thresholds work in a coordinate frame tied to the eyes, with one unit equal to the distance between the outer eye corners (~90 mm). Head movement doesn't break tracks, and detector thresholds don't depend on how far you sit from the camera.
- **Contrast against your own skin.** Every feature is detected as a difference from your face's own local baseline in CIELAB: a* for inflammation, L* for pigment, high-pass energy for texture, and a Hessian ridge filter for fine lines. Fixed colour thresholds would break across skin tones and lighting; local contrast doesn't.
- **Calibrated on real frames.** Detector thresholds and score ranges were tuned on live webcam frames: false detections were measured on the real face as captured, and sensitivity by injecting realistic synthetic lesions into those same frames. Spots are seeded at a strict threshold and measured at half their own peak, so faint spots keep their true size and strong lesions aren't inflated by their surrounding redness.
- **Analysis cadence.** Heavy analysis runs every second frame; in between, tracked lesions are re-projected through the face landmarks, so overlays stay locked to the face at full frame rate.
- **Privacy.** Frames are never written to disk. The camera stream and reset endpoint only accept the app's own pages (origin and host checks). When the face has been gone for more than 1.5 s, all findings, tracks and scores are discarded, so the next person never sees earlier results.
- **Hardware acceleration.** ONNX Runtime uses the best available execution provider in this order: TensorRT → CUDA → DirectML → OpenVINO → CPU. On Intel Arc or other non-NVIDIA laptops, DirectML is used. The CUDA preprocessing kernel only activates when CuPy and an NVIDIA GPU are present.

The wire format is specified in [docs/PROTOCOL.md](docs/PROTOCOL.md).

## Configuration

`python -m skin_analyzer --help` lists all flags. Each flag also has a `SKIN_*` environment variable, for example `SKIN_SOURCE` or `SKIN_PORT`.

| Flag | Default | Notes |
|------|---------|-------|
| `--source` | `camera:0` | `camera:<index>`, `file:<video or image>`, or `url:<http\|https\|rtsp stream>` |
| `--detector` | `auto` | `classical`, `onnx`, or `auto` (ONNX model if present) |
| `--preprocess` | `auto` | `cpu`, `cuda`, or `auto` |
| `--width/--height/--fps` | 1280×720 @ 30 | capture request |
| `--no-mirror` | off | the selfie mirror view is the default |
| `--host/--port` | 127.0.0.1:8000 | binding to a non-loopback host exposes your camera to the network; the server warns |
| `--extra-origins` | — | extra trusted browser origins (comma-separated) |
| `--open` | off | open the dashboard in an Edge app window |

### Using a phone as the camera

Install an IP-camera app on your phone and keep the phone and laptop on the same Wi-Fi. Start the stream in the app, then run:

```powershell
.\start.ps1 -Source url:http://<phone-ip>:<port>/video
```

The exact stream path depends on the app. The HTTP stream is unencrypted over the local network, so use it only on trusted Wi-Fi. Apps exposing the phone as a virtual webcam work as `camera:<index>` instead.

## Optional: learned lesion model

Without a model, the classical detector is used. To add a YOLOv8-seg model trained on a skin-lesion dataset in Ultralytics format:

```powershell
pip install ultralytics          # separate environment recommended (pulls in PyTorch)
python tools\train_yolo_seg.py --data path\to\data.yaml --epochs 100
```

The script exports the model to `backend/models/skin_yolov8_seg.onnx`. `--detector auto` then uses it for papules, pustules, comedones and nodules, and keeps the classical detector for redness, pigmentation, texture and fine lines.

## Development

```powershell
.venv\Scripts\python -m pytest -q backend   # backend tests (no camera or model needed)
npm --prefix frontend test                  # frontend unit/component tests
npm --prefix frontend run build             # strict type-check + production build
npm --prefix frontend run e2e               # Playwright end-to-end (uses installed Edge, no camera)
npm --prefix frontend run coverage          # frontend coverage report
.venv\Scripts\python -m pytest -q backend --cov=skin_analyzer   # backend coverage (needs pytest-cov)
.venv\Scripts\python -m bandit -r backend\skin_analyzer          # security scan
```

The end-to-end suite starts the real backend on a still image with no face in it (`frontend/e2e/fixtures/no-face.png`), so it runs without a camera.

Layout:

```
backend/skin_analyzer/
  preprocessing/   white balance, glare suppression, CIELAB (CPU + CUDA backends)
  face/            landmarker, canonical geometry & zones, quality gate, smoothing, skin mask
  detection/       classical CIELAB detector, YOLOv8-seg ONNX detector
  tracking/        Kalman lesion tracker
  metrics/         per-zone skin scores + temporal smoothing
  knowledge/       conditions, ingredients, products (JSON) + analysis & recommender
  capture/         threaded camera / video sources
  pipeline/        frame analyzer, runner thread, wire protocol
  api/             FastAPI app (REST + WebSocket, origin-locked)
frontend/src/      React dashboard (live overlay, telemetry, insights, recommendations)
frontend/e2e/      Playwright end-to-end specs + no-face fixture
tools/             model training / export
```

## Limitations

- Scores are heuristic and not clinically calibrated. Treat them as relative indicators to track over time under similar lighting.
- A webcam can't see depth. Raised lesions are told apart from flat marks by colour contrast alone, so a learned model trained on labelled data does better.
- Calibration so far comes from one person in one lighting setup. Because every feature is measured against the person's own skin it should transfer, but other skin tones and cameras haven't been verified yet.
- Oiliness has not been calibrated (no shine was present during calibration).
- The nose tip, nostrils and nasal sidewalls are excluded from spot detection: on a webcam their shadows are indistinguishable from pigmented spots.
- The named products are examples of formulations that contain the suggested ingredients, not endorsements.
