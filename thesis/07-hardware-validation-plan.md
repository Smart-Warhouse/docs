# Chapter 7 — Hardware validation plan

<!-- Sources: docs/00-sources/system-requirements.md §14 (T-01..T-16), §15; plan.md Track A and Track C;
     docs/12-firmware.md §6 "Needs the bench"; docs/13-ros2.md §3.
     docs/14-hardware-build.md (mounts, power tree, pin map, parts still to buy) and docs/15-bench-tests.md (step-by-step
     procedures and summary sheet for T-01 … T-07). ALL RESULTS IN THIS CHAPTER ARE PLANNED — the tables are left empty
     on purpose. -->

The build itself (3D-printed mounts generated with CadQuery from one parameter file, the power tree, the ESP32-S3
pin map and the parts that are not yet on the parts list) is documented in
[docs/14-hardware-build.md](../14-hardware-build.md). Step-by-step bench procedures for T-01 … T-07, with safety rules,
tools and a summary sheet, are in [docs/15-bench-tests.md](../15-bench-tests.md).

## 7.1 Approach

Tests run in order from a single part to the whole system, and each phase starts only after the previous one passes,
so that errors do not pile up. Phases 1–4 run on **one** forklift; the other two are built as copies in phase 5.
<!-- docs/00-sources/system-requirements.md §14 intro, §15; plan.md Track C -->

| Phase | Scope | Tests |
|---|---|---|
| 1 | Power, sensors, motor PID on one forklift | T-01, T-02, T-03, T-04 |
| 2 | Odometry, safety, watchdog | T-05, T-06, T-07 |
| 3 | Localisation and navigation on the real map | T-08, T-09 |
| 4 | Perception and docking: ArUco, YOLO, classical vs RL (30 + 30) | T-10, T-11, T-12 |
| 5 | Copy to forklifts 2 and 3; full task through the dashboard; fleet | T-13, T-14 |
| 6 | Endurance and network loss | T-15, T-16 |

<!-- plan.md Track C table -->

**Prerequisites before phase 1** (plan.md Track A): order one forklift's parts; confirm the Jetson Wi-Fi card, the
camera driver (IMX708 or a fallback) and the SSD size; buy the 12 V boost converter; open and measure the first
forklift (ME-01, ME-02) and retrain the docking policy with the real dimensions (≈ 15 min); print and fit the mounts;
wire and check the power tree; measure the floor and update the map; print the ArUco markers.

## 7.2 Test definitions

| Test | Level | Method | Acceptance criterion | Covers |
|---|---|---|---|---|
| T-01 Power | Part | Measure voltages and currents at full load for 30 min | Jetson never browns out; 5 V rail within ± 5 % | EL-01..05 |
| T-02 Sensors | Part | Read every sensor against a ruler / protractor | ToF ± 1 cm; IMU yaw drift ≤ 2°/min | FW-05 |
| T-03 Speed PID | Part | Step commands, plot the response | Settles ≤ 300 ms; steady error ≤ 5 % | FW-03 |
| T-04 Lift PID | Part | 20 random height commands | ± 3 mm | FW-04 |
| T-05 Odometry | Forklift | 2 m straight and a 1 × 1 m square | Error ≤ 3 % of distance | FW-02 |
| T-06 Safety | Forklift | Sudden obstacle in front at 0.3 m/s, 20 times | Stops 100 % without contact; ≤ 100 ms | SF-01..04, NFR-04 |
| T-07 Watchdog | Forklift | Unplug the USB link while moving | Stops within ≤ 600 ms | FW-06 |
| T-08 Localisation | Forklift | 10 marked floor points | ≤ 3 cm, ≤ 3° | NV-02, NFR-01 |
| T-09 Navigation | Forklift | 30 trips between random points | ≥ 95 % arrive without collision | NV-05..11 |
| T-10 ArUco | Forklift | Pallet pose from 5 distances × 3 angles | ≤ 1 cm, ≤ 2° | PC-04 |
| T-11 YOLO | Software | Test set + latency on the Jetson | mAP@0.5 ≥ 0.85; ≤ 30 ms | PC-07, PC-08 |
| T-12 Docking | Forklift | 30 classical + 30 RL attempts | ≥ 90 % success; RL ≥ classical | FR-04, AI-07 |
| T-13 Full task | System | 20 move tasks from the dashboard, one forklift | ≥ 90 % without intervention; WMS updated | FR-01..06 |
| T-14 Fleet | System | 3 forklifts × 30 min of concurrent tasks | No collision; no permanent deadlock | FR-08, SV-03 |
| T-15 Endurance | System | Continuous operation until low battery | ≥ 45 min; goes to charge by itself | NFR-05, SF-09 |
| T-16 Network loss | System | Switch off the router during tasks | Safe stop, then resume when the link returns | SF-05, CM-03 |

<!-- docs/00-sources/system-requirements.md §14 (translated) -->

## 7.3 Procedures prepared in software

Several tests already have a procedure and a host-side prediction; the bench run checks what the model cannot.
Full procedures for T-01 … T-07 are in docs/15-bench-tests.md; the table below summarises them.
<!-- docs/12-firmware.md §6 "Needs the bench / the forklift"; docs/15-bench-tests.md -->

Writing the bench procedures exposed four firmware gaps to close before the bench run: no IMU readout on the
console (T-02 needs micro-ROS for yaw drift), bench mode refreshes the heartbeat itself so pulling the USB cable does
not trip the watchdog, no console command that drops the heartbeat while keeping a non-zero command (T-07), and no
timestamped state-change log (T-06 latency is measured by slow-motion video instead).
<!-- docs/15-bench-tests.md "Gaps found while writing these procedures" -->

| Test | Prepared procedure | Host prediction to compare with |
|---|---|---|
| T-02 | Firmware console `tof` and `status` against a ruler / protractor after `cal imu`; watch `i2c_err` in `diag` | — |
| T-03 | Wheels off the ground: `bench on`, `step 0.2 1000` → CSV; retune with `cal drive` or the ROS parameters | Settles ≤ 300 ms, ≤ 5 % error on the motor model (docs/12 §6) |
| T-04 | `cal pot …`, then 20 × `lift <mm>` checked with a ruler | All 20 within ± 3 mm in < 3.5 s on the model |
| T-05 | Drive 2 m and a 1 × 1 m square; compare `wheel_odom` with floor marks | 2 m through the quantised encoder within 1 cm on the model |
| T-06 | Obstacle 20 × at 0.3 m/s; log `safety_state` and `loop_us` from `diagnostics` | v = 0 in the same 1 ms tick at < 15 cm (logic only) |
| T-07 | Unplug USB while moving, or `bench off` without the Jetson | 560 ms on the model (limit 600 ms) |
| T-10 | Printed markers at 5 distances × 3 angles; compare `pallet_pose` with measured positions | ≤ 1 cm / ≤ 2° on rendered images (docs/13 §3) |
| T-12 | `forklift_rl` dock action, alternating classical and RL, 30 each, same start poses | Simulation: 90.0 % vs 98.6 %, 10.3 s vs 6.4 s (Chapter 4) |
| T-16 | Router off mid-task; robot should finish its lane, stop, and resume (`require_reset_after_server_loss: false`) | Host: step finishes, nothing new starts, `wifi_lost` event on reconnect (docs/13 §3) |

## 7.4 Results (to be filled)

Record every run with its date, the commit hash of the firmware / ROS / server, the result and notes. Raw logs
(rosbag, CSV) go next to the results table in the repository.
<!-- plan.md Track C "Record every test in a results table" -->

| Test | Date | Commit | Result | Pass / fail | Notes |
|---|---|---|---|---|---|
| T-01 Power | | | | planned | |
| T-02 Sensors | | | | planned | |
| T-03 Speed PID | | | | planned | |
| T-04 Lift PID | | | | planned | |
| T-05 Odometry | | | | planned | |
| T-06 Safety | | | | planned | |
| T-07 Watchdog | | | | planned | |
| T-08 Localisation | | | | planned | |
| T-09 Navigation | | | | planned | |
| T-10 ArUco | | | | planned | |
| T-11 YOLO | | | | planned | |
| T-12 Docking | | | | planned | |
| T-13 Full task | | | | planned | |
| T-14 Fleet | | | | planned | |
| T-15 Endurance | | | | planned | |
| T-16 Network loss | | | | planned | |

### T-12 docking comparison (to be filled)

| Controller (real forklift, 30 attempts each) | Docked | Collisions / contacts | Mean time | Lateral error |
|---|---|---|---|---|
| Classical | | | | |
| RL (docking_v? retrained with ME-01 dimensions) | | | | |

## 7.5 Risks to the plan

| Risk | Effect | Mitigation |
|---|---|---|
| Real dimensions differ from the placeholders | Planner turning radius, RL policy and footprint wrong | Measure first (ME-01); everything reads one config; retrain in ≈ 15 min |
| Camera driver for IMX708 missing on JetPack | No perception | Fallback IMX219 or USB camera (JS-03) |
| Motors stall above driver ratings | Driver failure | Measure stall current first (ME-02) before choosing the driver |
| Jetson brown-out on motor current spikes | Reboots | Separate boost branch; T-01 at full load for 30 min |
| Aisles too narrow for a 90° turn | Navigation fails at racks | EN-01 check; adjust the floor before T-09 |
| RL does not beat classical on the real robot | AI-07 not met | The classical controller is the default and fallback; report honestly |
| Build of three forklifts takes longer than planned | T-14 late | Phases 1–4 on one forklift; the defence can fall back to the simulator (demo script) |

<!-- docs/00-sources/system-requirements.md ME-01, ME-02, JS-03, EN-01, EL-05; plan.md A1–A5 -->
