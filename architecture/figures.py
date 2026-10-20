"""Designed diagrams for the architecture document (img/*.svg), all in one visual style.

Run:  python figures.py        (standard library only)
The system-context figure (img/system-context.svg) is drawn by hand; everything else is generated here.
"""

from __future__ import annotations

from pathlib import Path

OUT = Path(__file__).resolve().parent / "img"

INK, TEXT, MUTED, LINE = "#124A5A", "#3D4F58", "#5B6B73", "#DCE3E6"
AMBER, AMBER_BG = "#C98F12", "#FFF7E0"
RED, RED_BG = "#B23A2E", "#FBE7E4"
GREEN, GREEN_BG = "#2E8B57", "#E3F4EA"
BAND = {  # layer colours, same as the system-context figure
    "server": ("#E8F2F5", INK),
    "jetson": ("#F3F0FA", "#5B4A9A"),
    "esp": ("#FDF3E3", AMBER),
    "hw": ("#F4F6F6", "#7F8C8D"),
    "cloud": ("#EEF3FB", "#3B5B92"),
}


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class Fig:
    def __init__(self, w: int, h: int, title: str = ""):
        self.w, self.h, self.parts = w, h, []
        if title:
            self.text(w / 2, 30, title, 18, INK, "middle", 700)

    # --------------------------------------------------------------- primitives
    def text(self, x, y, s, size=13, fill=TEXT, anchor="start", weight=400, italic=False):
        st = ' font-style="italic"' if italic else ""
        self.parts.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" '
                          f'font-weight="{weight}" dominant-baseline="central"{st}>{esc(s)}</text>')

    def lines(self, x, y, rows, size=12, fill=TEXT, anchor="middle", gap=17):
        for i, r in enumerate(rows):
            self.text(x, y + i * gap, r, size, fill, anchor)

    def rect(self, x, y, w, h, fill="#fff", stroke=INK, sw=1.4, r=8, dash=""):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{r}" fill="{fill}" '
                          f'stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def band(self, x, y, w, h, kind, title, note=""):
        fill, stroke = BAND[kind]
        self.rect(x, y, w, h, fill, stroke, 1.5, 12)
        self.text(x + 16, y + 22, title, 15, stroke, "start", 700)
        if note:
            self.text(x + w - 16, y + 22, note, 12, MUTED, "end", 400, True)

    def box(self, x, y, w, h, title, rows=(), fill="#fff", stroke=INK, tsize=14, rsize=12, badge=""):
        self.rect(x, y, w, h, fill, stroke)
        n = len(rows)
        top = y + h / 2 - (n * 16) / 2 - (2 if n else -1)
        self.text(x + w / 2, top, title, tsize, stroke if stroke != "#fff" else INK, "middle", 700)
        for i, r in enumerate(rows):
            self.text(x + w / 2, top + 19 + i * 16, r, rsize, TEXT, "middle")
        if badge:
            bw = 8 + 6.6 * len(badge)
            self.rect(x + w - bw - 6, y - 9, bw, 18, AMBER, AMBER, 1, 9)
            self.text(x + w - bw / 2 - 6, y, badge, 11, "#fff", "middle", 700)

    def pill(self, x, y, w, h, label, fill, stroke, size=13, weight=700, color=None):
        self.rect(x, y, w, h, fill, stroke, 1.6, h / 2)
        self.text(x + w / 2, y + h / 2, label, size, color or stroke, "middle", weight)

    def arrow(self, pts, label="", lx=None, ly=None, color=INK, both=False, dash="", anchor="middle", lsize=11.5, sw=1.7):
        d = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts)
        mk = f'marker-end="url(#a{color[1:]})"' + (f' marker-start="url(#a{color[1:]})"' if both else "")
        ds = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{sw}" {mk}{ds}/>')
        if label:
            if lx is None:
                (x1, y1), (x2, y2) = pts[len(pts) // 2 - 1], pts[len(pts) // 2]
                lx, ly = (x1 + x2) / 2, (y1 + y2) / 2
            tw = 6.3 * len(label) + 8
            ax = lx - tw / 2 if anchor == "middle" else (lx - 4 if anchor == "start" else lx - tw + 4)
            self.parts.append(f'<rect x="{ax:.1f}" y="{ly - 9:.1f}" width="{tw:.1f}" height="18" rx="4" fill="#fff" opacity=".92"/>')
            self.text(lx, ly, label, lsize, color if color != INK else MUTED, anchor, 400, True)

    def svg(self) -> str:
        colors = {INK, AMBER, RED, GREEN, MUTED, "#5B4A9A", "#3B5B92"}
        marks = "".join(
            f'<marker id="a{c[1:]}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
            f'orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="{c}"/></marker>' for c in colors)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" '
                f'font-family="Segoe UI, Arial, sans-serif"><defs>{marks}</defs>'
                f'<rect width="{self.w}" height="{self.h}" fill="#fff"/>{"".join(self.parts)}</svg>')

    def save(self, name: str):
        OUT.mkdir(exist_ok=True)
        (OUT / f"{name}.svg").write_bytes(self.svg().encode("utf-8"))


# ======================================================================================== 3. hardware
def hardware():
    f = Fig(1000, 720, "One forklift — power, controllers, sensors")
    # power column
    f.band(20, 50, 300, 630, "hw", "Power")
    chain = [("2S Li-ion pack", "4 × 18650 (2S2P), 6.0–8.4 V"), ("BMS 2S 20 A", "cell protection"),
             ("Fuse 5 A", ""), ("Main switch", "")]
    y = 90
    for i, (t, r) in enumerate(chain):
        f.box(70, y, 200, 50 if r else 40, t, [r] if r else [], tsize=13)
        if i < len(chain) - 1:
            f.arrow([(170, y + (50 if r else 40)), (170, y + (50 if r else 40) + 22)])
        y += (50 if r else 40) + 22
    # INA219 tap
    f.box(40, 100, 0, 0, "")  # no-op spacer
    f.rect(232, 152, 80, 34, AMBER_BG, AMBER)
    f.text(272, 169, "INA219 V+I", 11.5, AMBER, "middle", 700)
    f.arrow([(270, 152), (270, 120), (272, 120)], dash="4 3", color=AMBER)
    sw_y = y - 22  # bottom of the main switch box
    # three branches
    f.arrow([(170, sw_y), (170, sw_y + 22)])
    f.parts.append(f'<line x1="74" y1="{sw_y + 22}" x2="272" y2="{sw_y + 22}" stroke="{INK}" stroke-width="1.7"/>')
    bx = [(30, "E-Stop (NC)", ["motor branch only"], RED_BG, RED), (134, "Buck 5.1 V", ["logic + sensors"], "#fff", INK),
          (228, "Boost 12 V", ["≥ 30 W, Jetson"], "#fff", INK)]
    for x, t, r, fill, st in bx:
        f.arrow([(x + 44, sw_y + 22), (x + 44, sw_y + 44)])
        f.box(x, sw_y + 44, 88 if x != 30 else 96, 52, t, r, fill=fill, stroke=st, tsize=12, rsize=10.5)
    f.box(40, sw_y + 130, 92, 52, "Motor drivers", ["PWM in"], tsize=12, rsize=10.5)
    f.arrow([(86, sw_y + 96), (86, sw_y + 130)], color=RED)
    f.box(40, sw_y + 210, 92, 40, "Drive motor", [], tsize=12)
    f.box(150, sw_y + 210, 92, 40, "Lift motor", [], tsize=12)
    f.arrow([(86, sw_y + 182), (86, sw_y + 210)])
    f.arrow([(110, sw_y + 182), (110, sw_y + 196), (196, sw_y + 196), (196, sw_y + 210)])
    f.text(500, 700, "The hardware E-Stop cuts the motors only: the ESP32 and Jetson stay powered and report why the forklift stopped", 12, RED, "middle", 400, True)

    # ESP32 + sensors
    f.band(340, 50, 300, 630, "esp", "Real-time controller")
    f.box(400, 322, 180, 76, "ESP32-S3", ["FreeRTOS, 2 cores", "1 kHz safety + PID"], fill=AMBER_BG, stroke=AMBER, badge="LAST SAFETY LAYER")
    sensors_l = [(360, 92, "6 × VL53L1X ToF", "I²C via TCA9548A mux"), (360, 160, "MPU9250 IMU", "I²C, 100 Hz"),
                 (360, 228, "AS5600 encoder", "I²C, drive axle")]
    for x, y, t, r in sensors_l:
        f.box(x, y, 124, 50, t, [r], tsize=12, rsize=10.5)
    sensors_r = [(496, 92, "Fork sensors", "pot · limits · TCRT"), (496, 160, "Steering servo", "PWM"),
                 (496, 228, "Status LEDs + buzzer", "WS2812")]
    for x, y, t, r in sensors_r:
        f.box(x, y, 130, 50, t, [r], tsize=12, rsize=10.5)
    for x in (422, 448, 474):
        pass
    f.arrow([(422, 278), (422, 322)], both=True)
    f.arrow([(560, 278), (560, 322)], both=True)
    f.text(491, 296, "I²C · GPIO · PWM · ADC", 11, MUTED, "middle", 400, True)
    # buck feeds esp, drivers get PWM
    f.arrow([(182, sw_y + 96), (182, sw_y + 112), (326, sw_y + 112), (326, 380), (400, 380)], "5.1 V", 352, sw_y + 112)
    f.arrow([(400, 366), (334, 366), (334, sw_y + 156), (132, sw_y + 156)], "PWM", 200, sw_y + 156, color=AMBER)

    # Jetson column
    f.band(660, 50, 320, 630, "jetson", "Computer")
    f.box(700, 314, 240, 76, "Jetson Orin Nano Super", ["ROS 2 Humble · 15 W mode", "8 GB · NVMe"], fill="#F3F0FA", stroke="#5B4A9A")
    f.box(700, 110, 110, 60, "RPLIDAR C1", ["USB, 10 Hz"], tsize=12, rsize=10.5)
    f.box(830, 110, 110, 60, "Camera", ["CSI, fork carriage"], tsize=12, rsize=10.5)
    f.box(760, 200, 120, 50, "Wi-Fi 5 GHz", ["to the server"], tsize=12, rsize=10.5)
    f.arrow([(755, 170), (755, 314)])
    f.arrow([(885, 170), (885, 314)])
    f.arrow([(820, 250), (820, 314)], both=True)
    f.arrow([(580, 352), (700, 352)], "USB · micro-ROS", 640, 336, both=True)
    f.arrow([(268, sw_y + 96), (268, sw_y + 260), (650, sw_y + 260), (650, 470), (820, 470), (820, 390)], "12 V", 740, 470)
    f.lines(820, 520, ["Jetson: everything heavy", "mapping · planning · vision · AI"], 12, "#5B4A9A")
    f.lines(491, 520, ["ESP32: everything with a deadline", "motors · steering · lift · stop sensors"], 12, AMBER)
    f.save("hardware")


# ======================================================================================== 4. firmware
def firmware():
    f = Fig(1000, 720, "ESP32-S3 firmware — two cores, one safety state machine")
    # cores
    f.band(20, 50, 470, 300, "esp", "Core 1 · real time", "hardware task watchdog 1 s")
    tasks1 = [("safety_task", "1 kHz", "E-Stop, ToF, fork, battery, link times → state machine → speed cap"),
              ("motor_pid_task", "1 kHz", "encoder → drive PID · Ackermann → servo · lift · odometry"),
              ("tof_task", "50 Hz", "6 × VL53L1X through the mux, re-init a dropped sensor")]
    for i, (n, r, d) in enumerate(tasks1):
        y = 90 + i * 84
        f.rect(40, y, 430, 68, "#fff", AMBER)
        f.text(56, y + 20, n, 13.5, INK, "start", 700)
        f.pill(380, y + 9, 76, 22, r, AMBER_BG, AMBER, 11.5)
        f.text(56, y + 46, d, 11.5, TEXT)
    f.band(510, 50, 470, 300, "hw", "Core 0 · communication")
    tasks0 = [("microros_task", "event", "ROS 2 topics to the Jetson, agent reconnect, gains"),
              ("imu_task", "100 Hz", "MPU9250 → bias removal → Madgwick filter"),
              ("status_task", "10 Hz", "INA219 → battery % · LED ring · buzzer")]
    for i, (n, r, d) in enumerate(tasks0):
        y = 90 + i * 84
        f.rect(530, y, 430, 68, "#fff", "#7F8C8D")
        f.text(546, y + 20, n, 13.5, INK, "start", 700)
        f.pill(870, y + 9, 76, 22, r, "#EEF1F1", "#7F8C8D", 11.5)
        f.text(546, y + 46, d, 11.5, TEXT)

    # state machine
    f.text(500, 372, "Safety state machine — checked every 1 ms, E-Stop first", 15, INK, "middle", 700)
    S = {"BOOT": (40, 470), "IDLE": (230, 470), "ACTIVE": (430, 470), "SLOW": (640, 410), "STOP": (640, 530),
         "SAFE": (230, 610), "ESTOP": (840, 610)}
    sty = {"BOOT": ("#EEF1F1", MUTED), "IDLE": ("#fff", INK), "ACTIVE": (GREEN_BG, GREEN), "SLOW": (AMBER_BG, AMBER),
           "STOP": (RED_BG, RED), "SAFE": (RED_BG, RED), "ESTOP": (RED, RED)}
    W, H = 120, 40
    for k, (x, y) in S.items():
        fill, st = sty[k]
        f.pill(x, y, W, H, k, fill, st, 13.5, 700, "#fff" if k == "ESTOP" else None)

    def c(k, dx=0.5, dy=0.5):
        x, y = S[k]
        return x + W * dx, y + H * dy

    f.arrow([c("BOOT", 1), c("IDLE", 0)], "drivers ready", 170, 458)
    f.arrow([(350, 482), (430, 482)], "fresh cmd_vel", 390, 466)
    f.arrow([(430, 498), (350, 498)], "stopped", 390, 514)
    f.arrow([(550, 476), (600, 430), (640, 430)], "ToF < 40 cm · forks up · docking", 520, 420, color=AMBER, anchor="end")
    f.arrow([(550, 500), (600, 550), (640, 550)], "ToF < 15 cm ahead", 610, 572, color=RED)
    f.arrow([(700, 450), (700, 530)], color=RED)
    f.arrow([c("IDLE", 0.5, 1), c("SAFE", 0.5, 0)], "watchdog · battery < 8 % · sensor fault", 290, 572, color=RED, anchor="start")
    f.arrow([(230, 630), (100, 630), (100, 510)], "cause gone 1 s", 150, 646)
    f.arrow([(680, 630), (840, 630)], "from ANY state", 760, 614, color=RED)
    f.text(900, 666, "E-Stop pressed", 12.5, RED, "middle", 700)
    f.text(980, 690, "latched: release + explicit reset → BOOT", 11.5, RED, "end", 400, True)
    f.lines(780, 440, ["while docking the three front", "ToF are ignored (they see the", "pallet) and speed is capped"], 11, AMBER, "start", 15)
    f.save("firmware")


# ======================================================================================== 5. ROS 2
def ros2():
    f = Fig(1000, 560, "Jetson — ROS 2 node graph (one forklift, namespace /fl1)")
    cols = [(20, "Sensors"), (215, "Perception + state"), (430, "Decision"), (655, "Safety"), (830, "Server · controller")]
    for x, t in cols:
        f.text(x + 85, 62, t, 13, MUTED, "middle", 700)
    P = "#5B4A9A"
    f.box(30, 90, 160, 50, "RPLIDAR C1", ["/scan 10 Hz"], tsize=13)
    f.box(30, 220, 160, 50, "Camera", ["/image_raw 30 fps"], tsize=13)
    f.box(30, 360, 160, 50, "ESP32 (micro-ROS)", ["odom · imu · tof · fork"], fill=AMBER_BG, stroke=AMBER, tsize=13)
    f.box(225, 80, 170, 70, "slam_toolbox", ["laser filter → map", "map → odom"], tsize=13)
    f.box(225, 170, 170, 46, "EKF", ["odom → base_link"], tsize=13)
    f.box(225, 236, 170, 60, "aruco_node", ["pallet_pose ≥ 20 Hz", "± 1 cm"], tsize=13)
    f.box(225, 316, 170, 46, "YOLO (TensorRT)", ["person · obstacle"], tsize=13)
    f.box(440, 70, 190, 96, "mission node", ["behaviour tree", "go → dock → lift → go → place", "MQTT fleet client"],
          fill="#F3F0FA", stroke=P, tsize=14)
    f.box(440, 196, 190, 60, "Nav2", ["Smac Hybrid-A* · RPP"], tsize=13)
    f.box(440, 276, 190, 60, "dock server", ["RL policy (ONNX) 20 Hz", "classical fallback"], tsize=13)
    f.box(440, 356, 190, 46, "lift server", ["height target"], tsize=13)
    f.box(665, 196, 160, 140, "safety supervisor", ["clamps every source", "0.3 m/s · 0.1 docking", "person < 0.5 m stop",
                                                     "server lost > 3 s"], fill=AMBER_BG, stroke=AMBER, tsize=13)
    f.box(845, 236, 135, 60, "ESP32", ["cmd_vel 20 Hz", "heartbeat 10 Hz"], fill=AMBER_BG, stroke=AMBER, tsize=13)
    # arrows
    f.arrow([(190, 115), (225, 115)])
    f.arrow([(190, 245), (225, 260)])
    f.arrow([(190, 250), (205, 250), (205, 339), (225, 339)])
    f.arrow([(190, 385), (210, 385), (210, 193), (225, 193)])
    f.arrow([(395, 115), (440, 115)], "map, pose", 418, 100)
    f.arrow([(395, 193), (420, 193), (420, 220), (440, 220)])
    f.arrow([(395, 266), (440, 300)], "pallet_pose", 418, 268)
    f.arrow([(535, 166), (535, 196)], "navigate", 568, 181)
    f.arrow([(470, 166), (470, 175), (430, 175), (430, 306), (440, 306)], "dock", 432, 236, anchor="end")
    f.arrow([(600, 166), (600, 180), (645, 180), (645, 379), (630, 379)], "lift", 655, 360, anchor="start")
    f.arrow([(630, 226), (665, 226)], "cmd_vel_nav", 648, 210)
    f.arrow([(630, 306), (665, 306)], "cmd_vel_dock", 648, 322)
    f.arrow([(395, 339), (410, 339), (410, 440), (745, 440), (745, 336)], "person distance", 580, 440)
    f.arrow([(825, 252), (845, 252)])
    f.arrow([(845, 282), (825, 282)])
    f.text(835, 220, "commands ↓", 11, MUTED, "middle", 400, True)
    f.text(835, 316, "tof, state ↑", 11, MUTED, "middle", 400, True)
    # MQTT
    f.box(845, 80, 135, 70, "Fleet server", ["MQTT over Wi-Fi", "(off the robot)"], fill="#E8F2F5", stroke=INK, tsize=13)
    f.arrow([(630, 98), (845, 98)], "task · cmd · estop · lane grant", 738, 98, both=True)
    f.text(738, 124, "state · task_status · event · lane request", 11, MUTED, "middle", 400, True)
    f.lines(30, 480, ["Teleop from the dashboard also enters", "through the mission node and the", "supervisor — no path skips the clamp."],
            11.5, AMBER, "start", 16)
    f.save("ros2")


# ======================================================================================== 6. server
def server():
    f = Fig(1000, 640, "Fleet server — inside the backend")
    f.box(120, 52, 200, 50, "Dashboard", ["React, browser"], tsize=13)
    f.box(360, 52, 200, 50, "Phone app", ["Flutter"], tsize=13)
    f.box(600, 52, 160, 50, "API docs", ["Swagger /docs"], tsize=13)
    f.band(20, 130, 760, 470, "server", "backend · FastAPI, one process")
    f.box(40, 168, 340, 64, "REST /api/*", ["JWT roles viewer · operator · admin", "{ data, meta } envelope, stable error codes"], tsize=13)
    f.box(400, 168, 360, 64, "WebSocket /ws/live", ["snapshot 2 Hz · task · inventory · event frames"], tsize=13)
    for x in (300, 460, 680):
        f.arrow([(x, 102), (x, 168)], both=True)
    f.text(308, 136, "HTTPS", 11, MUTED, "start", 400, True)
    f.text(468, 136, "HTTPS + WSS", 11, MUTED, "start", 400, True)
    # fleet manager
    f.rect(40, 262, 720, 172, "#fff", INK)
    f.text(56, 284, "Fleet manager — 10 Hz loop, owns the live fleet state", 14, INK, "start", 700)
    mods = [("Allocator", ["nearest · Hungarian", "switchable live"]), ("Lane graph", ["A*, never through", "a pick/drop spur"]),
            ("Traffic", ["node + lane locks", "deadlock detection"]), ("Policies", ["battery · E-stop", "teleop clamp · heartbeat"]),
            ("Simulator", ["fake robots", "+ scenarios"])]
    for i, (t, r) in enumerate(mods):
        f.box(56 + i * 140, 304, 128, 110, t, r, fill="#E8F2F5", tsize=13, rsize=11)
    f.arrow([(210, 232), (210, 262)], both=True)
    f.arrow([(580, 262), (580, 232)])
    f.text(590, 247, "push", 11, MUTED, "start", 400, True)
    # bottom row
    f.box(40, 470, 170, 66, "warehouse_map.yaml", ["lane graph · zones", "locations · robots"], fill=AMBER_BG, stroke=AMBER, tsize=12.5)
    f.box(240, 470, 230, 66, "PostgreSQL", ["WMS tables · Alembic", "robots saved every 2 s"], tsize=13)
    f.box(500, 470, 260, 66, "MQTT bridge (aiomqtt)", ["robot topics in → manager", "manager outbox → broker"], tsize=13)
    f.arrow([(125, 470), (125, 434)])
    f.arrow([(355, 470), (355, 434)], both=True)
    f.arrow([(630, 470), (630, 434)], both=True)
    f.text(400, 568, "A pallet's location changes only on the robot's 'done', in the same transaction as its inventory move.",
           12, INK, "middle", 400, True)
    # broker + robots
    f.box(805, 470, 175, 66, "Mosquitto", ["one login per robot", "ACL · retained E-stop"], tsize=13)
    f.arrow([(760, 503), (805, 503)], both=True)
    for i, rid in enumerate(("fl1", "fl2", "fl3")):
        f.box(825, 180 + i * 80, 135, 52, f"Forklift {rid}", ["Jetson + ESP32"], fill="#F3F0FA", stroke="#5B4A9A", tsize=12.5)
    f.arrow([(892, 470), (892, 392)], "Wi-Fi · MQTT", 892, 440, both=True)
    f.save("server")


# ======================================================================================== 7. MQTT
def mqtt():
    f = Fig(1000, 600, "Robot ↔ server topics (MQTT, JSON, schema-checked)")
    f.box(30, 60, 180, 470, "Fleet server", [], fill="#E8F2F5")
    f.box(790, 60, 180, 470, "Forklift {id}", [], fill="#F3F0FA", stroke="#5B4A9A")
    rows = [("wh/fl/{id}/state", "up", "QoS 0 · 2 Hz", "pose, battery, mode, task", None),
            ("wh/fl/{id}/task", "down", "QoS 1", "pallet, from / to, route", None),
            ("wh/fl/{id}/task_status", "up", "QoS 1", "accepted → … → done / failed", None),
            ("wh/fl/{id}/cmd", "down", "QoS 1", "pause · resume · charge · reset · cancel", None),
            ("wh/fl/{id}/teleop", "down", "QoS 0 · ≤ 10 Hz", "manual drive, already clamped", None),
            ("wh/fl/{id}/event", "up", "QoS 1", "safety and error events", None),
            ("wh/traffic/{from}--{to}", "both", "QoS 1", "request · grant · deny · release", AMBER),
            ("wh/fleet/estop", "down", "QoS 1 · RETAINED", "every robot, also on reconnect", RED)]
    for i, (topic, d, qos, note, col) in enumerate(rows):
        y = 112 + i * 52
        c = col or INK
        pts = [(210, y), (790, y)] if d != "up" else [(790, y), (210, y)]
        f.arrow(pts, color=c, both=(d == "both"), sw=2 if col else 1.7)
        f.text(250, y - 13, topic, 12.5, c, "start", 700)
        f.text(780, y + 13, note, 11.5, MUTED, "end", 400, True)
        f.pill(630, y - 25, 140, 20, qos, "#fff" if not col else (AMBER_BG if col == AMBER else RED_BG), c, 11)
    f.lines(120, 548, ["subscribes wh/fl/+/…", "and wh/traffic/#"], 11.5, MUTED, "middle", 16)
    f.lines(880, 548, ["Last Will on state:", '{"online": false}'], 11.5, MUTED, "middle", 16)
    f.lines(500, 548, ["Every message carries seq + UTC ts · no anonymous access",
                       "a robot may publish only its own topics (per-robot login + ACL)"], 11.5, INK, "middle", 16)
    f.save("mqtt")


# ======================================================================================== 8. task flow
def task_flow():
    f = Fig(1000, 780, "One pallet move, end to end")
    lanes = [("Operator", 90, "#fff", INK), ("Dashboard", 270, "#fff", INK), ("Fleet server", 470, "#E8F2F5", INK),
             ("MQTT broker", 670, "#fff", MUTED), ("Forklift fl1", 870, "#F3F0FA", "#5B4A9A")]
    for n, x, fill, st in lanes:
        f.box(x - 75, 50, 150, 40, n, [], fill=fill, stroke=st, tsize=13.5)
        f.parts.append(f'<line x1="{x}" y1="90" x2="{x}" y2="760" stroke="{st}" stroke-width="1.2" stroke-dasharray="5 5"/>')
    X = {n: x for n, x, _, _ in lanes}
    k = [0]

    def num(x, y):
        k[0] += 1
        f.parts.append(f'<circle cx="{x}" cy="{y}" r="10" fill="{INK}"/>')
        f.text(x, y, str(k[0]), 11, "#fff", "middle", 700)

    def msg(a, b, y, label, color=INK, dash=""):
        xa, xb = X[a], X[b]
        f.arrow([(xa, y), (xb + (-6 if xb > xa else 6), y)], color=color, dash=dash)
        lx = (xa + xb) / 2
        f.parts.append(f'<rect x="{lx - 3.3 * len(label) - 6:.1f}" y="{y - 22}" width="{6.6 * len(label) + 12:.1f}" height="17" fill="#fff"/>')
        f.text(lx, y - 13, label, 12, color, "middle")
        num(min(xa, xb) - 14, y)

    def note(lane, y, label, fill="#FFF7E0", stroke=AMBER, w=None):
        w = w or 7 * len(label) + 20
        x = X[lane] - w / 2
        x = min(x, 990 - w)
        f.rect(x, y - 14, w, 28, fill, stroke, 1.3, 6)
        f.text(x + w / 2, y, label, 12, stroke, "middle", 700)
        num(x - 14, y)

    msg("Operator", "Dashboard", 120, "move pallet 7 to DOCK-OUT-1")
    msg("Dashboard", "Fleet server", 162, "POST /api/tasks")
    note("Fleet server", 202, "reserve pallet · allocator picks fl1 · A* route", "#E8F2F5", INK, 330)
    msg("Fleet server", "Forklift fl1", 248, "wh/fl/fl1/task")
    msg("Forklift fl1", "Fleet server", 290, "task_status: accepted")
    # loop box
    f.rect(400, 318, 590, 178, "none", AMBER, 1.5, 8, "6 4")
    f.rect(400, 318, 190, 22, AMBER, AMBER, 1, 6)
    f.text(495, 329, "loop · every lane on the route", 11.5, "#fff", "middle", 700)
    msg("Forklift fl1", "Fleet server", 366, "traffic request A21--J2", AMBER)
    msg("Fleet server", "Forklift fl1", 408, "grant: lane + far node locked", AMBER)
    note("Forklift fl1", 446, "Nav2 drives the lane", w=170)
    f.text(870, 470, "supervisor + ESP32 cap the speed", 11, MUTED, "middle", 400, True)
    msg("Forklift fl1", "Fleet server", 486, "release", AMBER)
    note("Forklift fl1", 534, "ArUco → RL docking → lift", w=200)
    msg("Forklift fl1", "Fleet server", 578, "task_status: picking … dropping")
    msg("Forklift fl1", "Fleet server", 620, "task_status: done", GREEN)
    note("Fleet server", 662, "ONE transaction: pallet location + inventory move + task done", GREEN_BG, GREEN, 440)
    msg("Fleet server", "Dashboard", 710, "WebSocket: task · inventory · map", INK, "6 4")
    f.text(500, 748, "Robot ↔ server arrows pass through the broker; the server never talks to a robot directly.", 12, MUTED,
           "middle", 400, True)
    f.save("task-flow")


# ======================================================================================== 9. safety
def safety():
    f = Fig(1000, 640, "Safety — four independent layers, the lowest one always wins")
    rows = [
        ("server", "1 · Fleet server", "warehouse-wide",
         ["STOP ALL → retained E-stop, every robot holds zero speed", "battery low → go charge · critical → safe stop",
          "no state for 3 s → offline, unlifted task re-queued", "one robot per lane and node · teleop clamp + dead-man"],
         "next MQTT message", "#E8F2F5", INK),
        ("jetson", "2 · Jetson supervisor", "per robot, software",
         ["clamps Nav2, RL policy and teleop alike", "0.3 m/s · 0.1 m/s with forks > 5 cm or docking",
          "person (YOLO) < 1 m slow · < 0.5 m stop", "server lost > 3 s → finish the step, then stop"],
         "20 Hz command loop", "#F3F0FA", "#5B4A9A"),
        ("esp", "3 · ESP32 safety loop", "per robot, real time",
         ["ToF ahead < 40 cm slow · < 15 cm stop", "heartbeat missing → SAFE, motors stop (≈ 560 ms, ≤ 600 ms required)",
          "battery < 8 % · sensor fault → SAFE", "safety output > 5 ms old → motor task brakes · watchdog 1 s"],
         "1 kHz, every 1 ms", AMBER_BG, AMBER),
        ("hw", "4 · Hardware E-Stop", "per robot, no software",
         ["normally-closed button in the motor power branch", "cuts the motors; Jetson and ESP32 stay on and report",
          "latched: release + explicit reset to drive again", ""],
         "instant", RED_BG, RED),
    ]
    for i, (kind, title, sub, trig, react, fill, st) in enumerate(rows):
        y = 56 + i * 140
        f.rect(80, y, 900, 124, fill, st, 1.6, 12)
        f.text(100, y + 26, title, 15.5, st, "start", 700)
        f.text(100, y + 48, sub, 12, MUTED, "start", 400, True)
        for j, t in enumerate(trig):
            if t:
                f.parts.append(f'<circle cx="{318}" cy="{y + 30 + j * 22}" r="3" fill="{st}"/>')
                f.text(328, y + 30 + j * 22, t, 12.5, TEXT)
        f.pill(820, y + 46, 144, 30, react, "#fff", st, 12)
        if i < 3:
            f.arrow([(48, y + 62), (48, y + 140 + 62)], color=st)
    f.text(48, 40, "commands", 11, MUTED, "middle", 400, True)
    f.parts.append(f'<circle cx="48" cy="118" r="6" fill="{INK}"/>')
    f.text(530, 626, "Every command, from the dashboard, Nav2, the RL policy or the gamepad, passes every layer below it. "
           "A lower layer never trusts the one above.", 12, INK, "middle", 400, True)
    f.save("safety")


# ======================================================================================== 10. AI
def ai():
    f = Fig(1000, 700, "Docking AI — from simulation to the robot")
    P = "#5B4A9A"
    f.band(20, 50, 960, 168, "hw", "Training (laptop, simulation)")
    steps = [("MuJoCo env", ["1:14 forklift + pallet", "randomised friction, delay,", "marker noise, load"]),
             ("Imitation", ["clone the classical", "controller first"]),
             ("Conservative PPO", ["lr 3·10⁻⁵ · clip 0.1", "target KL 0.01"]),
             ("Checkpoint pick", ["best on validation seeds", "(625 k steps)"])]
    for i, (t, r) in enumerate(steps):
        x = 40 + i * 236
        f.box(x, 86, 200, 112, t, r, tsize=13.5, rsize=11.5)
        if i < 3:
            f.arrow([(x + 200, 142), (x + 236, 142)])
    f.band(20, 236, 960, 140, "jetson", "On the robot (Jetson)")
    steps2 = [("ONNX export", ["→ TensorRT FP16"]), ("dock server", ["policy at 20 Hz", "ArUco pallet pose in"]),
              ("safety supervisor", ["caps 0.1 m/s while docking"]), ("ESP32", ["1 kHz safety loop"])]
    for i, (t, r) in enumerate(steps2):
        x = 40 + i * 236
        st = AMBER if i >= 2 else P
        f.box(x, 272, 200, 84, t, r, fill=AMBER_BG if i >= 2 else "#fff", stroke=st, tsize=13.5, rsize=11.5)
        if i < 3:
            f.arrow([(x + 200, 314), (x + 236, 314)])
    f.arrow([(848, 198), (848, 228), (224, 228), (224, 272)], color=MUTED)

    # results
    f.text(40, 410, "Result on 1000 randomised episodes (with the safety supervisor)", 15, INK, "start", 700)

    def bars(x0, y0, label, items, vmax, unit, fmt):
        f.text(x0, y0, label, 13, TEXT, "start", 700)
        for j, (name, v, col) in enumerate(items):
            y = y0 + 22 + j * 40
            f.text(x0, y + 12, name, 12, TEXT)
            w = 260 * v / vmax
            f.rect(x0 + 150, y, w, 24, col, col, 1, 4)
            f.text(x0 + 158 + w, y + 12, fmt(v) + unit, 13, col, "start", 700)

    bars(40, 440, "Docked", [("classical controller", 90.0, "#8FA3AB"), ("RL policy", 98.7, GREEN)], 100, " %",
         lambda v: f"{v:g}")
    bars(520, 440, "Mean time to dock", [("classical controller", 10.3, "#8FA3AB"), ("RL policy", 6.5, GREEN)], 11, " s",
         lambda v: f"{v:g}")
    f.text(40, 548, "Collisions: 0 % classical, 1.3 % RL — the classical controller stays as the fallback.", 12, MUTED,
           "start", 400, True)
    f.rect(40, 576, 940, 100, "#E8F2F5", INK, 1.4, 10)
    f.text(60, 600, "Task allocation (fleet server)", 14, INK, "start", 700)
    f.text(60, 626, "Hungarian (optimal assignment) vs nearest robot · 270 runs, 15 seeds, 2–4 robots, 3 task rates", 12.5, TEXT)
    f.text(60, 652, "Same at low load; when the fleet is saturated, Hungarian moves 53–67 % more tasks per hour.", 12.5, TEXT)
    f.pill(830, 612, 130, 30, "+53–67 % tasks/h", "#fff", GREEN, 13)
    f.save("ai")


# ======================================================================================== 12. deployment
def deployment():
    f = Fig(1000, 600, "Two ways to run it")
    C = "#3B5B92"
    f.band(20, 50, 560, 500, "cloud", "Railway — online demo", "simulator drives the fleet")
    f.box(40, 96, 150, 50, "Browser", [], fill="#fff", stroke=MUTED, tsize=13)
    f.box(410, 96, 150, 50, "Phone app", [], fill="#fff", stroke=MUTED, tsize=13)
    f.box(40, 196, 150, 60, "landing", ["nginx, strict CSP"], tsize=13)
    f.box(215, 196, 150, 60, "dashboard", ["static build"], tsize=13)
    f.rect(40, 296, 520, 230, "#F7F9FC", C, 1.3, 10, "6 4")
    f.text(56, 316, "private network", 12, C, "start", 700)
    f.box(195, 330, 170, 66, "backend", ["FastAPI · /api/health"], fill="#E8F2F5", tsize=13.5)
    f.box(60, 440, 150, 60, "Postgres", ["volume"], tsize=13)
    f.box(380, 440, 160, 66, "Mosquitto", ["TCP proxy + WSS", "per-robot logins"], tsize=13)
    f.arrow([(80, 146), (80, 196)])
    f.arrow([(160, 146), (160, 170), (290, 170), (290, 196)])
    f.arrow([(290, 256), (290, 330)], "HTTPS + WSS", 290, 285)
    f.arrow([(485, 146), (485, 300), (340, 300), (340, 330)])
    f.arrow([(230, 396), (135, 396), (135, 440)], both=True)
    f.arrow([(365, 363), (460, 363), (460, 440)], both=True)
    f.text(280, 570, "Push to main → that service redeploys · secrets only in Railway variables", 12, MUTED, "middle", 400, True)

    f.band(600, 50, 380, 500, "hw", "Warehouse LAN — live demo")
    f.box(630, 100, 320, 80, "Laptop (server)", ["backend + Mosquitto · docker compose", "dashboard in the browser"],
          fill="#E8F2F5", tsize=13.5)
    f.box(710, 230, 160, 56, "Router", ["Wi-Fi 5 GHz"], tsize=13)
    f.arrow([(790, 180), (790, 230)], both=True)
    for i, rid in enumerate(("fl1", "fl2", "fl3")):
        x = 630 + i * 112
        f.box(x, 360, 96, 64, rid, ["Jetson", "+ ESP32"], fill="#F3F0FA", stroke="#5B4A9A", tsize=13.5, rsize=11)
        f.arrow([(790, 286), (790, 320), (x + 48, 320), (x + 48, 360)], both=True)
    f.box(690, 460, 200, 56, "Phones", ["STOP ALL, alerts, drive"], fill="#fff", stroke=MUTED, tsize=13)
    f.arrow([(870, 258), (930, 258), (930, 488), (890, 488)], both=True)
    f.text(790, 570, "Low latency, no internet needed", 12, MUTED, "middle", 400, True)
    f.save("deployment")


if __name__ == "__main__":
    hardware()
    firmware()
    ros2()
    server()
    mqtt()
    task_flow()
    safety()
    ai()
    deployment()
    print("written to", OUT)
