# 11 — Hardware simulation for training the docking AI

Requirements §8 (AI-01..AI-09) and the pallet-docking task table. Code: `code/training/`.

## 1. What was researched

| Option | What it gives | Fit for this project today |
|---|---|---|
| **NVIDIA Isaac Sim / Isaac Lab** | Photoreal rendering, thousands of parallel envs on the GPU, strong domain randomisation. A 2024 study of a **1:14 forklift** used Isaac Sim + PPO with camera images as input and reached **60 % real-world approach success** (10 trials) — the closest prior work to this project. | Needs an RTX card with ≥ 8 GB (RTX 3070 minimum, 4080 recommended per NVIDIA forum guidance) and in practice Linux. This laptop has an **RTX 4050 Laptop, 6 GB** → below the minimum. Revisit on a lab PC or Colab-class GPU. |
| **Gazebo (Harmonic) + ROS 2** | Full-system digital twin: LiDAR, camera, Nav2, the real ROS nodes. Most published forklift RL work uses Gazebo (e.g. a 2026 multi-expert forklift RL paper on Gazebo 11 + ROS Noetic with randomised mass, friction and obstacles). | Needs Linux (Ubuntu 22.04 / WSL2). No WSL distro is installed here. Planned for `code/ros2_ws/forklift_sim` (AI-01 "full system"). |
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
controller and stays within the 10 mm lateral limit. The remaining 1.4 % are collisions, which on the real forklift
are caught by the ESP32 ToF ring and the safety supervisor (AI-06) — and the baseline's 0 % collision rate is a
reason to keep it as the fallback. These are simulation results only; the real comparison is AI-07 / T-12.
Model files: `code/training/models/docking_v3/` (`policy_selected.zip`, `meta.json` with every number above).
Video: [`docs/media/rl-docking-simulation.mp4`](media/rl-docking-simulation.mp4).

## 5. Next steps

1. Measure the real forklift (ME-01) and update `config.yaml`; re-fit the actuator lag and delay from T-03.
2. `scripts/export_onnx.py` → TensorRT FP16 on the Jetson (AI-05), wrapped by `forklift_safety` (AI-06).
3. Real comparison: 30 baseline + 30 RL attempts (AI-07, T-12).
4. Full-system twin in Gazebo Harmonic (`code/ros2_ws/forklift_sim`) once a Linux machine is available; Isaac Lab if
   an 8 GB+ RTX GPU is available.
