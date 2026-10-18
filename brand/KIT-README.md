# المخزن الذكي | Smart Warehouse — SW·Fleet

## Approved logo

**Concept 01: Lane Route** — warehouse roof and storage bay merged with one continuous yellow autonomous movement path terminating at a node. The symbol follows the approved visual identity moodboard, rebuilt as clean, editable vector geometry.

## Files

- `logo/horizontal.svg`: primary bilingual logo, Arabic first, fully outlined vector text (requires no fonts).
- `logo/stacked.svg`: centered stacked bilingual lockup, outlined.
- `logo/symbol.svg`: standalone symbol with transparent background.
- `logo/horizontal-monochrome.svg`, `logo/symbol-monochrome-navy.svg`: 1-color options.
- `logo/horizontal-on-navy.svg`, `logo/symbol-white.svg`, `logo/symbol-on-yellow.svg`: alternate surface treatments.
- `logo/*-editable-text.svg`: changeable wordmarks; text fonts depend on system availability.
- `logo/*png`: raster versions, logo icons, 16/32 px favicons.
- `logo/favicon.ico`: favicon bundle.
- `app-icons/ios-app-icon-1024.png`: square iOS master image (corner masks applied by OS/store); editable SVG included.
- `app-icons/android-adaptive-foreground-1024.png` and `android-adaptive-background-1024.png`: separate adaptive icon layers; matching SVG files included.
- `preview/brand-summary.png`: brand preview and selected logo on several surfaces.
- `tokens.json`: exact brand palette and font tokens.

## Brand colors — do not alter

| Token | Hex | Use |
|---|---|---|
| Slate Navy | #0C161E | Background/text |
| Steel Teal | #0F4C5C | Primary |
| Light Teal | #5DBACB | Dark-mode highlights |
| Forklift Yellow | #F5B400 | Small signature accents, robot ID |
| Ink Grey | #4A6070 | Secondary text |
| Mist | #F4F7F9 | Light background |
| Success | #16A34A | Operational success |
| Warning | #EA580C | Warning |
| Danger | #DC2626 | Emergency stop/fault ONLY |

## Typography

Target: **Thmanyah Sans** (Arabic UI and body), **Thmanyah Serif Text** (large Arabic headlines), **Lexend** (English). To make exported logos portable, the text on vector masters is outlined. The optional `*-editable-text.svg` files use `Noto Kufi Arabic` and `DejaVu Sans` as available stand-ins; for final UI implementation, use the requested Thmanyah/Lexend fonts when licensed and installed. No font files are included.

## Usage

- Keep free space of at least 1× the route end-node radius around the icon; recommended minimum app/icon size **24px**, absolute minimum **16px** for favicon only.
- Yellow must remain a sparse accent, never a full page fill except the dedicated yellow-background logo variant. Never use white text on yellow.
- Use **white** on Steel Teal, and **Slate Navy** on Light Teal / Forklift Yellow.
- Never use red as decoration. All maps/coordinates stay LTR even within Arabic RTL layout.
- Do not skew, apply gradients, replace colors, or place over noisy imagery without a solid protective panel.
- A light logo is supplied for dark backgrounds; do not simply put the dark original onto a navy surface.

## Project paths (integration suggestions)

- `docs/brand/logo/` — versioned brand master files.
- `code/dashboard/public/` — browser favicon and transparent SVG wordmark.
- `code/landing/public/` — horizontal SVG wordmark.
- `code/mobile/assets/` — iOS / Android icon raster and SVG masters.

This kit creates graphics/assets only. The actual application code and Figma files are not updated by this export.
