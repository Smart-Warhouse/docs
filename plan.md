# Project plan — Smart Warehouse & Autonomous Forklift Fleet

Living plan. Tick a box when its acceptance check passes, not when the code is written. Requirement ids
(FR-, SF-, AI-, T-…) refer to [docs/00-sources/system-requirements.md](docs/00-sources/system-requirements.md).
Last updated: 2026-10-18.

The hardware track is the critical path: phases 1–4 run on **one** forklift, then the other two are copied in
phase 5 (requirements §15). Software that needs no hardware runs in parallel.

---

## 0. Housekeeping — do first

- [ ] Commit everything not yet in git: the MQTT robot-client session's backend fixes
      (`code/backend/app/fleet/manager.py`, `mqtt_bridge.py`, `tests/test_mqtt_bridge.py`), the reference client
      (`code/ros2_ws/tools/mqtt_robot_client/`), the training simulator (`code/training/`), `docs/11-simulation-training.md`
      and `docs/media/` (videos + screenshots).
      *Check:* `git status` clean; backend `pytest` (26) and training `pytest` (8) pass on the committed tree.
- [ ] Decide whether the trained model files and videos go into git or into GitHub Releases / Git LFS
      (`docs/media/` ≈ 15 MB, `models/` a few MB).
- [ ] Create the GitHub repository and push (monorepo layout from NFR-10).

---

## Track A — Hardware (critical path, needs the parts)

### A1. Parts and workshop
- [ ] Order one forklift's set from the parts list (≈ 1,507,250 IQD — [parts-bom.pdf](docs/00-sources/parts-bom.pdf));
      the other two sets after phase 4 passes.
- [ ] Check the Jetson kit has a Wi-Fi card (JS-10); if not, add an Intel AX210.
- [ ] Confirm the camera: Camera Module 3 (IMX708) driver on Jetson, else IMX219 or USB camera (JS-03).
- [ ] Confirm the NVMe SSD size fits (2230/2280).
- [ ] Get the Boost converter 6–8.4 V → 12 V, ≥ 30 W for the Jetson (EL-05) — it is not on the parts list yet.

### A2. Open and measure the first forklift (ME-01, ME-02)
- [ ] Document drive motor, steering type (DC or servo), lift motor, side-shift motor, free space inside.
- [ ] Measure each motor's running and stall current (INA219 or meter) → choose the final driver.
- [ ] Measure real dimensions: wheelbase, body length/width, fork length/width/thickness/spacing, lift range,
      minimum turning radius (EN-01).
- [ ] Put the measurements into `code/training/forklift_rl/config.yaml` → retrain the docking policy
      (`scripts/train_ppo.py --bc-episodes 3200 --lr 3e-5 --clip 0.1 --target-kl 0.01 --steps 1000000
      --checkpoint-every 125000`, then `scripts/select_checkpoint.py`; ≈ 15 min).
      *Check:* AI-04 gate ≥ 95 % in `meta.json`.

### A3. Mechanics (ME-03 … ME-14)
- [ ] CAD + 3D-print mounts: LiDAR on the overhead guard, camera on the fork carriage (15–25° down),
      6 ToF mounts, electronics box with ventilation, battery tray low at the rear, E-Stop at the rear top.
- [ ] Fit AS5600 + magnet on the drive axle, slide pot + limit switches on the mast, TCRT5000 on the fork tips.
- [ ] Balance test with the heaviest pallet at full height and minimum turning radius (ME-13).
- [ ] Weigh all add-ons (target ≤ 700 g, ME-14).

### A4. Electronics and power (EL-01 … EL-10)
- [ ] Wire the power tree: battery → BMS → 5 A fuse → main switch → Boost 12 V (Jetson) / Buck 5.1 V (logic) /
      E-Stop (NC) → motor drivers.
- [ ] Perfboard prototype; check every rail with a multimeter before connecting.
- [ ] Verify the ESP32-S3 Zero pin map against the real board (no strapping / PSRAM pins).
- [ ] **T-01 power test:** 30 min at full load — Jetson never browns out, 5 V within ± 5 %.
- [ ] Later: KiCad PCB for the three forklifts (EL-10).

### A5. Warehouse floor (EN-01 … EN-11)
- [ ] Measure the real mini-warehouse; check aisle widths (≥ 85 cm in front of racks, EN-01/02).
- [ ] Re-measure every location (± 2 mm) and update `code/backend/app/warehouse_map.yaml` (nodes, edges, zones,
      locations). Delete `warehouse.db` so it reseeds.
- [ ] Print and stick ArUco markers: 30 mm ids 1–20 on pallets, 60 mm ids 21–40 on racks and chargers (PC-03, EN-08).
- [ ] Matte light floor, boundary walls ≥ LiDAR height + 5 cm, even lighting ≥ 300 lux, 1:14 pedestrian figures.

---

## Track B — Software that can be built now (no hardware needed)

### B1. ESP32-S3 firmware — `code/firmware` (requirements §4) — **recommended next**
- [ ] PlatformIO project (ESP-IDF or Arduino core) on FreeRTOS, same binary for every forklift, `robot_id` in NVS (FW-12).
- [ ] Core 1: `safety_task` 1 kHz (E-Stop sense, limits, ToF thresholds 40 cm → 30 % speed / 15 cm → stop,
      SF-02), `motor_pid_task` 1 kHz (drive speed from AS5600, lift height from the pot, steering servo).
- [ ] Core 0: `imu_task` (MPU9250 + Madgwick), `microros_task`, `status_task` (INA219, WS2812 ring, buzzer).
- [ ] State machine BOOT → IDLE → ACTIVE ↔ SLOW → STOP → SAFE / ESTOP; leaving ESTOP needs an explicit reset (FW-08).
- [ ] Watchdog: no `cmd_vel`/heartbeat for 500 ms → ramp to stop + SAFE (FW-06, SF-04).
- [ ] SF-08: speed ≤ 0.1 m/s when the forks are above 5 cm.
- [ ] Calibration stored in NVS (FW-05); diagnostics topic (FW-10).
- [ ] micro-ROS topics exactly as §10 (`cmd_vel`, `lift_cmd`, `heartbeat`, `wheel_odom`, `imu/data`, `tof_ring`,
      `fork_state`, `battery`, `safety_state`).
      *Check now:* compiles in CI; unit tests for the state machine and the Ackermann conversion on the host.
      *Check later:* T-02, T-03 (speed PID ≤ 300 ms, ≤ 5 %), T-04 (lift ± 3 mm), T-06, T-07 on the bench.

### B2. Policy export for the Jetson (AI-05, AI-06)
- [ ] `code/training/scripts/export_onnx.py`: actor network → ONNX; verify ONNX output = PyTorch output.
- [ ] Safety wrapper in front of the policy: clamp to 0.1 m/s, respect ToF stop, SF-03 front-sensor rule.
- [ ] On the Jetson later: TensorRT FP16, inference ≤ 5 ms, 20 Hz.

### B3. Linux / ROS 2 environment (needs Ubuntu)
- [ ] Install WSL2 Ubuntu 22.04 on the laptop (`wsl --install -d Ubuntu-22.04`) or use an Ubuntu PC.
- [ ] ROS 2 Humble + Nav2 + slam_toolbox + robot_localization + micro-ROS agent (JS-02).

### B4. ROS 2 packages — `code/ros2_ws` (requirements §5–§9)
- [ ] `forklift_description`: URDF/Xacro with the measured dimensions and sensor frames; full TF tree (JS-06).
- [ ] `forklift_interfaces`: Lift, Task, Status messages/services/actions.
- [ ] `forklift_mission`: Behavior Tree + MQTT fleet client implementing [docs/03-mqtt-contract.md](docs/03-mqtt-contract.md)
      (port the logic of `code/ros2_ws/tools/mqtt_robot_client`).
- [ ] `forklift_perception`: ArUco detection + solvePnP ≥ 20 Hz, `pallet_pose` with 5-sample moving average
      (PC-04/05). Can be developed now with a laptop webcam and a printed marker.
- [ ] `forklift_safety`: supervisor that clamps every command source (Nav2, RL, gamepad) (SF-07).
- [ ] `forklift_navigation`: slam_toolbox, EKF, Nav2 with Smac Hybrid-A* + Regulated Pure Pursuit, costmaps,
      keepout and speed filters (NV-01 … NV-12).
- [ ] `forklift_rl`: run the exported policy with TensorRT.
- [ ] `forklift_bringup`: one launch file, YAML configs, namespaces `/fl1 /fl2 /fl3`, systemd autostart (JS-05, JS-07).
- [ ] rosbag recording of every run (JS-08).

### B5. Full-system simulation — `code/ros2_ws/forklift_sim` (AI-01)
- [ ] Gazebo Harmonic world built from the warehouse map (EN-11) + forklift model with LiDAR, camera, IMU.
- [ ] Run Nav2 + mission + the fleet server against simulated forklifts (server `simulated: false`, MQTT on).
- [ ] Optional: Isaac Lab if an RTX GPU with ≥ 8 GB is available (this laptop's RTX 4050 has 6 GB).

### B6. Perception data (needs the real camera)
- [ ] Collect ≥ 400 images per class (`person`, `pallet`, `forklift`, `obstacle`) from the forklift camera,
      label in Roboflow/CVAT, split 70/20/10.
- [ ] Train YOLOv8n/v11n, export TensorRT FP16. *Check:* mAP@0.5 ≥ 0.85, person recall ≥ 0.95, ≤ 30 ms (T-11).

### B7. Server and apps — remaining items
- [ ] Test Mosquitto authentication + ACL for real (needs Docker Desktop working) (CM-01).
- [ ] Add Alembic migrations before the first real deployment.
- [ ] Camera stream for manual control (UI-08) — needs a stream from the Jetson.
- [ ] Release signing for the Flutter app; run it on a real phone.
- [ ] Landing page: team names, supervisor, university, real photos, domain (TODOs in `code/landing/src/i18n/copy/`).

---

## Track C — Integration and tests (in order; each phase starts after the previous passes)

| Phase | What | Tests to pass |
|---|---|---|
| 1 | Power, sensors, motor PID on one forklift | T-01, T-02, T-03, T-04 |
| 2 | Odometry, safety, watchdog | T-05, T-06, T-07 |
| 3 | Localisation and navigation on the real map | T-08, T-09 |
| 4 | Perception and docking: ArUco, YOLO, classical vs RL (30 + 30) | T-10, T-11, T-12 |
| 5 | Copy to forklifts 2 and 3; full task through the dashboard; fleet | T-13, T-14 |
| 6 | Endurance and network loss | T-15, T-16 |

- [ ] Record every test in a results table (date, result, notes) for the thesis results chapter.

---

## Track D — Thesis and defence

- [x] Simulation results available: docking policy 98.6 % vs classical 90 % on 1000 episodes, 6.4 s vs 10.3 s
      ([docs/11-simulation-training.md](docs/11-simulation-training.md)); Hungarian vs nearest allocation
      ≈ 300 vs ≈ 210 tasks/h in the fleet simulator ([docs/06-backend.md](docs/06-backend.md)).
- [x] Demo material in `docs/media/`: dashboard videos (dark, light), simulation walkthrough, RL docking video, screenshots.
- [ ] Write the simulation chapter: environment design, why plain PPO and curriculum failed, imitation + PPO,
      checkpoint selection, results table.
- [ ] Re-run the allocation comparison on the real map with real robot speeds.
- [ ] Replace design targets with measured numbers on the landing page as tests pass.
- [ ] Defence demo: kiosk mode on a big screen + the floor app + live forklifts (fallback: simulator).

---

## Done so far (for reference)

- `docs/` — requirements, architecture, API and MQTT contracts + JSON Schemas, data model, design system,
  traceability, simulation write-up.
- `code/backend` — Fleet Manager + WMS + API + simulator + MQTT bridge (26 tests).
- `code/dashboard` — control-room web console UI-01 … UI-10 (40 tests).
- `code/landing` — bilingual project website (29 tests).
- `code/mobile` — Flutter floor app (47 tests).
- `code/ros2_ws/tools/mqtt_robot_client` — reference robot client; real-robot MQTT path tested end to end against a
  Python broker.
- `code/training` — MuJoCo docking simulator, classical baseline, imitation + PPO policy passing AI-04.
