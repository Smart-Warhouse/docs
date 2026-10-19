# 08 — Landing page

The public page of the project, in `landing/` (developer notes: `landing/README.md`).
Static React 19 + Vite + TypeScript SPA, Tailwind 3.4, react-router-dom 7, Phosphor icons. Arabic is the
default (`/`, RTL); English lives at `/en` (LTR). Theme follows the OS, with a toggle that is remembered.

## Purpose and audience

Explain the project to a non-specialist visitor (examiners, students, people who receive the link) in
under five minutes, link to the live dashboard, and stay **honest**: this is work in progress.

**Honesty rule.** Every number on the page is a design target from `00-sources/system-requirements.md`,
labelled as such ("الهدف" / "Target", "الهدف التصميمي" / "Design target" column, notes in the hero, specs
and FAQ). No measured results, testimonials, partners, invented statistics or invented people. The team
block is empty with a "names will be added" line until real names are filled in. `copy.test.ts` fails the
build on forbidden claims in either language.

## Routes

| Path | Language | Notes |
|---|---|---|
| `/` | Arabic, RTL | Default. If the visitor chose English before (`localStorage['sw-lang']`), `public/lang-bootstrap.js` sends them to `/en` before paint. |
| `/en` | English, LTR | The language switch links between the two and stores the choice. |
| `*` | from the path | 404, `noindex`. |

`<html lang/dir>` is set before paint by `lang-bootstrap.js` and kept in sync by `LocaleProvider`.
Canonical + `hreflang` (ar, en, x-default) in `index.html` and per page via `usePageMeta`;
`robots.txt` and `sitemap.xml` in `public/`.

## Home page, section by section

| # | Section (`id`) | Content source | Visual |
|---|---|---|---|
| 1 | Hero | project definition (§1) | `FleetMap` SVG: racks, lane graph, 3 forklifts, a reserved segment, a waiting forklift; CTAs "Open dashboard" (`VITE_DASHBOARD_URL`) and "How it works" (`#how`); facts 1:14 / 3 + 1 / 4 layers; the "targets, not results" note |
| 2 | Problem & idea (`problem`) | overview "the idea in one sentence" | three pain points + idea card |
| 3 | How it works (`how`) | overview layer model | the 4 layers as a stack (server → Jetson → ESP32 → sensors & motors) with the link between each pair (Wi-Fi·MQTT, USB·micro-ROS, I²C·GPIO·ADC·PWM) + `ForkliftIllustration` (sensors): lift-yellow forklift, LiDAR scan plane on the roof, camera cone, ToF slow (<40 cm) and stop (<15 cm) fans; hardware E-Stop callout |
| 4 | Forklift hardware (`hardware`) | overview mount points 1–8, ME-01..14 | `ForkliftIllustration` (mounts) with numbered markers + the 8-point list; dimensions, battery, ≤ 700 g added-weight target |
| 5 | Software architecture (`software`) | §§4, 5, 10, 11 | three tiers (server modules, ROS 2 packages, FreeRTOS tasks) + how the parts talk (MQTT, micro-ROS, ROS 2) |
| 6 | AI (`ai`) | §§6, 8, overview AI journey | "AI proposes, safety decides"; YOLO perception, RL docking vs. classical baseline, task allocation, each with its targets; the 6-step model journey |
| 7 | Safety in layers (`safety`) | §9 | inverse "chapter" surface; E-Stop → ESP32 (ToF + 500 ms watchdog, 1 kHz) → Jetson supervisor + YOLO → server locks / stop-all, with the key numbers; ≤ 100 ms stop target; LED states |
| 8 | Fleet manager & dashboard (`fleet`) | §§11, 12 | detailed `FleetMap` (node ids, reserved segment, waiting halo, legend) + manager and dashboard feature lists; dashboard CTA |
| 9 | Target specs (`specs`) | NFR-01..07, §14 | table: metric · design target · how it is measured (test id + method) |
| 10 | Plan (`plan`) | §15 + §14 | 6 phases with test gates (see note below) |
| 11 | Parts / BOM (`bom`) | `00-sources/parts-bom.pdf` | cost by group (bars + amounts), 1,507,250 IQD per forklift, ≈ 6,029,000 IQD for 3 + 1, exclusions |
| 12 | Tech stack (`stack`) | §15 tools | grouped chips |
| 13 | FAQ (`faq`) | | 7 questions, native `<details>` |
| 14 | Final CTA | | inverse band, dashboard + how-it-works |

**Plan phases** were derived from §15 ("phases 1–4 on one forklift, the other two copied in phase 5,
server and dashboard in parallel from phase 2") and the test order in §14, because the embedded phase
chart is not in the exported requirements: 1 single parts (T-01–T-04) · 2 a forklift that moves safely
(T-05–T-07) · 3 map and navigation (T-08, T-09) · 4 perception and docking (T-10–T-12) · 5 full fleet
(T-13, T-14) · 6 endurance and readiness (T-15, T-16). **TODO:** confirm against the original phase chart.

**BOM groups** (IQD per forklift, sum = 1,507,250 as printed on the list; `bom.test.ts` checks):
compute 1,070,250 (Jetson 995,000 + NVMe 66,000 + ESP32-S3 9,250) · vision & motion sensing 370,500 ·
fork & wheel sensing 14,500 · power 36,750 · actuation & signalling 15,250. Not included: the Huina
forklift, the 12 V boost converter required by EL-05, 3D-printed mounts, the shared charger.

## Design system use

Follows `05-design-system.md`: semantic `--sw-*` tokens that flip under `.dark` (Tailwind names `bg`,
`surface`, `surface-2`, `line`, `ink`/`ink-2`/`ink-3`, `accent`/`accent-on`, `lift`/`lift-on`, status
colours, `ring`), Thmanyah Sans / Thmanyah Serif Text (Arabic display) / Lexend (English) self-hosted from
`public/fonts/`, Phosphor icons, logical properties, LTR-pinned diagrams and IDs.

Landing-only tokens (added in `src/index.css`, both themes):

| Token | Light | Dark | Why |
|---|---|---|---|
| `lift-text` (`text-lift-ink`) | `#865C00` | `#FFD23F` | the lift yellow `#F5B400` fails as text on light backgrounds |
| `lift-soft` | `#FFF9E0` | `#2B2E24` | yellow tint panels (principle card, pallets in the map) |
| `accent-soft` | `#E8F6F8` | `#132A36` | tint behind accent icons and target chips |
| `inverse`, `inverse-2`, `inverse-border`, `inverse-text`, `inverse-text-2` | `#162430` … | `#071017` … | one frozen-dark "chapter" surface, used twice (Safety, final CTA) |

The lift yellow is the signature: logo mark, forklift glyphs, the primary hero/CTA button
(`bg-lift text-lift-on`). Danger red only for the E-Stop (and the ToF stop fan in the drawing). Status
colours never carry meaning alone (LED states are written out).

**Arabic copy rule:** bounds are written in words ("100 ms كحد أقصى", "45 دقيقة على الأقل") instead of
≤/≥, because bidi mirroring flips those glyphs next to Latin units. Test-enforced.

**Motion:** `Reveal` only (12 px lift, 600 ms, once, IntersectionObserver `threshold: 0`), decided in JS so
reduced-motion visitors get static content; the hero `h1` (LCP) is never animated.

## Security and hosting

Docker: Node 22 build → `nginx:1.28-alpine`. CSP `default-src 'self'; script-src 'self'; style-src 'self';
font-src 'self'; img-src 'self' data:; connect-src 'none'; frame-src 'none'; frame-ancestors 'none';
object-src 'none'; base-uri 'self'; form-action 'none'` + HSTS, nosniff, DENY framing, COOP/CORP,
Permissions-Policy. No inline scripts (the pre-paint guards are files), no third-party hosts. The dashboard
link is a plain navigation in a new tab (`noopener noreferrer`). `VITE_DASHBOARD_URL` is a build arg.

## Quality gate

`npm run typecheck`, `npm run lint`, `npm run test`, `npm run build`. Tests (`vitest`):
copy parity AR/EN (structure, list lengths, ids, anchors), no empty strings, Arabic strings in Arabic,
no ≤/≥ in Arabic, forbidden claims in both languages, no placeholder people; home renders in both
languages with the right `lang`/`dir`/title, every section heading and nav anchor, dashboard links,
the targets column and honesty notes, the BOM total, language switch, 404 noindex; sitemap ↔ routes,
one origin across SEO files, no inline scripts, the CSP contract, nginx header includes, dashboard URL
validation; BOM sums.

## Open TODOs

1. Supervisor, university, department (`footer.team` in `ar.ts` and `en.ts`) — the three team names and photos are in.
2. Real domain (`SITE_ORIGIN` + `index.html` + `robots.txt` + `sitemap.xml`; now `https://sw-fleet.example`).
3. Real photos of the forklift and the scale warehouse; a 1200×630 `og:image`.
4. Replace targets with measured results as tests T-01…T-16 are run (and change the honesty notes then).
5. Confirm the 6-phase plan against the original phase chart.
6. Confirm the Thmanyah font licence allows web self-hosting.
