# 07 — Web monitoring dashboard (`code/dashboard`)

React 19 + Vite + TypeScript (strict) + Tailwind 3.4 single-page app. Pure client of the FastAPI server: it enforces
nothing the server does not (every role/state check is a UX mirror; the server still answers `403 forbidden` /
`409 invalid_state`). Arabic RTL by default, English LTR; light / dark / OS theme. Run instructions: `code/dashboard/README.md`.

## 1. Screens ↔ requirements

| Route (`/:lang/…`) | Screen | Requirements | API used |
|---|---|---|---|
| `login` | Sign-in | SV-07 | `POST /api/auth/login`, `GET /api/auth/me` |
| *(every screen)* | Top bar «إيقاف الكل / Stop all» + confirm; full-width danger banner with «release» while `fleet.estop` | **UI-07**, SF-11 | `POST /api/fleet/estop {engaged}`; state from WS `snapshot.fleet` |
| *(index)* | **Live map** (home): zones by kind, lane graph, nodes, locations with occupancy, forklift glyphs (oriented, `lift` yellow, id labels), remaining `path`, reserved segments per robot; click a location → side panel (pallet, create task to / from here); robot cards beside the map | **UI-01**, UI-03 (task from the map), SF-10 | `GET /api/map`, WS `snapshot` (robots, reservations, fleet) |
| `fleet` | One card per robot: mode + safety badges, battery bar + icon, task, last event, speed, fork height, pose; Pause / Resume / Go charge / Reset, disabled by role and state with the reason | **UI-02**, FR-06 | WS `snapshot`, `POST /api/robots/{id}/cmd` |
| `tasks` | Create task (searchable pallet, free destinations only, priority); list with status chips, robot filter, paging; live via WS `task`; cancel; drawer with status timeline | **UI-03**, FR-01, SV-01 | `GET/POST /api/tasks`, `GET /api/tasks/{id}`, `POST /api/tasks/{id}/cancel`, `GET /api/pallets`, `GET /api/locations` |
| `inventory` | Rack grid grouped by rack and level (top level first) with what is in each slot; SKU search; pallet drawer with movement history; register pallet | **UI-04**, SV-09 | `GET /api/locations`, `GET /api/pallets?q=`, `GET /api/pallets/{id}/moves`, `POST /api/pallets`, `GET /api/products`; WS `inventory` |
| `analytics` | 24 h / 7 d / custom range; KPI tiles (done, success rate, avg task time, avg lane wait); tasks-per-hour bars; per-robot utilization; congestion heat map drawn on the warehouse map; events by code; CSV export (tasks, events); PDF = print stylesheet | **UI-05**, **UI-10** (export), FR-11 | `GET /api/analytics/summary?from&to`, `GET /api/analytics/export?kind&from&to` (authed blob download) |
| `events` | Log with type / severity / robot filters, paging, live prepend from WS; critical events → toast + short WebAudio beep anywhere in the app (mute in the top bar) | **UI-06**, **SF-13** | `GET /api/events`, WS `event` |
| `manual` | Pick robot → switch to manual → drive with the browser Gamepad API (left stick y = v, x = ω; Y / d-pad-up lift up, A / d-pad-down lift down), on-screen pad or keyboard (WASD / arrows, E / Q); speed-limit slider; clamped `limited_v` shown; camera panel ("no camera stream configured") | **UI-08**, FR-10, SF-07 | `POST /api/robots/{id}/mode`, `POST /api/robots/{id}/teleop` |
| `settings` (admin) | Limits form (PATCH only changed fields), locations table add / edit, users list / add / delete, **Simulator** panel (person, obstacle, drain battery, disconnect, N random tasks) | **UI-09**, SV-06 | `GET/PATCH /api/settings`, `GET/POST/PATCH /api/locations`, `GET/POST/DELETE /api/users`, `POST /api/sim/scenario` |
| `kiosk` (also `/kiosk`) | Dark, no sidebar: full-bleed map + robot strip + fleet KPIs + live event ticker; Stop-all still visible | **UI-10** | same as the map + WS `event` |

Role gating (SV-07): **viewer** sees everything read-only (write buttons visible but disabled with "Requires the
Operator role"); **operator** gets tasks, robot commands, E-stop / release, manual control, pallet registration;
**admin** additionally sees the Settings nav item (hidden for others; the route explains if opened directly).

Every list / panel has a loading skeleton, an error state with retry (an error never reads as "empty"), and an empty
state (with a separate "no matches" text when filters are active).

## 2. Architecture

```
main.tsx → App: QueryClientProvider → ThemeProvider → ToastProvider → BrowserRouter → AuthProvider → AppRoutes
AppRoutes: /:lang (LangLayout: validates ar|en, sets <html lang dir>, stores preference)
  ├─ login
  └─ RequireAuth → LiveProvider (one WebSocket) → kiosk | AppShell (sidebar, top bar, E-stop banner) → screens (lazy)
```

- **API layer** (`src/api`): `fetch` wrapper adds `Authorization: Bearer <jwt>` (token in `localStorage`), unwraps
  `{data, meta}`, throws `ApiError{status, code, message, details}` from `{error:{…}}`. Any 401 (except the login call)
  clears the session and the route guard returns to login with a "session ended" note. `endpoints.ts` has one typed
  method per contract row; React Query hooks live beside each feature; query keys in `queryKeys.ts`.
- **Errors → text**: `errors.<code>` in the locale files (all contract codes + `network_error`, `server_error`);
  the server's English `message` is shown only in English when a code has no translation. Coded failures the user can
  act on are mapped onto the field (`location_occupied` → destination, `pallet_busy` → pallet, `duplicate` → the unique
  field); `validation_error.details.fields` is mapped onto inputs.
- **Forms**: react-hook-form + Zod (`src/validation/schemas.ts`; messages are i18n keys).
- **Live data** (`src/live`): `LiveStore` connects `ws(s)://<api host>/ws/live?token=<jwt>`, pings every 5 s, treats
  6 s of silence as a dead link, reconnects with 1 / 2 / 5 / 10 s backoff, and on close code `4401` logs out without
  retrying. `LiveProvider` mirrors frames into the query cache: `snapshot` → robots / fleet / traffic caches (2 Hz);
  `task` → task detail + debounced list refetch; `inventory` → pallets, locations and map refetch. `event` frames go
  to subscribers (event log prepend, critical alert toast + beep, kiosk ticker). While the socket is not live, the
  robots / fleet / traffic hooks fall back to polling REST every 3 s, so the UI never freezes silently; the top bar
  shows Live / Reconnecting / Disconnected.
- **Map** (`components/map/WarehouseMap.tsx`, `lib/mapTransform.ts`): metres with y up are converted with
  `toSvg(x, y) = [pad + x·s, pad + (H − y)·s]` (unit-tested; no CSS flip, so labels stay upright) and ROS yaw → SVG
  rotation `−yaw` in degrees. The SVG is pinned `dir="ltr"`. Robot glyphs move with a CSS transform transition so
  2 Hz snapshots glide. Reserved segments are coloured per robot (legend under the map); disabled robots
  (`enabled: false`, the spare `fl4`) and offline robots are drawn faded and their cards greyed out.
- **Design**: semantic `--sw-*` CSS variables (light + `.dark`) from docs/05 mapped in `tailwind.config.ts`; added
  `*-on` foregrounds for status fills, `accent-soft`, `scrim`, and map tokens (`--sw-zone-<kind>` fill + stroke,
  `--sw-heat-0..3`). Thmanyah Sans / Serif + Lexend self-hosted in `public/fonts`. Numbers in prose use Intl with
  Arabic-Indic digits in Arabic; telemetry, ids and coordinates are Latin, tabular, in LTR islands (`<Num>`).
  Charts (recharts) sit in `dir="ltr"` wrappers with token-coloured ticks and tooltips.
- **Teleop dead-man**: a 100 ms loop sends `{v, w, lift}` only while some input is held, never queues behind an
  in-flight request, sends one zero command on release, and clears held keys on window blur or on an error — so if
  the browser stops, the server watchdog stops the robot.

## 3. Contract notes for the backend (decisions taken on the client)

1. **Segment ids** are `"<a>--<b>"` (double dash, node ids sorted). The client matches `reservation.segment_id` /
   `congestion[].segment_id` to `edges[].id` first, then by splitting on `--` and looking the two node ids up in
   `/api/map` (either order).
2. **`Robot.enabled`** (optional boolean, missing = true) marks a disabled spare: greyed out, no commands, not drivable.
3. **Nullables**: the client accepts `null` *or* a missing key for every nullable field (`== null` checks).
4. **Paging**: `GET /api/tasks` and `GET /api/events` should return `meta: {total, limit, offset}`; if `total` is
   missing the client assumes there is no further page. `status` is sent comma-separated (`?status=queued,assigned`).
5. **Validation errors**: `details.fields` may be a map `{field: message}` or a list of `{field|loc, msg}`; FastAPI's
   unwrapped `422 {detail: [...]}` is also understood, but please wrap it in the envelope.
6. **CSV export** is fetched with the bearer header and saved as a blob; the file name comes from
   `Content-Disposition` when CORS exposes it (`expose_headers=["Content-Disposition"]`), otherwise
   `sw-fleet-<kind>.csv`.
7. **Analytics range**: `from` / `to` are sent as ISO-8601 UTC (`toISOString()`); `success_rate` and `busy_pct` are
   treated as ratios 0..1; `null` averages render as "—".
8. **Fleet E-stop while engaged**: robot commands other than `reset` are disabled in the UI; the server's
   `409 fleet_estopped` remains the authority. `POST /api/fleet/estop` is expected to return `FleetState`.
9. **Pallet picker** for new tasks lists all pallets but only `status == "stored"` ones are selectable; destinations
   are locations with `occupied == false` and `type != "charge"`, excluding the pallet's own location.
10. **WebSocket**: the client sends `{"type":"ping"}` every 5 s and ignores `pong`; any frame resets the 6 s staleness
    timer. Close code `4401` → logout; anything else → reconnect with backoff.

## 4. Not done / limits

- No camera stream (placeholder panel only; the contract has no camera endpoint).
- Lanes are not editable in Settings (the contract exposes the lane graph read-only via `/api/map`); locations, speed
  limits and users are.
- PDF export is the browser's print-to-PDF of the analytics page (print stylesheet hides the app chrome).
