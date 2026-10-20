"""Figures for the warehouse-map design guide (docs/warehouse-map/README.md and the PDF).

Reads the CURRENT map from backend/app/warehouse_map.yaml (sibling repo) and writes SVGs into img/:
  current-plan.svg      top view of the current map, with its main sizes
  current-3d.svg        isometric view of the same world as the Gazebo simulation (walls 45 cm, racks 15 cm)
  current-slam.png      the occupancy grid the simulation's map_server loads
  proposed-plan.svg     recommended new layout, with dimensions
  rack-elevation.svg    rack front + side view: levels, posts, LiDAR plane
  aisle-rule.svg        why the aisle in front of a rack must be about 1 m

Run:  python build_figures.py      (needs pyyaml; Pillow for the PNG)
"""

from __future__ import annotations

import math
import os
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
WS = Path(os.environ.get("SW_WORKSPACE", HERE.parents[1]))
MAP = WS / "backend" / "app" / "warehouse_map.yaml"
PGM = WS / "robot" / "ros2_ws" / "src" / "forklift_sim" / "maps" / "warehouse_sim.pgm"
OUT = HERE / "img"

FONT = "Segoe UI, Tahoma, Arial, sans-serif"
INK, MUTED, RED, LINE = "#124A5A", "#5B6B73", "#C0392B", "#DCE3E6"
ZONE = {  # fill, stroke, Arabic label
    "rack": ("#D9A35B", "#8A5A1F", "رف"),
    "dock_in": ("#BFE3F2", "#2B7FA8", "استلام"),
    "dock_out": ("#C8EBD3", "#2E8B57", "شحن"),
    "staging": ("#F6E7A8", "#B8961F", "انتظار"),
    "charge": ("#D6D9F5", "#4A55B5", "شحن البطاريات"),
    "pedestrian": ("#FBD9C2", "#D2691E", "مشاة"),
    "keepout": ("#F5C6C6", "#B22222", "ممنوع"),
}

DEFS = f"""<defs>
<marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
<path d="M0 0 L10 5 L0 10 z" fill="{RED}"/></marker>
<pattern id="hatch" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
<line x1="0" y1="0" x2="0" y2="8" stroke="#B22222" stroke-width="2" opacity=".45"/></pattern>
</defs>"""


def svg(w: int, h: int, body: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" font-family="{FONT}" font-size="14">'
            f'{DEFS}<rect width="{w}" height="{h}" fill="#fff"/>{body}</svg>')


def text(x, y, s, size=14, fill=INK, anchor="middle", weight="400", extra=""):
    # Arabic runs are laid out right-to-left; "start"/"end" keep meaning "text grows right"/"left" of x.
    if any("؀" <= ch <= "ۿ" for ch in str(s)):
        extra += ' direction="rtl" unicode-bidi="embed"'
        anchor = {"start": "end", "end": "start"}.get(anchor, anchor)
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" '
            f'font-weight="{weight}" dominant-baseline="central" {extra}>{s}</text>')


def dim(x1, y1, x2, y2, label, off=0.0, size=13, side=1):
    """Dimension line with arrows; label centred, pushed `side` (+1/-1) away from the line."""
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    horiz = abs(y2 - y1) < abs(x2 - x1)
    lx, ly = (mx, my - 11 * side) if horiz else (mx - 12 * side, my)
    rot = "" if horiz else f'transform="rotate(-90 {lx:.1f} {ly:.1f})"'
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{RED}" stroke-width="1.6" '
            f'marker-start="url(#a)" marker-end="url(#a)"/>'
            f'<rect x="{lx - 3.6 * len(label) - 4:.1f}" y="{ly - 9:.1f}" width="{7.2 * len(label) + 8:.1f}" height="18" '
            f'fill="#fff" opacity=".85" {rot}/>'
            + text(lx, ly, label, size, RED, extra=rot))


def ext(x1, y1, x2, y2):
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{RED}" stroke-width="1" stroke-dasharray="3 3"/>'


def cm(m: float) -> str:
    return f"{round(m * 100):d} سم"


class Plan:
    """Top-view drawing helper: metres → pixels, y up."""

    def __init__(self, W, H, s=140, ml=90, mt=70):
        self.W, self.H, self.s, self.ml, self.mt = W, H, s, ml, mt

    def X(self, x):
        return self.ml + x * self.s

    def Y(self, y):
        return self.mt + (self.H - y) * self.s

    def rect(self, x0, y0, x1, y1, fill, stroke, extra=""):
        return (f'<rect x="{self.X(x0):.1f}" y="{self.Y(y1):.1f}" width="{(x1 - x0) * self.s:.1f}" '
                f'height="{(y1 - y0) * self.s:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="1.6" {extra}/>')

    def floor(self):
        W, H = self.W, self.H
        return (self.rect(0, 0, W, H, "#F4F6F6", INK)
                + f'<rect x="{self.X(0) - 7:.1f}" y="{self.Y(H) - 7:.1f}" width="{W * self.s + 14:.1f}" '
                  f'height="{H * self.s + 14:.1f}" fill="none" stroke="#7F8C8D" stroke-width="7"/>')

    def grid(self, step=0.5):
        out = []
        x = step
        while x < self.W - 1e-6:
            out.append(f'<line x1="{self.X(x):.1f}" y1="{self.Y(0):.1f}" x2="{self.X(x):.1f}" y2="{self.Y(self.H):.1f}" stroke="{LINE}" stroke-width=".8"/>')
            x += step
        y = step
        while y < self.H - 1e-6:
            out.append(f'<line x1="{self.X(0):.1f}" y1="{self.Y(y):.1f}" x2="{self.X(self.W):.1f}" y2="{self.Y(y):.1f}" stroke="{LINE}" stroke-width=".8"/>')
            y += step
        return "".join(out)


def bbox(poly):
    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
    return min(xs), min(ys), max(xs), max(ys)


# ------------------------------------------------------------------------------------------------ current plan
def current_plan(wh) -> str:
    W, H = float(wh["width_m"]), float(wh["height_m"])
    p = Plan(W, H)
    b = [text(p.X(W / 2), 26, "الخارطة الحالية — من الأعلى (warehouse_map.yaml)", 19, INK, weight="700"), p.floor(), p.grid()]
    for z in wh["zones"]:
        fill, stroke, label = ZONE[z["kind"]]
        x0, y0, x1, y1 = bbox(z["polygon"])
        extra = 'fill-opacity=".9"'
        b.append(p.rect(x0, y0, x1, y1, fill, stroke, extra))
        if z["kind"] == "keepout":
            b.append(p.rect(x0, y0, x1, y1, "url(#hatch)", stroke))
        name = f'{label} {z["id"]}' if z["kind"] == "rack" else label
        b.append(text(p.X((x0 + x1) / 2), p.Y((y0 + y1) / 2), name, 14, stroke, weight="700"))
    nodes = wh["nodes"]
    for a, c in wh["edges"]:
        (x1, y1), (x2, y2) = nodes[a], nodes[c]
        b.append(f'<line x1="{p.X(x1):.1f}" y1="{p.Y(y1):.1f}" x2="{p.X(x2):.1f}" y2="{p.Y(y2):.1f}" stroke="{MUTED}" stroke-width="2" stroke-dasharray="6 4"/>')
    loc_nodes = {l["node"] for l in wh["locations"]}
    for n, (x, y) in nodes.items():
        if n in loc_nodes:
            b.append(f'<rect x="{p.X(x) - 6:.1f}" y="{p.Y(y) - 6:.1f}" width="12" height="12" fill="#fff" stroke="{INK}" stroke-width="2"/>')
        else:
            b.append(f'<circle cx="{p.X(x):.1f}" cy="{p.Y(y):.1f}" r="3.5" fill="{MUTED}"/>')
    # main sizes
    b += [ext(p.X(0), p.Y(0), p.X(0), p.Y(0) + 40), ext(p.X(W), p.Y(0), p.X(W), p.Y(0) + 40),
          dim(p.X(0), p.Y(0) + 32, p.X(W), p.Y(0) + 32, cm(W), side=-1),
          ext(p.X(0), p.Y(0), p.X(0) - 44, p.Y(0)), ext(p.X(0), p.Y(H), p.X(0) - 44, p.Y(H)),
          dim(p.X(0) - 36, p.Y(0), p.X(0) - 36, p.Y(H), cm(H))]
    # aisle widths at y = 2.0, corridor heights at x = 2.0
    for x0, x1 in [(0.5, 1.5), (2.5, 3.5), (4.5, 5.5)]:
        b.append(dim(p.X(x0), p.Y(2.0), p.X(x1), p.Y(2.0), "ممر " + cm(x1 - x0), size=12))
    b.append(dim(p.X(4.0), p.Y(0.35), p.X(4.0), p.Y(1.2), cm(0.85), size=12))
    b.append(dim(p.X(4.0), p.Y(2.8), p.X(4.0), p.Y(3.65), cm(0.85), size=12))
    b.append(dim(p.X(4.7), p.Y(3.65), p.X(4.7), p.Y(4.0), cm(0.35), size=11, side=-1))
    # rack size
    b.append(dim(p.X(1.5), p.Y(1.2) + 14, p.X(2.5), p.Y(1.2) + 14, cm(1.0), size=11, side=-1))
    b.append(dim(p.X(1.5) + 14, p.Y(1.2), p.X(1.5) + 14, p.Y(2.8), cm(1.6), size=11, side=-1))
    # legend
    ly = p.Y(0) + 70
    b.append(f'<rect x="{p.X(0):.1f}" y="{ly - 6:.1f}" width="12" height="12" fill="#fff" stroke="{INK}" stroke-width="2"/>')
    b.append(text(p.X(0) + 20, ly, "موقع التقاط/إنزال (عليه علامة ArUco)", 13, MUTED, "start"))
    b.append(f'<line x1="{p.X(2.6):.1f}" y1="{ly:.1f}" x2="{p.X(2.9):.1f}" y2="{ly:.1f}" stroke="{MUTED}" stroke-width="2" stroke-dasharray="6 4"/>')
    b.append(text(p.X(2.95), ly, "مسار الرافعات (مسار واحد لكل خط)", 13, MUTED, "start"))
    b.append(text(p.X(5.1), ly, "الشبكة كل 50 سم", 13, MUTED, "start"))
    return svg(int(p.X(W) + 70), int(ly + 26), "".join(b))


# ------------------------------------------------------------------------------------------------ isometric
def iso_world(wh) -> str:
    W, H = float(wh["width_m"]), float(wh["height_m"])
    s, c30, s30 = 120, math.cos(math.radians(30)), math.sin(math.radians(30))
    ox, oy = 90 + H * c30 * s, 120

    def P(x, y, z):  # camera at the south-east, looking north-west
        yy = H - y
        return ox + (x - yy) * c30 * s, oy + (x + yy) * s30 * s - z * s

    def poly(pts, fill, stroke="#124A5A", op=1.0, sw=1.2):
        d = " ".join(f"{a:.1f},{b:.1f}" for a, b in (P(*q) for q in pts))
        return f'<polygon points="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" fill-opacity="{op}"/>'

    def box(x0, y0, x1, y1, h, top, side1, side2, op=1.0):
        return (poly([(x0, y0, h), (x1, y0, h), (x1, y1, h), (x0, y1, h)], top, op=op)
                + poly([(x1, y0, 0), (x1, y1, 0), (x1, y1, h), (x1, y0, h)], side1, op=op)
                + poly([(x0, y0, 0), (x1, y0, 0), (x1, y0, h), (x0, y0, h)], side2, op=op))

    WH, WT = 0.45, 0.04
    b = [text(ox, 30, "نموذج ثلاثي الأبعاد للعالم الحالي (نفس عالم محاكاة Gazebo)", 19, INK, weight="700"),
         poly([(0, 0, 0), (W, 0, 0), (W, H, 0), (0, H, 0)], "#EEF1F1")]
    # far walls (north, west) first
    b.append(box(-WT, H, W, H + WT, WH, "#AEB6BA", "#C3CACD", "#9AA3A7"))
    b.append(box(-WT, -WT, 0, H, WH, "#AEB6BA", "#C3CACD", "#B5BDC1"))
    zones = sorted(wh["zones"], key=lambda z: bbox(z["polygon"])[0] + (H - bbox(z["polygon"])[3]))
    for z in zones:
        if z["kind"] == "rack":
            continue
        fill, stroke, _ = ZONE[z["kind"]]
        x0, y0, x1, y1 = bbox(z["polygon"])
        b.append(poly([(x0, y0, 0), (x1, y0, 0), (x1, y1, 0), (x0, y1, 0)], fill, stroke, .95))
    nodes = wh["nodes"]
    for a, c in wh["edges"]:
        (x1, y1), (x2, y2) = nodes[a], nodes[c]
        (X1, Y1), (X2, Y2) = P(x1, y1, 0), P(x2, y2, 0)
        b.append(f'<line x1="{X1:.1f}" y1="{Y1:.1f}" x2="{X2:.1f}" y2="{Y2:.1f}" stroke="{MUTED}" stroke-width="1.4" stroke-dasharray="5 4"/>')
    racks = sorted((z for z in wh["zones"] if z["kind"] == "rack"), key=lambda z: bbox(z["polygon"])[0])
    for z in racks:
        x0, y0, x1, y1 = bbox(z["polygon"])
        b.append(box(x0, y0, x1, y1, 0.15, "#D9A35B", "#B9843F", "#C99550"))
        cx, cy = P((x0 + x1) / 2, (y0 + y1) / 2, 0.15)
        b.append(text(cx, cy, f'رف {z["id"]} — ارتفاع 15 سم', 13, "#5A3A12", weight="700"))
    # near walls (south, east) as see-through
    b.append(box(0, -WT, W + WT, 0, WH, "#AEB6BA", "#C3CACD", "#9AA3A7", op=.28))
    b.append(box(W, 0, W + WT, H + WT, WH, "#AEB6BA", "#C3CACD", "#B5BDC1", op=.28))
    # forklift-sized block at CH1 for scale, and the LiDAR plane
    fx, fy = nodes["J45"]
    b.append(box(fx - 0.09, fy - 0.30, fx + 0.09, fy + 0.22, 0.317, "#F2B33D", "#D99B25", "#E5A930"))
    lx, ly = P(fx, fy + 0.4, 0.317)
    b.append(text(lx + 70, ly - 18, "رافعة 52×19×32 سم (للمقارنة)", 12, INK, "start"))
    for a, c in [((0, H, 0.36), (W, H, 0.36)), ((0, 0, 0.36), (0, H, 0.36))]:
        (X1, Y1), (X2, Y2) = P(*a), P(*c)
        b.append(f'<line x1="{X1:.1f}" y1="{Y1:.1f}" x2="{X2:.1f}" y2="{Y2:.1f}" stroke="{RED}" stroke-width="2" stroke-dasharray="8 5"/>')
    X1, Y1 = P(0, H * .55, 0.36)
    b.append(text(X1 + 30, Y1 + 34, "مستوى مسح الليدار 36 سم — الجدران 45 سم", 13, RED, "start", "700"))
    w, h = int(ox + (W + 0.3) * c30 * s + 40), int(oy + (W + H) * s30 * s + 50)
    return svg(w, h, "".join(b))


# ------------------------------------------------------------------------------------------------ proposed layout
PROPOSED = {
    "W": 6.0, "H": 4.0,
    "zones": [  # x0, y0, x1, y1, kind, label
        (0.00, 1.30, 0.60, 2.40, "dock_in", "استلام IN"),
        (4.50, 1.30, 5.10, 2.40, "dock_out", "شحن OUT"),
        (1.60, 1.30, 2.05, 2.40, "rack", "R1"),
        (3.05, 1.30, 3.50, 2.40, "rack", "R2"),
        (1.60, 0.00, 3.50, 0.40, "staging", "انتظار STG"),
        (0.70, 3.40, 2.90, 4.00, "charge", "شحن البطاريات"),
        (5.10, 0.00, 6.00, 4.00, "pedestrian", "منطقة المشاة والعمل"),
        (3.60, 3.40, 5.10, 4.00, "keepout", "ممنوع (راوتر/عدة)"),
    ],
    "aisles_x": [(0.60, 1.60), (2.05, 3.05), (3.50, 4.50)],
    "corridors_y": [(0.40, 1.30), (2.40, 3.40)],
}


def proposed_plan() -> str:
    d = PROPOSED
    W, H = d["W"], d["H"]
    p = Plan(W, H, s=140, ml=100, mt=70)
    b = [text(p.X(W / 2), 26, "التصميم المقترح للخارطة الجديدة — 6 × 4 م (القياسات تقريبية)", 19, INK, weight="700"),
         p.floor(), p.grid()]
    # driving area tint
    for x0, x1 in d["aisles_x"]:
        b.append(p.rect(x0, 0.40, x1, 3.40, "#E3F1F4", "none"))
    for y0, y1 in d["corridors_y"]:
        b.append(p.rect(0.0 if y0 < 1 else 0.0, y0, 5.10, y1, "#E3F1F4", "none"))
    for x0, y0, x1, y1, kind, label in d["zones"]:
        fill, stroke, _ = ZONE[kind]
        b.append(p.rect(x0, y0, x1, y1, fill, stroke, 'fill-opacity=".9"'))
        if kind == "keepout":
            b.append(p.rect(x0, y0, x1, y1, "url(#hatch)", stroke))
        ty = (y0 + y1) / 2
        lx = (x0 + x1) / 2
        if kind == "staging":
            lx = 1.95
        if kind == "charge":
            ty = 3.76
        if kind == "rack":
            ty = y1 + 0.06
        rot = f'transform="rotate(-90 {p.X((x0 + x1) / 2):.1f} {p.Y(ty):.1f})"' if kind == "pedestrian" else ""
        b.append(text(p.X(lx), p.Y(ty) if kind != "rack" else p.Y(y1) - 12, label, 14, stroke, weight="700", extra=rot))
    # rack slots: 3 per face, 30 cm pitch, posts at the slot borders
    aruco = 21
    for x0, x1 in [(1.60, 2.05), (3.05, 3.50)]:
        for face, fx0, fx1 in [("W", x0, (x0 + x1) / 2 - 0.01), ("E", (x0 + x1) / 2 + 0.01, x1)]:
            for i, yc in enumerate([1.55, 1.85, 2.15]):
                b.append(p.rect(fx0 + 0.005, yc - 0.10, fx1 - 0.005, yc + 0.10, "#fff", "#8A5A1F", 'stroke-dasharray="3 2"'))
                b.append(text(p.X((fx0 + fx1) / 2), p.Y(yc), str(aruco), 11, "#8A5A1F", weight="700"))
                aruco += 1
        for yb in [1.40, 1.70, 2.00, 2.30]:
            for xx in [x0, x1 - 0.02]:
                b.append(p.rect(xx, yb - 0.01, xx + 0.02, yb + 0.01, INK, INK))
    # pallet squares in docks / staging, charger bays
    for x0, x1 in [(0.00, 0.60), (4.50, 5.10)]:
        for yc in [1.60, 2.10]:
            b.append(p.rect((x0 + x1) / 2 - 0.15, yc - 0.15, (x0 + x1) / 2 + 0.15, yc + 0.15, "none", INK, 'stroke-dasharray="4 3"'))
    for xc in [2.50, 3.15]:
        b.append(p.rect(xc - 0.15, 0.05, xc + 0.15, 0.35, "none", INK, 'stroke-dasharray="4 3"'))
    for i, xc in enumerate([1.05, 1.55, 2.05, 2.55]):
        b.append(p.rect(xc - 0.20, 3.40, xc + 0.20, 4.00, "none", "#4A55B5", 'stroke-dasharray="5 3"'))
        b.append(text(p.X(xc), p.Y(3.50), f"C{i + 1}", 12, "#4A55B5", weight="700"))
    # lane centrelines
    for x0, x1 in d["aisles_x"]:
        xc = (x0 + x1) / 2
        b.append(f'<line x1="{p.X(xc):.1f}" y1="{p.Y(0.85):.1f}" x2="{p.X(xc):.1f}" y2="{p.Y(2.90):.1f}" stroke="{MUTED}" stroke-width="2" stroke-dasharray="7 5"/>')
    for y0, y1 in d["corridors_y"]:
        yc = (y0 + y1) / 2
        b.append(f'<line x1="{p.X(1.10):.1f}" y1="{p.Y(yc):.1f}" x2="{p.X(4.00):.1f}" y2="{p.Y(yc):.1f}" stroke="{MUTED}" stroke-width="2" stroke-dasharray="7 5"/>')
    # dimension chain along the bottom (x)
    xs = [0.0, 0.60, 1.60, 2.05, 3.05, 3.50, 4.50, 5.10, 6.0]
    yb = p.Y(0) + 34
    for x in xs:
        b.append(ext(p.X(x), p.Y(0), p.X(x), yb + 8))
    for a, c in zip(xs, xs[1:]):
        b.append(dim(p.X(a), yb, p.X(c), yb, str(round((c - a) * 100)), size=12, side=-1))
    b.append(text(p.X(W / 2), yb + 34, "عرض كل جزء بالسنتيمتر — المجموع 600 سم", 13, MUTED))
    # dimension chain on the left (y)
    ys = [0.0, 0.40, 1.30, 2.40, 3.40, 4.0]
    xl = p.X(0) - 40
    for y in ys:
        b.append(ext(p.X(0), p.Y(y), xl - 8, p.Y(y)))
    for a, c in zip(ys, ys[1:]):
        b.append(dim(xl, p.Y(a), xl, p.Y(c), str(round((c - a) * 100)), size=12))
    return svg(int(p.X(W) + 60), int(yb + 56), "".join(b))


# ------------------------------------------------------------------------------------------------ rack elevation
def rack_elevation() -> str:
    s = 5.0  # px per cm
    gx, gy = 70, 330  # floor line origin
    b = [text(640, 28, "الرف بالتفصيل — منظر أمامي (يمين) ومنظر جانبي (يسار) · القياسات بالسنتيمتر", 18, INK, weight="700")]

    def R(x, y, w, h, fill, stroke=INK, extra=""):
        return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="1.5" {extra}/>'

    # ---- side view (left): depth 45 = 21 + 3 + 21
    sx = gx + 20
    b.append(f'<line x1="{gx - 30}" y1="{gy}" x2="1260" y2="{gy}" stroke="{INK}" stroke-width="2"/>')
    b.append(R(sx, gy - 45 * s, 2 * s, 45 * s, INK))
    b.append(R(sx + 43 * s, gy - 45 * s, 2 * s, 45 * s, INK))
    b.append(R(sx, gy - 9.5 * s, 45 * s, 0.9 * s, "#B9843F"))
    for side in (0, 1):
        px = sx + (2 if side == 0 else 23.5) * s
        b.append(R(px, gy - 3.5 * s, 19.5 * s, 3.5 * s, "#D9A35B"))  # floor pallet
        b.append(R(px + 2 * s, gy - 7.5 * s, 15.5 * s, 4 * s, "#F6E7A8"))
        b.append(R(px, gy - 13 * s, 19.5 * s, 3.5 * s, "#D9A35B"))  # level 2 pallet
        b.append(R(px + 2 * s, gy - 17 * s, 15.5 * s, 4 * s, "#F6E7A8"))
    b.append(dim(sx, gy + 26, sx + 45 * s, gy + 26, "45", side=-1))
    b.append(text(sx + 22.5 * s, gy + 52, "عمق الرف ذو الوجهين: 21 + 3 + 21", 12, MUTED))
    b.append(text(sx + 22.5 * s, gy - 47 * s - 10, "منظر جانبي", 14, INK, weight="700"))

    # ---- front view (right): 3 slots × 30 cm, posts 2 cm
    fx = 400
    posts = [0, 30, 60, 90]
    for px in posts:
        b.append(R(fx + px * s, gy - 45 * s, 2 * s, 45 * s, INK))
    b.append(R(fx, gy - 9.5 * s, 92 * s, 0.9 * s, "#B9843F"))
    for i in range(3):
        cx = fx + (2 + i * 30 + 4) * s
        b.append(R(cx, gy - 3.5 * s, 20 * s, 3.5 * s, "#D9A35B"))
        b.append(R(cx + 2 * s, gy - 7.5 * s, 16 * s, 4 * s, "#F6E7A8"))
        b.append(R(cx, gy - 13 * s, 20 * s, 3.5 * s, "#D9A35B"))
        b.append(R(cx + 2 * s, gy - 17 * s, 16 * s, 4 * s, "#F6E7A8"))
        # rack location marker 6 x 6 cm on the shelf front / upright
        b.append(R(cx + 7 * s, gy - 31 * s, 6 * s, 6 * s, "#111", "#111"))
        b.append(R(cx + 8.5 * s, gy - 29.5 * s, 1.5 * s, 1.5 * s, "#fff", "#fff"))
        b.append(R(cx + 10.5 * s, gy - 27.5 * s, 1.5 * s, 1.5 * s, "#fff", "#fff"))
    b.append(text(fx + 46 * s, gy - 47 * s - 10, "منظر أمامي (الوجه اللي تدخل منه الشوكات)", 14, INK, weight="700"))
    # dims front
    b.append(dim(fx + 2 * s, gy + 26, fx + 30 * s, gy + 26, "28 فتحة", size=12, side=-1))
    b.append(dim(fx, gy + 56, fx + 92 * s, gy + 56, "92 طول الوجه (3 خانات)", size=12, side=-1))
    xr = fx + 92 * s + 26
    for y in (0, 9.5, 45):
        b.append(ext(fx + 92 * s, gy - y * s, xr + 8, gy - y * s))
    b.append(dim(xr, gy, xr, gy - 9.5 * s, "9.5", size=12, side=-1))
    b.append(dim(xr + 44, gy, xr + 44, gy - 45 * s, "45 ارتفاع الأعمدة", size=12, side=-1))
    b.append(ext(fx + 92 * s, gy - 17 * s, xr + 100, gy - 17 * s))
    b.append(text(xr + 104, gy - 17 * s, "أعلى حمولة ≈ 17", 12, MUTED, "start"))
    # LiDAR plane + wall
    b.append(f'<line x1="{gx - 30}" y1="{gy - 36 * s:.1f}" x2="1260" y2="{gy - 36 * s:.1f}" stroke="{RED}" stroke-width="2" stroke-dasharray="9 6"/>')
    b.append(text(1258, gy - 36 * s - 14, "مستوى مسح الليدار ≈ 36 سم (الأعمدة لازم تطلع فوقه حتى يشوفها)", 12.5, RED, "end", "700"))
    # forklift silhouette for scale (side view)
    kx = 1060
    b.append(R(kx, gy - 12 * s - 2, 32 * s * 0.6, 10 * s, "#F2B33D"))
    b.append(R(kx + 19 * s, gy - 31.7 * s, 1.6 * s, 31 * s, "#5B6B73"))
    b.append(R(kx + 20.6 * s, gy - 1.6 * s, 18 * s * .7, 1.2 * s, "#5B6B73"))
    b.append(f'<circle cx="{kx + 4 * s:.1f}" cy="{gy - 3.5 * s:.1f}" r="{3.5 * s:.1f}" fill="#2B2B2B"/>')
    b.append(f'<circle cx="{kx + 16 * s:.1f}" cy="{gy - 3.5 * s:.1f}" r="{3.5 * s:.1f}" fill="#2B2B2B"/>')
    b.append(text(kx + 16 * s, gy + 26, "الرافعة: الصاري 31.7، أقصى رفع ≈ 12", 12, MUTED))
    return svg(1280, gy + 80, "".join(b))


# ------------------------------------------------------------------------------------------------ aisle rule
def aisle_rule() -> str:
    s = 4.2  # px per cm
    x0, top = 140, 70
    b = [text(470, 28, "ليش الممر قدّام الرف لازم يكون ≈ 100 سم", 18, INK, weight="700")]
    # rack face at the top
    b.append(f'<rect x="{x0 - 60}" y="{top}" width="{60 * s + 120}" height="{12 * s}" fill="#D9A35B" stroke="#8A5A1F" stroke-width="1.5"/>')
    b.append(text(x0 + 30 * s, top + 6 * s, "واجهة الرف", 14, "#5A3A12", weight="700"))
    face = top + 12 * s
    # pallet being taken out
    b.append(f'<rect x="{x0 + 20 * s}" y="{face:.1f}" width="{20 * s}" height="{20 * s}" fill="#F6E7A8" stroke="#B8961F" stroke-width="1.5"/>')
    b.append(text(x0 + 30 * s, face + 10 * s, "البالية 20", 13, "#7A6512"))
    # forklift pulled straight back: forks under the pallet, body behind
    fk = face
    fk = face + 20 * s
    for fxx in (x0 + 22.5 * s, x0 + 33.5 * s):  # two forks, 3.5 wide
        b.append(f'<rect x="{fxx:.1f}" y="{fk:.1f}" width="{3.5 * s}" height="{18 * s}" fill="#5B6B73" stroke="{INK}" stroke-width="1"/>')
    b.append(f'<rect x="{x0 + 20.65 * s}" y="{fk + 21 * s:.1f}" width="{18.7 * s}" height="{31.4 * s}" fill="#F2B33D" fill-opacity=".85" stroke="{INK}" stroke-width="1.5"/>')
    b.append(text(x0 + 30 * s, fk + 35 * s, "الرافعة 52.4", 13, INK, weight="700"))
    b.append(text(x0 + 30 * s, fk + 41 * s, "(مع الشوكات)", 11, INK))
    # dims on the right
    xr = x0 + 62 * s
    pts = [face, face + 20 * s, face + 72.4 * s, face + 87.4 * s, face + 100 * s]
    for y in pts:
        b.append(ext(x0 + 40 * s, y, xr + 10, y))
    b.append(dim(xr, pts[0], xr, pts[1], "20", size=12, side=-1))
    b.append(dim(xr, pts[1], xr, pts[2], "52.4", size=12, side=-1))
    b.append(dim(xr, pts[2], xr, pts[3], "15", size=12, side=-1))
    b.append(dim(xr + 60, pts[0], xr + 60, pts[4], "100 موصى به", size=12, side=-1))
    b.append(f'<line x1="{x0 - 60}" y1="{pts[4]:.1f}" x2="{x0 + 60 * s + 60}" y2="{pts[4]:.1f}" stroke="{INK}" stroke-width="3"/>')
    b.append(text(x0 + 30 * s, pts[4] + 18, "الرف أو المنطقة المقابلة", 13, MUTED))
    # explanation box
    ex = x0 + 62 * s + 130
    lines = ["الحد الأدنى حسب EN-01", "• طول الرافعة 52.4", "• عمق البالية 20", "• هامش 15", "المجموع 87.4 سم ≈ 90",
             "حساب محافظ: كأن البالية", "كلها قدّام الشوكات", "", "نوصي بـ 100 سم لأن الرافعة", "توجّه من الخلف (Ackermann)", "وما تدور بمكانها: تحتاج", "مسافة حتى تصفّ مستقيمة", "قبل ما تدخل الشوكات."]
    for i, line in enumerate(lines):
        b.append(text(ex, top + 20 + i * 24, line, 14, INK if i in (0, 4) else MUTED, "start", "700" if i in (0, 4) else "400"))
    return svg(int(ex + 270), int(pts[4] + 40), "".join(b))


def slam_png():
    from PIL import Image

    im = Image.open(PGM).convert("L")
    w, h = im.size
    im = im.resize((w * 2, h * 2), Image.NEAREST)
    im.save(OUT / "current-slam.png")


def main():
    OUT.mkdir(exist_ok=True)
    wh = yaml.safe_load(MAP.read_text(encoding="utf-8"))
    for name, s in [("current-plan", current_plan(wh)), ("current-3d", iso_world(wh)), ("proposed-plan", proposed_plan()),
                    ("rack-elevation", rack_elevation()), ("aisle-rule", aisle_rule())]:
        (OUT / f"{name}.svg").write_bytes(s.encode("utf-8"))
    slam_png()
    print("figures written to", OUT)


if __name__ == "__main__":
    main()
