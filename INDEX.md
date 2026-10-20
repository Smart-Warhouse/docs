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
| 14 | [14-hardware-build.md](14-hardware-build.md) | Wiring diagram, power tree, pin map, 3D-printed mounts (`robot/cad`) |
| — | [architecture/](architecture/README.md) | Full system architecture in one place: layers, repos, hardware, firmware, ROS 2, server, MQTT, task flow, safety, AI, testing, deployment (with PDF) |
| — | [warehouse-map/](warehouse-map/README.md) | Current warehouse map, its 3D and occupancy models, and the requirements + recommended sizes for the new floor (EN-01 … EN-11), Arabic, with PDF |
| — | [measurements/](measurements/README.md) | What to measure on the forklift and pallet, with drawings and a form to send back (ME-01, ME-02) |
| 15 | [15-bench-tests.md](15-bench-tests.md) | Step-by-step bench tests T-01 … T-07 with the firmware console |
| 16 | [16-vision.md](16-vision.md) | YOLO pipeline: data collection, training, ONNX/TensorRT export |
| 17 | [17-integration-tests.md](17-integration-tests.md) | Fleet over a real Mosquitto broker + server response times |
| 18 | [18-allocation-study.md](18-allocation-study.md) | Task allocation study: nearest vs Hungarian (AI-08) |
| 19 | [19-gazebo-sim.md](19-gazebo-sim.md) | Gazebo digital twin running headless in CI |
| — | [thesis/](thesis/) | Thesis chapter drafts, demo script; defence deck: https://claude.ai/artifact/SMrvxUx6hZ3rMrHL4nJYG2 |
| — | [brand/](brand/) | Approved brand kit (logo, app icons, tokens) and the visual-identity prompt |
