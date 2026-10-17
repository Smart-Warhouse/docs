# 10 — Requirement traceability (software built so far)

Only requirements touched by the code in this repository are listed. Hardware, firmware, ROS 2 and training
requirements (ME-*, EL-*, FW-*, JS-*, PC-*, NV-*, AI-01..07) have no code yet. Test names refer to
`code/backend/tests/`; UI rows point at the per-app docs.

| Req | What | Where | Verified by |
|---|---|---|---|
| FR-01 | Move order from dashboard / WMS | `POST /api/tasks` · `manager.create_task` · dashboard Tasks, app "Move a pallet" | `test_full_task_moves_pallet` |
| FR-02 | Auto-assign to an available robot | `manager._allocate` + `allocator.py` | `test_full_task_moves_pallet`, `test_allocators` |
| FR-05 | WMS updates pallet location after each move | `manager._complete_task` (one transaction) | `test_full_task_moves_pallet` |
| FR-06 | Live position/state/battery | `/ws/live` snapshots 2 Hz · dashboard map + fleet · app fleet | `test_ws_live_snapshot` |
| FR-07 (server side) | Stop on person/obstacle, continue after | simulator `person`/`obstacle` scenarios, `safety_state` | `test_pause_resume_and_person_scenario` |
| FR-08 / SF-10 | No collisions in lanes (one robot per lane/node) | `traffic.py` locks, `manager._drive`, deadlock resolution | `test_three_robots_many_tasks_no_collision`, `test_traffic_all_or_nothing_and_deadlock`, stress runs (06-backend.md) |
| FR-09 / SF-09 / SV-05 | Low battery → charge; critical → safe stop | `manager._battery_policy` | `test_low_battery_goes_to_charge_and_refuses_tasks` |
| FR-10 / UI-08 | Manual mode with safety still active | `/robots/{id}/mode`, `/teleop` (clamped, 0.5 s dead-man) · dashboard Manual · app Manual drive | `test_manual_mode_teleop_clamped` |
| FR-11 / UI-05 | Reports & analytics | `/api/analytics/summary`, `/export` | `test_full_task_moves_pallet` |
| SV-01 | Priority task queue | `_allocate` orders by priority, then age | — |
| SV-02 | Lane graph from YAML + A* | `warehouse_map.yaml`, `graph.py` | `test_map_is_connected_and_spurs_are_dead_ends`, `test_astar_avoids_blocked` |
| SV-03 | Reservations, waiting, deadlock detect + resolve | `traffic.py`, `manager._resolve_traffic` | unit + stress |
| SV-04 | Re-assign on failure | `_go_offline` re-queues unloaded tasks | `test_disconnect_requeues_unloaded_task` |
| SV-06 | Fake robots | simulator in `manager.py` | all fleet tests |
| SV-07 | JWT + roles | `security.py`, `deps.py` | `test_auth_required_and_roles` |
| SV-08 | OpenAPI | `/docs` | manual |
| SV-09 | Pallet moves only on `done`, one transaction | `_complete_task` | `test_full_task_moves_pallet` |
| SV-10 | WebSocket 2 Hz | `_broadcast_loop` | `test_ws_live_snapshot` |
| SF-05 | Connection loss → stop, wait | `_go_offline`, heartbeat timeout, SAFE until reset | `test_disconnect_requeues_unloaded_task` |
| SF-07 / SF-08 | Speed limits on all commands, raised-fork limit | `_drive`, `teleop` clamp | `test_manual_mode_teleop_clamped` |
| SF-11 / UI-07 | Stop all ≤ 1 s | `POST /api/fleet/estop` (effective next tick, ≤ 100 ms) + retained MQTT · always-visible button in dashboard and app | `test_fleet_estop_stops_everything` |
| SF-13 / UI-06 | Every safety event logged and shown | `events` table, `event` WS frames | several tests assert event codes |
| CM-01 | Broker auth per robot | `mosquitto.conf`, `acl` | manual |
| CM-03 | Last Will | `mqtt_bridge._handle` (`online:false`) | not yet (needs a robot client) |
| CM-04 | Timestamp + sequence on every message | `mqtt_bridge._drain` | not yet |
| CM-05 | JSON Schemas | `docs/schemas/` | — |
| NFR-09 | Add a robot by config only | `robots:` in `warehouse_map.yaml` (fl4 spare is defined but disabled) | `test_map_and_inventory` |
| UI-01..UI-10 | Dashboard screens | see [07-dashboard.md](07-dashboard.md) | dashboard Vitest suite |
