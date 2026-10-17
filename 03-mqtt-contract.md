# 03 — Robot ↔ server MQTT contract

Requirements §10 (CM-01..CM-05). Implemented server-side in `code/backend/app/fleet/mqtt_bridge.py`; the robot side
is the `forklift_mission` fleet client in `code/ros2_ws` (not written yet). JSON Schemas for every payload are in
[`schemas/`](schemas/) (CM-05).

Broker: Mosquitto on the server (`code/backend/docker-compose.yml`), no anonymous access, one MQTT user per robot
named after its id (`fl1`…), ACL in `code/backend/mosquitto/acl` — a robot can only publish its own topics (CM-01).
Every message carries `seq` (per-sender counter) and `ts` (UTC ISO-8601); clocks synced with chrony (CM-04).

| Topic | Dir | QoS | Retain | Schema |
|---|---|---|---|---|
| `wh/fl/{id}/state` | robot → server | 0, 2 Hz | no | [state.schema.json](schemas/state.schema.json) |
| `wh/fl/{id}/task` | server → robot | 1 | no | [task.schema.json](schemas/task.schema.json) |
| `wh/fl/{id}/task_status` | robot → server | 1 | no | [task_status.schema.json](schemas/task_status.schema.json) |
| `wh/fl/{id}/cmd` | server → robot | 1 | no | [cmd.schema.json](schemas/cmd.schema.json) |
| `wh/fl/{id}/teleop` | server → robot | 0, ≤10 Hz | no | [teleop.schema.json](schemas/teleop.schema.json) (extension for UI-08) |
| `wh/fl/{id}/event` | robot → server | 1 | no | [event.schema.json](schemas/event.schema.json) |
| `wh/traffic/{segment}` | both | 1 | no | [traffic.schema.json](schemas/traffic.schema.json) |
| `wh/fleet/estop` | server → all | 1 | **yes** | [estop.schema.json](schemas/estop.schema.json) |

## Behaviour

- **Last Will (CM-03):** each robot connects with will topic `wh/fl/{id}/state`, payload `{"online": false}`, QoS 1.
  The server marks the robot offline immediately; if no state arrives for `heartbeat_timeout_s` (default 3 s, SF-05)
  it is marked offline anyway. A task not yet lifted is re-queued for another robot (SV-04); a loaded robot keeps
  its task and waits for an operator reset.
- **Traffic (SV-03, SF-10):** the segment in the topic is `<from>--<to>` (direction of travel). Before driving a lane
  the robot publishes `{"robot_id":"fl1","action":"request"}`; the server answers on the same topic with
  `grant` or `deny` (a robot ignores answers addressed to another `robot_id`). Granted = the lane *and* the far
  node are locked for that robot. On arrival the robot publishes `release`, which frees the lane and the node it
  left. On `deny` the robot waits and re-requests every 500 ms.
- **E-stop (SF-11):** `wh/fleet/estop` is retained, so a robot that (re)connects learns the state at once. While
  `engaged` the robot must hold `cmd_vel = 0` until it sees `engaged: false`.
- **Task flow:** `task` → robot replies `task_status` `accepted` → `to_pickup` → `picking` → `to_drop` → `dropping`
  → `done` | `failed` (+ `reason`). The WMS moves the pallet only on `done` (SV-09).

## Example task message

```json
{
  "task_id": "T-0042", "type": "move_pallet", "pallet_id": 7,
  "from": {"location": "R1-E1-L2", "x": 2.65, "y": 1.6, "yaw": 3.1416, "height_mm": 60},
  "to":   {"location": "DOCK-OUT-1", "x": 5.65, "y": 1.6, "yaw": 0.0, "height_mm": 0},
  "route": ["J5", "A22", "A21", "R1-E1", "A21", "J2", "J3", "A31", "DO1"],
  "priority": 2, "issued_at": "2026-10-16T19:50:00Z", "seq": 118, "ts": "2026-10-16T19:50:00Z"
}
```
