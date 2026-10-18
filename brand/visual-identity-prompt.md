# Visual identity — prompt

A ready-to-paste prompt for generating the project's visual identity with an AI design tool (ChatGPT image /
Midjourney / Ideogram / Recraft / Figma AI), then a short brief for refining it by hand. It extends the colours
and type already used in the code ([05-design-system.md](../05-design-system.md)), so what you generate stays
consistent with the dashboard, landing page and app.

## 1. Master prompt (paste as one message)

> Design a complete visual identity for a university graduation project called **«المخزن الذكي» — "Smart
> Warehouse"**, short mark **SW·Fleet**: a 1:14-scale miniature warehouse where three small autonomous yellow
> forklifts move pallets on their own, coordinated by a central fleet manager and a live dashboard. Audience:
> engineering professors, a thesis defence jury, technical recruiters in Iraq and the region. Bilingual: Arabic
> first (right-to-left), English second.
>
> **Brand idea:** "Precision in motion" — calm, trustworthy industrial engineering, not playful toys. Three
> forklifts moving in coordinated lanes; safety first; AI that proposes and a safety layer that decides.
>
> **Logo:** a geometric symbol that combines a pallet/fork shape with a lane or route line (one continuous stroke
> suggesting a path between racks), built on a square grid so it also works as an app icon and a sticker on the
> forklift. Provide: primary horizontal lockup (symbol + «المخزن الذكي» + "Smart Warehouse"), stacked lockup,
> symbol alone, monochrome version, and a version on yellow. Arabic wordmark in a clean geometric Naskh/Kufi-
> inspired sans (in the style of Thmanyah Sans), Latin in a geometric sans (in the style of Lexend). No gradients
> in the logo, flat vector, works at 16 px.
>
> **Colour palette (use exactly):** Slate Navy #0C161E (backgrounds, text), Steel Teal #0F4C5C (primary),
> Light Teal #5DBACB (primary on dark), Forklift Yellow #F5B400 (signature accent — the robots, the logo
> highlight), Ink Grey #4A6070 (secondary text), Mist #F4F7F9 (light background); status colours Success
> #16A34A, Warning #EA580C, Danger #DC2626 (danger only for emergency stop and faults).
>
> **Typography:** Arabic — Thmanyah Sans (UI, body), Thmanyah Serif Text (large Arabic headings only); English —
> Lexend. Tabular numbers for telemetry.
>
> **Graphic language:** thin lane lines and node dots taken from a warehouse route map, isometric pallet blocks,
> subtle LiDAR scan rings, ArUco-style square markers as a texture element, generous white space, 8-px grid.
> Icons: Phosphor-style line icons (regular weight).
>
> **Show the identity applied to:** (1) the app icon on a phone home screen, (2) a dashboard screen in dark mode
> with a warehouse map, (3) a landing-page hero, (4) the livery on a small yellow forklift — logo on the
> counterweight, robot ID "FL1" on the side, warning chevrons on the fork carriage, (5) a pallet label with an
> ArUco marker and SKU, (6) a thesis cover page, (7) a presentation title slide, (8) a lanyard/badge for the
> defence day, (9) a sticker sheet. Present everything as one clean brand-guidelines board on a light background,
> with colour swatches (hex codes), type specimens in Arabic and English, logo clear-space and minimum-size rules.

## 2. Follow-up prompts (one at a time, same chat)

1. "Give me 4 alternative logo symbols for the same brief, each built on a 24-unit grid, flat vector, shown at
   512 px and 16 px."
2. "Take option N. Show it in all lockups: horizontal AR+EN, stacked, symbol only, monochrome navy, white on
   navy, navy on yellow."
3. "Make the forklift livery sheet: side, top and rear views of a small yellow forklift with the logo, the robot
   IDs FL1–FL4, and black/yellow warning chevrons on the fork carriage. Keep the LiDAR on the roof visible."
4. "Make a pallet label template (60 × 40 mm): ArUco marker on the left, SKU, product name in Arabic and
   English, pallet ID, QR placeholder."
5. "Make a 16:9 slide template set: title, section divider, content with image, two-column comparison, results
   chart, thank-you — Arabic RTL and English LTR versions."

## 3. Rules to keep when you pick and refine (so it matches the code)

- Never change the hex values above — they are already the tokens in the dashboard, landing page and app.
- Yellow is the signature, used sparingly: robots, the logo highlight, one call-to-action. Not as page background.
- Red only for emergency stop and faults, never decoration.
- On a teal or yellow fill the text colour is fixed: white on Steel Teal, Slate Navy on Forklift Yellow and on
  Light Teal (never white on yellow — unreadable).
- Arabic first, right-to-left; maps, charts and coordinates stay left-to-right.
- Final logo files to produce: SVG (primary, stacked, symbol, mono), PNG 512/1024, favicon 32/16, Android
  adaptive icon (foreground + background), iOS 1024 icon. Put them in `docs/brand/logo/`; then the dashboard
  (`code/dashboard/public`), landing (`code/landing/public`) and app (`code/mobile/assets`) can switch to them.
