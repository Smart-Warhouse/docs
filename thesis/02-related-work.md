# Chapter 2 — Related work

<!--
Citation policy: sources [1]–[6] are the ones already cited in docs/11-simulation-training.md (links there).
The others are well-known references added from memory; bibliographic details that were NOT checked against the
publisher are marked [CHECK]. Before submission, verify every entry and convert to the university's citation style.
-->

## 2.1 Autonomous forklifts

Pallet handling is the defining task of a forklift and the hardest part to automate, because the forks must enter
openings only slightly wider than themselves. Classical approaches detect the pallet (with markers, depth sensing or
learned detectors), estimate its pose and servo the vehicle onto the pallet axis. An IEEE paper on pallet detection
and docking with an autonomous forklift [6] is one example of this classical pipeline.

Learning-based approaches have recently been applied to the same problem. The work closest to ours trained a
**1:14-scale forklift** in NVIDIA Isaac Sim with PPO from camera images and transferred the policy zero-shot to the
real vehicle, reporting **60 % real-world approach success over 10 trials** [1]. A 2026 multi-expert RL study for
autonomous forklifts used Gazebo 11 with ROS Noetic and randomised mass, friction and obstacles [2]. Mapless
navigation for intralogistics has also been trained in simulation with NVIDIA's Isaac SDK [3].
<!-- figures for [1] and [2] as summarised in docs/11-simulation-training.md §1 -->

**Difference in this project.** Instead of learning from pixels, our policy observes the ArUco pallet pose plus ToF
and fork-tip sensors — the same signals our perception stack already produces — so the sim-to-real gap is reduced to
pose noise and actuator dynamics, both of which are randomised (Chapter 4). The policy is also gated: it must beat a
classical controller in simulation (AI-04) and later on the real forklift (AI-07) before it replaces it.
<!-- docs/11-simulation-training.md §1 "Design consequence" -->

## 2.2 Fleets of mobile robots in warehouses

Large-scale warehouse robotics became widely known through the Kiva system, in which hundreds of drive units carry
shelving pods to pickers, coordinated by a central server [7]. Central coordination of many robots raises two
classical problems that our fleet manager also has to solve:

- **Path planning on a graph.** Our routes are A* searches [8] on a lane graph, with dead-end *spur* nodes for rack
  slots, docks and chargers so that a docking robot never blocks an aisle.
- **Resource contention and deadlock.** Granting lanes and nodes to robots is a resource-allocation problem; the
  four Coffman conditions for deadlock [9] explain why we acquire all resources for a step at once (no hold-and-wait)
  and detect cycles in a wait-for graph when waits still occur.
- **Task assignment.** Assigning N tasks to M robots to minimise total cost is the linear assignment problem, solved
  optimally by the Hungarian method [10]. We compare it with a greedy nearest-robot rule (AI-08).

Multi-agent path finding (MAPF) with conflict-based search is the research frontier for this problem
[CHECK: add Sharon et al., "Conflict-based search for optimal multi-agent pathfinding", Artificial Intelligence,
2015, if the chapter needs a MAPF reference]. We chose lock-based traffic control because it is simple to verify,
matches the requirement wording (SF-10: one robot per lane segment) and degrades safely when a robot stops.

## 2.3 Robot software: ROS 2, Nav2 and SLAM

Each forklift runs ROS 2 Humble. Navigation uses **Nav2** [11], the ROS 2 navigation stack, with the Smac Hybrid-A*
planner for car-like vehicles that respects a minimum turning radius and reversing [12], and the Regulated Pure
Pursuit controller, which slows down in tight turns and near obstacles [13]. Mapping and localisation use
**SLAM Toolbox** [14]. Wheel odometry and IMU are fused with an extended Kalman filter from the
`robot_localization` package [15]. The ESP32 joins the ROS graph through **micro-ROS** over USB [16].
<!-- docs/13-ros2.md §1 "Key values"; docs/00-sources/system-requirements.md §5, §7 -->

## 2.4 Fiducial markers and pose estimation

Square fiducial markers give a reliable 6-DoF pose from a single calibrated camera. **ArUco** [17] markers are
generated from dictionaries with a guaranteed inter-marker distance and are detected in OpenCV; the pose follows from
the four corners with a Perspective-n-Point solver. We use `DICT_4X4_50`, 30 mm markers on pallets (ids 1–20) and
60 mm markers on racks and chargers (ids 21–40), and require ≤ 1 cm and ≤ 2° at distances up to 50 cm (PC-04).
<!-- docs/00-sources/system-requirements.md §6 PC-03, PC-04 -->

People and unmarked pallets are detected by a YOLO model as a second layer (PC-06..PC-08)
[CHECK: cite the Ultralytics YOLOv8 / YOLO11 software reference in the required style; this part is planned, not built].

## 2.5 Reinforcement learning for docking

**Algorithm.** Proximal Policy Optimisation (PPO) [18] is the standard on-policy actor-critic method for continuous
control. We use the Stable-Baselines3 implementation [19] on a Gymnasium environment [20] simulated in MuJoCo [21].

**Simulation-to-reality.** Domain randomisation — training over randomised physical and sensor parameters so that
the real world looks like one more sample — was popularised by Tobin et al. [22]. We randomise floor friction, motor
delay, actuator lag, wheel slip, steering bias, pallet load and marker noise (AI-03).

**Sparse rewards and demonstrations.** Tasks whose success region is tiny are hard for random exploration. Learning
from demonstrations — initialising the policy by behaviour cloning and then fine-tuning with RL — is a well-known
remedy, for example in dexterous manipulation [23]. Chapter 4 shows that this was exactly the failure mode of plain
PPO on our docking task and that demonstration-initialised PPO solves it.

**Simulator choice.** Isaac Sim / Isaac Lab offers photoreal rendering and GPU-parallel environments but needs an RTX
GPU with at least 8 GB [5]; our development laptop has 6 GB. Gazebo is the natural full-system twin but needs Linux.
MuJoCo runs natively on Windows, is fast on CPU and plugs into Stable-Baselines3, so it was chosen for training
[4][21].
<!-- docs/11-simulation-training.md §1 table -->

## 2.6 Summary

| Topic | Typical approach | This project |
|---|---|---|
| Pallet docking | Classical visual servoing [6] or pixel-based RL [1] | Pose-based RL initialised from a classical controller, gated against it |
| Fleet traffic | Central reservation, MAPF | Lane graph + node/lane locks + deadlock resolution |
| Task allocation | Greedy or optimal assignment [10] | Both, switchable at run time and compared |
| Robot stack | ROS + Nav2 [11] | ROS 2 Humble, Nav2 Smac Hybrid-A* + RPP, SLAM Toolbox |
| Safety | Certified safety PLC and scanners (full scale) | Four independent layers on low-cost parts (Chapter 3) |

---

## References

From `docs/11-simulation-training.md` (links verified when that document was written):

1. Visual-based forklift learning system enabling zero-shot sim2real transfer (1:14 forklift, Isaac Sim + PPO).
   arXiv:2412.11503, 2024. https://arxiv.org/html/2412.11503v1 [CHECK: authors and final venue]
2. Multi-expert reinforcement learning for autonomous forklifts (Gazebo 11 + ROS Noetic). arXiv:2601.07304, 2026.
   https://arxiv.org/pdf/2601.07304 [CHECK: authors and title wording]
3. Mapless navigation in intralogistics with NVIDIA Isaac SDK. arXiv:2202.11512, 2022.
   https://arxiv.org/pdf/2202.11512 [CHECK: authors and title wording]
4. Farama Foundation, Gymnasium custom-environment tutorial.
   https://gymnasium.farama.org/v1.1.1/tutorials/gymnasium_basics/
5. NVIDIA Developer Forums, "GPU requirement" (Isaac Sim). https://forums.developer.nvidia.com/t/gpu-requirement/305727/2
6. Pallet detection and docking with an autonomous forklift. IEEE (record at İzmir University of Economics GCRIS).
   https://gcris.ieu.edu.tr/entities/publication/5129756f-05ce-4394-9a02-d61b6a1cbb45 [CHECK: authors, conference, year]

Well-known references added for this chapter:

7. P. R. Wurman, R. D'Andrea, M. Mountz, "Coordinating hundreds of cooperative, autonomous vehicles in warehouses,"
   *AI Magazine*, 29(1), 2008. [CHECK: pages 9–19]
8. P. E. Hart, N. J. Nilsson, B. Raphael, "A formal basis for the heuristic determination of minimum cost paths,"
   *IEEE Trans. Systems Science and Cybernetics*, 4(2), 1968.
9. E. G. Coffman, M. Elphick, A. Shoshani, "System deadlocks," *ACM Computing Surveys*, 3(2), 1971.
10. H. W. Kuhn, "The Hungarian method for the assignment problem," *Naval Research Logistics Quarterly*, 2(1–2), 1955.
11. S. Macenski, F. Martín, R. White, J. Ginés Clavero, "The Marathon 2: A navigation system," *IEEE/RSJ IROS*, 2020.
12. S. Macenski et al., "Open-source, cost-aware kinematically feasible planning for mobile and surface robotics,"
    arXiv:2401.13078, 2024. [CHECK: number and author list]
13. S. Macenski, S. Singh, F. Martín, J. Ginés, "Regulated pure pursuit for robot path tracking," *Autonomous
    Robots*, 2023. [CHECK: volume and pages]
14. S. Macenski, I. Jambrecic, "SLAM Toolbox: SLAM for the dynamic world," *Journal of Open Source Software*, 6(61),
    2021.
15. T. Moore, D. Stouch, "A generalized extended Kalman filter implementation for the Robot Operating System,"
    *Intelligent Autonomous Systems 13*, Springer, 2016. [CHECK: year and pages]
16. micro-ROS project, https://micro.ros.org [CHECK: replace with the micro-ROS book chapter if a paper is required]
17. S. Garrido-Jurado, R. Muñoz-Salinas, F. J. Madrid-Cuevas, M. J. Marín-Jiménez, "Automatic generation and detection
    of highly reliable fiducial markers under occlusion," *Pattern Recognition*, 47(6), 2014.
18. J. Schulman, F. Wolski, P. Dhariwal, A. Radford, O. Klimov, "Proximal policy optimization algorithms,"
    arXiv:1707.06347, 2017.
19. A. Raffin, A. Hill, A. Gleave, A. Kanervisto, M. Ernestus, N. Dormann, "Stable-Baselines3: Reliable reinforcement
    learning implementations," *Journal of Machine Learning Research*, 22(268), 2021.
20. M. Towers et al., "Gymnasium: A standard interface for reinforcement learning environments," arXiv:2407.17032,
    2024. [CHECK]
21. E. Todorov, T. Erez, Y. Tassa, "MuJoCo: A physics engine for model-based control," *IEEE/RSJ IROS*, 2012.
22. J. Tobin, R. Fong, A. Ray, J. Schneider, W. Zaremba, P. Abbeel, "Domain randomization for transferring deep neural
    networks from simulation to the real world," *IEEE/RSJ IROS*, 2017.
23. A. Rajeswaran, V. Kumar, A. Gupta, G. Vezzani, J. Schulman, E. Todorov, S. Levine, "Learning complex dexterous
    manipulation with deep reinforcement learning and demonstrations," *Robotics: Science and Systems (RSS)*, 2018.
24. S. O. H. Madgwick, "An efficient orientation filter for inertial and inertial/magnetic sensor arrays," report,
    University of Bristol, 2010. [CHECK] (used for the IMU filter in Chapter 3)
