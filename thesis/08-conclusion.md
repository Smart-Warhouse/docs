# Chapter 8 — Conclusion and future work

<!-- Sources: plan.md, docs/11-simulation-training.md, docs/06-backend.md, docs/12-firmware.md, docs/13-ros2.md. -->

## 8.1 Summary

This project designed and built the software of a 1:14 smart warehouse with an autonomous forklift fleet and prepared
its hardware. The main outcomes are:

1. **A complete, layered system.** ESP32-S3 firmware with a 1 kHz safety loop, nine ROS 2 packages for the Jetson, a
   fleet manager and WMS with a REST/WebSocket API and an MQTT robot contract, a control-room dashboard with a kiosk
   mode, a floor app and a public landing page — all sharing one design system and one set of contracts.
   <!-- docs/01-architecture.md -->
2. **Safety in four independent layers** — hardware E-Stop, ESP32, Jetson supervisor, server — each of which keeps the
   forklift safe when the layers above it fail.
3. **Fleet traffic control** on a lane graph with all-or-nothing node and lane locks, wait-for-graph deadlock
   detection and detour / back-off resolution; no gridlock in 10 one-hour stress runs with 3 robots and 5 % pickup
   failures. Optimal (Hungarian) allocation completed ≈ 300 tasks/h against ≈ 210 for the nearest rule in the
   simulator — a preliminary result to be repeated on the real map.
   <!-- docs/06-backend.md -->
4. **A docking policy that beats its classical reference in simulation.** Plain PPO and a curriculum both reached 0 %
   success; behaviour cloning from the classical controller followed by conservative PPO fine-tuning and
   validation-based checkpoint selection docked **98.6 %** of 1000 test episodes in **6.4 s** on average, against
   **90.0 %** in **10.3 s** for the classical controller, passing the AI-04 gate.
   <!-- docs/11-simulation-training.md §4; code/training/models/docking_v3/meta.json -->
5. **Verification without hardware.** 485 host tests across seven parts and a nine-job CI pipeline, including a ROS 2
   build and 134 colcon tests on Ubuntu 22.04 / Humble, all passing.
   <!-- Chapter 6 table; plan.md -->

## 8.2 Lessons learned

- **Failed experiments are informative.** The 0 % results of plain PPO and of the curriculum showed that the task's
  success region is too small for random exploration; this led directly to learning from demonstrations.
- **"Last checkpoint" is not "best checkpoint".** PPO fine-tuning improved and then degraded the policy; a separate
  validation set and an explicit selection rule (success − 2 × collisions) were needed.
- **Keep a classical fallback.** The classical controller never collided in simulation. Gating RL against it (AI-04,
  AI-07) means the project works even if learning fails on the real robot.
- **Contracts first.** Writing the MQTT contract and JSON Schemas before the robot client allowed the server, the
  reference client and the ROS 2 mission node to be developed and tested independently.
- **Integration problems hide in the environment.** All three CI fixes for the ROS 2 job (rosdep keys, NumPy 2 vs
  OpenCV, OpenCV corner refinement) were invisible to host tests.
  <!-- plan.md §0 -->

## 8.3 Limitations

- No hardware test has been run yet; every hardware result in Chapter 7 is planned.
- All dimensions (wheelbase, turning radius, floor coordinates) are placeholders until the first forklift and the
  floor are measured.
- The docking results are from simulation only; camera image effects are represented by a noise model.
- The allocation comparison was measured on a placeholder map with simulated speeds.
- The YOLO person detector (SF-06) needs a dataset from the real camera and has not been trained.
  <!-- plan.md B6 -->

## 8.4 Future work

**Immediately after the parts arrive (plan.md Track A, C):**

1. Measure the first forklift, update the shared configuration and retrain the docking policy.
2. Run phases 1–6 of the validation plan (T-01 … T-16) and fill in the results tables of Chapter 7.
3. Collect ≥ 400 images per class from the forklift camera and train YOLO for people, pallets, forklifts and
   obstacles (T-11).
4. Deploy the policy with TensorRT FP16 on the Jetson (≤ 5 ms, 20 Hz).
5. Run the full-system simulation in Gazebo Harmonic with the real ROS nodes against the fleet server
   [CHECK: link docs/19 (Gazebo) when it exists].
6. Re-run the allocation comparison on the real map with real robot speeds
   [CHECK: link docs/18-allocation-study.md when it exists].

**Extensions:**

- Learned docking from camera images in Isaac Lab on a GPU with ≥ 8 GB, compared with the pose-based policy.
- Multi-agent path finding or multi-agent RL for allocation and traffic (AI-08 "advanced").
- A custom PCB for the three forklifts (EL-10) and over-the-air firmware updates (FW-11).
- Camera streaming from the Jetson to the dashboard's manual-control screen (UI-08).

## 8.5 Closing

[TEAM: one paragraph in your own words — what the project taught you and what you would do differently.]

## Acknowledgements

[TEAM: thank [SUPERVISOR], [DEPARTMENT], [UNIVERSITY] and anyone who helped.]
