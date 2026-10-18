# 19 — Gazebo digital twin (`forklift_sim`)

Requirements AI-01 ("Gazebo for the full system"), EN-11; plan item B5. Code: `robot/ros2_ws/src/forklift_sim`.
CI: `.github/workflows/sim.yml`. The ROS graph it feeds is described in [13-ros2.md](13-ros2.md); the docking policy
is trained separately in MuJoCo ([11-simulation-training.md](11-simulation-training.md)).

## 1. Simulator choice: Gazebo Fortress

The requirements name Gazebo Harmonic. The robots run ROS 2 **Humble** (Ubuntu 22.04, JetPack 6), and for Humble
the officially paired Gazebo is **Fortress** (`ros-humble-ros-gz` from the ROS apt repository). Harmonic on Humble
is a non-default pairing: it needs `ros-humble-ros-gzharmonic` from the OSRF repository, which replaces the Fortress
`ros_gz` packages and is not what `rosdep` resolves for `ros_gz_sim`. The twin therefore uses Fortress, so
`rosdep install` alone sets up the same Gazebo on a laptop, in CI and on a Jetson.

Moving to Harmonic later (e.g. with ROS 2 Jazzy) is a rename: `ignition-gazebo-*-system` →
`gz-sim-*-system`, `ignition::gazebo::systems::` → `gz::sim::systems::` (`SYS` in `scripts/generate_world.py` and
the plugins in `urdf/forklift_gz.urdf.xacro`), `ignition_frame_id` → `gz_frame_id`, `ignition.msgs.` → `gz.msgs.`
in `config/bridge.yaml`, and `ign gazebo` → `gz sim` in `launch/sim.launch.py`.

## 2. What the twin models

| Real system | Twin | Where |
|---|---|---|
| Mini warehouse 6 × 4 m (1:14) | Generated from `backend/app/warehouse_map.yaml`: 4 walls 0.45 m high (LiDAR 0.36 m + ≥ 5 cm, EN-07), racks R1/R2 as 0.15 m boxes, coloured floor patches for docks, staging, chargers, walkway, keep-out | `worlds/warehouse.sdf` (`scripts/generate_world.py`) |
| Occupancy map from slam_toolbox (NV-01) | Same walls + racks rasterised at 2 cm, for `localization:=truth` | `maps/warehouse_sim.{pgm,yaml}` (same script) |
| Forklift body, mast, fork carriage, frames | `forklift_description` URDF unchanged (same `dimensions.yaml`), included by a sim Xacro | `urdf/forklift_gz.urdf.xacro` |
| RPLIDAR C1, 360°, 10 Hz | `gpu_lidar` 450 samples, 0.05–12 m, σ 1 cm → `/<id>/scan` (frame `laser`) | sim Xacro |
| Fork camera 640×480 on the carriage (ME-05) | `camera` 640×480 rgb8, 62° HFOV, 15 Hz (real 30 Hz) → `/<id>/image_raw`, `camera_info` (frame `camera_optical_frame`), moves with the fork link | sim Xacro |
| MPU9250 (100 Hz) | `imu` 100 Hz → `/<id>/imu/data` (frame `imu`) | sim Xacro |
| ESP32 drive + wheel odometry (50 Hz) | `VelocityControl` on `/<id>/cmd_vel`; `OdometryPublisher` 50 Hz → `/<id>/ground_truth/odom` (world pose) → `wheel_odom_stub.py` → `/<id>/wheel_odom` from 0 at the spawn pose, like the firmware after power-up (no TF; the EKF publishes `odom → base_link`) | sim Xacro, `scripts/wheel_odom_stub.py` |
| Fork lift joint | `JointStatePublisher` → `/<id>/joint_states` → robot_state_publisher | sim Xacro |
| ROS namespace per robot | `ros_gz_bridge` with `config/bridge.yaml` (ROBOT_ID replaced per robot); `/clock` once | `launch/sim.launch.py` |

Gazebo topic names equal the ROS names of the real robot (`docs/13` §2), so the bridge maps them 1:1 and the stack's
YAML (EKF `wheel_odom` + `imu/data`, laser_filters `scan` → `scan_filtered`, Nav2) is used unchanged. A host test
(`test/test_world.py`) checks that every Gazebo topic of the sim Xacro is bridged and that the EKF still reads those
names.

### `sim.launch.py`

```bash
ros2 launch forklift_sim sim.launch.py                                   # headless server, fl1
ros2 launch forklift_sim sim.launch.py robots:=fl1,fl2,fl3 gui:=true     # + Gazebo GUI
ros2 launch forklift_sim sim.launch.py stack:=nav                        # + EKF, map, Nav2 per robot
ros2 launch forklift_sim sim.launch.py stack:=nav localization:=slam     # slam_toolbox mapping instead of truth
```

| Argument | Default | Meaning |
|---|---|---|
| `robots` | `fl1` | comma list; spawn nodes: fl1 J1 (east), fl2 J5 (west), fl3 A31 (north), fl4 J45 |
| `gui` | `false` | also start `ign gazebo -g` (the server always runs headless, `-s -r`) |
| `stack` | `none` | `nav`: laser_filters, EKF, localisation, Nav2 (`forklift_navigation/launch/navigation.launch.py`), `supervisor_bypass` |
| `localization` | `truth` | `truth`: map_server with the generated map + static `map → odom` = spawn pose; `slam`: slam_toolbox mapping |
| `camera_rate` | `15` | fork camera Hz (software rendering in CI is slow) |
| `world`, `warehouse_map` | installed files | override for other layouts |

All nodes run with `use_sim_time: true`. Each robot gets robot_state_publisher (sim Xacro), the bridge, `wheel_odom_stub` and a
`ros_gz_sim create` spawn from `/<id>/robot_description`; TF is namespaced (`/<id>/tf`) as on the robots.

## 3. Running it on Ubuntu 22.04 with the GUI

```bash
sudo apt install ros-humble-desktop ros-humble-ros-gz        # ros-gz pulls Gazebo Fortress
cd robot/ros2_ws
rosdep install --from-paths src --ignore-src -y --rosdistro humble --skip-keys "sllidar_ros2 micro_ros_agent"
colcon build --packages-up-to forklift_sim && source install/setup.bash
ros2 launch forklift_sim sim.launch.py robots:=fl1,fl2 stack:=nav gui:=true
rviz2 -d src/forklift_description/rviz/forklift.rviz --ros-args -r /tf:=/fl1/tf -r /tf_static:=/fl1/tf_static
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -r cmd_vel:=/fl1/cmd_vel   # with stack:=none
```

Send a goal from RViz ("2D Goal Pose" on `/fl1/goal_pose`) or with
`ros2 action send_goal /fl1/navigate_to_pose nav2_msgs/action/NavigateToPose "{pose: {header: {frame_id: map}, pose: {position: {x: 2.5, y: 0.6}}}}"`.
Regenerate the world and the map after editing `warehouse_map.yaml`: `python src/forklift_sim/scripts/generate_world.py`
(a host test fails when they are stale).

## 4. What CI checks (`.github/workflows/sim.yml`)

Container `ros:humble` on `ubuntu-22.04`, `apt install ros-humble-ros-gz xvfb`, `rosdep install`,
`colcon build --packages-up-to forklift_sim -DFORKLIFT_SIM_TESTS=ON`, then `colcon test --packages-select forklift_sim`
under `xvfb-run` with Mesa software rendering (`LIBGL_ALWAYS_SOFTWARE=1`). The launch tests only exist with that CMake
option, so the plain `colcon test` of `ci.yml` never needs a simulator.

| Test | Asserts |
|---|---|
| `test/launch/sim_sensors_drive.launch.py` | fl1 spawned at J1; rates measured on header stamps (sim time): `scan` 8–12 Hz, `wheel_odom` 40–60 Hz, `imu/data` 80–120 Hz, `image_raw` 5–18 Hz; frames `laser`, `camera_optical_frame`, `odom`/`base_link`; 640×480 image, `camera_info`, fork joint in `joint_states`; spawn pose (1.0, 0.6) ± 3 cm; LiDAR sees the south wall at 0.6 m and the east wall at 5.1 m (± 6 cm); scripted `cmd_vel` 0.2 m/s × 5 s → 1.0 ± 0.1 m with < 5 cm drift, arc 0.1 m/s + 0.3 rad/s × 3 s → 0.9 ± 0.1 rad, and the robot stops on zero |
| `test/launch/sim_nav.launch.py` | `stack:=nav`: real Nav2 params (Smac Hybrid-A*, RPP, keep-out + speed filters, `navigate_lane.xml`), EKF on `wheel_odom` + `imu/data`; NavigateToPose (2.5, 0.6, 0°) from J1 succeeds and the ground-truth pose is within 10 cm / 0.15 rad; rosbag of scan, odometry, cmd_vel, TF and plan |

Artifacts (`sim-artifacts`): `nav_bag/` (rosbag2), `sensor_rates.json`, ctest/launch_test XML and logs, ROS logs.

First green run (sim.yml run 6, 2026-10-18, ~6 min of the job is apt + build): scan 10.0 Hz, wheel_odom and
ground_truth/odom 50.0 Hz, imu 100.0 Hz, camera 10.9 Hz (configured 15 Hz; llvmpipe renders slower than the sensor
period, so frames are skipped in sim time); straight run 1.009 m / 0 drift, arc 0.904 rad; NavigateToPose
succeeded in ~12 s with a ground-truth error of 4.0 cm / 0.001 rad (goal checker 5 cm / 5°).

### Stack bugs the twin found

The first runs of the real Nav2 configuration (never started before: the dev laptop has no Ubuntu and ci.yml only
builds and runs the unit tests) failed on two configuration errors in `forklift_navigation`, both fixed:

1. `config/ekf.yaml`: `process_noise_covariance` mixed `0` and `0.05`; rcl rejects a list with mixed int/float
   ("Sequence should be of same type") and `ekf_node` aborted at start — it would have on the robot too.
   `tests/test_workspace.py::test_parameter_lists_have_one_type` now checks every `ros__parameters` list.
2. `bt_navigator` loads a NavigateThroughPoses tree as well; Nav2's default one contains `Spin`, whose BT node is
   deliberately not registered (Ackermann), so bt_navigator failed to configure and Nav2 never activated.
   `behavior_trees/navigate_through_lanes.xml` (no Spin) is now passed as `default_nav_through_poses_bt_xml`.

## 5. Known gaps vs the real robot

- **Drive**: a velocity-controlled body (unicycle) on frictionless wheel contacts, not rear-wheel Ackermann steering
  with the ESP32's PID and steering servo; it can turn on the spot if commanded. Nav2's planner still only produces
  car-like paths (minimum_turning_radius 0.35 m), but controller tracking errors of the real steering are not
  reproduced. Gazebo's `AckermannSteering` system assumes front steering; a rear-steer model is a follow-up.
- **Odometry is ground truth** (OdometryPublisher re-based to the spawn pose, no slip or noise): the EKF and `localization:=truth` are
  optimistic. `localization:=slam` exercises slam_toolbox but is not checked in CI.
- **No ESP32 stand-in** for `tof_ring`, `fork_state`, `safety_state`, `heartbeat`, `lift_cmd`: the fork joint is not
  actuated (it rests at 0), and the safety supervisor is replaced by `supervisor_bypass` (cmd_vel_nav → cmd_vel
  with a 0.5 s watchdog). mission_node, the fleet server/MQTT, lift_server, dock_server, ArUco perception and the YOLO
  person detector are not started.
- **World**: racks are solid 0.15 m boxes (PLACEHOLDER height), below the LiDAR plane — as on the real floor the LiDAR
  sees only walls, but real rack legs/pallets are not modelled; no pallets or ArUco textures yet (PC-03), so the
  camera sees no markers; flat zone patches only.
- **Sensors**: camera at 15 Hz rgb8 (real 30 Hz mono8 from v4l2), no lens distortion or calibration file; LiDAR has
  Gaussian noise only (no dropouts, no reflections, 450 instead of ~500 points); IMU without bias/noise model.
- **Physics**: masses and inertias of the URDF are placeholders (ME-01); the twin is not validated against measured
  robot behaviour (T-08/T-09 need the real floor).
