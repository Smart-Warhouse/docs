# 15 — Bench tests T-01 … T-07

Requirements §14 (tests T-01 … T-07, the "part" and "forklift" levels). Run them in this order on the first
forklift after the build in [14-hardware-build.md](14-hardware-build.md); results go into the tables below and
then into the thesis results chapter (date, result, notes — §14). T-08 onwards need the Jetson stack and the
warehouse floor and are not covered here.

Tools: multimeter (two if possible), USB-C cable to a laptop, serial monitor at 115200 baud
(`.venv\Scripts\pio device monitor -b 115200` in `robot/firmware`), steel rule + tape measure, protractor,
matte white card (A5), stopwatch, phone with 240 fps slow-motion video, a stand that lifts the wheels off the
ground, masking tape for floor marks.

## 0. Safety rules for every test

1. **Wheels off the ground** (forklift on a stand) for everything except T-05 and T-06. Forks down, nothing
   on the forks, fingers away from the mast and the fork carriage.
2. **E-Stop within one hand's reach** of the person at the keyboard. Press it first when anything is
   unexpected; leave ESTOP only with `reset` after the button is released.
3. **`bench on` disables the link watchdog.** In bench mode the firmware makes its own heartbeat and keeps the
   last `cmd` alive (`consolePoll`), so **unplugging the USB cable does NOT stop the motors** — only the
   E-Stop, `cmd 0 0`, `bench off` or a ToF obstacle does. Always type `cmd 0 0` before walking away.
4. Battery: charge with the IMAX B3 on the balance lead, never unattended, on a non-flammable surface. Stop
   any test at 6.4 V (≈ 10 %); never discharge below 6.0 V.
5. First power-up of any new wiring: current-limited bench supply at 7.4 V / 1 A instead of the battery, check
   the rails (5.10 V, 12.0 V) with the multimeter before plugging in the ESP32, the Jetson or the motors.
6. With no E-Stop wired yet, GPIO 18 must be tied to GND — and then there is **no hardware stop**: keep the
   main switch in reach instead and limit tests to wheels-off-the-ground.

Console reminders (full list: `help`, [firmware README](https://github.com/Smart-Warhouse/robot/blob/main/firmware/README.md#console)):

| Command | Prints / does |
|---|---|
| `status` | `id state reason link bench microros`, `v_cmd v_meas cap steer duty`, `fork mm raw top bottom tcrt lift_duty`, `odom x y th enc_raw ok`, `battery V A % valid low` |
| `tof` | 6 lines `name distance valid present age err` |
| `diag` | FW-10 JSON: state, reason, chip temperature, heap, encoder/imu/fork/battery ok, I2C errors, per-ToF ok/err, per-task `loop_us [last, max, overruns]` |
| `bench on/off`, `cmd <v> <w>` | console stands in for the Jetson; cmd_vel in m/s and rad/s |
| `step <v> <ms>` | speed step, CSV `t_ms,v_target,v_ramped,v_measured,duty,state` at 100 Hz |
| `lift <mm>`, `odom reset`, `reset`, `cal …` | |

Safety states printed by `status`: `BOOT IDLE ACTIVE SLOW STOP SAFE ESTOP`; reasons: `none booting no_link
tof_slow tof_stop tof_fault fork_raised docking watchdog_heartbeat watchdog_cmd battery_low battery_critical
estop_pressed estop_wait_reset sensor_fault`.

Before T-02 … T-07 do the **calibration** of the firmware README (`id flN`, pot, servo, `cal imu`, wheel,
`cal save`) — T-02 and T-04 check its result.

---

## T-01 Power (EL-01 … EL-05) — part level

**Goal:** 30 min at full load — the Jetson never browns out, the 5 V rail stays within ± 5 %.

Setup: complete power tree of doc 14 §2, battery fully charged (8.3–8.4 V), forklift on the stand, Jetson
with JetPack, ESP32 flashed.

1. Main switch OFF. Measure battery voltage at the XT30: 7.4–8.4 V. Record.
2. Main switch ON, loads unplugged: buck output **5.10 ± 0.02 V**, boost output **12.0 ± 0.1 V**, motor rail
   (after the E-Stop) = battery voltage. Press the E-Stop: motor rail → 0 V, buck and boost unchanged.
3. Plug ESP32 and Jetson. Console `status`: `battery … valid=1`; compare the battery V with the meter
   (± 0.05 V) and, with a 1 A load, the current with a series meter (± 50 mA after the 0.01 Ω shunt swap).
4. Full load for **30 min**:
   - Jetson in the **15 W** nvpmodel mode (`sudo nvpmodel -q --verbose` lists the modes; MAXN is blocked by
     §3), CPU + GPU loaded: `stress-ng --cpu 6 --timeout 30m &` plus a GPU load (the YOLO / ArUco pipeline in
     a loop, or any CUDA sample); log `tegrastats --interval 5000 --logfile t01_tegrastats.log`.
   - LiDAR spinning (plugged into the Jetson USB).
   - Motors: `bench on`, `cmd 0.30 0` (wheels free), and every 30 s `lift 100` / `lift 0` alternately.
5. Every 5 min record: battery V and A (`status`), 5 V at the ESP32 5V pin (meter), 12 V at the Jetson jack,
   Jetson VDD_IN power and temperatures (tegrastats), boost and buck temperature by finger / IR thermometer.
6. At 30 min: `cmd 0 0`, `bench off`. On the Jetson: `uptime` (no reboot) and `sudo dmesg | grep -i -E
   "under-?voltage|throttl|brown"` (nothing).

**Pass:** Jetson up the whole time (uptime ≥ 30 min, no undervoltage messages); 5 V rail **4.85–5.36 V**
(5.10 ± 5 %) at every reading incl. lift reversals; 12 V rail 11.4–12.6 V; fuse intact; no part hotter than
~70 °C. **Fail actions:** 5 V dips → more capacitance at the ESP32 / servo, thicker buck wires; Jetson resets →
boost too small or input wires too thin; fuse blows at low battery → doc 14 §2 rule 8.

| Time (min) | Batt V | Batt A (INA219) | 5 V rail | 12 V rail | Jetson W | Jetson °C | Notes |
|---|---|---|---|---|---|---|---|
| 0 | | | | | | | |
| 5 | | | | | | | |
| 10 | | | | | | | |
| 15 | | | | | | | |
| 20 | | | | | | | |
| 25 | | | | | | | |
| 30 | | | | | | | |

---

## T-02 Sensors (FW-05) — part level

**Goal:** every sensor reads correctly; ToF ± 1 cm, IMU yaw drift ≤ 2°/min.

1. **Bus check** — `diag`: `encoder_ok:1, imu_ok:1, fork_ok:1, battery_ok:1`, `i2c_err` not increasing
   between two `diag` calls 10 s apart, all six `tof` entries `ok:1`.
2. **ToF ring (± 1 cm)** — for each sensor, hold the white card square to its axis at **10, 20, 40, 100 cm**
   (rule from the sensor face), wait 1 s, `tof`, write down the distance. Also cover each sensor in turn with
   a finger and check the **right name** drops to ~0 m (or `valid=0`) (proves mux channel = `TofIndex`, doc 14 §3).
3. **Fork pot + limits** — move the forks to 0, 30, 60, 90, 120 mm (rule from the floor to the fork top minus
   the fork height at rest), `status` → `fork=… mm`. Press each limit switch by hand → `top=1` / `bottom=1`.
4. **TCRT5000** — card 5 mm above each fork-tip sensor → `tcrt=1/…` resp. `…/1`; card away → 0. Adjust
   the module trimmer if needed.
5. **AS5600** — `odom reset`, turn the drive wheel exactly 10 turns by hand (tape mark) → `status` x should be
   10 × 2π × wheel radius (± 1 %); `enc_raw` must change smoothly. Negative x → `cal encdir -1`.
6. **IMU drift (≤ 2°/min)** — forklift still and level, `cal imu`, wait 5 s, `cal save`. The console has **no
   IMU readout yet** (see "Gaps"), so read yaw over micro-ROS on the Jetson:
   ```bash
   ros2 topic echo /fl1/imu/data --field orientation   # note the quaternion at t=0 and t=10 min
   python3 -c "import math,sys; x,y,z,w=map(float,sys.argv[1:]); print(math.degrees(math.atan2(2*(w*z+x*y),1-2*(y*y+z*z))))" X Y Z W
   ```
   Drift = |yaw(10 min) − yaw(0)| / 10.
7. **INA219** — done in T-01 step 3.

**Pass:** all `ok`; every ToF reading within ± 1 cm at 10–100 cm; pot within ± 3 mm at all five heights;
limits and TCRT switch correctly; 10 wheel turns within ± 1 %; yaw drift ≤ 2°/min.

| Sensor | 10 cm | 20 cm | 40 cm | 100 cm | Max error | Pass |
|---|---|---|---|---|---|---|
| front | | | | | | |
| front_left | | | | | | |
| front_right | | | | | | |
| left | | | | | | |
| right | | | | | | |
| rear | | | | | | |

| Check | Expected | Measured | Pass |
|---|---|---|---|
| Pot 0 / 30 / 60 / 90 / 120 mm | ± 3 mm | | |
| Limit top / bottom | 1 when pressed | | |
| TCRT left / right | 1 with card | | |
| 10 wheel turns | 20 π r ± 1 % | | |
| IMU yaw drift | ≤ 2°/min | | |

---

## T-03 Speed PID (FW-03) — part level

**Goal:** step response settles in ≤ 300 ms, steady-state error ≤ 5 %.

Setup: wheels off the ground, forks down (forks above 5 cm cap the speed at 0.1 m/s, SF-08), ≥ 50 cm free in
front of and behind the ToF sensors (a ToF seeing the bench stops the motor: state `STOP` / `tof_fault`).

1. `bench on`.
2. For v = **0.10, 0.20, 0.30 m/s**: `step <v> 2000`, copy the CSV into `t03_<v>.csv` (stop logging after the
   500 ms tail). Repeat each 3 times.
3. Plot `v_measured` and `v_ramped` against `t_ms`. The target is ramped by the acceleration limit
   (0.6 m/s², so 0.3 m/s takes 500 ms to reach); measure the PID on the **ramped** target:
   - **settling time** = time from the end of the ramp until `v_measured` stays within ± 5 % of v;
   - **steady-state error** = mean |v_measured − v| / v over the last 500 ms of the step.
4. If it fails: tune with `cal drive <kp> <ki> <kd> <kff>` (start by `kff` so the duty at steady state is
   right, then `kp`, then `ki`), repeat, `cal save`. With the Jetson the same gains are ROS parameters
   `drive_kp …` + `save_calibration`.
5. Repeat one 0.2 m/s step **on the floor** (T-05 setup) — the load changes the plant; it must still pass.

**Pass:** all 9 runs settle ≤ 300 ms after the ramp, steady error ≤ 5 %, no `state` other than ACTIVE in the CSV.

| v (m/s) | Run | Settle (ms) | SS error (%) | Overshoot (%) | Gains (kp ki kd kff) | Pass |
|---|---|---|---|---|---|---|
| 0.10 | 1–3 | | | | | |
| 0.20 | 1–3 | | | | | |
| 0.30 | 1–3 | | | | | |
| 0.20 floor | 1 | | | | | |

---

## T-04 Lift PID (FW-04) — part level

**Goal:** 20 random height commands reach the target within ± 3 mm; the lift stops at once on a limit switch.

1. Generate 20 random heights in 5 … 115 mm (e.g. `python -c "import random; print(sorted(random.sample(range(5,116),20)))"`,
   then shuffle). Forks empty first, then repeat with the heaviest demo pallet.
2. For each: `lift <mm>`, wait until `status` shows `lift_duty=0.00` (≤ 3 s), then measure the real fork-top
   height with the rule / caliper at the fork heel, and note `fork=… mm` from `status`.
3. **Limit stop**: `lift 120`, press the top limit switch by hand halfway → lift motor stops immediately
   (`top=1`, `lift_duty=0.00`). Same for the bottom switch on `lift 0`.

**Pass:** |measured − commanded| ≤ 3 mm for all 20 (empty and loaded); limit switches stop the motor every time.

| # | Command (mm) | Measured (mm) | `status` fork (mm) | Error (mm) | Time to stop (s) | Pass |
|---|---|---|---|---|---|---|
| 1 | | | | | | |
| … | | | | | | |
| 20 | | | | | | |

---

## T-05 Odometry (FW-02) — forklift level

**Goal:** error ≤ 3 % of the distance on a 2 m straight line and on a 1 × 1 m square.

Setup: forklift on the floor (matte, clear 3 × 3 m), ToF ring working, USB cable long enough (≥ 3 m) or a
person carrying the laptop; second person on the E-Stop. Tape a start mark at the front axle centre and the
fork direction.

1. **Straight 2 m**: `odom reset`, `bench on`, `cmd 0.10 0`, stopwatch: after **20 s** `cmd 0 0`. Measure the
   real travel of the axle mark with the tape (along and across), read `status` → `odom x y th`.
2. Repeat 3 times; also once at 0.2 m/s for 10 s.
3. **Square 1 × 1 m** (counter-clockwise): `odom reset`, then per side: `cmd 0.10 0` for ~10 s (1 m), then a
   left turn `cmd 0.10 0.6` until the forklift points 90° left (watch the floor tape; ≈ 2.6 s at ω = 0.6),
   ×4. `cmd 0 0`. Measure the real end position vs the start mark and read the odom pose.

Error = distance between the odometry end point and the measured end point; % of the path length (2 m or 4 m).

**Pass:** straight ≤ 6 cm (3 % of 2 m); square ≤ 12 cm (3 % of 4 m). Fix: `cal wheel` (distance),
`cal servo` / `cal servo_gain` (curving, heading error), `WHEELBASE_M` after ME-01.

| Run | Path (m) | Real end x / y (cm) | Odom x / y (cm) | Error (cm) | % | Pass |
|---|---|---|---|---|---|---|
| Straight 0.1 #1 | 2 | | | | | |
| Straight 0.1 #2 | 2 | | | | | |
| Straight 0.1 #3 | 2 | | | | | |
| Straight 0.2 | 2 | | | | | |
| Square | 4 | | | | | |

---

## T-06 Safety (SF-01 … SF-04, NFR-04) — forklift level

**Goal:** an obstacle appearing in front of the forklift driving at 0.3 m/s is never touched (20 / 20), and
the stop reacts within ≤ 100 ms.

Setup: as T-05, straight 3 m lane. Obstacle: a 15 × 20 cm box (matte, not black) on a string so it can be
pulled into the lane suddenly. Phone at 240 fps filming from the side with the box and a wheel in view.

1. **E-Stop (SF-01)** first: `bench on`, `cmd 0.20 0`, press the E-Stop → wheels stop **at once** (hardware),
   `status` → `ESTOP estop_pressed`; Jetson and ESP32 stay on. Release, `reset` → IDLE. 3 times.
2. **ToF slow-down (SF-02)**: drive at 0.3 m/s towards a fixed box; `status` during the approach shows `SLOW
   tof_slow` from < 40 cm (30 % speed) and `STOP tof_stop` at < 15 cm; the forklift stops without touching.
3. **Sudden obstacle (× 20)**: `cmd 0.30 0`; when the forks are ~50 cm from the string line, pull the box in
   front of the forklift (land it 20–35 cm ahead). After the stop, `cmd 0 0`, measure the remaining gap, back
   up (`cmd -0.1 0`), repeat. Mix: centre, front-left, front-right.
4. **Reaction time** from the video: frame where the box crosses the 15 cm line (tape mark on the floor) →
   frame where the drive wheel stops turning faster than the free-roll; at 240 fps one frame = 4.2 ms.
   This end-to-end figure includes the ToF period (20 ms), the 1 kHz safety loop and the motor brake.
5. **Watchdog (SF-04)**: covered by T-07.

**Pass:** 20 / 20 stops with no contact (gap > 0); reaction ≤ 100 ms in every run; E-Stop stops instantly and
needs `reset`.

| # | Speed | Position | Gap after stop (cm) | Reaction (ms, video) | Contact? | Pass |
|---|---|---|---|---|---|---|
| 1 | 0.3 | centre | | | | |
| … | | | | | | |
| 20 | | | | | | |

---

## T-07 Watchdog (FW-06) — forklift level

**Goal:** losing the Jetson link while driving stops the forklift within ≤ 600 ms (500 ms watchdog + ramp).

The real test needs the Jetson driving the ESP32 over micro-ROS (micro-ROS build, see the firmware README —
the console then sits on UART0, GPIO 43/44, read it with a 3.3 V USB-UART adapter).

1. Wheels off the ground first, then on the floor.
2. Jetson: `ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/ttyACM0 -b 921600`, then
   ```bash
   ros2 topic pub -r 10 /fl1/heartbeat std_msgs/msg/UInt32 "{data: 1}" &
   ros2 topic pub -r 20 /fl1/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2}}"
   ```
3. While the wheels turn, **pull the USB cable** at the ESP32. Film at 240 fps (cable and wheel in view).
4. UART console `status` afterwards: `SAFE watchdog_heartbeat`; after re-plugging and 1 s of heartbeat the
   state returns to IDLE (no `reset` needed — only ESTOP needs it).
5. Also: stop only the `cmd_vel` publisher (heartbeat keeps running) → `SAFE watchdog_cmd` within 600 ms.
6. 10 runs each.

Console-only pre-check (no Jetson): `bench on`, `cmd 0.2 0`, `bench off` → after 1 s `status` shows
`SAFE watchdog_heartbeat`. This proves the detection only: `bench off` also zeroes the command, so the wheels
stop by the normal ramp, not by the watchdog.

**Pass:** wheels stopped ≤ 600 ms after the cable leaves the socket in 10 / 10 runs (video); correct reason;
automatic recovery after the link returns.

| # | Trigger | Stop time (ms) | State / reason | Recovered | Pass |
|---|---|---|---|---|---|
| 1 | USB pulled | | | | |
| … | | | | | |
| 10 | | | | | |
| 1 | cmd_vel stopped | | | | |
| … | | | | | |

---

## Summary sheet

| Test | Date | Forklift | Result (pass / fail) | Key number | Notes |
|---|---|---|---|---|---|
| T-01 Power | | | | min 5 V = | |
| T-02 Sensors | | | | max ToF err = | |
| T-03 Speed PID | | | | max settle = | |
| T-04 Lift PID | | | | max err = | |
| T-05 Odometry | | | | max % = | |
| T-06 Safety | | | | stops 20/20, max ms = | |
| T-07 Watchdog | | | | max ms = | |

## Gaps found while writing these procedures (firmware follow-ups)

- **No IMU readout on the console**: T-02's yaw drift needs micro-ROS (`/flN/imu/data`). A console `imu`
  command printing yaw / pitch / roll and gyro z would let T-02 run without the Jetson.
- **Bench mode ignores a lost USB link**: `consolePoll` refreshes the heartbeat and the last `cmd` on its own
  while `bench on`, so pulling the cable keeps the motors running. Suggest refreshing only while bytes arrive
  (or while USB CDC DTR is set), so bench mode keeps the watchdog.
- **No console watchdog test with a non-zero command**: `bench off` sets `cmd 0 0`, so it never exercises the
  watchdog ramp (`SAFE_DECEL_MPS2`). A `bench drop` command that stops the heartbeat but keeps the command
  would make T-07 possible on the bench without the Jetson.
- **No timestamped event log**: T-06 reaction time is measured by video; a CSV line on every state change
  (`t_ms, state, reason, tof[]`) would give the latency directly.
