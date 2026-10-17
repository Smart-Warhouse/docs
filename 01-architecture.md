# 01 — System architecture

Source: [system-requirements.md](00-sources/system-requirements.md) and [project-overview.pdf](00-sources/project-overview.pdf).

## Layers

```
 ┌──────────────────────────── Layer 4 · Server (LAN laptop / mini PC) ─────────────────────────────┐
 │  code/backend  FastAPI ─ Fleet Manager (allocation, lane graph A*, traffic locks, battery policy)  │
 │                         ─ WMS (PostgreSQL: locations, pallets, tasks, events, moves)              │
 │                         ─ REST /api + WebSocket /ws/live (2 Hz)  ─ simulator (fake robots)        │
 │                Mosquitto MQTT broker                                                             │
 │  code/dashboard  React control-room console  ·  code/mobile  Flutter floor app                   │
 │  code/landing    public project site (no API)                                                    │
 └───────────────▲──────────────────────────────── Wi-Fi 5 GHz · MQTT JSON ───────────────────────────┘
                 │ task / cmd / estop ↓       state / task_status / event ↑      traffic request/grant ↕
 ┌───────────────┴──────────── Layer 3 · Jetson Orin Nano Super (×3) — code/ros2_ws ─────────────────┐
 │  forklift_mission (BT + MQTT fleet client) · forklift_navigation (slam_toolbox, EKF, Nav2)         │
 │  forklift_perception (ArUco, YOLO/TensorRT) · forklift_rl (docking policy) · forklift_safety       │
 └───────────────▲──────────────────────────────── USB · micro-ROS ──────────────────────────────────┘
 ┌───────────────┴──────────── Layer 2 · ESP32-S3 — code/firmware ───────────────────────────────────┐
 │  Core 1 (1 kHz): safety loop (ToF, limits, E-stop, watchdog 500 ms), PID drive, PID lift           │
 │  Core 0: micro-ROS client, IMU, status LEDs                                                        │
 └───────────────▲─────────────────────────────────────────────────────────────────────────────────┘
 Layer 1 · sensors + motors + hardware E-Stop (cuts motor power without software)
```

## Code map

| Folder | What | Status |
|---|---|---|
| `code/backend` | Fleet Manager + WMS + API + simulator + MQTT bridge (Python 3.11, FastAPI, SQLAlchemy, PostgreSQL/SQLite) | built, tested |
| `code/dashboard` | Control-room web console UI-01..UI-10 (React 19 + TS + Vite + Tailwind) | built |
| `code/landing` | Public project website (React + Vite, static) | built |
| `code/mobile` | Floor operator app: stop-all, alerts, fleet, tasks, manual drive (Flutter) | built |
| `code/firmware` | ESP32-S3 firmware (PlatformIO, FreeRTOS, micro-ROS) — §4 | placeholder |
| `code/ros2_ws` | ROS 2 Humble packages on the Jetson — §5–§8 | placeholder |
| `code/training` | YOLO + RL training (Gymnasium/SB3, Ultralytics) — §6, §8 | placeholder |

## Why the server is independent of ROS

The server speaks plain MQTT + JSON (§10), so it can be developed and demoed **before any forklift exists**:
the built-in simulator (SV-06) drives fake robots over the same lane graph, traffic locks and task lifecycle the
real robots will use. When a real forklift comes online, set `simulated: false` for it in
`code/backend/app/warehouse_map.yaml`, enable MQTT, and the same Fleet Manager logic drives it.

## Key decisions

| Decision | Choice | Requirement |
|---|---|---|
| Traffic control | Lane graph (YAML) + per-node and per-lane locks, all-or-nothing acquisition, wait-for-graph deadlock detection, detour or back-off resolution | FR-08, SV-03, SF-10, NV-09 |
| Pallet stations | Every rack slot / dock / charger is a dead-end *spur* node: robots never route through a spur, so a robot docking never blocks an aisle | NV-11 |
| Task allocation | `nearest` (v1) and optimal `hungarian` (v2), switchable at runtime; compared by tasks/hour | AI-08 |
| WMS consistency | Pallet location changes only when the robot reports `done`, in one transaction with the inventory move | SV-09 |
| Safety on the server | Fleet E-stop (retained MQTT), battery policy (low → charge, critical → safe stop), teleop clamping, dead-man timeout | SF-05, SF-07..SF-11 |
| Adding a robot | One line in `warehouse_map.yaml` | NFR-09 |
