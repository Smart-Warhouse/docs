# 05 — Design system (shared by dashboard, landing, mobile)

Adapted from the IMMAR design-system rules (semantic tokens that flip with the theme, paired on-fill foregrounds,
Arabic-first RTL, logical properties, Phosphor icons only, self-hosted fonts) with a palette of its own for an
industrial warehouse product.

**Product name:** «المخزن الذكي» / **Smart Warehouse** — short mark **SW·Fleet**.

## Palette (primitives — identical hex in all three apps)

| Ramp | 50 | 100 | 200 | 300 | 400 | 500 | 600 | 700 | 800 | 900 |
|---|---|---|---|---|---|---|---|---|---|---|
| `ink` (slate navy) | #F4F7F9 | #E6ECF0 | #CBD6DE | #A3B4C1 | #6E8494 | #4A6070 | #344857 | #233544 | #162430 | #0C161E |
| `primary` (steel teal) | #E8F6F8 | #C6E9EE | #94D3DD | #5DBACB | #2E9CB0 | #1C7F93 | #146577 | #0F4C5C | #0B3844 | #072630 |
| `lift` (forklift yellow — signature) | #FFF9E0 | #FFEFB0 | #FFE27A | #FFD23F | #F5B400 | #D99A00 | #B07A00 | #865C00 | #5E4000 | #3A2700 |
| `success` | #ECFDF3 | | | | #22C55E | #16A34A | #15803D | | | |
| `warning` | #FFF7ED | | | | #FB923C | #EA580C | #C2410C | | | |
| `danger` | #FEF2F2 | | | | #F87171 | #DC2626 | #B91C1C | | | |
| `info` | #EFF6FF | | | | #60A5FA | #2563EB | #1D4ED8 | | | |

## Semantic tokens (CSS variables `--sw-*`; Flutter `SwTokens` light/dark)

| Token | Light | Dark | Use |
|---|---|---|---|
| `bg` | #F4F7F9 | #0C161E | page ground |
| `surface` | #FFFFFF | #13202A | cards, panels |
| `surface-2` | #EEF2F5 | #1A2A36 | inset, table header, map ground |
| `border` | #DCE3E8 | #26394A | dividers, field borders |
| `text` | #0C161E | #E9EFF3 | primary text |
| `text-2` | #4A6070 | #A3B4C1 | secondary text |
| `text-3` | #6E8494 | #6E8494 | captions, placeholders |
| `accent` | #0F4C5C | #5DBACB | interactive primary fill / links |
| `accent-hover` | #146577 | #94D3DD | |
| `accent-on` | #FFFFFF | #072630 | foreground ON an accent fill (never hard-code white) |
| `lift` | #F5B400 | #F5B400 | brand signature, robot glyphs, the logo mark — **same in both themes** |
| `lift-on` | #3A2700 | #3A2700 | foreground on `lift` |
| `success` / `warning` / `danger` / `info` | 600 step | 400 step | status (never the only signal — pair with icon or words) |
| `*-soft` | 50 step | 600 step @ 15% (baked hex) | status tint backgrounds |
| `ring` | #2E9CB0 | #94D3DD | focus-visible ring |

Rules:
1. Components use semantic tokens only — no raw hex, no `text-white` on fills (use `*-on`).
2. No `dark:` variants for colour; tokens flip themselves. No Tailwind opacity modifiers on `var()` tokens.
3. **Danger red** is for E-stop, faults and destructive actions only. The «إيقاف الكل / Stop all» button is always
   danger, always visible (UI-07).
4. Robot state colours: idle = `text-2`, busy = `accent`, charging = `info`, paused/manual = `warning`,
   safe/estop/error/offline = `danger`. Always with a label.

## Type

Thmanyah Sans (Arabic UI), Thmanyah Serif Text (Arabic display headings only), Lexend (English). Self-hosted
woff2 in `docs/brand/fonts/` — copy into each app (`public/fonts`, Flutter `assets/fonts`). Weights 300/400/500/700/900.
Numbers in tables and telemetry are tabular (`font-variant-numeric: tabular-nums`) and pinned `dir="ltr"`.

## Direction & language

Arabic (RTL) default, English (LTR) switchable; logical properties only (`ms/me/ps/pe/start/end`). The warehouse
map, charts and coordinate readouts are always LTR (x grows to the right). Strings live in locale files, never
inline.

## Icons

Phosphor (`@phosphor-icons/react` on web, `phosphor_flutter` in the app). Regular weight; `fill` only for an active
state. Suggested: Forklift → `Truck`/`Package`, robot `Robot`, battery `BatteryHigh/Medium/Low/Warning`, E-stop
`Octagon`/`HandPalm`, map `MapTrifold`, tasks `ListChecks`, inventory `Stack`, analytics `ChartLineUp`,
events `Warning`/`Bell`, gamepad `GameController`, settings `GearSix`.

## Theme

Dashboard defaults to the OS theme with a manual toggle; landing follows the OS; app follows system. Kiosk mode
(UI-10) = dark, sidebar hidden, map full-bleed.
