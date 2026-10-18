# Docs index

| # | Document | What |
|---|---|---|
| 00 | [00-sources/](00-sources/) | The original material: [system requirements](00-sources/system-requirements.md), [project overview PDF](00-sources/project-overview.pdf), [parts / BOM PDF](00-sources/parts-bom.pdf) |
| 01 | [01-architecture.md](01-architecture.md) | Layers, code map, key design decisions |
| 02 | [02-api-contract.md](02-api-contract.md) | REST + WebSocket contract (server ↔ dashboard / app) |
| 03 | [03-mqtt-contract.md](03-mqtt-contract.md) + [schemas/](schemas/) | Robot ↔ server MQTT topics and JSON Schemas |
| 04 | [04-data-model.md](04-data-model.md) | WMS tables and the lane-graph map file |
| 05 | [05-design-system.md](05-design-system.md) | Palette, tokens, type, RTL, icons shared by the three UIs ([fonts](brand/fonts/)) |
| 06 | [06-backend.md](06-backend.md) | Server modules, simulator, test results |
| 07 | [07-dashboard.md](07-dashboard.md) | Control-room console: screens ↔ UI-01..UI-10 |
| 08 | [08-landing.md](08-landing.md) | Public project website |
| 09 | [09-mobile.md](09-mobile.md) | Floor operator app: use cases |
| 10 | [10-traceability.md](10-traceability.md) | Requirement → code → test |
| 11 | [11-simulation-training.md](11-simulation-training.md) | Hardware simulation (MuJoCo) for training the docking AI: research, env, baseline, results |
| 12 | [12-firmware.md](12-firmware.md) | ESP32-S3 firmware: tasks, state machine, safety, what is host-tested vs bench |
| 13 | [13-ros2.md](13-ros2.md) | ROS 2 packages, node/topic graph per robot, host tests vs what needs Ubuntu |
