# 17 — Integration and performance tests (fleet over MQTT)

`code/integration/` runs the real server against a real broker and real robot clients — no mocks between them:

```
Mosquitto (passwords + ACL)  ⇄  FastAPI server (MQTT_ENABLED=true)  ⇄  REST / WebSocket test clients
        ⇅                       map copy: fl1..fl3 (perf: fl1..fl4) simulated: false
3–4 × reference robot client (code/ros2_ws/tools/mqtt_robot_client/robot_client.py), one MQTT user each
```

It closes plan.md B7 "Test Mosquitto authentication + ACL" (CM-01) in CI and is the automated version of T-14
(three forklifts, full tasks through the server). It also covers the performance requirements SV-10 and NFR-07.
The robot client stands in for `forklift_mission`, so these tests check the server and the MQTT contract
([03](03-mqtt-contract.md)), not Nav2 or the hardware.

## What is covered

| Test | Requirement | What it checks |
|---|---|---|
| `test_fleet_e2e.py::test_anonymous_and_wrong_password_are_refused` | CM-01 | An anonymous login, a wrong password and an unknown user all get a refused CONNACK |
| `…::test_robot_cannot_publish_as_another_robot` | CM-01 | `fl2` publishing on `wh/fl/fl1/state` and `/event` is dropped by the broker: a subscriber never sees it and the server's view of fl1 is unchanged. Positive control: fl2's own topic gets through |
| `…::test_robot_cannot_read_another_robots_commands` | CM-01 | fl2 subscribes to `wh/fl/fl1/task` and `wh/fl/+/cmd`; of commands sent to fl1 and fl2 it receives only its own. The SUBACK code for fl1's topic is printed (`testbroker.py` answers 0x80); the test only requires that nothing arrives |
| `…::test_rest_task_completes_and_pallet_moves` | FR-01, SV-09 | `POST /api/tasks` → assigned → `to_pickup` … `done` over MQTT; the pallet, both locations and the move history change only at `done` |
| `…::test_three_robots_twenty_tasks_no_conflicts_no_gridlock` | SV-01..SV-03, SF-10, T-14 | 20 random pallet moves (up to 10 open at once) on 3 robots. A 5 Hz monitor on `/api/robots` + `/api/traffic` checks: no two robots closer than 0.2 m (the closest nodes are 0.35 m apart), never more than one lane reserved per robot, no robot with a task standing still for 25 s. All 20 must finish `done` and every robot must have worked |
| `test_faults.py::test_last_will_marks_offline_and_requeues_unloaded_task` | CM-03, SV-04 | The robot standing at the pallet (`picking`, forks not lifted) is killed with `kill -9`. The broker publishes the Last Will and the server marks it offline in well under the 3 s heartbeat. The task goes back to the queue and another robot gets it. The dead robot restarts at the spur it died in and drives home, and the other robot finishes the task |
| `…::test_fleet_estop_is_retained_stops_all_and_release_resumes` | SF-11 | `POST /api/fleet/estop` while robots drive: the message is retained (a newly connecting robot learns `engaged: true`), every robot stops (speed 0, position frozen for 2 s), `reset` is refused with `fleet_estopped`. Release → retained `false` and every task finishes |
| `…::test_broker_restart_clients_and_server_reconnect` | SF-05, T-16 | Broker stopped for 2 s mid-task. The server's bridge and all robot clients reconnect by themselves. Robots that dropped out long enough have their unloaded tasks re-queued, and the stale ones are cancelled. All tasks plus a new one finish `done` |
| `perf/test_perf.py` (`perf/run_perf.py`) | SV-10, NFR-07 | REST latency, WebSocket snapshot rate and command latency with 4 robots and 5 WebSocket clients (below) |

## Run locally

```bash
cd code/integration
../backend/.venv/Scripts/pip install -r requirements.txt     # on top of the backend's requirements
../backend/.venv/Scripts/python -m pytest -v -rs              # e2e + faults + perf (relaxed thresholds), ~4-5 min
../backend/.venv/Scripts/python perf/run_perf.py              # perf with the spec targets → table + perf/results.json
../backend/.venv/Scripts/python stack.py up                   # leave the whole stack running (dashboard, manual tests)
```

The broker is picked by `IT_BROKER` (`stack.py`):

| `IT_BROKER` | Broker |
|---|---|
| `auto` (default) | `container` if `MQTT_CONTAINER` is set, else `docker` if `docker info` answers, else `binary` if `mosquitto` is on PATH / `MOSQUITTO_BIN`, else **every test is skipped** with the reason |
| `docker` | `docker run eclipse-mosquitto:2` with the repo's `mosquitto.conf` + `acl` and a generated passwd file |
| `binary` | a local `mosquitto -c` with the same files (paths and port rewritten) |
| `container` | an already running container (`MQTT_CONTAINER`, `MQTT_HOST`, `MQTT_PORT`), configured with `python stack.py broker-config DIR` — the CI service container |
| `python` | `testbroker.py`, a small MQTT 3.1.1 broker in this folder that reads the same passwd (`$7$` PBKDF2-SHA512) and ACL files and follows Mosquitto's rules for what the suite uses: refused CONNACK, silently dropped publishes, SUBACK 0x80, retained messages, Last Will, keep-alive. Never chosen automatically |

Every run uses throw-away logins (`server`, `fl1`..`fl4`, in `stack.py`), a fresh SQLite database and a temporary
copy of `warehouse_map.yaml` with the robots set to `simulated: false`. The repo map is never edited. Clients drive
at 1 m/s with 0.5 s pick/drop (2 s in `test_faults.py`), so a few simulated minutes of fleet work take about 2 min.
Logs of every process are attached to a failing test. `IT_VERBOSE=1` adds client debug logs and a trace of every
non-state MQTT message.

## Run in CI

A separate job with a Mosquitto service container. A service container starts before the checkout, so the job
copies the repo config in and restarts the broker. The passwd file is generated by `stack.py broker-config`, so
no password is committed:

```yaml
  # in jobs.changes: outputs.integration: ${{ steps.f.outputs.integration }}, and in the paths filter:
  #   integration: ['code/integration/**', 'code/backend/**', 'code/ros2_ws/tools/**', '.github/workflows/ci.yml']
  integration:
    needs: changes
    if: needs.changes.outputs.integration == 'true'
    runs-on: ubuntu-latest
    timeout-minutes: 30
    services:
      mqtt:
        image: eclipse-mosquitto:2
        ports: ["1883:1883"]
        options: --name mqtt
    env:
      IT_BROKER: container
      MQTT_CONTAINER: mqtt
      MQTT_HOST: 127.0.0.1
      MQTT_PORT: "1883"
      IT_PERF_OUT: ${{ github.workspace }}/perf-results.json
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip
          cache-dependency-path: |
            code/backend/requirements.txt
            code/integration/requirements.txt
      - run: pip install -r code/backend/requirements.txt -r code/integration/requirements.txt
      - name: Load the repo's mosquitto.conf + ACL and generated test logins into the broker
        run: |
          python code/integration/stack.py broker-config /tmp/mqtt
          docker cp /tmp/mqtt/. mqtt:/mosquitto/config/
          docker exec mqtt sh -c 'chown mosquitto:mosquitto /mosquitto/config/passwd /mosquitto/config/acl && chmod 0600 /mosquitto/config/passwd /mosquitto/config/acl'
          docker restart mqtt
      - name: Fleet over Mosquitto + perf (relaxed thresholds)
        working-directory: code/integration
        run: python -m pytest -v -rs
      - if: always()
        uses: actions/upload-artifact@v4
        with: { name: perf-results, path: perf-results.json, if-no-files-found: ignore }
      - if: failure()
        run: docker logs mqtt --tail 200
```

The broker-restart test restarts the service container itself (`docker stop` / `docker start mqtt`). CI uses the
relaxed perf thresholds (REST p95 ≤ 300 ms, WebSocket 2 Hz ± 25 %, command p95 ≤ 500 ms), because shared runners
are noisy. The spec targets apply to `perf/run_perf.py` on the server machine.

## Results

### Local, 2026-10-18 (Windows 11 laptop, 20 logical CPUs, Python 3.11.9)

Docker Desktop's engine does not answer on this laptop (and WSL has no distribution), and there is no Mosquitto
binary, so `auto` skips everything (checked: 9 skipped with the message above). The suites were run with
**`IT_BROKER=python`**: real server, real robot clients and real MQTT over TCP, but the broker is `testbroker.py`,
not Mosquitto. So locally the ACL tests check the repo's ACL file under Mosquitto's rules as `testbroker.py`
implements them. The check against Mosquitto itself is the CI job.

| Run | Result |
|---|---|
| `pytest -v` (all 9) | 9 passed in 4 min 11 s |
| `test_fleet_e2e.py`, 2 more runs | 5/5 passed each time; 20/20 tasks done on 3 robots, 0 violations, at most 1 lane per robot |
| `test_faults.py`, 3 more runs (with the final code) | 3/3 passed each time. Kill -9 → offline after 15–312 ms (Last Will, not the 3 s heartbeat). Broker down 2 s → server back after 0.5–0.7 s, all robots online after 1.0–1.1 s |
| backend `pytest` (unit, incl. the new stale-lock test) | 40 passed |

Performance, `perf/run_perf.py` (spec thresholds; 4 real robots on tasks, 5 WebSocket clients, 200 requests per
endpoint, sequential):

| REST endpoint | p50 ms | p95 ms | p99 ms | max ms |
|---|---|---|---|---|
| `GET /api/health` | 0.8 | 1.1 | 1.5 | 2.1 |
| `GET /api/robots` | 2.7 | 4.4 | 21.6 | 26.9 |
| `GET /api/fleet/state` | 3.9 | 8.0 | 19.7 | 23.4 |
| `GET /api/traffic` | 2.6 | 4.2 | 6.0 | 24.4 |
| `GET /api/tasks?limit=50` | 8.3 | 13.4 | 19.8 | 53.6 |
| `GET /api/pallets` | 7.7 | 13.3 | 24.3 | 38.6 |
| `GET /api/locations` | 4.0 | 6.9 | 9.1 | 22.0 |
| `GET /api/events?limit=100` | 3.5 | 5.5 | 7.5 | 15.8 |
| `GET /api/map` | 5.4 | 8.7 | 12.0 | 73.1 |
| `GET /api/analytics/summary` | 3.8 | 6.9 | 8.0 | 35.1 |

| Command latency (60 × pause/resume on fl4) | p50 ms | p95 ms | p99 ms | max ms |
|---|---|---|---|---|
| REST response | 12.3 | 32.5 | 135.1 | 276.2 |
| REST → `wh/fl/fl4/cmd` delivered by the broker | 29.7 | 43.8 | 146.2 | 290.6 |
| REST → robot client applied it (its next state says `paused` / not paused) | 30.4 | 44.7 | 146.9 | 291.2 |

| WebSocket `/ws/live` | |
|---|---|
| Snapshot rate, each of 5 clients | 1.974 Hz |
| Interval p50 / p95 / max | 501 / 534 / 686 ms |

| Target | Measured | |
|---|---|---|
| REST p95 ≤ 100 ms (NFR-07) | worst endpoint 13.4 ms | pass |
| Snapshots 2 Hz ± 10 % (SV-10) | 1.97 Hz | pass |
| Command REST → robot ≤ 200 ms on localhost | p95 44.7 ms | pass |

Notes:
- The robot-applied time is an upper bound for the one-way time. It includes the robot's state message
  travelling back to the probe.
- Most of the ~30 ms to the broker is the bridge's 20 ms outbox poll plus, on Windows, the hop from uvicorn's
  Proactor loop to the bridge's selector-loop thread.
- The snapshot loop sleeps 0.5 s and then builds the snapshot, so it runs slightly under 2 Hz (about 1.3 % low).
  The occasional p99 spike (~150–300 ms) is SQLite writes from the fleet loop on the same event loop.
- The pytest run with relaxed thresholds measured the same picture: worst REST p95 17.2 ms, 1.96 Hz,
  command p95 44.4 ms.
- `perf/results.json` holds the full numbers of the latest `run_perf.py` run.

### CI

Not run yet from this folder: the job above has to be added to `.github/workflows/ci.yml`. Its first green run is
the Mosquitto CM-01 result. Add the numbers from its `perf-results` artifact here.

## Bugs found and fixed

| Where | Bug | Fix | Covered by |
|---|---|---|---|
| reference client | Real robots meeting head-on in a corridor (fl2 at J2 wanting J3, fl3 at J3 wanting J2) waited forever. The server detects the cycle but never re-routes a real robot | Robot-side wait breaking: denied for a random 2–4 s → ask once more, then a detour round the blocked node, then any free neighbour (lane nodes first), waiting there 1–3 s. A late grant is handed back with `release`. Written into [03](03-mqtt-contract.md) | `test_three_robots_twenty_tasks…` (failed before: gridlock after 4–7 tasks) |
| reference client | After a task the robot stayed parked in the drop spur, so a later move to or from the other level of that rack slot could never get in | Drives home after `--home-after-s` (2 s) idle, still reporting `idle`; a new task cancels the trip | same; `test_last_will…` |
| reference client | Broker lost → SAFE until an operator reset, but the contract says finish the lane, stop, and resume (operator reset is an option) | Default now follows the contract: lane finished, waits, resumes. `--require-reset` keeps the old behaviour | `test_broker_restart…` |
| reference client | `--start` also replaced the robot's home, so a robot restarted elsewhere treated that spot as home | Home always comes from the map | `test_last_will…` |
| server `manager.py` | A `release` published while the broker was down never arrives, so the lane and node stayed locked forever and blocked the next robot (seen once in the first full `test_faults.py` runs: the follow-up task waited forever behind a lane held by an idle robot at home) | `_drop_stale_locks`: a state report at node N frees every lock of that robot except node N and the newest lane out of N | `tests/test_mqtt_bridge.py::test_lost_release_does_not_block_a_lane_forever`, `test_broker_restart…` |

## Not covered here

- Mosquitto itself locally (no Docker / binary on the development laptop). CI covers it.
- Mixed fleets (simulated and real robots sharing lanes), `go_charge` for real robots (the reference client then
  stays in `charging`), manual mode / teleop over MQTT, TLS.
- PostgreSQL: the suite uses SQLite. Point `DATABASE_URL` at PostgreSQL in `stack.py` to repeat the perf numbers
  on the deployment database.
