# System architecture — Smart Warehouse & Autonomous Forklift Fleet

A 1:14-scale warehouse in which three autonomous forklifts (plus one spare) move pallets between racks, inbound
and outbound docks without human help, under a central fleet server and a live control-room dashboard.
Printable copy: [system-architecture.pdf](system-architecture.pdf).

| | |
|---|---|
| **Scale** | 1:14 · floor 6 × 4 m · forklift Huina 1577 Pro, 52.4 × 18.7 × 31.7 cm |
| **Fleet** | 3 forklifts + 1 spare · 26 locations today (rack, dock, staging, charger) · 10–20 pallets |
| **Per forklift** | ESP32-S3 (real-time control and safety) + Jetson Orin Nano Super (ROS 2, perception, AI) |
| **Server** | FastAPI fleet manager + WMS, Mosquitto MQTT, PostgreSQL |
| **Clients** | React dashboard, Flutter phone app, public landing page |
| **Code** | 7 public repositories in the [Smart-Warhouse](https://github.com/Smart-Warhouse) GitHub organisation |

---

## 1. System context

Four layers. Each layer only talks to the one next to it, and every layer can stop the robot on its own.

![System context: four layers](img/system-context.svg)

**Why the server does not use ROS.** The server speaks plain MQTT + JSON, so it was built and demoed before any
forklift existed. Its built-in simulator drives fake robots over the same lane graph, traffic locks and task
lifecycle that real robots use. A real forklift joins by setting `simulated: false` in the map file.

## 2. Repositories

| Repository | Contents | Stack | State |
|---|---|---|---|
| [backend](https://github.com/Smart-Warhouse/backend) | Fleet manager, WMS, REST + WebSocket API, simulator, MQTT bridge, Mosquitto config, integration + perf tests, allocation study | Python 3.11, FastAPI, SQLAlchemy, Alembic, aiomqtt | built, tested, deployed |
| [dashboard](https://github.com/Smart-Warhouse/dashboard) | Control-room console: live map, fleet, tasks, inventory, analytics, events, manual drive, settings, kiosk | React 19, Vite, TypeScript, Tailwind | built, deployed |
| [mobile](https://github.com/Smart-Warhouse/mobile) | Floor app: STOP ALL, alerts, fleet, mini map, move pallet, manual drive | Flutter, Riverpod, go_router, Dio | built, APK |
| [landing](https://github.com/Smart-Warhouse/landing) | Public project site, Arabic + English | React, Vite, nginx with strict CSP | built, deployed |
| [robot](https://github.com/Smart-Warhouse/robot) | ESP32 firmware, ROS 2 workspace (10 packages), Gazebo twin, CAD for printed mounts | PlatformIO / FreeRTOS, ROS 2 Humble, Gazebo Fortress, CadQuery | written, host-tested, no hardware yet |
| [ai](https://github.com/Smart-Warhouse/ai) | Docking simulator and training, YOLO data/training pipeline | MuJoCo, Gymnasium, Stable-Baselines3, ONNX, Ultralytics | trained in simulation |
| [docs](https://github.com/Smart-Warhouse/docs) | Requirements, contracts, JSON schemas, plan, thesis, guides, brand | Markdown | living |

The repositories sit side by side in one workspace folder; tests that need a sibling (for example the robot tests that
read the backend's map) find it there, and CI checks the sibling out the same way.

---

## 3. One forklift: hardware

```mermaid
flowchart TB
  subgraph PWR["Power"]
    BAT["2S Li-ion<br/>4 × 18650 (2S2P)"] --> BMS["BMS 2S 20 A"] --> FUSE["Fuse 5 A"] --> SW["Main switch"]
    SW --> ES["E-Stop (NC)<br/>motor branch only"] --> DRV["Motor drivers"]
    SW --> BUCK["Buck 5.1 V"]
    SW --> BOOST["Boost 12 V ≥ 30 W"]
    INA["INA219<br/>V + I"] -.- BMS
  end
  DRV --> M1["Drive motor"]
  DRV --> M3["Lift motor"]
  BUCK --> ESP["ESP32-S3"]
  BUCK --> SENS["Sensors, LEDs"]
  BOOST --> JET["Jetson Orin Nano Super"]
  ESP -->|PWM| DRV
  ESP -->|PWM| SERVO["Steering servo"]
  ESP -->|"I²C via TCA9548A"| TOF["6 × VL53L1X ToF"]
  ESP -->|I²C| IMU["MPU9250 IMU"]
  ESP -->|I²C| ENC["AS5600 encoder"]
  ESP -->|"ADC / GPIO"| FORK["Slide pot, limit switches,<br/>TCRT5000 fork tips"]
  JET <-->|"USB · micro-ROS"| ESP
  JET -->|USB| LIDAR["RPLIDAR C1"]
  JET -->|CSI| CAM["Camera (fork carriage)"]
  JET <-->|"Wi-Fi 5 GHz"| NET(("Warehouse Wi-Fi"))
```

- **The E-Stop cuts only the motor branch.** The Jetson and ESP32 stay powered, so they can still log and report
  why the forklift stopped (EL-02).
- **The ESP32 owns everything with a deadline:** motors, steering, lift, and the short-range sensors that stop the robot.
- **The Jetson owns everything heavy:** LiDAR, camera, mapping, planning, AI.

## 4. Layer 2 — ESP32-S3 firmware

FreeRTOS on both cores. All decision logic (`forklift_core`) is plain C++ tested on the laptop (60 test cases);
the board build runs in CI.

| Task | Core / rate | Job |
|---|---|---|
| `safety_task` | 1 · 1 kHz | E-Stop, ToF, fork height, battery, link times → safety state machine → speed limit. The only task on the hardware watchdog (1 s → reboot) |
| `motor_pid_task` | 1 · 1 kHz | Encoder → speed → drive PID with feed-forward; rear-steer Ackermann → servo; odometry; lift controller. Brakes on its own if the safety output is > 5 ms old |
| `tof_task` | 1 · 50 Hz | 6 × VL53L1X through the I²C mux; re-initialises a dropped sensor every 2 s |
| `imu_task` | 0 · 100 Hz | MPU9250 → Madgwick filter |
| `microros_task` | 0 · event | ROS 2 topics, agent reconnect, gains as ROS parameters |
| `status_task` | 0 · 10 Hz | Battery %, LED ring, buzzer |

```mermaid
stateDiagram-v2
    [*] --> BOOT
    BOOT --> IDLE: drivers ready
    IDLE --> ACTIVE: fresh cmd_vel and heartbeat alive
    ACTIVE --> SLOW: ToF < 40 cm ahead · forks > 5 cm · docking
    SLOW --> ACTIVE: cause gone
    ACTIVE --> STOP: ToF < 15 cm ahead
    SLOW --> STOP: ToF < 15 cm ahead
    STOP --> ACTIVE: obstacle gone
    ACTIVE --> SAFE: watchdog · battery < 8 % · sensor fault
    SAFE --> IDLE: cause gone for 1 s
    ACTIVE --> ESTOP: E-Stop pressed (from any state)
    ESTOP --> BOOT: released AND explicit reset
```

The E-Stop is latched: releasing the button alone does nothing. While docking, the three front ToF sensors are
ignored, because they would see the pallet the forklift is about to pick up (SF-03). Speed is capped instead.

| micro-ROS topic | Direction | Rate |
|---|---|---|
| `cmd_vel`, `lift_cmd` | Jetson → ESP32 | 20 Hz |
| `heartbeat` | Jetson → ESP32 | 10 Hz (missing → SAFE) |
| `wheel_odom` / `imu/data` | ESP32 → Jetson | 50 Hz / 100 Hz |
| `tof_ring`, `fork_state` | ESP32 → Jetson | 20 Hz |
| `safety_state` | ESP32 → Jetson | 10 Hz + on change |
| `battery` | ESP32 → Jetson | 1 Hz |

## 5. Layer 3 — Jetson, ROS 2 Humble

Ten packages. Decision logic is plain Python without `rclpy`, so it is tested on the laptop; the ROS nodes are thin
wrappers. The whole workspace builds and passes `colcon test` in a `ros:humble` container in CI.

| Package | Role |
|---|---|
| `forklift_mission` | Behaviour tree for a task (go → dock → lift → go → place), MQTT fleet client, traffic requests, server-loss handling |
| `forklift_navigation` | slam_toolbox, EKF (wheel odometry + IMU), Nav2 with Smac Hybrid-A* (Reeds-Shepp) and Regulated Pure Pursuit, no rotate-in-place |
| `forklift_perception` | ArUco detection + solvePnP → `pallet_pose`; initial pose from location markers |
| `forklift_rl` | Docking policy (ONNX) with a classical fallback |
| `forklift_safety` | Supervisor that clamps every command source; bridge for fork state |
| `forklift_description` | URDF/Xacro, dimensions, TF tree `map → odom → base_link → {laser, camera, imu, fork}` |
| `forklift_bringup` | One launch file, YAML configs, namespaces `/fl1 /fl2 /fl3`, systemd autostart, rosbag recording |
| `forklift_interfaces` | Messages, services and actions (`Lift`, `Dock`, `MoveTask`, `Reset`, …) |
| `forklift_camera_stream` | Low-resolution MJPEG of the fork camera for manual driving |
| `forklift_sim` | Gazebo Fortress digital twin generated from the warehouse map |

```mermaid
flowchart TB
  LIDAR[RPLIDAR] -->|scan| FILT[laser filter] --> SLAM[slam_toolbox] -->|map, map→odom| NAV[Nav2]
  ESP[(ESP32)] -->|wheel_odom, imu| EKF[EKF] -->|odom→base_link| NAV
  CAM[camera] -->|image_raw| ARUCO[aruco_node] -->|pallet_pose| DOCK[dock server<br/>RL policy]
  MISSION[mission node<br/>behaviour tree] -->|navigate_to_pose| NAV
  MISSION -->|dock action| DOCK
  MISSION -->|lift action| LIFT[lift server]
  NAV -->|cmd_vel_nav| SUP{{safety<br/>supervisor}}
  DOCK -->|cmd_vel_dock| SUP
  LIFT -->|lift_cmd| SUP
  MISSION -->|teleop| SUP
  SUP -->|cmd_vel 20 Hz, heartbeat| ESP
  ESP -->|tof_ring, safety_state| SUP
  MISSION <-->|MQTT| SERVER[(fleet server)]
```

**Supervisor limits:**

- **Speed:** 0.3 m/s normally, 0.1 m/s with the forks above 5 cm or while docking.
- **ToF ahead:** slow below 40 cm, stop below 15 cm, in the direction of travel.
- **Person (YOLO):** slow below 1 m, stop below 0.5 m.
- **Server lost for more than 3 s:** finish the current step, then stop.

## 6. Layer 4 — fleet server

```mermaid
flowchart TB
  subgraph API["FastAPI app"]
    REST["REST /api/*<br/>JWT roles"] --- WS["WebSocket /ws/live<br/>snapshot 2 Hz + events"]
  end
  subgraph FM["Fleet manager — 10 Hz loop"]
    ALLOC["Allocator<br/>nearest · Hungarian"]
    GRAPH["Lane graph + A*<br/>never through spurs"]
    TRAF["Traffic manager<br/>node + lane locks,<br/>deadlock detection"]
    POL["Policies<br/>battery, E-stop,<br/>teleop clamp, heartbeat"]
    SIM["Simulator<br/>fake robots + scenarios"]
  end
  BR["MQTT bridge (aiomqtt)"]
  DB[("PostgreSQL<br/>WMS tables")]
  MAP[/"warehouse_map.yaml"/]
  API --> FM
  FM --> API
  FM <--> DB
  MAP --> GRAPH
  FM <--> BR <--> MQ[["Mosquitto"]]
```

| Module | Responsibility |
|---|---|
| `fleet/graph.py` | Lane graph from the map file; A* that never routes through a pick/drop spur |
| `fleet/traffic.py` | One robot per lane and node, all-or-nothing lock acquisition, wait-for graph to detect deadlocks |
| `fleet/allocator.py` | `nearest` and optimal `hungarian` task assignment, switchable at run time |
| `fleet/manager.py` | Robot state, task lifecycle, commands, fleet E-stop, battery policy, teleop clamping, simulator |
| `fleet/mqtt_bridge.py` | Robot topics in → manager; manager outbox → broker |
| `routers/*` | REST endpoints and the WebSocket |
| `migrate.py` | Alembic upgrade on start-up |

### Data model (WMS)

| Table | Holds |
|---|---|
| `locations` | Code (`R1-W1-L2`), type, x/y/yaw, level, height, ArUco id, lane-graph node, occupied |
| `pallets` / `products` | Pallet (ArUco id 1–20, SKU, quantity, weight, location, status) and product catalogue |
| `robots` | Status, battery, pose, current task (live state in memory, saved every 2 s) |
| `tasks` | `T-0042`, pallet, from/to, robot, priority 1–5, status, route, distance, wait, timestamps, failure reason |
| `inventory_moves` | Every pallet move, written **in the same transaction** as the task's `done` |
| `events` | Safety / error / info events with severity, code and position |
| `traffic_waits` | Time spent waiting per lane, for the congestion heat map |
| `users` / `settings` | Accounts with roles (viewer / operator / admin), runtime settings |

### REST API (summary)

| Area | Endpoints |
|---|---|
| Auth | `POST /api/auth/login`, `GET /api/auth/me` |
| Fleet | `GET /api/fleet/state`, `POST /api/fleet/estop`, `GET /api/robots`, `POST /api/robots/{id}/cmd · /mode · /teleop`, `GET /api/robots/{id}/camera` |
| Tasks | `GET/POST /api/tasks`, `GET /api/tasks/{id}`, `POST /api/tasks/{id}/cancel` |
| Inventory | `GET/POST /api/pallets`, `GET /api/pallets/{id}/moves`, `GET/POST /api/products`, `GET/POST/PATCH /api/locations` |
| Map, traffic | `GET /api/map`, `GET /api/traffic` |
| Monitoring | `GET /api/events`, `GET /api/analytics/summary`, `GET /api/analytics/export` (CSV) |
| Admin | `GET/PATCH /api/settings`, `GET/POST/DELETE /api/users`, `POST /api/sim/scenario` |
| Health | `GET /api/health` (no login) |

Every response uses one envelope, `{ "data": …, "meta": … }`, and errors carry a stable code.

## 7. Robot ↔ server communication (MQTT)

| Topic | Direction | QoS | Notes |
|---|---|---|---|
| `wh/fl/{id}/state` | robot → server | 0 · 2 Hz | Pose, battery, mode, task; Last Will `{"online": false}` |
| `wh/fl/{id}/task` | server → robot | 1 | Pallet, from/to with coordinates and height, route |
| `wh/fl/{id}/task_status` | robot → server | 1 | accepted → to_pickup → picking → to_drop → dropping → done / failed |
| `wh/fl/{id}/cmd` | server → robot | 1 | pause, resume, go_charge, reset, cancel |
| `wh/fl/{id}/teleop` | server → robot | 0 · ≤ 10 Hz | Manual drive, already clamped by the server |
| `wh/fl/{id}/event` | robot → server | 1 | Safety and error events |
| `wh/traffic/{from}--{to}` | both | 1 | request / grant / deny / release of a lane |
| `wh/fleet/estop` | server → all | 1 · **retained** | A robot that reconnects learns the E-stop state at once |

Every message carries a sequence number and a UTC timestamp, and is validated against a JSON schema in
[docs/schemas](https://github.com/Smart-Warhouse/docs/tree/main/schemas). The broker has no anonymous access.
Each robot has its own login, and the ACL lets a robot publish only its own topics.

## 8. End to end: one pallet move

```mermaid
sequenceDiagram
  autonumber
  actor Op as Operator
  participant D as Dashboard
  participant S as Fleet server
  participant B as MQTT broker
  participant R as Forklift fl1
  Op->>D: Move pallet 7 to DOCK-OUT-1
  D->>S: POST /api/tasks
  S->>S: reserve pallet · allocator picks fl1 · A* route
  S->>B: wh/fl/fl1/task
  B->>R: task
  R->>B: task_status accepted
  loop every lane on the route
    R->>B: traffic request A21--J2
    B->>S: request
    S->>B: grant (lane + far node locked)
    B->>R: grant
    R->>R: Nav2 drives the lane (supervisor + ESP32 limit speed)
    R->>B: traffic release
  end
  R->>R: ArUco pose → RL docking → lift
  R->>B: task_status picking … to_drop … dropping
  R->>B: task_status done
  B->>S: done
  S->>S: ONE transaction: pallet location + inventory move + task done
  S-->>D: WebSocket: task, inventory, map update
```

## 9. Safety architecture

Defence in depth: each layer assumes the one above it can fail.

```mermaid
flowchart TB
  A["Server<br/>fleet E-stop (retained) · battery policy · teleop clamp · heartbeat timeout 3 s · lane locks"]
  B["Jetson safety supervisor<br/>clamps Nav2, RL, teleop · person stop · server-loss stop"]
  C["ESP32 safety loop, 1 kHz<br/>ToF slow / stop · watchdog · battery critical · sensor fault"]
  D["Hardware E-Stop<br/>cuts motor power — no software involved"]
  A --> B --> C --> D
```

| Failure | What happens |
|---|---|
| Person in front | YOLO → supervisor slows < 1 m, stops < 0.5 m; ToF stops < 15 cm anyway |
| Wi-Fi or server lost | Robot finishes the current lane, stops, waits, and resumes when the link returns |
| Robot disconnects | Broker sends its Last Will → server marks it offline; an unlifted task goes to another robot |
| Jetson crashes or USB unplugged | ESP32 misses the heartbeat → SAFE, motors stop (≈ 560 ms on the model, ≤ 600 ms required) |
| ESP32 control task stalls | Motor task brakes if the safety output is > 5 ms old; hardware watchdog reboots after 1 s |
| Two robots want the same lane | Only one gets the lock; deadlocks are detected and broken by detour or back-off |
| Battery low / critical | Low → go charge; critical (< 8 %) → safe stop |
| Operator presses STOP ALL | Retained E-stop: every robot holds zero speed until released |

## 10. AI components

| Component | Method | Result (simulation) |
|---|---|---|
| Pallet docking | MuJoCo environment with domain randomisation; imitation of the classical controller, then conservative PPO; checkpoint chosen on validation seeds; exported to ONNX | **98.7 %** docked, 6.5 s (with the safety supervisor), vs 90 %, 10.3 s for the classical controller, on 1000 episodes |
| Task allocation | Hungarian (optimal assignment) vs nearest robot | Same at low load; when saturated, **53–67 % more tasks/h** (270 runs, 15 seeds) |
| People / obstacles | YOLOv8n/v11n, TensorRT FP16 on the Jetson | Pipeline ready; needs ≥ 400 real images per class |
| Pallet pose | ArUco + solvePnP, sub-pixel corners | ≤ 1 cm, ≤ 2° required at ≤ 50 cm |

The AI never drives the motors directly: every command it produces goes through the safety supervisor and the
ESP32 safety loop, like any other command.

## 11. Simulation and testing

| Level | Tool | What it proves |
|---|---|---|
| Fleet logic | Built-in server simulator | Allocation, traffic, deadlocks, battery, failures — no hardware |
| Robot ↔ server | Real Mosquitto + reference robot client | Logins, ACL, Last Will, retained E-stop, broker restart, 3 robots × 20 tasks |
| Docking | MuJoCo + Gymnasium | Training and evaluation of the docking policy |
| Whole robot | Gazebo Fortress twin of the warehouse | Nav2 + mission + server against simulated forklifts |
| Firmware | Host unit tests + board build | Safety state machine, kinematics, PID, IMU filter |

CI runs on every push in each repository (13 jobs across the organisation): unit tests, type checks, lint, builds,
the ROS 2 `colcon` build and tests in `ros:humble`, and the integration suite against a real Mosquitto container.

## 12. Deployment

```mermaid
flowchart LR
  subgraph RW["Railway (cloud demo)"]
    L["landing<br/>nginx"]
    DSH["dashboard<br/>static"]
    API["backend<br/>FastAPI"]
    PG[("Postgres")]
    MQ[["Mosquitto<br/>TCP proxy + WSS"]]
    API --- PG
    API ---|private network| MQ
  end
  U(("Browser")) --> L
  U --> DSH
  DSH -->|HTTPS + WSS| API
  PH(("Phone app")) -->|HTTPS + WSS| API
  subgraph LAN["Warehouse LAN (live demo)"]
    LAP["Laptop: backend + Mosquitto<br/>(docker compose)"]
    RT["Wi-Fi 5 GHz router"]
    LAP --- RT
    RT --- F1["fl1"]
    RT --- F2["fl2"]
    RT --- F3["fl3"]
  end
```

- **Railway (cloud demo):** the online demo, with the simulator driving the fleet. Every push to `main` redeploys
  the matching service. Secrets live only in Railway's service variables.
- **Warehouse LAN (live demo with real forklifts):** the same backend and broker run on a laptop on the
  warehouse Wi-Fi. That gives lower latency and no dependence on the internet.

## 13. Key design decisions

| Decision | Choice | Why |
|---|---|---|
| Robot ↔ server protocol | MQTT + JSON schemas, not ROS across the network | Server built and tested without robots; robust over Wi-Fi; Last Will and retained messages give safety for free |
| Traffic control | Lane graph with node + lane locks | Predictable, testable, no gridlock; robots never block an aisle while docking (spurs) |
| One source of truth for the floor | `warehouse_map.yaml` | Same file drives the server, dashboard, Gazebo world and occupancy map |
| WMS consistency | Pallet moves only on `done`, in one transaction | Inventory always matches reality, even if a task fails half-way |
| Where AI is used | Docking, allocation, vision only | Navigation, control and safety stay classical and verifiable |
| Safety | Four independent layers, hardware E-Stop last | No single software failure can keep the motors running |
| Adding a robot | One entry in the map file | No code change (NFR-09) |
