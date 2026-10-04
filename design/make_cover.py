"""Cover sheet of the design dossier ("Membrane Cartography", see drawings/design_philosophy.md).

Every line is computed from the real geometry (wing_geometry.py + butterfly_params.json) and the Fusion
mass export, so the art is also a true-scale drawing.

Run:  analysis/.venv/Scripts/python design/make_cover.py
"""
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Polygon, Rectangle, Circle, Arc

import wing_geometry as wg

HERE = Path(__file__).parent
OUT = HERE / "drawings"
FONTS = Path(r"C:\Users\Admin\.claude\skills\synced\84c7a5b4-017e-4de4-8045-680fd6db7772_92c80b8d-8e49-4727-88f7-7316049f950a\canvas-design\canvas-fonts")
for f in ("Jura-Light.ttf", "Jura-Medium.ttf", "IBMPlexMono-Regular.ttf", "WorkSans-Regular.ttf"):
    font_manager.fontManager.addfont(str(FONTS / f))
TITLE, MONO, SANS = "Jura", "IBM Plex Mono", "Work Sans"

PAPER, INK, INK2 = "#f6f2ea", "#1d1c1a", "#8a857b"
FORE, HIND, SIGNAL = "#f2c79a", "#e9a970", "#c2402f"

W = wg.Wing()
P = W.prm
MP = json.loads((HERE / "fusion_mass_properties.json").read_text(encoding="utf-8"))
ROOT = tuple(P["wing"]["root"])
IN = 1 / 25.4
PAGE = (420, 297)                 # A3 landscape, mm


def top(p_local3, sgn):
    """wing-local 3D -> model -> top view (page x = model y, page y = model x)."""
    x, y, z = wg.to_model(W, p_local3, sgn, ROOT)
    return (y, x)


def main():
    fig = plt.figure(figsize=(PAGE[0] * IN, PAGE[1] * IN), facecolor=PAPER)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, PAGE[0])
    ax.set_ylim(0, PAGE[1])
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(Rectangle((0, 0), *PAGE, fc=PAPER, ec="none", zorder=-10))

    # ---------------------------------------------------------------- measured border (tick ladders + registration)
    m = 12
    ax.add_patch(Rectangle((m, m), PAGE[0] - 2 * m, PAGE[1] - 2 * m, fill=False, ec=INK, lw=0.35))
    for x in range(0, int(PAGE[0] - 2 * m) + 1):
        h = 2.6 if x % 10 == 0 else (1.6 if x % 5 == 0 else 0.8)
        for yb, s in ((m, 1), (PAGE[1] - m, -1)):
            ax.plot([m + x, m + x], [yb, yb + s * h], color=INK, lw=0.18)
    for y in range(0, int(PAGE[1] - 2 * m) + 1):
        h = 2.6 if y % 10 == 0 else (1.6 if y % 5 == 0 else 0.8)
        for xb, s in ((m, 1), (PAGE[0] - m, -1)):
            ax.plot([xb, xb + s * h], [m + y, m + y], color=INK, lw=0.18)
    for cx, cy in ((m - 6, m - 6), (PAGE[0] - m + 6, m - 6), (m - 6, PAGE[1] - m + 6), (PAGE[0] - m + 6, PAGE[1] - m + 6)):
        ax.plot([cx - 3, cx + 3], [cy, cy], color=INK, lw=0.3)
        ax.plot([cx, cx], [cy - 3, cy + 3], color=INK, lw=0.3)
        ax.add_patch(Circle((cx, cy), 1.6, fill=False, ec=INK, lw=0.3))

    # ---------------------------------------------------------------- plate 1: top view at scale 1:3.2
    sc = 1 / 3.2
    ox, oy = 150, 196                       # page position of the model origin (wing-root LE plane, centreline)

    def T(p):
        return (ox + p[0] * sc, oy + p[1] * sc)

    for sgn in (1, -1):
        for poly, col, hind in ((W.fore_panel(24), FORE, False), (W.hind_panel(24), HIND, True)):
            pts = [T(top(W.fold(p, hind), sgn)) for p in poly]
            ax.add_patch(Polygon(pts, closed=True, fc=col, ec="none", alpha=0.55, zorder=1))
        outline = [T(top(W.fold(p, W.is_hind(p) or p in W.hind_curve), sgn)) for p in W.outline(24)]
        ax.add_patch(Polygon(outline, closed=True, fill=False, ec=INK, lw=0.55, zorder=3))
        for r in W.rods():
            hind = r["name"] in W.HIND_RODS
            a, b = T(top(W.fold(r["a"], hind), sgn)), T(top(W.fold(r["b"], hind), sgn))
            col = SIGNAL if r["name"] == "Fold" else INK
            ax.plot([a[0], b[0]], [a[1], b[1]], color=col, lw=0.25 + r["od"] * 0.38, solid_capstyle="round", zorder=4)
    # body: servos, frame, spine, tray, battery
    sv = P["servo"]
    of, H, Wd = sv["output_face_x"], sv["H"], sv["W"]
    for sgn in (1, -1):
        y0, y1 = sorted((sgn * 0.2, sgn * (0.2 + Wd)))
        ax.add_patch(Rectangle(T((y0, of)), (y1 - y0) * sc, H * sc, fc=INK, ec="none", zorder=5))
    sp = P["body"]["spine"]
    ax.plot([ox, ox], [T((0, sp["x_front"]))[1], T((0, sp["x_front"] - sp["length"]))[1]], color=INK, lw=0.9, zorder=5)
    tr = P["body"]["tray"]
    ax.add_patch(Rectangle(T((-tr["width"] / 2, tr["centre_x"] - tr["length"] / 2)), tr["width"] * sc, tr["length"] * sc,
                           fill=False, ec=INK, lw=0.5, zorder=5))
    bt = P["body"]["battery"]
    ax.add_patch(Rectangle(T((-bt["size"][1] / 2, bt["centre_x"] - bt["size"][0] / 2)), bt["size"][1] * sc, bt["size"][0] * sc,
                           fill=False, ec=INK2, lw=0.4, ls=(0, (2, 1.5)), zorder=5))
    # CG + neutral point markers on the centreline
    cgx = MP["cg_mm"][0]
    c = T((0, cgx))
    ax.add_patch(Circle(c, 2.2, fc=PAPER, ec=INK, lw=0.5, zorder=6))
    ax.add_patch(Polygon([c, (c[0] + 2.2, c[1]), (c[0] + 2.2 * math.cos(math.pi / 2), c[1] + 2.2)], fc=INK, ec="none", zorder=7))
    ax.add_patch(Polygon([c, (c[0] - 2.2, c[1]), (c[0], c[1] - 2.2)], fc=INK, ec="none", zorder=7))
    try:
        stab = json.loads((HERE.parent / "analysis" / "results" / "stability.json").read_text(encoding="utf-8"))
        npx = -stab["neutral_point_mm"]
        n = T((0, npx))
        ax.plot([n[0] - 3.5, n[0] + 3.5], [n[1], n[1]], color=SIGNAL, lw=0.6, zorder=6)
        ax.text(n[0] - 5, n[1], "NP", fontsize=5.5, family=MONO, color=SIGNAL, va="center", ha="right")
    except FileNotFoundError:
        stab = None
    ax.text(c[0] - 5, c[1], "CG", fontsize=5.5, family=MONO, color=INK, va="center", ha="right")
    # span dimension
    tipx = max(abs(top(W.fold(p, False), 1)[0]) for p in W.fore_panel(24))
    yd = oy + 40 * sc + 14
    ax.plot([T((-tipx, 0))[0], T((tipx, 0))[0]], [yd, yd], color=INK, lw=0.3)
    for sx in (-tipx, tipx):
        ax.plot([T((sx, 0))[0]] * 2, [yd - 2, yd + 2], color=INK, lw=0.3)
    ax.text(ox, yd + 2.2, "%.0f" % (2 * tipx), fontsize=6.5, family=MONO, color=INK, ha="center", va="bottom")
    ax.text(m + 8, PAGE[1] - m - 9, "PLATE I   ·   hình chiếu bằng   ·   1 : 3.2", fontsize=6, family=MONO, color=INK2)

    # ---------------------------------------------------------------- plate 2: flap envelope, front view (small)
    fx, fy, fs = 150, 46, 1 / 5.0
    amp, dih = P["flight"]["amp_deg"], P["wing"]["dihedral_deg"]
    span = 400
    for sgn in (1, -1):
        base = (fx + sgn * sv["shaft_y"] * fs, fy)
        for a, lw, col in ((dih + amp, 0.45, INK), (dih, 0.7, SIGNAL), (dih - amp, 0.45, INK)):
            r = math.radians(a)
            ax.plot([base[0], base[0] + sgn * span * fs * math.cos(r)], [base[1], base[1] + span * fs * math.sin(r)],
                    color=col, lw=lw, solid_capstyle="round")
        for k in range(1, 9):
            rr = span * fs * k / 8
            theta1, theta2 = (dih - amp, dih + amp) if sgn > 0 else (180 - dih - amp, 180 - dih + amp)
            ax.add_patch(Arc(base, 2 * rr, 2 * rr, theta1=theta1, theta2=theta2, ec=INK2, lw=0.18))
    ax.add_patch(Rectangle((fx - 2.6, fy - 3.2), 5.2, 5.2, fc=INK, ec="none"))
    ax.text(m + 8, fy + 47, "PLATE II   ·   biên độ vỗ ±%d°  ·  nhị diện %d°  ·  1 : 5" % (amp, dih), fontsize=6, family=MONO, color=INK2)

    # ---------------------------------------------------------------- data column + title
    cx0 = 300
    ax.text(cx0, 252, "BƯỚM", fontsize=30, family=TITLE, color=INK)
    ax.text(cx0, 241, "RC · 2 SERVO · v3", fontsize=10, family=TITLE, color=INK)
    ax.plot([cx0, cx0 + 92], [236, 236], color=INK, lw=0.4)
    fa, ha = W.areas()
    rows = [
        ("sải cánh", "%.0f mm" % (2 * tipx)),
        ("diện tích", "%.2f dm²" % (2 * (fa + ha) / 1e4)),
        ("khối lượng", "%.1f g" % MP["mass_g"]),
        ("trọng tâm", "%.1f mm sau mép trước" % MP["cg_behind_le_mm"]),
        ("điểm trung hòa", ("%.1f mm" % stab["neutral_point_mm"]) if stab else "—"),
        ("dự trữ ổn định", ("%.1f mm" % stab["static_margin_mm"]) if stab else "—"),
        ("góc gấp tấm sau", "%.2f°  →  cúi %.0f°" % (math.degrees(W.beta), abs(P["wing"]["hind_incidence_deg"]))),
        ("vỗ cánh", "%.1f Hz · ±%d°" % (P["flight"]["f_hz"], P["flight"]["amp_deg"])),
        ("servo", P["servo"]["model"]),
        ("điều khiển", "ESP32-C3 Super Mini"),
    ]
    y = 226
    for k, v in rows:
        ax.text(cx0, y, k, fontsize=6.6, family=SANS, color=INK2)
        ax.text(cx0 + 92, y, v, fontsize=6.6, family=MONO, color=INK, ha="right")
        ax.plot([cx0, cx0 + 92], [y - 2.6, y - 2.6], color=INK, lw=0.12)
        y -= 8.2
    # legend of materials
    y -= 6
    for col, lab in ((FORE, "màng — tấm trước"), (HIND, "màng — tấm sau (gấp)"), (SIGNAL, "đường gấp / trục vỗ trung tính"), (INK, "que carbon · servo · thân")):
        if col in (SIGNAL, INK):
            ax.plot([cx0, cx0 + 7], [y + 1.2, y + 1.2], color=col, lw=1.0)
        else:
            ax.add_patch(Rectangle((cx0, y - 0.6), 7, 3.6, fc=col, alpha=0.75, ec="none"))
        ax.text(cx0 + 10, y + 1.2, lab, fontsize=6.2, family=SANS, color=INK, va="center")
        y -= 7
    ax.text(PAGE[0] - m - 8, m + 7, "membrane cartography · design/drawings · tất cả đường nét tính từ butterfly_params.json",
            fontsize=5.2, family=MONO, color=INK2, ha="right")

    OUT.mkdir(exist_ok=True)
    fig.savefig(OUT / "butterfly_cover.pdf", facecolor=PAPER)
    fig.savefig(OUT / "butterfly_cover.png", dpi=220, facecolor=PAPER)
    print("saved")


if __name__ == "__main__":
    main()
