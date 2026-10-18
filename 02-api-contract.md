# 02 — Server API contract (REST + WebSocket)

Source of truth for `backend` and its three clients (`dashboard`, `mobile`, and — for the
`/api/public/*` stats only — nothing else; the landing page calls no API). Requirements: §10–§12 of
[system-requirements.md](00-sources/system-requirements.md) (SV-*, UI-*, SF-11).

Base URL in development: `http://localhost:8000`. All REST paths are under `/api`. OpenAPI/Swagger is served at
`/docs` (SV-08).

## 1. Conventions

- JSON, **snake_case** field names, ISO-8601 UTC timestamps (`2026-10-16T19:50:00Z`), distances in **metres**,
  angles in **radians** (`yaw`), fork heights in **millimetres**, battery in **percent (0–100)**.
- Success envelope: `{ "data": <payload>, "meta": { ... } }`. `meta` is `{}` unless the endpoint is paginated:
  `{ "total": 120, "limit": 50, "offset": 0 }`.
- Error envelope (any 4xx/5xx): `{ "error": { "code": "task_not_found", "message": "Human readable (English)", "details": {} } }`.
  Clients map `code` to localized text; never show `message` raw to Arabic users unless there is no mapping.
- Auth: `Authorization: Bearer <jwt>` on every path except `POST /api/auth/login`, `GET /api/health`.
  WebSocket passes the token as a query parameter: `/ws/live?token=<jwt>`. The camera stream
  (`GET /api/robots/{id}/camera`) accepts either the header or `?token=<jwt>` (§3.3).
- Roles (SV-07): `viewer` (read only) < `operator` (tasks, robot commands, E-stop, manual control) < `admin`
  (settings, locations, users). A forbidden call returns `403 forbidden`.

### Error codes

| HTTP | code | When |
|---|---|---|
| 400 | `validation_error` | Body/query failed validation (`details.fields` lists them) |
| 401 | `unauthorized` | Missing/invalid/expired token |
| 401 | `invalid_credentials` | Wrong username or password |
| 403 | `forbidden` | Role too low |
| 404 | `not_found`, `task_not_found`, `robot_not_found`, `pallet_not_found`, `location_not_found` | |
| 409 | `location_occupied` | Destination already holds a pallet |
| 409 | `pallet_busy` | Pallet already has an active task |
| 409 | `fleet_estopped` | Command refused while the fleet E-stop is engaged |
| 409 | `invalid_state` | e.g. cancel a finished task, resume a robot that is not paused |
| 409 | `robot_offline` | Command to a robot that is offline |
| 409 | `duplicate` | Unique field already used (username, location code, aruco id, sku) |
| 404 | `camera_not_configured` | The robot has no `camera_url` in `warehouse_map.yaml` (§3.3) |
| 409 | `camera_inactive` | Camera stream asked while the robot is not in manual mode |
| 502 | `camera_unreachable` | The robot's camera did not answer, refused the server token, or is not MJPEG |
| 503 | `camera_busy` | Viewer cap reached (server `CAMERA_MAX_VIEWERS` or the robot's own `max_clients`) |

## 2. Shapes

```jsonc
// User
{ "id": 1, "username": "operator", "name": "Floor Operator", "role": "operator" }

// Robot  (FR-06, UI-02)
{
  "id": "fl1", "name": "Forklift 1", "ip": "192.168.50.11",
  "online": true,
  "mode": "busy",            // idle | busy | charging | paused | manual | safe | estop | error | offline
  "safety_state": "normal",  // normal | slow | stop | safe | estop
  "battery_pct": 82.5,
  "x": 1.20, "y": 0.45, "yaw": 1.57, "speed": 0.22,
  "fork_height_mm": 0,
  "carrying_pallet_id": 7,   // null when empty
  "current_task_id": "T-0042",
  "route": ["N3", "N4", "N7"],          // remaining waypoint ids
  "path": [[1.2, 0.45], [1.2, 1.0]],    // remaining polyline in metres (map frame)
  "last_event": { /* Event | null */ },
  "last_seen": "2026-10-16T19:50:00Z",
  "simulated": true
}

// Task  (FR-01, SV-01)
{
  "id": "T-0042", "type": "move_pallet",
  "pallet_id": 7, "pallet_sku": "SKU-0007",
  "from_location_id": 3, "from_code": "R1-L2",
  "to_location_id": 12, "to_code": "DOCK-OUT-1",
  "robot_id": "fl2",          // null until assigned
  "priority": 2,              // 1 (low) .. 5 (urgent); default 2
  "status": "to_pickup",      // queued | assigned | to_pickup | picking | to_drop | dropping | done | failed | cancelled
  "route": ["N3", "N4", "N7"],
  "created_at": "...", "started_at": "...", "finished_at": null,
  "fail_reason": null, "created_by": "operator"
}

// Location  (WMS `locations`)
{ "id": 3, "code": "R1-L2", "type": "rack",   // rack | dock_in | dock_out | staging | charge
  "x": 1.20, "y": 0.45, "yaw": 1.57, "level": 1, "height_mm": 60, "aruco_id": 23,
  "node_id": "N3", "occupied": true, "pallet_id": 7 }

// Pallet
{ "id": 7, "aruco_id": 7, "sku": "SKU-0007", "product_name": "Bottled water", "quantity": 24,
  "weight_g": 180, "location_id": 3, "location_code": "R1-L2",
  "status": "stored" }        // stored | in_transit | reserved

// Product
{ "sku": "SKU-0007", "name": "Bottled water", "category": "beverages" }

// Event  (SF-13, UI-06)
{ "id": 551, "robot_id": "fl1", "type": "safety",   // safety | error | info
  "severity": "critical",                            // info | warning | critical
  "code": "person_detected",                         // see §5
  "message": "Person detected 0.8 m ahead — stopped",
  "x": 2.1, "y": 1.3, "created_at": "..." }

// InventoryMove
{ "id": 90, "pallet_id": 7, "from_code": "R1-L2", "to_code": "DOCK-OUT-1", "task_id": "T-0042", "moved_at": "..." }

// FleetState  (SF-11)
{ "estop": false, "estop_by": null, "estop_at": null, "robots_online": 3, "robots_total": 4,
  "queued_tasks": 2, "active_tasks": 3 }

// Reservation (traffic lock, SF-10)
{ "segment_id": "A11--R1-W1", "robot_id": "fl1", "since": "..." }   // edge id = "<a>--<b>", node ids sorted
```

## 3. Endpoints

| Method | Path | Role | Purpose | Body / query → data |
|---|---|---|---|---|
| GET | `/api/health` | — | Liveness | → `{ "status": "ok", "version": "0.1.0", "mqtt": "disabled\|connected\|disconnected", "simulator": true }` |
| POST | `/api/auth/login` | — | Login | `{ username, password }` → `{ access_token, token_type: "bearer", expires_in, user: User }` |
| GET | `/api/auth/me` | viewer | Current user | → `User` |
| GET | `/api/fleet/state` | viewer | Fleet summary | → `FleetState` |
| POST | `/api/fleet/estop` | operator | Stop all / release (SF-11) | `{ engaged: true\|false }` → `FleetState` |
| GET | `/api/robots` | viewer | Fleet status (FR-06) | → `Robot[]` |
| GET | `/api/robots/{id}` | viewer | One robot | → `Robot` |
| POST | `/api/robots/{id}/cmd` | operator | Robot command | `{ cmd: "pause"\|"resume"\|"go_charge"\|"reset"\|"cancel" }` → `Robot` |
| POST | `/api/robots/{id}/mode` | operator | Manual / auto (FR-10) | `{ mode: "manual"\|"auto" }` → `Robot` |
| POST | `/api/robots/{id}/teleop` | operator | Manual drive, call at ≤10 Hz while held (UI-08) | `{ v: -0.3..0.3, w: -1.0..1.0, lift: -1\|0\|1 }` → `{ accepted: true, limited_v: 0.1 }` (server clamps, SF-07) |
| GET | `/api/robots/{id}/camera/info` | viewer | Can the manual-control camera be watched now (UI-08) | → `CameraInfo` (§3.3) |
| GET | `/api/robots/{id}/camera` | operator | Low-res camera stream, only in manual mode (UI-08) | header or `?token=<jwt>` → `multipart/x-mixed-replace; boundary=frame` (no envelope, §3.3) |
| GET | `/api/tasks` | viewer | List | `?status=a,b&robot_id=&limit=50&offset=0` → `Task[]` + paging meta (newest first) |
| POST | `/api/tasks` | operator | Create move (FR-01) | `{ pallet_id, to_location_id, priority? }` → `Task` (201) |
| GET | `/api/tasks/{id}` | viewer | One task | → `Task` |
| POST | `/api/tasks/{id}/cancel` | operator | Cancel | → `Task` |
| GET | `/api/pallets` | viewer | Inventory | `?q=` (sku/name/aruco) → `Pallet[]` |
| POST | `/api/pallets` | operator | Register pallet | `{ aruco_id, sku, quantity, weight_g, location_id }` → `Pallet` |
| GET | `/api/pallets/{id}/moves` | viewer | Movement history (UI-04) | → `InventoryMove[]` |
| GET | `/api/products` | viewer | Products | → `Product[]` |
| POST | `/api/products` | admin | Add product | `{ sku, name, category }` → `Product` |
| GET | `/api/locations` | viewer | Locations | `?type=` → `Location[]` |
| POST | `/api/locations` | admin | Add location | Location fields minus `id/occupied/pallet_id` → `Location` |
| PATCH | `/api/locations/{id}` | admin | Edit location | partial → `Location` |
| GET | `/api/map` | viewer | Map + lane graph (SV-02) | → `{ width_m, height_m, resolution_m, nodes: [{id,x,y}], edges: [{id,a,b,length,bidirectional}], zones: [{id, kind: "rack"\|"dock_in"\|"dock_out"\|"staging"\|"charge"\|"pedestrian"\|"keepout", label, polygon: [[x,y]...]}], locations: Location[] }` |
| GET | `/api/traffic` | viewer | Segment reservations | → `Reservation[]` |
| GET | `/api/events` | viewer | Event log | `?type=&severity=&robot_id=&limit=100&offset=0` → `Event[]` + paging meta |
| GET | `/api/analytics/summary` | viewer | Analytics (FR-11, UI-05) | `?from=&to=` (ISO, default last 24 h) → see §3.1 |
| GET | `/api/analytics/export` | viewer | CSV export (UI-10) | `?from=&to=&kind=tasks\|events` → `text/csv` file (no envelope) |
| GET | `/api/settings` | viewer | Runtime settings (UI-09) | → Settings |
| PATCH | `/api/settings` | admin | Change settings | partial Settings → Settings |
| GET | `/api/users` | admin | Users | → `User[]` |
| POST | `/api/users` | admin | Add user | `{ username, name, role, password }` → `User` |
| DELETE | `/api/users/{id}` | admin | Remove user | → `{ deleted: true }` |
| POST | `/api/sim/scenario` | admin | Simulator helpers (SV-06) | `{ action: "person"\|"obstacle"\|"drain_battery"\|"disconnect"\|"random_tasks", robot_id? , count? }` → `{ ok: true }` |

### 3.1 Analytics summary

```jsonc
{
  "from": "...", "to": "...",
  "tasks_total": 120, "tasks_done": 110, "tasks_failed": 6, "tasks_cancelled": 4,
  "success_rate": 0.948,               // done / (done + failed)
  "avg_task_seconds": 74.2,
  "avg_wait_seconds": 3.1,              // time spent waiting for a segment lock
  "tasks_per_hour": [{ "hour": "2026-10-16T18:00:00Z", "done": 12, "failed": 1 }],
  "robots": [{ "robot_id": "fl1", "name": "Forklift 1", "tasks_done": 40, "busy_pct": 0.71, "distance_m": 132.4 }],
  "congestion": [{ "segment_id": "J1--J2", "waits": 9, "wait_seconds": 31.0 }],   // heat map input
  "events_by_code": [{ "code": "person_detected", "count": 4 }]
}
```

### 3.2 Settings

```jsonc
{ "max_speed_mps": 0.3, "docking_speed_mps": 0.1, "loaded_raised_speed_mps": 0.1,
  "battery_low_pct": 15, "battery_critical_pct": 8, "battery_resume_pct": 90,
  "allocation_strategy": "nearest",       // nearest | hungarian
  "heartbeat_timeout_s": 3, "simulator_enabled": true, "sim_speed_factor": 1.0 }
```

### 3.3 Camera (UI-08)

The browser never talks to a robot. Each robot may have an optional `camera_url` in `warehouse_map.yaml`
(its `forklift_camera_stream` node, `http://<robot-ip>:8081/stream.mjpg`); the server relays it.

```jsonc
// GET /api/robots/fl1/camera/info → CameraInfo
{ "robot_id": "fl1", "configured": true, "available": false,
  "reason": "camera_inactive",            // null | camera_not_configured | robot_disabled | camera_inactive
  "stream_path": "/api/robots/fl1/camera" }
```

`GET /api/robots/{id}/camera` (operator+) answers `200 multipart/x-mixed-replace; boundary=frame`, one JPEG per part
(`--frame`, `Content-Type: image/jpeg`, `Content-Length: n`, blank line, JPEG bytes, CRLF), byte for byte what the
robot sends: 320×240 at ≤10 fps, JPEG quality 60 by default (about 3–12 kB a frame, ≤1 Mbit/s). Rules:

- streams only while the robot is in `manual` mode (`409 camera_inactive` otherwise; the robot enforces the same rule
  and ends open streams when it leaves manual mode);
- the server authenticates to the robot with the shared `CAMERA_TOKEN` (`Authorization: Bearer`), never with the
  user's JWT;
- at most `CAMERA_MAX_VIEWERS` (default 2) relays per robot; when the viewer disconnects the server closes the
  upstream connection and the robot stops encoding;
- prefer the header: a `?token=` JWT ends up in access logs. The dashboard reads the stream with `fetch` and the
  header; `?token=` exists for a plain `<img src>` (e.g. the kiosk or a quick test).

Errors before the stream starts use the normal envelope (§1): `camera_not_configured`, `camera_inactive`,
`camera_unreachable`, `camera_busy`. A stream that ends or stalls is simply closed; clients reconnect with backoff.

## 4. WebSocket `/ws/live?token=<jwt>` (SV-10: 2 Hz)

Server → client JSON frames, each `{ "type": ..., "data": ..., "ts": "..." }`:

| type | when | data |
|---|---|---|
| `snapshot` | on connect, then every 500 ms | `{ robots: Robot[], reservations: Reservation[], fleet: FleetState }` |
| `task` | any task change | `Task` |
| `event` | any new event | `Event` |
| `inventory` | a pallet moved (SV-09) | `{ pallet: Pallet, move: InventoryMove }` |

Client → server: `{ "type": "ping" }` (server replies `{ "type": "pong" }`). Reconnect with backoff
(1 s, 2 s, 5 s, max 10 s). Close code `4401` = bad token (do not retry; go to login).

## 5. Event codes

`person_detected`, `obstacle_detected`, `tof_stop`, `tof_slow`, `estop_pressed`, `fleet_estop`, `fleet_estop_released`,
`watchdog_timeout`, `wifi_lost`, `robot_offline`, `robot_online`, `battery_low`, `battery_critical`, `go_charge`,
`charged`, `task_assigned`, `task_done`, `task_failed`, `pickup_failed`, `nav_failed`, `deadlock_resolved`,
`manual_mode`, `auto_mode`, `paused`, `resumed`, `reset`.

## 6. Development logins

Seeded only when the database is empty (`backend/app/seed.py`): `admin`, `operator`, `viewer` — passwords are in
`backend/.env.example` (`SEED_*_PASSWORD`), dev-only; change them before any real deployment.
