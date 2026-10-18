# 04 — Data model (WMS)

Tables follow requirements §11 "WMS — قاعدة البيانات"; defined in `backend/app/models.py`. Tables are created
on server start (`create_all`); for schema changes after the first real deployment, add Alembic.

| Table | Key fields | Notes |
|---|---|---|
| `locations` | id, code (`R1-W1-L2`), type (rack/dock_in/dock_out/staging/charge), x, y, yaw, level, height_mm, aruco_id, **node_id**, occupied | `node_id` ties the location to its spur node on the lane graph; both levels of a rack slot share a node and an ArUco marker |
| `pallets` | id, aruco_id (unique, 1–20), sku → products, quantity, weight_g, location_id, status (stored/reserved/in_transit) | `reserved` while a task is queued/assigned |
| `products` | sku, name, category | |
| `robots` | id, name, ip, status, battery_pct, x, y, yaw, current_task_id, last_seen | live state is in memory; this row is persisted every 2 s |
| `tasks` | id (`T-0042`), type, pallet_id, from_location, to_location, robot_id, priority (1–5), status, route (JSON), distance_m, wait_s, created_by, created_at, started_at, finished_at, fail_reason | status: queued → to_pickup → picking → to_drop → dropping → done / failed / cancelled |
| `events` | id, robot_id, type (safety/error/info), severity (info/warning/critical), code, message, x, y, created_at | SF-13 |
| `inventory_moves` | id, pallet_id, from_location, to_location, task_id, moved_at | written in the same transaction as the pallet move (SV-09) |
| `traffic_waits` | id, robot_id, segment_id, wait_s, created_at | added for the congestion heat map (UI-05) |
| `users` | id, username, name, role (admin/operator/viewer), password_hash (bcrypt) | SV-07 |
| `settings` | key, value (JSON) | runtime settings (§3.2 of the API contract) |

## Lane graph (`backend/app/warehouse_map.yaml`)

6 m × 4 m floor; bottom corridor y = 0.6, top corridor y = 3.4, three aisles at x = 1.0 / 3.0 / 5.0, two racks
(R1, R2) with 4 faces × 2 slots × 2 levels = 16 rack locations, 2 inbound docks, 2 outbound docks, 2 staging spots,
4 chargers (one per robot incl. the spare). **All coordinates are placeholders — re-measure on the real floor
(EN-01, EN-08) and update the YAML; nothing else needs to change.**
