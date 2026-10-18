# المخزن الذكي وأسطول الرافعات الذاتية — Smart Warehouse & Autonomous Forklift Fleet

Graduation project: a 1:14-scale warehouse where three autonomous forklifts (+1 spare) move pallets between racks,
docks and staging without human help, supervised by a central server, a control-room dashboard and a floor app.

```
docs/                 everything written — start at docs/README.md
code/
  backend/            Fleet Manager + WMS + REST/WebSocket API + simulator (FastAPI)      ← runs today
  dashboard/          control-room web console (React + TypeScript)                       ← runs today
  landing/            public project website (React)                                      ← runs today
  mobile/             floor operator app (Flutter)                                        ← runs today
  firmware/           ESP32-S3 firmware (PlatformIO, FreeRTOS)                            ← host-tested, builds
  ros2_ws/            ROS 2 packages for the Jetson                                       ← host-tested
  training/           MuJoCo docking simulator + RL training                              ← runs today
```

## Quick start (no hardware needed)

```bash
# 1 — server with simulated robots → http://localhost:8000/docs
cd code/backend && python -m venv .venv && .venv/Scripts/pip install -r requirements-dev.txt
.venv/Scripts/python -m uvicorn app.main:app --port 8000

# 2 — dashboard → http://localhost:5173  (login: operator / see code/backend/.env.example)
cd code/dashboard && npm install && npm run dev

# 3 — landing page → http://localhost:5174
cd code/landing && npm install && npm run dev -- --port 5174

# 4 — floor app (emulator: server URL http://10.0.2.2:8000)
cd code/mobile && flutter pub get && flutter run
```

Each folder has its own README with details. What to do next: [plan.md](plan.md).
