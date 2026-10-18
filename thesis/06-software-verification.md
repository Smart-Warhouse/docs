# Chapter 6 — Software verification

<!-- Sources: plan.md (status 2026-10-18), .github/workflows/ci.yml, docs/06-backend.md, docs/07-dashboard.md,
     docs/09-mobile.md, docs/10-traceability.md, docs/12-firmware.md §6, docs/13-ros2.md §3, code/*/README.md.
     TODO(integration tests): docs/17 (integration tests), docs/15 (bench tests) and docs/19 (Gazebo) are being written in
     parallel sessions; add their results to §6.5 when they exist. -->

## 6.1 Strategy

The hardware is the critical path of the project and was not available while the software was written. The
verification strategy was therefore designed so that as much as possible can be proven **without hardware**:

1. **Separate decisions from devices.** Everything that decides whether and how fast a forklift may move is plain
   code with no hardware or middleware imports: the firmware's `lib/forklift_core` (C++17, no Arduino headers) and the
   ROS 2 "core" modules (Python without `rclpy`). Device drivers and ROS nodes are thin wrappers.
   <!-- docs/12-firmware.md §1; docs/13-ros2.md intro -->
2. **Test against the contracts.** The robot ↔ server MQTT messages have JSON Schemas (`docs/schemas/`); the robot
   client's tests validate every message it publishes against them, and the server's tests drive the same topics.
   <!-- docs/13-ros2.md §3 "MQTT contract" -->
3. **Simulate the fleet.** The server's simulator moves fake robots through the same lane graph, locks and task
   lifecycle as real robots, so fleet behaviour is testable before any robot exists.
   <!-- docs/01-architecture.md -->
4. **Model the plant.** Control loops (speed, lift) and odometry are tested in closed loop against motor and
   encoder models with deliberate parameter errors.
   <!-- docs/12-firmware.md §6 -->
5. **Run everything in CI** on every push.

## 6.2 Test counts per part

| Part | Tooling | Tests | Status (2026-10-18) |
|---|---|---|---|
| Backend (fleet manager, WMS, API, MQTT bridge, migrations) | pytest | 27 | pass |
| Dashboard | Vitest + Testing Library; typecheck, lint, build | 40 | pass |
| Landing page | Vitest; typecheck, lint, build | 29 | pass |
| Floor app | flutter test; format, analyze | 47 | pass |
| Training (docking env, baseline) | pytest | 8 | pass |
| Firmware core | PlatformIO Unity, native host | 60 | 60 / 60 pass; board build OK (RAM 6.7 %, flash 27.1 %) |
| ROS 2 cores (host) | pytest | 275 | 274 pass, 1 skipped (needs a real broker) |
| ROS 2 on Ubuntu 22.04 / Humble | colcon build + colcon test | 134 | pass in CI |

<!-- plan.md "Done so far": backend 27 (Alembic migrations), dashboard 40, landing 29, mobile 47; plan.md §0: training 8;
     plan.md B1 + docs/12-firmware.md §6: firmware 60/60, RAM 6.7 %, flash 27.1 %;
     plan.md B4 + docs/13-ros2.md §3: 274 passed, 1 skipped; 134 colcon tests -->

On the host this is **485 passing tests** (27 + 40 + 29 + 47 + 8 + 60 + 274), plus 134 colcon tests on Ubuntu in CI.
<!-- sum computed from the table above -->

[CHECK: docs/06-backend.md still says "pytest: 20 tests" and plan.md §0 says 26 at the housekeeping commit; plan.md
"Done so far" says 27 after the Alembic migrations. Re-run `pytest -q` in code/backend before printing and use that
number everywhere.]

## 6.3 Continuous integration

GitHub Actions (`.github/workflows/ci.yml`) runs a change-detection job and eight build/test jobs:

| Job | What it runs |
|---|---|
| backend | `pytest` |
| dashboard | typecheck, lint, test, production build |
| landing | typecheck, lint, test, production build |
| mobile | `dart format` check, `flutter analyze`, `flutter test` |
| training | `pytest` on CPU PyTorch |
| firmware | `pio test -e native`, `pio run -e esp32s3` |
| ros2-host-tests | `pytest` on the rclpy-free cores |
| ros2-colcon-build | in the `ros:humble` container: rosdep, `colcon build`, `colcon test` |

**All nine jobs were green on run 4.** Getting the ROS 2 job green took three rounds of fixes, each a real
integration problem that host tests could not have shown: missing rosdep keys, NumPy 2 against Ubuntu 22.04's
OpenCV (built for NumPy 1), and ArUco corner-refinement accuracy that differed between OpenCV 4.5 and 5 (fixed by
implementing our own sub-pixel corner refinement).
<!-- plan.md §0 CI line; git log e3030b3, 51b4a8e, c306c2d -->

## 6.4 What each part's tests establish

**Backend.** Authentication and roles; the response envelopes; a full task including the WMS move, inventory history,
analytics and CSV; three robots with nine concurrent tasks and a no-shared-lock / no-shared-node invariant checked
every tick; cancel rules; occupied destination; fleet E-stop freeze and release; pause/resume; the person scenario;
low battery → charging; disconnect → re-queue → reset; manual teleop clamp, dead-man and rejoin; WebSocket snapshot;
A*, locks, deadlock detection and both allocators; the MQTT bridge; migrations on new and old databases.
<!-- docs/06-backend.md "Verification so far"; plan.md B7 -->

Beyond the unit suite, **10 stress runs × 1 simulated hour** (3 robots, continuous random tasks, 5 % pickup failures)
showed no gridlock after the back-off fix (not in CI).
<!-- docs/06-backend.md -->

**Firmware.** The safety state machine (ESTOP latched and reset rules; heartbeat loss → SAFE at 501 ms and v = 0 within
600 ms of the last heartbeat; stale commands; sensor faults), the ToF rules by direction, docking and raised-fork caps,
battery hysteresis, rear-steer Ackermann and its inverse, odometry (2 m straight; a full circle closes; 2 m through the
quantised encoder within 1 cm), the speed loop (settles ≤ 300 ms with ≤ 5 % error for 0.09–0.3 m/s, motor gain ± 25 %,
time constant 0.05–0.12 s), the lift loop (20 random heights within ± 3 mm in < 3.5 s), NVS calibration with CRC and the
Madgwick filter.
<!-- docs/12-firmware.md §6 host table -->

**ROS 2.** The MQTT client against the contract (will, credentials, 2 Hz state, sequence numbers, grant/deny with
500 ms retry, foreign grants ignored, retained E-stop, teleop dead-man, offline queue); a full mission through all
phases against a fake fleet server with lane locks; navigation failure handling; server loss (SF-05); the safety
supervisor's clamps and source gating; **ArUco pose ≤ 1 cm and ≤ 2° at 0.2–0.5 m and ± 25° on rendered 30 mm and 60 mm
markers** (PC-04); initial pose from a charger marker ≤ 1 cm / ≤ 1°; the RL observation identical (< 10⁻⁵) to the
training environment on 718 recorded states; URDF expansion, Nav2 footprint and generated filter masks.
<!-- docs/13-ros2.md §3 host table -->

**Apps.** Dashboard: API client and error mapping, live store (WebSocket backoff, 4401 logout), map transform,
role gating, forms. Floor app: models, envelope and errors, map transform, hold-to-stop button, RTL smoke test, teleop
loop. Landing: copy completeness in both languages and an "honesty" test that fails on claims such as "proven" or
"tested results".
<!-- docs/07-dashboard.md; code/mobile/README.md quality gate; code/landing/README.md "Honesty" -->

**Training.** Environment and baseline tests; the ONNX export matches PyTorch to 6·10⁻⁷.
<!-- code/training/README.md; plan.md B2 -->

**End to end without hardware.** The reference robot client (`code/ros2_ws/tools/mqtt_robot_client`) was run against
the server over a real MQTT connection: a task completed and moved the pallet; killing the client fired the Last
Will; killing the broker mid-task re-queued the task and recovery worked; pause/resume and fleet E-stop held.
<!-- plan.md "Done so far"; docs/03-mqtt-contract.md -->

## 6.5 Host-verified vs pending hardware

| Area | Verified now (host / CI) | Needs Ubuntu runtime | Needs hardware |
|---|---|---|---|
| Firmware safety + control | Logic, models | — | Real ToF latency and stop distance (T-06), watchdog on the drivetrain (T-07), PID on real motors (T-03, T-04) |
| micro-ROS link | Topic list written | First compile of the micro-ROS build (Linux) | Topic rates with the real firmware |
| ROS 2 nodes | Cores + colcon build/test | Nodes actually started, Nav2 parameters accepted, slam_toolbox in a namespace, RViz | Localisation (T-08), navigation (T-09) |
| Perception | ArUco on rendered images | — | ArUco on real images (T-10), camera calibration, YOLO dataset + training (T-11) |
| Docking AI | Simulation results, ONNX parity | — | TensorRT latency (AI-05), RL vs classical (T-12) |
| Fleet server | Unit + stress + reference-client E2E | — | Mosquitto ACL with real credentials (CM-01), full tasks (T-13), fleet (T-14), network loss (T-16) |
| Apps | Unit tests | — | Floor app on a real phone; camera stream for manual control (UI-08) |

<!-- docs/12-firmware.md §6; docs/13-ros2.md §3; plan.md "Blocked" table -->

Bench procedures for the hardware rows are in [docs/15-bench-tests.md](../15-bench-tests.md) (Chapter 7).
[CHECK: add the integration-test results (docs/17), vision (docs/16) and Gazebo results (docs/19) here when those
documents are finished.]

## 6.6 Requirement traceability

Every software requirement touched by the code is traced to its implementation and the test that checks it in
`docs/10-traceability.md` (FR, SV, SF, CM, NFR and UI ids). [CHECK: docs/10 was written before the firmware and ROS 2
code existed and still says those requirements "have no code yet"; extend it with FW-*, JS-*, PC-*, NV-* and AI-* rows
from docs/12 and docs/13 before submission.]

## 6.7 Threats to validity

- Models are not plants: the PID and odometry results hold for the motor models used; real motors may differ beyond
  the ± 25 % gain and the time-constant range tested.
- Rendered ArUco images are cleaner than camera images (blur, lighting, lens distortion).
- The fleet simulator uses ideal lane following; real robots will take variable time per lane, which affects waits
  and allocation results.
- Placeholder dimensions (wheelbase, turning radius, floor coordinates) are used everywhere until ME-01 and EN-01.
