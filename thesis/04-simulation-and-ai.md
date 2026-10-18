# Chapter 4 — Simulation and AI: learning to dock

<!-- Sources: docs/11-simulation-training.md; code/training/models/docking_v3/meta.json; code/training/models/baseline_eval.json;
     code/training/README.md; plan.md B2. All results in this chapter are SIMULATION results. The real-forklift
     comparison (AI-07 / T-12) is planned (Chapter 7). -->

## 4.1 The task

Docking is the last ≈ 40 cm of a pick: the forklift starts 30–60 cm in front of the pallet, up to ± 10 cm to the side
and ± 20° off its axis, with the forks at a random height, and must insert both forks at least 80 % of their length
into the openings, with ≤ 1 cm lateral error at both the tips and the carriage, without moving the pallet. The
forks have only **1.75 cm of clearance per side**.
<!-- docs/11-simulation-training.md §2 "Success", "Start"; §4 "1.75 cm clearance per side" -->

The requirement is staged: a classical controller is built first as the reference, the RL policy must reach
**≥ 95 % success on 1000 random simulated episodes (AI-04)** before it may be transferred, and on the real forklift it
must do at least as well as the classical controller over 30 + 30 attempts (AI-07, T-12). This guarantees the project
works even if RL is late or fails.
<!-- docs/00-sources/system-requirements.md §8 -->

## 4.2 Choice of simulator

| Option | Strength | Why (not) chosen |
|---|---|---|
| Isaac Sim / Isaac Lab | Photoreal rendering, thousands of GPU-parallel environments | Needs an RTX GPU with ≥ 8 GB and in practice Linux; the laptop has an RTX 4050 with 6 GB |
| Gazebo Harmonic + ROS 2 | Full-system twin with the real ROS nodes | Needs Linux; kept for the full-system simulation (`forklift_sim`) |
| **MuJoCo + Gymnasium** | Accurate contact physics, native on Windows, ≈ 2,000 environment steps/s per CPU core, works with Stable-Baselines3 | **Chosen** for training |

<!-- docs/11-simulation-training.md §1 -->

**Design consequence.** The policy does not learn from pixels. It observes the **ArUco pallet pose** that the real
perception stack produces, plus ToF and fork-tip sensor readings, so the sim-to-real gap is narrowed to pose noise and
actuator dynamics — both randomised.

## 4.3 The environment (`ForkliftDocking-v0`)

<!-- docs/11-simulation-training.md §2 -->

| Part | Implementation |
|---|---|
| Forklift | 1:14 Huina 1577-style body, rear-wheel steering (bicycle model about the driven front axle, ω = −v·tan δ / L), forks on a lift joint, mast, LiDAR, wheels. Dimensions in `config.yaml` (placeholders until ME-01). |
| Pallet | 20 × 20 cm deck, three stringers forming two fork openings, a load box and a real ArUco `DICT_4X4_50` id 7 texture; on the floor or on a 60 mm rack shelf; a free body — pushing it more than 1 cm counts as a collision. |
| Observation (18) | Pallet pose in the carriage frame from the simulated marker (field-of-view cone, minimum range, ± 5 mm / ± 1° noise, per-episode bias, 5-sample moving average, odometry carry-over when not visible), fork-height error, speed, steering, fork height, 3 front ToF rays, 2 fork-tip sensors, previous action, time left |
| Action (3) | Speed ± 0.1 m/s, steering ± 30°, lift rate |
| Reward | Progress to the goal + reduction of lateral / heading / height error, −0.01 per step, steering-change penalty, **+100 docked, −100 collision**, −50 out of range |
| Domain randomisation | Floor friction 0.6–1.2, motor delay 20–80 ms, actuator lag, wheel slip 0.90–1.05, steering bias ± 1.5°, pallet load 0–0.4 kg, marker noise and bias, sensor noise |

![Docking simulation](../media/rl-docking-simulation.mp4)
**Figure 4.1** — The MuJoCo docking scene with the trained policy (video `docs/media/rl-docking-simulation.mp4`;
use a still frame in the printed thesis).

## 4.4 Classical baseline

The baseline lifts the forks to the opening height, tracks the pallet axis with a second-order lateral controller in
the distance domain, κ = −(2ζλ·heading + λ²·lateral) with λ = 11 m⁻¹, slows near the pallet face, and backs off and
retries when the fork tips arrive misaligned. It uses the same observation as the policy.

**On 1000 randomised test episodes (seeds 10000–10999) it docked 90.0 %, with 0 % collisions, 10.3 s mean time and
1.7 mm mean lateral error at the tips.**
<!-- docs/11-simulation-training.md §3; code/training/models/baseline_eval.json: success_rate 0.9, collision_rate 0.0,
     mean_time_s 10.3025, mean_lateral_mm 1.67 -->

## 4.5 What did not work

These negative results are part of the contribution: they explain *why* the final recipe is needed.

**Plain PPO (v1).** After 400 k steps the policy had **0 % success and 0 % collisions**: it had learned that standing
still (return ≈ −3) beats trying (≈ −31 on average). With 1.75 cm of clearance per side, and the randomised steering
bias alone drifting the forklift ≈ 1 cm over 40 cm, random exploration essentially never produces an insertion, so
the +100 reward is never seen.
<!-- docs/11-simulation-training.md §4 -->

**Curriculum (`--curriculum`).** Starting close and aligned and widening the start region on success also gave
**0 % at 250 k steps**: even at the easiest level, driving straight collides 67 % of the time. Closed-loop correction
is needed from the very first step, so there is no "easy" version of the task for a random policy.
<!-- docs/11-simulation-training.md §4 -->

## 4.6 What worked: RL from demonstrations

1. **Demonstrations.** Roll out the classical controller 3,200 times (691,889 steps; the controller succeeded in
   89.0 % of these demonstration episodes).
   <!-- meta.json behaviour_cloning.demo_episodes 3200, demo_steps 691889, demo_success 0.8896875 -->
2. **Behaviour cloning.** Fit the PPO actor to the controller's actions (mean-squared error) and the critic to the
   discounted returns of the demonstrations.
3. **PPO fine-tuning** on the original reward for 1 M steps with a *conservative* update: learning rate 3·10⁻⁵, clip
   range 0.1, target KL 0.01; 16 parallel environments, MLP 128 × 128; 12.1 minutes of wall-clock time on 16 CPU
   cores.
   <!-- meta.json timesteps 1000000, envs 16, learning_rate 3e-05, clip_range 0.1, target_kl 0.01, wall_clock_min 12.1;
        docs/11-simulation-training.md §4 (MLP 128×128) -->

A larger update (v2: learning rate 10⁻⁴, clip 0.2) peaked early and then drifted to 91 % success with 9 % collisions:
fine-tuning has to stay close to the cloned behaviour.
<!-- docs/11-simulation-training.md §4 -->

[CHECK: docs/11 §4 says "the cloned policy alone already docked 95 % of 200 evaluation episodes … with 4 % collisions",
but meta.json v3 bc_only_eval and the results table give 90 % / 0 % collisions. The 95 % figure is probably from an
earlier run — confirm and fix docs/11 before quoting either.]

## 4.7 Checkpoint selection

PPO performance is not monotonic: success first rises, then falls as collisions creep back in. A checkpoint was saved
every 125 k steps and each one was evaluated on **400 validation episodes (seeds 20000–20399)**, separate from the test
seeds. The rule was **maximise success − 2 × collision rate**.
<!-- meta.json validation[], selected.rule "max(success − 2·collision) on seeds 20000-20399" -->

| Checkpoint (validation, 400 episodes) | Docked | Collisions | Mean time | Lateral error |
|---|---|---|---|---|
| Imitation only | 87.5 % | 0.0 % | 10.0 s | 1.6 mm |
| PPO 125 k | 96.8 % | 3.3 % | 8.1 s | 2.3 mm |
| PPO 250 k | 98.5 % | 1.5 % | 7.4 s | 2.6 mm |
| PPO 375 k | 97.5 % | 2.5 % | 7.0 s | 2.7 mm |
| PPO 500 k | 97.5 % | 2.5 % | 6.6 s | 3.0 mm |
| **PPO 625 k (selected)** | **99.3 %** | **0.8 %** | **6.4 s** | 2.8 mm |
| PPO 750 k | 97.3 % | 2.8 % | 6.4 s | 2.5 mm |
| PPO 875 k | 96.3 % | 3.8 % | 6.3 s | 2.3 mm |
| PPO 1 M | 94.3 % | 5.8 % | 6.3 s | 2.2 mm |

<!-- code/training/models/docking_v3/meta.json "validation" (rounded to one decimal; checkpoint names are 124,992 …
     999,936 steps). [CHECK: draw this as Figure 4.2, success and collision vs steps] -->

The selected checkpoint was then scored **once** on the test seeds.

## 4.8 Results

| Controller (1000 test episodes, full randomisation) | Docked | Collisions | Mean time | Lateral error |
|---|---|---|---|---|
| Classical baseline | 90.0 % | 0.0 % | 10.3 s | 1.7 mm |
| Imitation only (200 episodes) | 90.0 % | 0.0 % | 9.9 s | 1.7 mm |
| **Imitation + PPO (checkpoint 625 k)** | **98.6 %** | 1.4 % | **6.4 s** | 2.7 mm |
| PPO end of training (1 M) | 95.3 % | 4.7 % | 6.3 s | 2.3 mm |

<!-- docs/11-simulation-training.md §4 results table; meta.json eval_1000 (0.986, 0.014, 6.41 s, 2.75 mm) and
     bc_only_eval (200 episodes: 0.9, 0.0, 9.85 s, 1.70 mm); baseline_eval.json -->

**Interpretation.**

- The selected policy **passes the AI-04 gate** (≥ 95 %) and docks **38 % faster** than the classical controller
  (6.4 s vs 10.3 s), within the 10 mm lateral limit.
  <!-- docs/11-simulation-training.md §4; meta.json ai04_gate_passed: true -->
- It trades accuracy margin for speed: mean lateral error is 2.7 mm vs 1.7 mm, still well inside the limit.
- The remaining **1.4 % are collisions**, which on the real forklift are caught by the ESP32 ToF ring (corner sensors
  still stop during docking) and the safety supervisor (AI-06). The baseline's 0 % collision rate is a reason to keep
  it as the fallback (`forklift_rl` runs both).
- Selecting by validation mattered: on the test set the end-of-training policy is 3.3 points worse in success
  (95.3 % vs 98.6 %) and has about 3.4 × the collisions (4.7 % vs 1.4 %) of the selected one.

## 4.9 Deployment path

The selected actor was exported to ONNX (78 KB, opset 17). Its output differs from PyTorch by at most 6·10⁻⁷; through
ONNX Runtime it docked 99 % of 200 simulation episodes, at 0.009 ms per call on the laptop CPU. On the Jetson it will
run with TensorRT FP16, with a target of ≤ 5 ms per inference at 20 Hz (AI-05, planned).
<!-- plan.md B2; meta.json onnx (bytes 78487, opset 17, max_abs_diff_vs_torch 5.8e-7, sim_200_episodes 0.99) -->

On the robot, `forklift_rl` builds the same 18-value observation from live topics. It was checked to be identical
(< 10⁻⁵) to the training environment on 718 recorded states, so the policy sees on the robot exactly what it saw in
training.
<!-- docs/13-ros2.md §3 "RL" -->

## 4.10 Limits of these results

- Every number above is from simulation; dimensions are placeholders until the first forklift is measured (ME-01),
  after which the policy is retrained (≈ 15 min).
  <!-- plan.md A2 -->
- The real comparison — 30 classical + 30 RL attempts — is test T-12 and is **planned** (Chapter 7).
- The simulator models neither camera image quality nor lighting; the pose noise model stands in for them.
