# 11 — Hardware simulation for training the docking AI

Requirements §8 (AI-01..AI-09) and the pallet-docking task table. Code: `ai/training/`.

## 1. What was researched

| Option | What it gives | Fit for this project today |
|---|---|---|
| **NVIDIA Isaac Sim / Isaac Lab** | Photoreal rendering, thousands of parallel envs on the GPU, strong domain randomisation. A 2024 study of a **1:14 forklift** used Isaac Sim + PPO with camera images as input and reached **60 % real-world approach success** (10 trials) — the closest prior work to this project. | Needs an RTX card with ≥ 8 GB (RTX 3070 minimum, 4080 recommended per NVIDIA forum guidance) and in practice Linux. This laptop has an **RTX 4050 Laptop, 6 GB** → below the minimum. Revisit on a lab PC or Colab-class GPU. |
| **Gazebo (Harmonic) + ROS 2** | Full-system digital twin: LiDAR, camera, Nav2, the real ROS nodes. Most published forklift RL work uses Gazebo (e.g. a 2026 multi-expert forklift RL paper on Gazebo 11 + ROS Noetic with randomised mass, friction and obstacles). | Needs Linux (Ubuntu 22.04 / WSL2). No WSL distro is installed here. Planned for `robot/ros2_ws/forklift_sim` (AI-01 "full system"). |
| **MuJoCo + Gymnasium** | Fast, accurate contact physics, native on Windows, offscreen rendering, ~2,000 env-steps/s per CPU core, plugs straight into Stable-Baselines3. No published forklift work found — but the requirement only needs a light env for fast training (AI-01 "بيئة Gymnasium خفيفة"). | **Chosen** for the training env now. |

Design consequence: instead of learning from pixels (the 60 % study), our policy observes the **ArUco pallet pose**
(PC-04/05) plus ToF/TCRT readings. That is the input our real perception stack already produces, so the
sim-to-real gap is in the pose noise and the actuator dynamics — both of which are randomised.

Sources: [Visual-based forklift learning system, zero-shot sim2real (1:14 forklift, Isaac Sim)](https://arxiv.org/html/2412.11503v1) ·
[Multi-expert RL for autonomous forklifts (Gazebo 11)](https://arxiv.org/pdf/2601.07304) ·
[Mapless navigation in intralogistics with Isaac SDK](https://arxiv.org/pdf/2202.11512) ·
[Isaac Sim GPU requirement (NVIDIA forum)](https://forums.developer.nvidia.com/t/gpu-requirement/305727/2) ·
[Gymnasium custom-environment tutorial](https://gymnasium.farama.org/v1.1.1/tutorials/gymnasium_basics/) ·
[Pallet detection and docking with autonomous forklift (IEEE)](https://gcris.ieu.edu.tr/entities/publication/5129756f-05ce-4394-9a02-d61b6a1cbb45)

## 2. The environment (`forklift_rl/`)

| Part | Implementation | Requirement |
|---|---|---|
| Forklift | 1:14 Huina 1577-style body, **rear-wheel steering** (bicycle model about the front drive axle: ω = −v·tanδ/L), forks on a lift joint, mast, LiDAR, wheels. Dimensions in `config.yaml` (placeholders until ME-01). | FW-01, ME-01 |
| Pallet | 20 × 20 cm deck, three stringers → two fork openings, load box, **real ArUco DICT_4X4_50 id 7** texture (generated with OpenCV). On the floor or on a rack shelf at 60 mm. Free body — anything that pushes it > 1 cm is a collision. | PC-03, EN-04, EN-05 |
| Observation (18) | pallet pose in the carriage frame from the simulated marker (FOV cone, minimum range, ±5 mm / ±1° noise, per-episode bias, 5-sample moving average, odometry carry-over when not visible), fork-height error, speed, steering, fork height, 3 front ToF rays, 2 TCRT fork-tip sensors, previous action, time left | §8 observation row, PC-05 |
| Action (3) | speed ±0.1 m/s, steering ±30°, lift rate | §8 action row, SF-03 |
| Reward | progress to the goal + lateral/heading/height error reduction, −0.01 per step, steering-change penalty, **+100 docked, −100 collision**, −50 out of range | §8 reward row |
| Success | forks ≥ 80 % inside, lateral ≤ 1 cm at both tip and carriage, forks within the opening height, pallet not moved | §8 success row, NFR-02 |
| Start | 30–60 cm from the pallet, ±10 cm lateral, ±20°, random fork height | §8 start row |
| Domain randomisation | floor friction 0.6–1.2, motor delay 20–80 ms, actuator lag, wheel slip 0.90–1.05, steering bias ±1.5°, pallet load 0–0.4 kg, marker noise and bias, sensor noise | AI-03 |

## 3. Classical baseline (AI-07 reference)

`forklift_rl/baseline.py`: lift to the opening height, track the pallet axis with a second-order lateral controller
in the distance domain (κ = −(2ζλ·heading + λ²·lateral), λ = 11 m⁻¹), slow near the face, back off and retry when
the fork tips arrive misaligned. Same observation as the policy.

**Result on 1000 randomised episodes (seeds 10000–10999): 90 % docked, 0 % collisions, 10.3 s mean, 1.7 mm mean
lateral error at the tips.** The RL policy has to beat this (AI-07).

## 4. Training (AI-02, AI-09)

`scripts/train_ppo.py`: Stable-Baselines3 PPO, 16 parallel envs, MLP 128×128, 2–3 M steps, checkpoints every
0.5 M, TensorBoard logs in `runs/`, evaluation every 250 k steps, a final 1000-episode evaluation against the
**AI-04 gate (≥ 95 %)** and a versioned output folder `models/docking_vN/` with `policy.zip` + `meta.json`.

What did not work, and why (worth a paragraph in the thesis):

- **Plain PPO (v1):** after 400 k steps, 0 % success **and** 0 % collisions — the policy learned that standing still
  (return ≈ −3) beats trying (≈ −31 on average): the forks have only 1.75 cm clearance per side and the randomised
  steering bias alone drifts ≈ 1 cm over 40 cm, so random exploration essentially never inserts.
- **Curriculum (`--curriculum`):** start close and aligned, widen on success. Still 0 % at 250 k: even at the easiest
  level, driving straight collides 67 % of the time — closed-loop correction is needed from the very first step.

What works — **RL from demonstrations** (`--bc-episodes N`): roll out the classical controller N times, clone its
actions into the PPO actor (behaviour cloning, MSE) and fit the critic to its discounted returns, then fine-tune with
PPO on the original §8 reward at a lower learning rate. The cloned policy alone already docked **95 %** of 200
evaluation episodes (baseline 90 %) but with 4 % collisions; PPO fine-tuning is meant to remove those and shorten
the docking time.

**Final run v3:** 3,200 demonstrations → behaviour cloning → PPO fine-tuning for 1 M steps with a conservative update
(lr 3·10⁻⁵, clip 0.1, target KL 0.01), 12 min on 16 CPU cores. A larger learning rate (v2: lr 10⁻⁴, clip 0.2)
peaked early and then drifted to 91 % with 9 % collisions — fine-tuning has to stay close to the cloned behaviour.
`scripts/select_checkpoint.py` chose the best checkpoint on **validation seeds 20000–20399**, then it was scored once
on the **test seeds 10000–10999**:

| Controller (1000 test episodes, full randomisation) | Docked | Collisions | Mean time | Lateral error |
|---|---|---|---|---|
| Classical baseline | 90.0 % | 0.0 % | 10.3 s | 1.7 mm |
| Imitation only (200 episodes) | 90.0 % | 0.0 % | 9.9 s | 1.7 mm |
| **Imitation + PPO (checkpoint 625 k)** | **98.6 %** | 1.4 % | **6.4 s** | 2.7 mm |
| PPO end of training (1 M) | 95.3 % | 4.7 % | 6.3 s | 2.3 mm |

The selected policy passes the **AI-04 gate (≥ 95 % in simulation)**, docks 38 % faster than the classical
controller and stays within the 10 mm lateral limit. The remaining 1.4 % are collisions. §5 shows that the safety
supervisor and the ESP32 ToF ring do **not** catch them, because they happen with the forks already inside the
pallet. The baseline's 0 % collision rate is a reason to keep it as the fallback. These are simulation results
only; the real comparison is AI-07 / T-12.
Model files: `ai/training/models/docking_v3/` (`policy_selected.zip`, `meta.json` with every number above).
Video: [`docs/media/rl-docking-simulation.mp4`](media/rl-docking-simulation.mp4).

## 5. Safety supervisor (AI-06)

AI-06 says every policy command passes the safety supervisor (0.1 m/s, ToF) before it reaches the ESP32. To check
what that does to docking, `forklift_rl/safety_wrapper.py` (a `gymnasium.Wrapper`) runs every policy action through
the **same two safety layers as the robot**:

```
policy.onnx (onnxruntime) → (v, ω) as docking_core.action_to_command
  → Jetson: forklift_safety.safety_core.SafetySupervisor   (the real module, imported from ros2_ws, source "dock")
  → ESP32:  forklift_rl/firmware_limiter.DriveLimiter       (port of lib/forklift_core, see below)
  → simulated motors
```

Both layers get the readings the policy sees: the three front ToF rays (front-left, front, front-right; the side
and rear sensors are not simulated and report "no target") and the fork height. The supervisor also gets the ESP32
state byte from the previous tick, as on the robot. Same as the robot's docking node, the policy sees its own
previous action, and the episode is aborted when the supervisor holds the forklift stopped for 3 s
(`safety_stop_timeout_s`).

**Equivalence with the firmware.** Calling the C++ from Python needed no binding layer, so the ESP32 layer is a
one-to-one Python port (`direction_of`, `evaluate_tof`, `speed_cap`, `ramp_speed` and the normal-driving part of
`SafetyStateMachine::update`). `tests/test_firmware_limiter.py` checks the port three ways:
1. its constants are parsed out of `config.h`, so the test fails if the firmware changes and the port does not;
2. the firmware's own native tests for ToF, docking, raised forks and speed caps (`test/test_safety/test_safety.cpp`)
   are replayed at 1 kHz;
3. when `g++` is installed, `safety_limiter.cpp` and `safety_state_machine.cpp` are compiled into a shared library
   with a small `extern "C"` shim (`tests/firmware_shim.cpp`). The test then compares port and C++ on 10,000 random
   ToF/cap/ramp inputs and on 4 × 4000-tick random drives. Speed, yaw rate and the `safety_state` byte must agree.

`scripts/eval_safety.py` uses the same 1000 test seeds (10000–10999) as the AI-04 gate. Results are in
`models/docking_v3/safety_eval.json`; the run takes 9 min on 10 processes.

| 1000 test episodes | Docked | Collisions | Safety aborts | Timeouts | Mean time |
|---|---|---|---|---|---|
| Policy alone | 98.6 % | 1.4 % | – | 0 % | 6.41 s |
| Policy + supervisor, *original* docking mask (centre ToF only — since fixed) | **0 %** | 0.1 % | 99.5 % | 0.4 % | – |
| **Policy + supervisor, current firmware mask** (all three front ToF ignored while docking) | 98.7 % | 1.3 % | 0 % | 0 % | 6.48 s |
| Policy + supervisor, front ignored + *proposed* docking stop (2 cm) | 98.7 % | 0.8 % | 0.5 % | 0 % | 6.48 s |
| Baseline alone | 90.0 % | 0 % | – | 10.0 % | 10.30 s |
| Baseline + supervisor, original mask | 0 % | 0 % | 74.6 % | 25.4 % | – |
| Baseline + supervisor, current firmware mask | 89.7 % | 0 % | 0 % | 10.3 % | 10.32 s |

What it shows:

1. **The original docking mask blocked every docking — now fixed.** `TOF_MASK_DOCKING_IGNORE` (and the supervisor's
   `docking_ignored_tof`) used to leave out only the centre sensor. The two corner sensors (±8.4 cm, 2 cm above the floor)
   look straight at the outer stringers of a floor pallet, or at the rack shelf face. They read < 15 cm while the
   fork tips are only ≈ 4 cm inside (2 cm on the rack), so SF-02 stops the forklift (70,271 `tof_stop` steps in 999 episodes) and the
   docking node gives up. `config.h` already says "add the corners if they also see the pallet". In this model of
   the forklift they do, so **SF-03 has to ignore all three front sensors while docking** (both the firmware mask and
   `forklift_safety` `docking_ignored_tof`). **Done:** both now ignore all three front sensors while docking (firmware
   test `test_docking_ignores_front_sensors_and_caps_speed`, re-evaluated: 98.7 % docked). This still has to be
   checked on the real forklift once the ToF ring is mounted (ME-06); drop a corner from the mask if it never
   sees the pallet.
2. **With that fixed, the supervisor hardly changes the policy, and it prevents none of its collisions.** The
   action space already ends at 0.1 m/s, so neither the docking cap (SF-03) nor the raised-fork cap (SF-08) ever
   binds. The only active rule is the supervisor's acceleration ramp (0.5 m/s², 3000 steps = 2.3 % of commands, about
   three steps per episode while starting off). Paired by seed: 3 of the 14 policy-alone collisions dock instead, and 2 other seeds collide
   instead of docking (13 vs 14). That is the small trajectory change of the ramp, not a ToF stop. Cost: +0.07 s
   mean time, 6 baseline episodes become timeouts. No new safety aborts.
3. **Why the ToF rules cannot help.** Every policy collision happens *inside* the pallet. In 9 of 14 the forks are
   in deeper than the 80 % goal but 10–16 mm to the side (success needs ≤ 10 mm), the policy keeps driving and the
   fork backrest hits the deck. In 4 the mast hits the rack shelf the same way, and in 1 a fork tip hits the centre
   stringer. A rule that stops for things in front of the forks would block docking itself.
4. **A docking stop would be a candidate rule (not implemented on the robot).** While docking, stop when a
   front-corner ToF reads below a threshold, i.e. the forks are fully in. The threshold was chosen on the
   validation seeds 20000–20399 with the checkpoint rule max(success − 2·collision); 4 cm already blocked 38 % of
   dockings. On the test seeds the chosen 2 cm prevents 7 of 14 collisions: all 5 mast-on-rack collisions, with 4
   seeds becoming safe aborts and 3 docking instead. The 7 backrest-on-deck collisions remain, and 1 good docking
   becomes an abort. The better fix belongs in the docking logic, not in the safety layer: stop at the insertion
   depth whatever the lateral error, then back off and retry like the baseline.

## 6. Stress tests

The same 1000 seeds, each time with one condition outside the training randomisation. The supervisor runs with all
front ToF ignored (row 3 above), and additionally with the proposed docking stop.

| Condition | Policy alone: docked / coll. | + supervisor | + supervisor + docking stop (aborts) |
|---|---|---|---|
| Training randomisation | 98.6 % / 1.4 % | 98.7 % / 1.3 % | 98.7 % / 0.8 % (0.5 %) |
| Marker noise and bias ×2 (±10 mm, ±2°) | 95.4 % / 4.6 % | 95.9 % / 4.1 % | 95.6 % / 2.5 % (1.9 %) |
| Motor delay 120 ms (trained 20–80 ms) | 99.0 % / 1.0 % | 99.1 % / 0.9 % | 99.1 % / 0.8 % (0.1 %) |
| Steering bias ±3° (trained ±1.5°) | 96.6 % / 3.4 % | 96.4 % / 3.6 % | 95.9 % / 2.1 % (2.0 %) |
| Low friction 0.3–0.5 + wheel slip 0.80–0.95 | 98.6 % / 1.4 % | 98.8 % / 1.2 % | 98.6 % / 1.0 % (0.4 %) |

- The policy stays **above the 95 % AI-04 gate in every condition**. Doubled marker noise and the ±3° steering
  bias cost the most: both leave a lateral error the policy only partly removes before the forks go in.
- A 120 ms motor delay does not hurt. The policy drives slowly near the pallet, so the delay barely matters.
- In this simulator the base is driven by velocity actuators, so floor friction only acts on the pallet. "Low
  friction" is modelled as wheel slip, which makes docking slower (7.1 s vs 6.4 s) but not less safe.
- The supervisor as it is changes none of this. The proposed docking stop turns about half of the stress
  collisions into safe stops, but at 2 % aborts it also costs dockings. The real fix is still the docking logic
  (§5.4). Physical safety stays with the ToF ring for obstacles that are not the pallet (people, a second pallet,
  a wall), which this docking task does not include.

No clip was rendered: with the robot's rules no collision is actually prevented by a safety stop, so a "prevented
collision" video would be misleading.

## 7. Next steps

1. Measure the real forklift (ME-01) and update `config.yaml`; re-fit the actuator lag and delay from T-03.
2. `scripts/export_onnx.py` → TensorRT FP16 on the Jetson (AI-05), wrapped by `forklift_safety` (AI-06). Before
   that, add the front corners to the SF-03 docking mask (§5.1) if the mounted ToF ring sees the pallet with them.
3. Docking logic: stop at the insertion depth and back off when the lateral error is too large (§5.4), then
   re-run `scripts/eval_safety.py`.
4. Real comparison: 30 baseline + 30 RL attempts (AI-07, T-12).
5. Full-system twin in Gazebo Harmonic (`robot/ros2_ws/forklift_sim`) once a Linux machine is available; Isaac Lab if
   an 8 GB+ RTX GPU is available.
