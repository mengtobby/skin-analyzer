---
name: Skin Analyzer
description: A calm, private on-device skin scanner whose dotted face mesh is the brand.
colors:
  sage-mist: "#e8edea"
  sage-deep: "#52665c"
  surface: "#f7f9f7"
  surface-glass: "rgb(255 255 255 / 72%)"
  border: "#d4ddd6"
  control-border: "#758278"
  ink: "#141815"
  ink-hover: "#303c33"
  muted: "#536057"
  accent: "#b95729"
  accent-text: "#9c4520"
  peach: "#f4b08c"
  apricot: "#e8935f"
  ring-track: "#f3dfd2"
  success: "#286343"
  success-soft: "#e1eee4"
  warning: "#795015"
  warning-soft: "#f6e8cf"
typography:
  display:
    fontFamily: "'Urbanist Variable', 'Segoe UI', system-ui, sans-serif"
    fontSize: "clamp(2.8rem, 5vw, 5rem)"
    fontWeight: 600
    lineHeight: 1.05
    letterSpacing: "-0.035em"
  headline:
    fontFamily: "'Urbanist Variable', 'Segoe UI', system-ui, sans-serif"
    fontSize: "clamp(36px, 5vw, 56px)"
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: "-0.035em"
  title:
    fontFamily: "'Urbanist Variable', 'Segoe UI', system-ui, sans-serif"
    fontSize: "24px"
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: "-0.02em"
  body:
    fontFamily: "'Urbanist Variable', 'Segoe UI', system-ui, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.65
    fontFeature: "'tnum'"
  label:
    fontFamily: "'Urbanist Variable', 'Segoe UI', system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 600
    lineHeight: 1.4
  score:
    fontFamily: "'Urbanist Variable', 'Segoe UI', system-ui, sans-serif"
    fontSize: "2rem"
    fontWeight: 600
    lineHeight: 1.15
    fontFeature: "'tnum'"
rounded:
  field: "12px"
  inner: "20px"
  card: "28px"
  pill: "999px"
spacing:
  "1": "4px"
  "2": "8px"
  "3": "12px"
  "4": "16px"
  "5": "24px"
  "6": "32px"
  "7": "48px"
  "8": "64px"
components:
  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "#ffffff"
    typography: "{typography.label}"
    rounded: "{rounded.pill}"
    padding: "11px 22px"
    height: "44px"
  button-primary-hover:
    backgroundColor: "{colors.ink-hover}"
  button-cta:
    backgroundColor: "{colors.ink}"
    textColor: "#ffffff"
    rounded: "{rounded.pill}"
    padding: "6px 6px 6px 24px"
    height: "54px"
  button-cta-arrow:
    backgroundColor: "{colors.ink-hover}"
    textColor: "#ffffff"
    size: "36px"
  button-secondary:
    backgroundColor: "{colors.surface-glass}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "11px 22px"
    height: "44px"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "11px 22px"
  icon-button-ink:
    backgroundColor: "{colors.ink}"
    textColor: "#ffffff"
    size: "44px"
  chip:
    backgroundColor: "{colors.surface-glass}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "9px 18px"
    height: "44px"
  chip-pressed:
    backgroundColor: "{colors.ink}"
    textColor: "#ffffff"
  card:
    backgroundColor: "{colors.surface-glass}"
    rounded: "{rounded.card}"
    padding: "28px"
  card-solid:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.card}"
    padding: "28px"
  badge-neutral:
    backgroundColor: "{colors.sage-mist}"
    textColor: "{colors.muted}"
    rounded: "{rounded.pill}"
    padding: "4px 10px"
  badge-success:
    backgroundColor: "{colors.success-soft}"
    textColor: "{colors.success}"
    rounded: "{rounded.pill}"
    padding: "4px 10px"
  badge-warning:
    backgroundColor: "{colors.warning-soft}"
    textColor: "{colors.warning}"
    rounded: "{rounded.pill}"
    padding: "4px 10px"
  badge-dark:
    backgroundColor: "{colors.ink}"
    textColor: "#ffffff"
    rounded: "{rounded.pill}"
    padding: "4px 10px"
  floating-badge:
    backgroundColor: "{colors.ink}"
    textColor: "#ffffff"
    typography: "{typography.label}"
    rounded: "{rounded.pill}"
    padding: "10px 16px"
  nav-link:
    textColor: "{colors.muted}"
    typography: "{typography.label}"
    rounded: "{rounded.pill}"
    padding: "11px 16px"
    height: "48px"
  nav-link-active:
    backgroundColor: "{colors.ink}"
    textColor: "#ffffff"
  input-field:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.field}"
    padding: "12px 16px"
---

# Design System: Skin Analyzer

## Overview

**Creative North Star: "The Quiet Scanner"**

The scan is the brand. One dotted face-mesh grammar, built from the facial zones the backend actually measured, runs from the Start hero through the live camera to the captured results. Everything else is a calm frame around it: a sage-mist ground, frosted cards with generous 28px rounding and a soft offset shadow, black ink pills with round arrow buttons, peach fills and apricot donut rings, and dark floating badges with peach glyphs that sit beside the face and point at what they name. Urbanist, self-hosted, sets every word.

The mood is a private, unhurried check-in rather than a clinic or a beauty ad. Density is low: one primary action per view, wide gutters, short plain sentences in the product's fixed wording. Colour is restrained to a cool sage neutral world with a single warm family (peach, apricot, terracotta) that marks the scanner's attention. Ink black carries every committed action.

Imagery is only ever the user's own capture or the mesh drawn from it. There is no stock photography, no product shots and no illustrative people, and nothing on screen claims a number the report did not produce.

**Key Characteristics:**
- Dotted white mesh with peach vertices as the single recurring signature, derived from real zone polygons.
- Sage-mist ground, frosted white glass cards (72% white, 24px blur), soft sage-tinted offset shadows.
- Ink pills for actions; the CTA pill carries a round darker arrow disc.
- Peach is fill and glyph; apricot is the decorative gauge arc; terracotta is text-safe accent.
- Dark pill badges with peach icons placed beside the face, joined to their anchor by a thin leader line.
- Phone: floating frosted bottom nav pill of 48px icon targets.

## Colors

A cool sage neutral world with one warm peach-to-terracotta family that marks where the scanner is looking, and ink black for every action.

### Primary
- **Ink** (`ink`): primary buttons, CTA pills, pressed chips, the active nav pill, floating badges, round icon buttons, stepper progress and the progress bar fill. Also the body text colour (`--text` and `--progress` alias it). White on ink is 17.9:1.
- **Ink Lift** (`ink-hover`): hover state for every ink surface, and the resting fill of the CTA's arrow disc so it reads as a separate, slightly raised button inside the pill.

### Secondary
- **Peach** (`peach`): the warm fill. The inline scan pill in the hero headline, glyphs inside dark badges and icon discs (9.8:1 on ink), routine icon discs, mesh vertices on the Start illustration, the scan-sweep highlight on live vertices, stepper markers, the checked radio fill, the selection colour and the URL field focus halo. Never text on a light surface.
- **Apricot** (`apricot`): the donut gauge arc and list markers in results and treatments. Decorative only (2.3:1 on surface), so it never carries information on its own.
- **Ring Track** (`ring-track`): the pale peach full circle under every apricot arc (arc-to-track 1.9:1, kept at 1.6:1 minimum by test).

### Tertiary
- **Terracotta** (`accent`): the "skin" half of the wordmark, Start tip icons, input caret and accent-color for native controls, focus-ring tint. 4.45:1 on surface and 3.98:1 on sage-mist, so it is for large text, icons and non-text marks only.
- **Terracotta Text** (`accent-text`): links, form errors and invalid field borders; the text-safe accent (6.0:1 on surface, 5.4:1 on sage-mist).
- **Sage Deep** (`sage-deep`): the deep surface of the Start mesh-face card, as the outer stop of a soft radial glow that lifts toward the face centre. White mesh lines read at 6.2:1 against it.

### Neutral
- **Sage Mist** (`sage-mist`): page ground, under a faint fixed white radial bloom at the top left. Also neutral badge fill and hover fill for ghost and secondary buttons and nav links.
- **Mist Surface** (`surface`): solid card, field and header fill; the fallback whenever `backdrop-filter` is unsupported.
- **Frosted Glass** (`surface-glass`): default card, chip, secondary button, header and bottom-nav fill, always paired with `blur(24px) saturate(1.2)`.
- **Hairline** (`border`): dividers between tip columns, measurement rules, progress tracks, quiet outlines.
- **Control Edge** (`control-border`): unpressed chip outline, field and radio borders, scrollbar thumb. 3.8:1 on surface and 3.4:1 on sage-mist, meeting the 3:1 non-text minimum.
- **Muted Sage** (`muted`): secondary copy, captions, inactive nav and stepper labels. 5.6:1 on sage-mist, 6.2:1 on surface.
- **Status pairs**: `success` on `success-soft` (5.9:1) for "Camera connected" and saved states; `warning` on `warning-soft` (5.8:1) for reconnecting and caution badges.

### Data marker hues
Tracked-area markers, contours and list dots use a fixed categorical set per label, defined in `overlay/draw.ts` (`LABEL_COLORS`): rose papule, amber pustule, coral red mark, pink diffuse redness, umber hyperpigmentation, sky texture, lilac fine lines, grey comedone, red nodule. These encode data, not brand, and appear only on or about the capture.

### Named Rules
**The Ink Commits Rule.** Every committed action and every selected state is ink with white text. Peach and apricot never fill a button.

**The Two Terracottas Rule.** Text in the accent hue uses `accent-text`; `accent` is reserved for 18.7px-bold-and-larger type, icons and marks. Any new accent text must clear 4.5:1 against both sage-mist and surface.

**The Warm Means Attention Rule.** The warm family appears where the scanner is looking or measuring: mesh vertices, sweep, gauges, badge glyphs, the scan pill. It does not decorate chrome.

## Typography

**Display Font:** Urbanist Variable (self-hosted via `@fontsource-variable/urbanist`, with Segoe UI, system-ui)
**Body Font:** Urbanist Variable
**Label/Mono Font:** none distinct; tabular figures come from Urbanist's `tnum` (`font-variant-numeric: tabular-nums` is set on body)

**Character:** One geometric, slightly rounded sans for everything. Large headings are set tight (-0.035em) and weight 600 so they feel soft but sure; body copy runs open at 1.65 line height. No runtime font requests: the face ships with the app, offline.

### Hierarchy
- **Display** (600, clamp(2.8rem, 5vw, 5rem), 1.05): the Start hero headline only, balanced, holding the inline peach scan pill.
- **Headline** (600, clamp(36px, 5vw, 56px), 1.15): page h1 on Camera and Settings. Results and Treatments step down to clamp(1.8rem, 3vw, 2.5rem), -0.03em.
- **Title** (600, 24px, -0.02em): card and section h2; 20px for Start tip titles; 1.25rem for ingredient names; 17px h3 and 16px h4 at -0.02em.
- **Body** (400, 16px, 1.65): paragraphs and list items, capped at 75ch; hero lede 18px muted at 42ch.
- **Label** (600, 14px): nav links, floating badges, chips (16px inherited), stepper labels (14px, 12px on phones). Small badges are 600 at 12px. No uppercase, no tracking-out.
- **Score** (600, 2rem, tabular): the visible gauge value, followed by a 0.875rem muted "/ 100".
- **Wordmark** (650, 25px, -0.035em; 22px on phones): "skin" in terracotta, "analyzer" in ink.

### Named Rules
**The One Face Rule.** Urbanist is the only typeface. Do not add a serif, a mono, or a system display face for numbers; use tabular figures instead.

**The Sentence Case Rule.** Headings, labels and chips are sentence case in the product's own wording. No small-caps kickers above headings.

## Layout

Content sits in a centred 1180px column (`main` padding 48px 32px 64px; 32px 16px on phones, with 112px plus the safe-area inset reserved at the bottom for the floating nav). Spacing follows a 4/8/12/16/24/32/48/64px scale; cards pad 28px (20px under 640px), grids gap 24px, and page sections stack 32px apart (24px on phones).

The four-step stepper spans the column under the header as four equal segments. The Start hero is a two-column grid (1.1fr text, 1fr mesh card, 48px gap) that collapses to one column under 800px with the card capped at 480px. Camera is 1.7fr live panel beside a 260px-minimum guidance card. Results is 1.25fr map-and-list beside a 280px-minimum detail card, collapsing under 850px; the four score cards go 4-up, then 2-up. Ingredient cards auto-fit at 260px minimum and align their headers with a container query only when side by side. Morning and evening routines sit as two columns down to 540px.

Breakpoints in use: 540px, 600/640px, 800px, 850px, 900px, 1220px.

## Elevation & Depth

Depth is soft, sage-tinted and offset downward, layered with frosted translucency. Surfaces sit on the mist ground with a long diffuse shadow whose spread is negative, so the shadow pools below the card rather than haloing it. Glass cards add a 1px near-white edge (`rgb(255 255 255 / 75–85%)`) that reads as a lit rim. Nothing uses hard or coloured offset shadows.

### Shadow Vocabulary
- **Card rest** (`box-shadow: 0 18px 40px -20px rgb(31 48 40 / 28%)`): every card, the header pill, results map, list rows, recommendation row, routine headers.
- **Float** (`box-shadow: 0 12px 30px -12px rgb(31 48 40 / 35%)`): floating badges and the phone bottom nav, the things that hover over other content.
- **Focus** (`outline: 2px solid ink; outline-offset: 3px; box-shadow: 0 0 0 3px rgb(185 87 41 / 30%)`): global `:focus-visible`. Map markers and list rows use a 3px outline at 3px offset; the URL field adds a 4px peach halo.

### Named Rules
**The Frost Fallback Rule.** Any glass surface declares its solid `surface` fill first and switches to `surface-glass` plus `blur(24px) saturate(1.2)` only inside `@supports (backdrop-filter)`.

**The One Level Rule.** A card never sits inside a card. Inside a card, grouping uses hairline rules, spacing, or a single tinted callout without shadow.

## Shapes

Everything is soft. Cards, the results map and the Start mesh card use 28px; inner panels (live canvas, list rows, camera options, routine headers, warning callout, quality banner) use 20px, with the recommendation row at 24px; plain fields use 12px and the stream URL field 20px. Every button, chip, badge, nav link, header and bottom nav is a full pill (999px); icon buttons, arrow discs, icon discs, markers and stepper dots are circles. Strokes are 1px; selected rows and options show ink with an extra 1px inset ring instead of a thicker border. Icons are 24px line icons at 1.75 stroke with round caps and joins.

## Components

### Buttons
Tactile, confident and black.
- **Shape:** full pill (999px); 44px minimum at medium, 54px at large.
- **Primary:** ink fill, white 600 text, 11px 22px padding; 16px text and 15px 28px at large.
- **CTA:** ink pill with 24px left padding and a 36px round arrow disc in ink-lift tucked 6px from the right edge. Used once per view for the forward step ("Start analyzing", "Analyze my skin", "Start a new analysis"). The arrow is drawn by the component; label wording stays as written.
- **Hover / Focus:** ink surfaces lift to ink-hover; secondary and ghost fill with sage-mist. Global focus ring applies. Disabled is 50% opacity with `not-allowed`.
- **Secondary:** frosted glass pill with hairline border, for retreat and alternate actions ("Retake", "Back to results", "Cancel scan").
- **Ghost:** transparent until hover, for low-stakes controls ("Reset tracking").
- **Icon button:** 44px circle, ink (white glyph) or glass (control-edge border); always carries an accessible label.
- **Recommendation row:** a full-width glass pill row (24px radius) with a peach-glyph ink disc at left, label, and an ink arrow disc pushed right; leads from Results to Treatments.

### Chips
- **Style:** 44px pill, 9px 18px, 600 weight, frosted glass with control-edge border.
- **State:** `aria-pressed` toggles; pressed is solid ink with white text. Used as the single-select area filter under the results map, wrapping with 8px gaps inside a labelled group.
- **Static actives:** key-active tags in routines are non-interactive pill badges (8px 14px, control-edge border on sage-mist) and must not look pressable.

### Cards / Containers
- **Corner Style:** 28px.
- **Background:** frosted glass by default; solid surface variant where blur would muddy content.
- **Shadow Strategy:** Card rest (see Elevation).
- **Border:** 1px near-white rim.
- **Internal Padding:** 28px (20px under 640px); optional header row with a title and one action, 24px below.
- **Tinted callout:** the one permitted inset inside a card: peach at ~22% with a terracotta 1px border, 20px radius, no shadow, for "seek professional advice" warnings.

### Badges
- **Static badge:** 12px 600 pill, 4px 10px. Tones: neutral (sage-mist / muted), accent (peach / ink), success, warning, dark (ink / white). Optional 18px peach icon.
- **Connection status** uses success or neutral tone in the header's right slot.

### Floating Badges (signature)
Dark pills that label what the scan found, placed beside the face.
- **Style:** ink pill, 10px 16px, 14px 600 white text, 20px peach glyph, Float shadow; 12px text and 7px 10px on phones.
- **Placement:** computed by `lib/badgeLayout.ts`. Each badge goes in a column just outside the face box (12px gap) on the side of its anchor, flips sides when it will not fit or that side is full, keeps 8px from the frame edge, and stacks with the gap preserved, redistributing evenly only on overflow. Tracked-area markers are obstacles: a badge that would cover one moves vertically or switches sides until it is clear.
- **Leader line:** a 1px white (70%) line from the badge's inner edge to the measured anchor, ending in a 3px peach dot.
- **Single line:** text never wraps; width is capped to the space beside the face and truncates with an ellipsis. Widths are measured in the real font and re-measured once Urbanist has loaded.
- **Content:** only real data: the top three detected labels with counts on the live view; the selected area's name and confidence on results.

### Score Ring (donut gauge)
- **Geometry:** 100-unit viewBox, radius 42, 6-unit stroke, round cap, arc starting at 12 o'clock. 112px by default, 72px beside ingredient names.
- **Colour:** apricot arc on a ring-track circle.
- **Value as text:** the arc is decorative and hidden from assistive tech. The number is always visible text: below the ring as the Score style with "/ 100" in skin scores, or centred inside the ring (25-unit, 600, tabular) beside a visible "Recommendation match" label, mirrored by a visually hidden progress element.
- **Missing data:** an em dash and "Score unavailable", never an estimated arc.

### Inputs / Fields
- **Style:** surface fill, 1px control-edge border, 12px radius, 12px 16px padding; terracotta caret and accent colour.
- **Focus:** global ring; the stream URL field uses an ink outline with a 4px peach halo.
- **Error:** border and message in terracotta text; status messages in success green.
- **Radio options:** 60px-tall 20px-radius glass rows; 24px custom radio that fills peach with an ink check when chosen; the chosen row gets an ink border plus inset ring. Native radios return in forced-colours mode.

### Navigation
- **Desktop:** a frosted 999px header pill (80px tall, 20px from the top, Card rest shadow) holding the wordmark, icon-plus-label nav links (48px, muted, hover sage-mist), and a status slot at right. The active link is an ink pill with white text.
- **Phone (under 640px):** the same nav becomes a fixed, centred, frosted bottom pill 12px above the safe-area inset, with Float shadow and 48px circular icon-only targets; labels stay in the DOM as visually hidden text. The header keeps only the wordmark and status.
- **Stepper:** four equal labelled segments; 4px pill track at 55% hairline, ink fill animating its width; the current step shows an 8px peach dot with a 2px ink ring and 600-weight label. Completed steps are buttons.

### Face Mesh & Scan Sweep (signature)
- **Source:** `meshFromZones` joins each zone polygon's vertices, connects them to the zone centroid, and links each zone to its nearest neighbour; `meshFromFace` adds an 18-point oval at 46% of the face box, each point tied to its nearest zone vertex. The mesh is always derived from zone data (real, or a fixed synthetic face on Start), never a stock wireframe.
- **Stroke:** 1px white at ~65–75% opacity, dashed 3/4 on canvas and the results map, 2/5 on the Start illustration; vertices are 3px dots, white (90%) on captures, peach on the Start card, with landmark polylines (brows, eyes, nose, lips) in a 1.5px 2/3 dash and paler peach dots.
- **Scan sweep:** during the three-second scan, vertices above the sweep line turn peach with an 8px peach glow, and a 36px horizontal band of peach (0 to 30% to 0) travels down the face box. The band is skipped under reduced motion; the vertex colouring still shows progress, as does the ink progress bar.
- **Results:** the mesh overlays the captured photo beneath clickable 44px markers (data-hued dot with a 2px white ring), and the selected area's contour is outlined in its data hue.

## Do's and Don'ts

### Do:
- **Do** build every new surface from the sage-mist ground, frosted 28px cards with Card rest shadow, and ink pill actions.
- **Do** derive any face graphic from zone polygons through `meshFromZones` / `meshFromFace` and draw it with `drawFaceMesh` or the same dashed-white-and-dot styling.
- **Do** place floating badges with `layoutBadges`, beside the face, joined by a leader line, on one line, with markers passed as obstacles.
- **Do** print every score as visible text; the apricot arc only decorates it.
- **Do** use the CTA pill with its arrow disc for the single forward step on a view, and secondary glass pills for going back.
- **Do** keep 44px minimum targets (48px in navigation), `aria-pressed` on toggles, labelled icon-only buttons and live-region announcements for selection changes.
- **Do** honour `prefers-reduced-motion`: the global rule stops animations and transitions; gauge reveal (1.2s, cubic-bezier(.16, 1, .3, 1)), marker pulse (2.5s, twice), stepper width (300ms ease-out) and the sweep band all switch off.
- **Do** keep the privacy line and the cosmetic disclaimer visible where they are, and keep the product's existing wording.

### Don't:
- **Don't** nest a card inside a card; use rules, spacing or the single tinted callout.
- **Don't** put small uppercase eyebrow labels or kickers above headings.
- **Don't** use gradient-filled text; the only gradients are the page bloom, the deep-sage card glow and the sweep band.
- **Don't** use stock photography, people, product shots or illustrative faces other than the zone-derived mesh.
- **Don't** show a number, badge, gauge or marker that does not come from the capture's report; empty data shows an em dash.
- **Don't** let a floating badge sit on the face, cover a marker, wrap to two lines, or float without a leader to its anchor.
- **Don't** set accent-hue text in `accent` at body size, or any information in apricot or peach on a light surface.
- **Don't** fill buttons or chips with peach or apricot; selection is ink.
- **Don't** load fonts or assets from a CDN; the app must work offline under a strict CSP.
