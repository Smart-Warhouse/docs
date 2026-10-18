# Defence demo script — 7–8 minutes

<!-- Commands from backend/README.md, dashboard/README.md, mobile/README.md, landing/README.md.
     Scenario names from docs/02-api-contract.md (POST /api/sim/scenario) and docs/06-backend.md. -->

**Date / room:** [DATE] · [ROOM] · **Projector:** [RESOLUTION / INPUT]

## Roles

| Role | Who | Device | Does |
|---|---|---|---|
| **Presenter** | [TEAM MEMBER 1] | clicker | Talks, drives the slide deck |
| **Driver (laptop)** | [TEAM MEMBER 2] | demo laptop = server, signed in as `admin` | Big screen: kiosk and dashboard, Simulator panel |
| **Floor operator** | [TEAM MEMBER 3] | Android phone with SW Floor, signed in as `operator` | Phone mirrored on the screen (scrcpy) or shown to the committee |
| **Backup / forklift** | [TEAM MEMBER 4] | spare laptop with the same checkout + the forklift (if it runs) | Watches the forklift, ready with the fallback laptop and the videos |

Passwords for `admin` / `operator` / `viewer` are in `backend/.env.example` (`SEED_*_PASSWORD`). Do not show
them on the projector.

---

## Running order (≈ 7 min 30 s)

| Time | Who | Screen | Action | Say |
|---|---|---|---|---|
| 0:00–0:30 | Presenter | Kiosk (`/ar/kiosk`), dark | Kiosk already running with live traffic (`sim_auto_tasks_per_min` = 2) | «هذا المخزن مباشرةً: ثلاث رافعات، كل لون مسار محجوز لرافعة واحدة.» — three forklifts, each coloured lane is reserved for one robot. |
| 0:30–1:30 | Driver | Dashboard → **Tasks** | Create a task: pick a pallet on R1, destination `DOCK-OUT-1`, priority 3 → *Create*. Switch to **Live map**; point at the robot that takes it and its reserved segments | Allocation picks the robot (Hungarian), lanes are locked all-or-nothing, WMS moves the pallet only on `done`. |
| 1:30–2:15 | Floor operator | Phone → **Move a pallet** | Create a second task from the phone (search the pallet by ArUco id). Show it appear on the big screen | Same server, two clients; the phone is for people in the aisle. |
| 2:15–3:00 | Driver | **Settings → Simulator** | Press **person** for `fl1` | fl1 stops at once and continues after 4 s; the event appears in the log and as a red alert on the phone. |
| 3:00–3:40 | Driver | Simulator | Press **disconnect** for `fl2` | fl2 goes offline → safe stop; its unlifted task is re-queued to another forklift. Then **Reset** fl2 from the Fleet screen. |
| 3:40–4:10 | Driver | Simulator | Press **drain battery** for `fl3` | fl3 refuses new tasks and drives to a charger by itself. |
| 4:10–4:50 | Floor operator | Phone | **Press and hold STOP ALL (1 s)** | The whole fleet freezes within one tick; dashboard shows the red banner; phone turns red. Driver **releases** from the dashboard after the confirm. |
| 4:50–6:20 | Presenter | Video `docs/media/rl-docking-simulation.mp4` (40 s, full screen) | Play; pause on the HUD | Plain PPO: 0 %. Curriculum: 0 %. Imitation + PPO: **98.6 %** vs classical **90 %**, **6.4 s** vs **10.3 s** on 1000 simulated episodes. Real comparison (T-12) is planned. |
| 6:20–7:00 | Driver | Dashboard → **Analytics** | 24 h range: tasks per hour, utilisation, congestion heat map; Events screen | Every safety event is logged with robot, time and position. |
| 7:00–7:30 | Presenter | Kiosk / last slide | Back to the kiosk; close | What is next: the hardware phases T-01 … T-16. |

**Live forklift (only if phases 1–5 have passed):** replace 1:30–2:15 with a real task for the real forklift
(`simulated: false` for that robot in the map file, MQTT on). Keep the simulated robots for the other two.
If anything looks wrong with it, the backup person presses its **hardware E-Stop** and the driver continues with the
simulator — say so calmly: "this is exactly what the hardware layer is for".

---

## Start every service

Run in this order on the demo laptop, one terminal each. The laptop is the server; phone and laptop must be on the
same Wi-Fi (or the laptop's hotspot).

**1. Server (FastAPI + simulator, SQLite).** `--host 0.0.0.0` so the phone can reach it.

```bash
cd backend
```

```bash
.venv/Scripts/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Check: http://localhost:8000/docs opens (Swagger). For a clean start, stop the server and delete `warehouse.db` first
(it reseeds the map, pallets and users).

**2. Dashboard.**

```bash
cd dashboard
```

```bash
npm run dev
```

Open http://localhost:5173 → sign in as `admin` → kiosk at http://localhost:5173/ar/kiosk (second browser window on the
projector, F11 for full screen). The dashboard reads `VITE_API_BASE_URL` from `dashboard/.env`
(default `http://localhost:8000`).

**3. Continuous demo traffic** (as admin; or the Settings page fields):

```bash
curl -X PATCH http://localhost:8000/api/settings -H "Authorization: Bearer <admin token>" -H "Content-Type: application/json" -d "{\"sim_auto_tasks_per_min\": 2}"
```

[CHECK: the README describes this as `PATCH /api/settings {"sim_auto_tasks_per_min": 2}`; doing it from the dashboard's
Settings page is simpler and avoids pasting a token.]

**4. Floor app** — on the phone (installed build) or from the laptop:

```bash
cd mobile
```

```bash
flutter run
```

On the sign-in screen enter `http://<laptop LAN IP>:8000`, press the plug icon (health check), sign in as `operator`.
Mirror the phone with scrcpy if the committee should see it on the big screen [CHECK: install scrcpy on the demo
laptop beforehand].

**5. Landing page (optional, for the opening or Q&A):**

```bash
cd landing
```

```bash
npm run dev
```

http://localhost:5180

**6. Real forklift (only if hardware is ready):** Mosquitto with per-robot users (`docker compose up` in
`backend`, see its README), `MQTT_ENABLED=true` in `backend/.env`, the forklift's `simulated: false` in
`backend/app/warehouse_map.yaml`, then power the forklift and wait for it to appear online on the Fleet screen.
[CHECK: write the forklift bring-up command here once `forklift_bringup` runs on the Jetson.]

**Simulator scenarios by API** (if the Settings page misbehaves):

```bash
curl -X POST http://localhost:8000/api/sim/scenario -H "Authorization: Bearer <admin token>" -H "Content-Type: application/json" -d "{\"action\": \"person\", \"robot_id\": \"fl1\"}"
```

Actions: `person`, `obstacle`, `drain_battery`, `disconnect`, `random_tasks` (with `count`).

---

## Pre-flight checklist (T − 60 min)

- [ ] Laptop on mains power; sleep, screen saver and OS updates disabled; notifications off (Focus mode).
- [ ] `git status` clean on the demo commit; note the commit hash on paper.
- [ ] Delete `backend/warehouse.db`, start the server, confirm `/docs` opens.
- [ ] Dashboard: signed in as `admin` in one window, kiosk in another on the projector; theme dark; language Arabic.
- [ ] Browser zoom so the whole map fits at the projector resolution; F11 full screen tested.
- [ ] Demo traffic on (`sim_auto_tasks_per_min` 2) for at least 10 min before the start, so Analytics has data.
- [ ] Phone: charged, Wi-Fi on the demo network, app signed in as `operator`, "test connection" green, vibration on,
      do-not-disturb off for the app.
- [ ] Pallet for the live task chosen in advance (its ArUco id written down) and its destination free.
- [ ] Videos copied locally and tested in the player: `docs/media/rl-docking-simulation.mp4`,
      `docs/media/simulation-walkthrough.mp4`, `docs/media/dashboard-live-10s.mp4`.
- [ ] Slide deck opened and tested on the projector (link in the deck section of the report), offline PDF export as a
      backup on a USB stick.
- [ ] Backup laptop: same commit, server + dashboard started, signed in, on the same network.
- [ ] HDMI + USB-C adapters, clicker batteries, phone cable, power strip.
- [ ] If the forklift runs: battery full, E-Stop tested, floor clear, markers in place, one dry run done.
- [ ] One full rehearsal with a stopwatch: ≤ 8 min.

---

## Fallback plan

| Failure | Sign | Do this | Say |
|---|---|---|---|
| **Wi-Fi down** | Phone shows "Reconnecting", phone cannot reach server | Driver switches the phone to the laptop hotspot (pre-saved), re-enter `http://<hotspot IP>:8000`. If it takes > 30 s, skip the phone steps and do STOP ALL from the dashboard instead. | "The server keeps running locally; the robots would finish their lane and stop — that is SF-05." |
| **Forklift misbehaves** | Wrong direction, stuck, unsafe | Backup person presses the **hardware E-Stop**; driver sets it disabled / continues with simulated robots only | "The hardware layer stopped it without software. We continue in the simulator, which runs the same fleet logic." |
| **Server crash** | Dashboard "Disconnected", 5xx | Restart uvicorn (command above, ≈ 5 s). If it fails twice, move the projector to the backup laptop | — |
| **Dashboard blank / login loop** | White page or back to login | Reload; clear site data; sign in again; else backup laptop | — |
| **Projector issue** | No image / wrong resolution | Try the other input / adapter; duplicate (not extend) the display; if still broken, present from the laptop screen turned to the committee and use the PDF deck | — |
| **Live demo fails completely** | Anything not recoverable in 30 s | Play `docs/media/simulation-walkthrough.mp4` (42 s: simulator panel → allocation and lane locks → person stop → battery → lost connection → event log) then `docs/media/dashboard-live-10s.mp4` | "This is a recording of the same scenarios from the same build." |
| **Video will not play** | Player error | Open the MP4 in the browser (drag the file into a tab); the deck also embeds the docking clip | — |
| **Over time** | Presenter at 6:30 before the docking video | Skip Analytics; go straight to the video and close | — |

---

## Q&A crib (numbers and where they come from)

| Claim | Number | Source |
|---|---|---|
| Docking success, RL vs classical (simulation, 1000 episodes) | 98.6 % vs 90.0 % | docs/11-simulation-training.md §4 |
| Docking time | 6.4 s vs 10.3 s | same |
| RL collisions in simulation | 1.4 % (caught by ToF ring + supervisor on the robot) | same |
| Allocation (simulator, preliminary) | Hungarian ≈ 300 vs nearest ≈ 210 tasks/h | docs/06-backend.md |
| Watchdog | SAFE at 501 ms, v = 0 by ≤ 600 ms (host model) | docs/12-firmware.md §6 |
| Tests | 485 host tests + 134 colcon tests, 9 CI jobs green | docs/thesis/06-software-verification.md |
| Parts per forklift | 1,507,250 IQD | landing/src/content/bom.ts |
| Hardware tests T-01 … T-16 | planned | docs/thesis/07-hardware-validation-plan.md |
