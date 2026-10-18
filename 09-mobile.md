# 09 — Mobile floor app (`mobile`, Flutter)

The **SW Floor** app is for the people working on the warehouse floor with a phone or tablet. The control room uses
the web dashboard (`dashboard`); both are clients of the same server and contract
([02-api-contract.md](02-api-contract.md)). Visual rules come from [05-design-system.md](05-design-system.md).
How to run and configure it: [`mobile/README.md`](https://github.com/Smart-Warhouse/mobile/blob/main/README.md).

## 1. Use cases ↔ requirements

| # | Use case | Requirement ids | Endpoints / frames | Where |
|---|---|---|---|---|
| 1 | Connect & sign in: server address (LAN IP, emulator hint `10.0.2.2`), username/password, "test connection"; address + username remembered, JWT in secure storage | SV-07, §10 | `GET /api/health`, `POST /api/auth/login`, `GET /api/auth/me` | `features/auth` |
| 2 | **STOP ALL**: big danger button on every signed-in screen, press and hold 1 s (haptic) → stop the fleet; engaged E-stop = full-screen red state; operator releases after a confirm dialog | **SF-11**, UI-07 | `POST /api/fleet/estop {engaged:true\|false}`, `snapshot.fleet.estop` | `core/widgets/hold_to_stop_button.dart`, `shared/widgets/floor_frame.dart` |
| 3 | Fleet at a glance: a card per robot (mode + safety badge with colour, icon and words, battery, task, speed, fork, carried pallet, last event); Pause / Resume / Go charge / Reset / Drive by role and state; disabled spare greyed out | FR-06, UI-02 | WS `snapshot` (2 Hz, SV-10), `POST /api/robots/{id}/cmd` | `features/fleet` |
| 4 | Safety alerts: live feed of `event` frames on top of `GET /api/events`; critical events (`person_detected`, `estop_pressed`, `fleet_estop`, `watchdog_timeout`, `battery_critical`, `robot_offline`, `wifi_lost`, `tof_stop`, or any `severity: critical`) raise a red in-app banner and vibrate; filters by severity, type, robot | **SF-13**, SF-06, UI-06 | WS `event`, `GET /api/events` | `features/alerts` |
| 5 | Mini live map: zones, lanes, reserved segments, locations (occupied filled), planned paths, robots as oriented glyphs; tap a robot → its card | UI-01 (lite), SV-02, SF-10 | `GET /api/map`, WS `snapshot` (robots, reservations) | `features/map` |
| 6 | Move a pallet on the spot: pick a pallet (search SKU / name / ArUco id) → free destination → priority 1..5 → create; task list (mine / all) with live status and cancel | FR-01, UI-03 | `GET /api/pallets?q=`, `GET /api/locations`, `POST /api/tasks`, `GET /api/tasks`, `POST /api/tasks/{id}/cancel`, WS `task` | `features/tasks` |
| 7 | Manual drive: choose robot → switch to manual → joystick + lift up/down; teleop at 10 Hz **only while the dead-man's button is held**; release → one stop command then nothing; requested vs server-clamped speed shown; leaving the screen (or backgrounding the app) drops the dead-man and switches back to auto | **FR-10**, UI-08, SF-07 | `POST /api/robots/{id}/mode`, `POST /api/robots/{id}/teleop` | `features/drive` |
| 8 | Pallet lookup: search inventory, location, quantity, weight, ArUco id, movement history; "move this pallet" shortcut | UI-04, SV-09 | `GET /api/pallets?q=`, `GET /api/pallets/{id}/moves`, WS `inventory` | `features/pallets` |
| — | Role gating: `viewer` sees everything read-only; command buttons are replaced by a "Viewer account: read only" note; STOP ALL is drawn disabled and explains to call an operator or use the robot's own E-stop | SV-07 | `403 forbidden` mapped too | everywhere (`canOperateProvider`) |
| — | Live link: status chip (Live / Connecting / Reconnecting in N s / Offline), reconnect backoff 1 / 2 / 5 / 10 s, ping, close `4401` → sign out | SV-10, §4 of the contract | `/ws/live?token=` | `core/realtime` |

Out of scope for the phone (dashboard only): analytics (UI-05), settings / users / locations admin (UI-09), CSV
export and kiosk mode (UI-10), the camera stream of UI-08, simulator helpers.

## 2. Safety behaviour (SF-06, SF-11, SF-13)

- STOP ALL is part of the frame around every signed-in route (tabs and pushed screens), never inside a scrollable,
  64 dp tall, danger-red in both themes. A hold (not a tap) avoids pocket presses; a screen reader gets a direct
  long-press action. The POST uses short timeouts (2 s send / 3 s receive): on failure the person is told the stop
  was **not** sent and to use the robot's physical E-stop. The returned `FleetState` is applied at once, without
  waiting for the next snapshot.
- While `fleet.estop` is true the whole app is covered in red (who and when), every robot command is hidden, and
  "Hide" collapses it to a red strip that stays until release. A new stop always re-opens the full screen.
- The phone is an extra layer only. Robot-side layers (hardware E-stop, ESP32 ToF/watchdog, Jetson supervisor) do
  not depend on it; manual drive relies on the server clamp (SF-07) and shows the clamped speed.
- Manual drive never queues commands: a tick is skipped while the previous request is in flight; teleop requests
  time out after 0.4 / 0.6 s; any server refusal (E-stop, offline, not manual) drops the dead-man; a fleet E-stop
  drops it immediately.

## 3. Architecture

```
widget ──watch──▶ Riverpod provider/notifier ──▶ repository (Result<T>, never throws)
                                                      │ callApi('METHOD /path', …) → JsonReader models
                                                      ▼
                                  Dio + AuthInterceptor (Bearer, Accept-Language, 401 → sign out)

/ws/live ──▶ LiveSocket (backoff, ping, 4401) ──▶ LiveController (robots, reservations, fleet)
                                               └─▶ liveFrameBus ─▶ AlertsController, TasksController, PalletSearch
```

- **Feature-first folders** (`lib/features/<f>/{data,domain,presentation}`), shared shell in `lib/shared`, cross-
  cutting code in `lib/core`. Follows the conventions of the team's IMMAR Flutter app (Riverpod, go_router with a
  single auth redirect, Dio + `callApi`/`Result`, hand-written models over `JsonReader`, ARB l10n, design tokens),
  without its branding.
- **Contract fidelity**: success envelope `{data, meta}` unwrapped by `ApiEnvelope`; error envelope
  `{error:{code,message,details}}` mapped to `ServerFailure(code: ErrorCode…)`; widgets switch on the code and show
  localized text, the English `message` only when a code is unknown. Every inbound enum has an `unknown` value so a
  new server value never crashes a screen.
- **Session**: `SessionController` restores the cached user + token (opens even if the server is briefly down),
  then re-checks `GET /api/auth/me`. `apiDioProvider` is rebuilt when the server address changes.
- **Routing**: `/splash`, `/login`; a `ShellRoute` (`FloorFrame`: STOP ALL, E-stop takeover, alert banner) holding a
  `StatefulShellRoute` with five tabs (`/fleet`, `/map`, `/tasks`, `/inventory`, `/alerts`) and pushed screens
  (`/move`, `/pallet/:id`, `/drive?robot=`, `/settings`).
- **Design**: `SwTokens` (ThemeExtension) holds the docs/05 light/dark tokens, the only raw hex in the app; status is
  always colour + icon + words; robot states follow docs/05 rule 4. Arabic (RTL) is the default, English
  switchable in Settings; the map, joystick and telemetry stay LTR. Fonts: Thmanyah Sans / Serif Text (Arabic),
  Lexend (English), converted from the brand WOFF2 files.
- **Map transform** (`features/map/domain/map_transform.dart`): uniform scale, letterboxed, map origin bottom-left
  with +y up → canvas origin top-left with +y down; yaw (CCW) becomes canvas angle `-yaw`. Reserved segments are
  matched on the edge id `"<a>--<b>"` (sorted node ids, double dash).

## 4. Contract notes and decisions

| Topic | Decision |
|---|---|
| `GET /api/pallets/{id}` does not exist | The detail screen receives the pallet from the list; opened by path it searches `GET /api/pallets` and picks the id. |
| "My tasks" | No `created_by` filter on `GET /api/tasks`; the app loads the newest 50 and filters `created_by == username` locally (toggle Mine / All). |
| Free destinations | `GET /api/locations`, keep `occupied == false`, not the pallet's own location, not `charge`. The server stays the judge (`location_occupied`, `pallet_busy`). |
| Robot actions by state | Pause: idle/busy · Resume: paused · Go charge: idle/paused/busy · Reset: safe/error · Drive: idle/paused; nothing when offline, disabled or fleet E-stopped. The server's `invalid_state` remains authoritative. |
| `enabled` on Robot | Read with default `true` when absent; a disabled spare (fl4) is shown greyed with no actions. |
| Segment ids | `"<a>--<b>"`, node ids sorted (node ids contain single dashes). |
| Teleop release | After the dead-man is released the app sends one `{v:0,w:0,lift:0}` and then stops sending, so the robot halts at once instead of waiting for its watchdog. |
| Critical alerts | `severity == critical` OR one of the alarm codes above (some arrive as `warning`). |
| Icons | `phosphoricons_flutter` (Dart 3 compatible fork with the same glyphs); `phosphor_flutter` 2.1.0 does not compile on Flutter 3.44. |

## 5. Tests

`flutter test` (47 tests): contract JSON → models and WS frames (incl. unknown enums, garbage frames), envelope and
error mapping through a fake Dio adapter (Bearer header, 401 → sign out, network/contract failures), localized
error text, server URL normalisation, the map coordinate transform and tap hit-test, the hold-to-stop button
(short press, 1 s hold + haptic, restart, disabled), teleop loop (10 Hz only while held, stop on release, no queue),
backoff schedule, robot action rules, and full-app smoke tests with a fake WebSocket: Arabic RTL render, STOP ALL →
`POST /api/fleet/estop` → red takeover, critical event → banner + alarm, close `4401` → login, English LTR viewer
read-only, every tab at 360 dp, and the manual-drive flow end to end.
