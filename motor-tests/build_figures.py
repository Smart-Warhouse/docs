"""Wiring diagrams for the motor measurement guide (img/*.svg). Standard library only: python build_figures.py"""
from pathlib import Path

OUT = Path(__file__).resolve().parent / "img"
INK, TEXT, MUTED = "#124A5A", "#3D4F58", "#5B6B73"
RED, RED_BG, AMBER, AMBER_BG, GREEN, GREEN_BG = "#B23A2E", "#FBE7E4", "#C98F12", "#FFF7E0", "#2E8B57", "#E3F4EA"
WIRE_P, WIRE_N = "#C0392B", "#222"


class S:
    def __init__(self, w, h, title):
        self.w, self.h, self.p = w, h, []
        self.t(w / 2, 28, title, 17, INK, "middle", 700)

    def t(self, x, y, s, size=13, fill=TEXT, anchor="start", weight=400, italic=False):
        it = ' font-style="italic"' if italic else ""
        s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        self.p.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" font-weight="{weight}" dominant-baseline="central"{it}>{s}</text>')

    def r(self, x, y, w, h, fill="#fff", stroke=INK, rx=8, sw=1.5, dash=""):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.p.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def wire(self, pts, color=WIRE_P, sw=3):
        d = "M" + " L".join(f"{x} {y}" for x, y in pts)
        self.p.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{sw}" stroke-linejoin="round"/>')

    def dot(self, x, y, c=INK):
        self.p.append(f'<circle cx="{x}" cy="{y}" r="4" fill="{c}"/>')

    def motor(self, x, y, label="M", sub=""):
        self.p.append(f'<circle cx="{x}" cy="{y}" r="34" fill="#EEF1F1" stroke="{INK}" stroke-width="2"/>')
        self.t(x, y, label, 22, INK, "middle", 700)
        if sub:
            self.t(x, y + 50, sub, 12, MUTED, "middle")

    def battery(self, x, y, label):
        self.r(x, y, 90, 120, "#FDF3E3", AMBER)
        self.r(x + 32, y - 8, 26, 8, AMBER, AMBER, 2)
        self.t(x + 45, y + 30, "+", 22, WIRE_P, "middle", 700)
        self.t(x + 45, y + 92, "−", 24, WIRE_N, "middle", 700)
        for i, line in enumerate(label):
            self.t(x + 45, y + 140 + i * 16, line, 12, MUTED, "middle")

    def meter(self, x, y, mode, sockets="COM · 10A"):
        self.r(x, y, 110, 120, "#FFF7C2", "#7A6512", 10)
        self.r(x + 12, y + 12, 86, 34, "#E9F2D8", "#7A6512", 4)
        self.t(x + 55, y + 29, mode, 16, "#3B4A1A", "middle", 700)
        self.t(x + 55, y + 72, "multimeter", 11, "#7A6512", "middle")
        self.t(x + 55, y + 96, sockets, 11, "#7A6512", "middle", 700)

    def fuse(self, x, y):
        self.r(x - 20, y - 9, 40, 18, "#fff", INK, 9)
        self.t(x, y, "5 A", 10, INK, "middle", 700)

    def note(self, x, y, w, lines, fill=AMBER_BG, stroke=AMBER, color=None):
        self.r(x, y, w, 18 + 18 * len(lines), fill, stroke, 8)
        for i, line in enumerate(lines):
            self.t(x + 12, y + 18 + i * 18, line, 12.5, color or stroke, "start", 700 if i == 0 else 400)

    def save(self, name):
        OUT.mkdir(exist_ok=True)
        body = "".join(self.p)
        (OUT / f"{name}.svg").write_bytes(
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" font-family="Segoe UI, Arial, sans-serif">'
            f'<rect width="{self.w}" height="{self.h}" fill="#fff"/>{body}</svg>'.encode())


def identify():
    s = S(1000, 330, "Step 1 — what kind of motor is it? Count the wires")
    cards = [
        (30, "DC motor", "2 wires", ["Drive, lift and side-shift", "are usually this type.", "Reverses when you swap", "the two wires."], [WIRE_P, WIRE_N]),
        (350, "Servo", "3 wires", ["Brown/black = GND", "red = + (4.8–6 V)", "orange/yellow/white = signal", "Do NOT put battery V on signal."], [WIRE_N, WIRE_P, "#E6A817"]),
        (670, "DC + feedback pot", "5 wires", ["2 thick = motor", "3 thin = potentiometer", "(the angle sensor).", "Common for RC toy steering."], [WIRE_P, WIRE_N, "#888", "#888", "#888"]),
    ]
    for x, t, w, lines, cols in cards:
        s.r(x, 56, 300, 250, "#fff", INK, 12)
        s.t(x + 150, 82, t, 16, INK, "middle", 700)
        s.t(x + 150, 104, w, 13, MUTED, "middle")
        s.p.append(f'<circle cx="{x + 80}" cy="170" r="34" fill="#EEF1F1" stroke="{INK}" stroke-width="2"/>')
        s.t(x + 80, 170, "M" if "Servo" not in t else "S", 20, INK, "middle", 700)
        for i, c in enumerate(cols):
            yy = 150 + i * (40 / max(1, len(cols) - 1)) if len(cols) > 1 else 170
            s.wire([(x + 114, yy), (x + 200, yy)], c, 3)
        s.r(x + 196, 140, 26, 60, "#fff", MUTED, 3)
        for i, line in enumerate(lines):
            s.t(x + 150, 228 + i * 18, line, 12, TEXT, "middle")
    s.save("identify")


def resistance():
    s = S(1000, 330, "Step 2 — winding resistance (motor disconnected, no battery anywhere)")
    s.motor(250, 170, "M", "motor terminals")
    s.meter(520, 110, "Ω  200", "COM · VΩ")
    s.wire([(284, 160), (420, 160), (420, 140), (520, 140)], WIRE_P)
    s.wire([(284, 180), (440, 180), (440, 200), (520, 200)], WIRE_N)
    s.dot(284, 160, WIRE_P)
    s.dot(284, 180, WIRE_N)
    s.note(680, 70, 300, ["Why this first", "Safe: no current flows.", "Stall current ≈ V ÷ R", "e.g. 8.4 V ÷ 2.0 Ω ≈ 4.2 A", "Turn the shaft slowly; write", "the LOWEST and highest value.", "Touch the probes together first:", "subtract that lead resistance."])
    s.t(250, 270, "Unsolder or unplug the motor from the toy's board first", 12, RED, "middle", 400, True)
    s.save("resistance")


def series():
    s = S(1000, 380, "Method B — the meter goes IN SERIES with one motor")
    s.battery(60, 120, ["battery", "(stock pack or 2S 7.4–8.4 V)"])
    s.fuse(250, 120)
    s.meter(330, 70, "A  10", "COM · 10A")
    s.motor(700, 180, "M", "motor (or the toy's board)")
    s.wire([(105, 120), (105, 100), (230, 100), (230, 120)], WIRE_P)
    s.wire([(270, 120), (300, 120), (300, 100), (330, 100)], WIRE_P)
    s.wire([(440, 100), (560, 100), (560, 170), (666, 170)], WIRE_P)
    s.wire([(150, 212), (190, 212), (190, 300), (560, 300), (560, 190), (666, 190)], WIRE_N)
    s.t(570, 118, "red probe in the 10A socket", 12, WIRE_P, "middle", 700)
    s.t(380, 312, "battery − straight to the motor", 12, MUTED, "middle")
    s.note(780, 60, 200, ["Never", "put the meter in", "A-mode ACROSS the", "battery or a motor:", "that is a short", "circuit."], RED_BG, RED)
    s.save("series")


def stock_method():
    s = S(1000, 330, "Method A — measure through the toy's own board (nothing cut)")
    s.battery(50, 90, ["stock battery"])
    s.meter(220, 60, "A  10", "COM · 10A")
    s.r(450, 70, 170, 130, "#EEF1F1", INK, 10)
    s.t(535, 120, "original", 14, INK, "middle", 700)
    s.t(535, 140, "receiver board", 14, INK, "middle", 700)
    s.wire([(95, 90), (95, 76), (220, 76)], WIRE_P)
    s.wire([(330, 90), (450, 90)], WIRE_P)
    s.wire([(140, 182), (170, 182), (170, 240), (430, 240), (430, 180), (450, 180)], WIRE_N)
    for i, (lbl, y) in enumerate([("drive", 90), ("steering", 125), ("lift", 160), ("side-shift", 195)]):
        s.wire([(620, y), (700, y)], INK, 2)
        s.p.append(f'<circle cx="725" cy="{y}" r="16" fill="#EEF1F1" stroke="{INK}" stroke-width="1.5"/>')
        s.t(725, y, "M", 12, INK, "middle", 700)
        s.t(752, y, lbl, 12.5, TEXT)
    s.note(40, 268, 920, ["Reading  =  board idle current  +  the one motor you are using.   Motor current  =  reading − idle.",
                          "Use the remote to run ONE function at a time. Good first test: shows the original behaviour, risk-free."])
    s.save("stock-method")


def stall():
    s = S(1000, 300, "Step 5 — stall current: block the motor for at most 2 seconds")
    s.motor(200, 150, "M", "")
    s.p.append(f'<rect x="250" y="110" width="40" height="80" rx="4" fill="#B9843F" stroke="#5A3A12" stroke-width="2"/>')
    s.t(270, 210, "wheel held", 12, MUTED, "middle")
    s.t(360, 140, "≤ 2 s", 30, RED, "middle", 700)
    s.t(360, 172, "then let go", 12, RED, "middle")
    s.note(450, 60, 520, ["How", "1. Meter in series (step 4), 10A socket, lift the wheels off the floor.",
                          "2. Start the motor, then grip the wheel / hold the shaft until it stops.",
                          "3. Read the number within 1–2 s, then let go. Wait 30 s between tries.",
                          "4. Repeat 3 times, keep the highest."], AMBER_BG, AMBER)
    s.note(450, 200, 520, ["Not for the lift at its end stop · not for the servo · not if it smokes"], RED_BG, RED)
    s.save("stall")


if __name__ == "__main__":
    identify()
    resistance()
    series()
    stock_method()
    stall()
    print("written to", OUT)
