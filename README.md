# المخزن الذكي وأسطول الرافعات الذاتية — Smart Warehouse & Autonomous Forklift Fleet

Graduation project: a 1:14-scale warehouse where three autonomous forklifts (+1 spare) move pallets between racks,
docks and staging without human help, supervised by a central server, a control-room dashboard and a floor app.

This repo holds the documentation, the plan and the brand kit. The code lives in sibling repos of the
[Smart-Warhouse](https://github.com/Smart-Warhouse) organization:

| Repo | What | Stack |
|---|---|---|
| [docs](https://github.com/Smart-Warhouse/docs) | requirements, architecture, API + MQTT contracts (+ JSON Schemas), design system, thesis drafts, media, brand kit, [plan.md](plan.md) | Markdown |
| [backend](https://github.com/Smart-Warhouse/backend) | Fleet Manager + WMS + REST/WebSocket API + simulator; `integration/` fleet tests over Mosquitto; `experiments/` allocation study | FastAPI, SQLAlchemy, Alembic |
| [dashboard](https://github.com/Smart-Warhouse/dashboard) | control-room web console (live map, tasks, analytics, manual control, kiosk) | React 19, TypeScript, Vite |
| [landing](https://github.com/Smart-Warhouse/landing) | public project website | React 19, Vite, Tailwind |
| [mobile](https://github.com/Smart-Warhouse/mobile) | floor operator app (stop-all, alerts, fleet, tasks, manual drive) | Flutter |
| [robot](https://github.com/Smart-Warhouse/robot) | `firmware/` ESP32-S3 · `ros2_ws/` ROS 2 Humble packages + Gazebo twin · `cad/` 3D-printable mounts | C++/FreeRTOS, ROS 2, CadQuery |
| [ai](https://github.com/Smart-Warhouse/ai) | `training/` MuJoCo docking simulator + imitation/PPO policy · `vision/` YOLO pipeline | MuJoCo, SB3, Ultralytics |

## Workspace layout

Some tests and tools read files from a sibling repo (the robot plans on the backend's lane graph, the ROS 2
contract tests check the MQTT schemas in this repo, the RL tests replay the firmware's safety limiter, …).
They expect all repos **side by side in one folder** — clone them with:

```bash
mkdir smart-warhouse && cd smart-warhouse
for r in docs backend dashboard landing mobile robot ai; do git clone https://github.com/Smart-Warhouse/$r.git; done
```

```
smart-warhouse/
  docs/  backend/  dashboard/  landing/  mobile/  robot/  ai/
```

A different layout works too: set `SW_WORKSPACE` to the folder that holds the repos. CI does the same — each job
checks out the siblings it needs next to its own repo.

## Quick start (no hardware needed)

```bash
# 1 — server with simulated robots → http://localhost:8000/docs
cd backend && python -m venv .venv && .venv/Scripts/pip install -r requirements-dev.txt
.venv/Scripts/python -m uvicorn app.main:app --port 8000

# 2 — dashboard → http://localhost:5173  (login: operator / see backend/.env.example)
cd dashboard && npm install && npm run dev

# 3 — landing page → http://localhost:5174
cd landing && npm install && npm run dev -- --port 5174

# 4 — floor app (emulator: server URL http://10.0.2.2:8000)
cd mobile && flutter pub get && flutter run
```

Docs index: [INDEX.md](INDEX.md). What to do next: [plan.md](plan.md).

History: until 2026-10-18 everything lived in one repository (`AhmedITD/smart-warehouse-fleet`); each repo here
keeps the history of its own folders.
