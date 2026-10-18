# 06 — Backend (Fleet Manager + WMS + API)

Code: `backend`. Contract: [02-api-contract.md](02-api-contract.md), [03-mqtt-contract.md](03-mqtt-contract.md).

## Modules

| File | Responsibility | Requirements |
|---|---|---|
| `app/main.py` | App factory, lifespan (create tables, seed, load fleet), 10 Hz fleet loop, 2 Hz snapshot broadcast | SV-10 |
| `app/fleet/graph.py` | Lane graph from YAML, A* (never through spurs, optional blocked nodes) | SV-02, NV-09 |
| `app/fleet/traffic.py` | Node + lane locks, all-or-nothing acquire, wait-for graph, deadlock detection | SV-03, SF-10, FR-08 |
| `app/fleet/allocator.py` | `nearest` greedy and `hungarian` optimal assignment | AI-08, FR-02 |
| `app/fleet/manager.py` | Robot state, task lifecycle, commands, fleet E-stop, battery policy, teleop clamping, simulator, deadlock resolution, MQTT handlers | FR-01..FR-10, SV-01, SV-04..06, SF-05..SF-11 |
| `app/fleet/mqtt_bridge.py` | aiomqtt client: inbound robot topics → manager, manager outbox → broker | §10, CM-01..04 |
| `app/fleet/settings_store.py` | Runtime settings persisted in DB | UI-09 |
| `app/routers/*` | REST endpoints, WebSocket | §11 REST API, SV-07, SV-08 |
| `app/models.py`, `app/seed.py` | WMS tables, demo data, dev users | §11 WMS |

## Simulator (SV-06)

Robots with `simulated: true` move along the lane graph at the configured speed (0.3 m/s, 0.1 m/s on the final
approach into a spur and when the forks are raised), spend 3 s on each pick/drop, drain and recharge battery, and
honour every lock. Admin-only scenarios (`POST /api/sim/scenario`): `person` (stop 4 s), `obstacle` (30 % speed
3 s), `drain_battery`, `disconnect` (offline 8 s, then SAFE until reset), `random_tasks`. Settings
`sim_speed_factor`, `sim_failure_rate`, `sim_auto_tasks_per_min` (continuous demo traffic).

## Verification so far

- `pytest`: 20 tests — auth/roles, envelopes, full task with WMS move + inventory history + analytics + CSV,
  3 robots × 9 concurrent tasks with a no-shared-lock / no-shared-node invariant checked every tick, cancel rules,
  occupied destination, fleet E-stop freeze/release, pause/resume, person scenario, low-battery charging, disconnect
  re-queue + reset, manual teleop clamp + dead-man + rejoin, WebSocket snapshot/ping, users admin, A*, locks,
  deadlock detection, allocators.
- Stress (not in CI): 10 runs × 1 simulated hour, 3 robots, continuous random tasks, 5 % pickup-failure rate —
  no gridlock after the back-off fix. In these runs Hungarian allocation finished ≈300 tasks/h vs ≈210 for nearest
  — a candidate result for AI-08 (re-measure with the real map and real robot speeds).

## Not done yet

- Real-robot path is implemented but untested against hardware (no `forklift_mission` client exists yet).
- No Alembic migrations (tables are created at start-up).
- Camera stream for UI-08 is not proxied by the server (the dashboard shows a placeholder).
