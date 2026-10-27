# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

People who want a calm, private check-in on how their facial skin looks, using a laptop webcam or their phone camera as a stream. Today the author is the main user; the product is intended for real users later (confirmed 2026-10-26), so it must feel like a finished consumer app and use plain, approachable language.

## Product Purpose

Real-time, on-device skin analysis: the app tracks visible skin features (inflamed lesions, red marks, pigmentation, texture, fine lines, oiliness), scores them per facial zone, explains likely causes, and suggests ingredients and example routines. Success is a user who understands what the camera saw, trusts that it stayed private, and leaves with sensible cosmetic next steps.

## Positioning

Everything runs locally: no frames leave the machine, and captures live only in memory. Findings are tied to what this capture actually measured (tracked areas, zone scores, capture-quality checks), never to generic beauty claims.

## Operating Context

A guided four-step flow: Start (lighting and positioning tips) → Camera (live view, capture-quality guidance, three-second scan) → Results (captured face with clickable areas, details, overall scores) → Treatments (ingredients, morning/evening routine, warnings, disclaimer). A separate Settings page chooses a local camera or a phone/network stream. Used on desktop browsers and phone-sized screens.

## Capabilities and Constraints

- Backend streams frames with face box, facial zone polygons, tracked areas (bbox, contour, label, size, confidence) and overall metrics (redness, texture, oiliness, pigmentation, 0–100).
- Analysis pauses when capture quality fails and says what to fix.
- Captures are never saved to disk; changing input clears findings.
- Cosmetic guidance only, not a medical diagnosis; the disclaimer and the privacy line must always remain visible where they are today.
- All existing wording and the four-step flow are fixed unless the user changes them (confirmed 2026-10-26).
- Offline-capable: no runtime calls to external CDNs; strict Content-Security-Policy on the local server.

## Brand Commitments

- Name: Skin Analyzer (wordmark "skinanalyzer").
- Visual reference supplied by the user (2026-10-26): a soft "AI skincare app" look (sage-mist ground, frosted cards, generous rounding, peach/apricot accent, black pill and round arrow buttons, donut score gauges, dotted face-mesh scan overlay with floating dark badges, filter chips, floating bottom navigation on phones). Binding as the target vibe.

## Evidence on Hand

- No stock photography, testimonials or product photos. Imagery is the user's own capture only (confirmed 2026-10-26); never add stock people or fabricated results.
- Synthetic face fixture for screenshots and tests: `frontend/e2e/fixtures/`.

## Product Principles

1. Private by construction: say so plainly and never imply data leaves the device.
2. Show what was measured: every visual claim (badge, gauge, marker) maps to real report data.
3. Calm guidance over alarm: cosmetic, non-diagnostic language; professional advice for persistent concerns.
4. Quality before verdicts: when capture conditions are poor, guide the user instead of reporting.

## Accessibility & Inclusion

WCAG 2.2 AA (contrast, focus order, live-region announcements, keyboard operation of markers and steps), as established by the earlier accessibility pass. Respect reduced-motion preferences. Works across skin tones; calibration beyond one person is still unverified.
