"""1:1 construction drawings of the wing, generated from the same geometry as the CAD and the simulations.

Outputs (design/drawings/):
  wing_template_A2.pdf        two A2 pages (right wing, left wing), print at 100 % / "actual size"
  wing_template_A4_tiles.pdf  the same drawings tiled on A4 with 10 mm overlap and join marks
  rod_cut_list.md             carbon rods with cut lengths, positions and angles

Run with the analysis venv:  analysis/.venv/Scripts/python design/make_drawings.py
"""
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Polygon as MplPolygon, Rectangle, Circle

from matplotlib import font_manager

import wing_geometry as wg

# typography and palette shared with the dossier cover (drawings/design_philosophy.md)
FONTS = Path(r"C:\Users\Admin\.claude\skills\synced\84c7a5b4-017e-4de4-8045-680fd6db7772_92c80b8d-8e49-4727-88f7-7316049f950a\canvas-design\canvas-fonts")
for _f in ("Jura-Medium.ttf", "IBMPlexMono-Regular.ttf", "WorkSans-Regular.ttf", "WorkSans-Bold.ttf"):
    if (FONTS / _f).exists():
        font_manager.fontManager.addfont(str(FONTS / _f))
plt.rcParams["font.family"] = ["Work Sans", "DejaVu Sans"]
INK, INK2, FORE_C, HIND_C, SIGNAL, ACCENT = "#1d1c1a", "#8a857b", "#f6dcc0", "#f0c49a", "#c2402f", "#2a78d6"

OUT = Path(__file__).parent / "drawings"
OUT.mkdir(exist_ok=True)
IN = 1 / 25.4
A2 = (420, 594)
A4 = (210, 297)

W = wg.Wing()
P = W.prm
WRAP = P["wing"]["membrane_wrap_mm"]
SOCKET_BORE_START = 3.0      # mm from R, horn adapter (see fusion_build.py)
CONN_BORE_START = 1.0        # mm beyond the host-rod surface, printed vein connectors


def cut_list():
    rows = []
    rods = {r["name"]: r for r in W.rods()}
    for r in W.rods():
        if r["on"] is None:
            insert = SOCKET_BORE_START
            where = "khớp nối tay servo (gốc R)"
        else:
            insert = rods[r["on"]]["od"] / 2 + CONN_BORE_START
            where = "khớp %s trên que %s, cách R %.0f mm" % (r["name"][-1], r["on"], r["t"])
        host_ang = ""
        if r["on"] is not None:
            h = rods[r["on"]]
            a1 = math.atan2(h["b"][1] - h["a"][1], h["b"][0] - h["a"][0])
            a2 = math.atan2(r["b"][1] - r["a"][1], r["b"][0] - r["a"][0])
            host_ang = "%.0f°" % abs(math.degrees((a2 - a1 + math.pi) % (2 * math.pi) - math.pi))
        mat = "ống carbon %.1f×%.1f" % (r["od"], r["id"]) if r["id"] else "que carbon đặc Ø%.1f" % r["od"]
        rows.append(dict(name=r["name"], mat=mat, L=r["length"], cut=r["length"] - insert, where=where,
                         ang=host_ang, panel="sau" if r["name"] in W.HIND_RODS else "trước"))
    return rows


def wrap_tab(a, b, side_sign):
    """Rectangle-ish tab of width WRAP along edge a->b on its outer side, ends chamfered 45 deg."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy)
    ux, uy = dx / L, dy / L
    nx, ny = uy * side_sign, -ux * side_sign
    a2 = (a[0] + ux * WRAP + nx * WRAP, a[1] + uy * WRAP + ny * WRAP)
    b2 = (b[0] - ux * WRAP + nx * WRAP, b[1] - uy * WRAP + ny * WRAP)
    return [a, b, b2, a2]


def draw_wing(ax, mirror, title):
    s = 1 if mirror else -1          # right wing seen from above: x to the right (forward), span down the page
    T = lambda p: (p[0], s * p[1])
    outline = [T(p) for p in W.outline(16)]
    fore = [T(p) for p in W.fore_panel(16)]
    hind = [T(p) for p in W.hind_panel(16)]
    ax.add_patch(MplPolygon(fore, closed=True, fc=FORE_C, ec="none"))
    ax.add_patch(MplPolygon(hind, closed=True, fc=HIND_C, ec="none"))
    ax.add_patch(MplPolygon(outline, closed=True, fill=False, ec=INK, lw=1.2))
    # wrap tabs (membrane folded round the LE and root rods)
    for a, b in ((W.R, W.LE_END), (W.E, W.R)):
        tab = [T(p) for p in wrap_tab(a, b, 1)]
        ax.add_patch(MplPolygon(tab, closed=True, fill=False, ec=INK, lw=0.8, ls=(0, (6, 3))))
    # fold line
    ax.plot(*zip(T(W.R), T(W.N)), color=SIGNAL, lw=1.0, ls=(0, (10, 4, 2, 4)))
    mid = T(((W.R[0] + W.N[0]) / 2, (W.R[1] + W.N[1]) / 2))
    ang = math.degrees(math.atan2(T(W.N)[1] - T(W.R)[1], T(W.N)[0] - T(W.R)[0]))
    if ang > 90 or ang < -90:          # keep text upright
        ang += 180
    ax.text(mid[0] - 12, mid[1], "ĐƯỜNG GẤP — que Ø1.0 dán dọc; gập phần sau xuống %.1f°" % math.degrees(W.beta),
            rotation=ang, rotation_mode="anchor", fontsize=7, color=SIGNAL, ha="center", va="bottom")
    # rods
    cl = {r["name"]: r for r in cut_list()}
    colors = {"LE": INK, "Fold": SIGNAL, "Root": INK}
    for r in W.rods():
        a, b = T(r["a"]), T(r["b"])
        ax.plot(*zip(a, b), color=colors.get(r["name"], INK), lw=max(r["od"], 0.6) * 1.4, solid_capstyle="butt")
        k = 0.3 if r["name"] == "Fold" else 0.55          # keep the fold-rod label clear of the fold-line note
        mx, my = (a[0] * (1 - k) + b[0] * k), (a[1] * (1 - k) + b[1] * k)
        ra = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
        if ra > 90 or ra < -90:
            ra += 180
        c = cl[r["name"]]
        ax.text(mx, my, " %s  %s  cắt %.1f mm " % (r["name"], c["mat"], c["cut"]), rotation=ra, rotation_mode="anchor",
                fontsize=6.5, ha="center", va="bottom", color=INK2, family="IBM Plex Mono")
        if r["on"] is not None:
            ax.add_patch(Circle(a, 2.2, fill=False, ec=ACCENT, lw=0.8))
            ax.text(a[0] + 3, a[1] + 3 * s, "khớp %s (t=%d)" % (r["name"][-1], r["t"]), fontsize=6, color=ACCENT)
    # reference marks
    ax.add_patch(Circle(T(W.R), 3, fill=False, ec="black", lw=0.8))
    ax.plot([T(W.R)[0] - 6, T(W.R)[0] + 6], [T(W.R)[1]] * 2, "k", lw=0.5)
    ax.plot([T(W.R)[0]] * 2, [T(W.R)[1] - 6, T(W.R)[1] + 6], "k", lw=0.5)
    ax.text(T(W.R)[0] + 5, T(W.R)[1] - 9 * s, "R — gốc cánh / tâm khớp nối tay servo", fontsize=6.5)
    for p, lab in ((W.LE_END, "đầu que cạnh trước"), (W.N, "N — đỉnh chỗ khuyết"), (W.E, "E — cuối que gốc")):
        ax.plot(*T(p), "k+", ms=7)
        ax.text(T(p)[0] + 3, T(p)[1] + 3, lab, fontsize=6)
    ax.text(-290, 16 if s < 0 else -12, title, fontsize=11, family="Jura", color=INK, va="bottom" if s < 0 else "top")


def scale_bar(ax, x, y):
    ax.add_patch(Rectangle((x, y), 100, 4, fc=INK))
    for k in range(0, 101, 10):
        ax.plot([x + k, x + k], [y, y - (3 if k % 50 else 6)], "k", lw=0.6)
    ax.text(x, y + 6, "Thước kiểm tra: phải đo đúng 100 mm (và ô vuông 50 × 50 mm)", fontsize=6.5)
    ax.add_patch(Rectangle((x + 120, y - 16), 50, 50, fill=False, ec="black", lw=0.8))
    ax.text(x + 122, y - 14, "50 × 50 mm", fontsize=6)


def notes(ax, x, y):
    """Cut list as a column-aligned table (proportional font: the monospace font lacks Vietnamese glyphs)."""
    rows = cut_list()
    ax.text(x, y, "CẮT QUE CARBON (mỗi cánh; nhân 2 cho cả bướm)", fontsize=7, weight="bold", va="top")
    cols = [(0, "Que"), (16, "Vật liệu"), (58, "Dài thiết kế"), (82, "CHIỀU DÀI CẮT"), (110, "Tấm"), (122, "Gắn vào"), (205, "Góc")]
    yy = y - 5
    for dx, h in cols:
        ax.text(x + dx, yy, h, fontsize=6.3, weight="bold", va="top")
    for r in rows:
        yy -= 3.6
        vals = [r["name"], r["mat"], "%.1f mm" % r["L"], "%.1f mm" % r["cut"], r["panel"], r["where"], r["ang"] or "—"]
        for (dx, _), v in zip(cols, vals):
            ax.text(x + dx, yy, v, fontsize=6.3, va="top", weight="bold" if dx == 82 else "normal")
    fa, ha = W.areas()
    lines = ["MÀNG: 1 tấm liền mỗi bên, %.0f cm² (tấm trước %.0f + tấm sau %.0f); chừa mép bọc %d mm (nét đứt) quanh que cạnh trước và que gốc." % ((fa + ha) / 100, fa / 100, ha / 100, WRAP),
             "GẤP: dán que gấp Ø1.0 dọc đường gấp R–N; phần sau gập xuống %.1f° → cánh sau cúi %.0f°, rủ thêm %.1f°. Không dán que dọc mép sau (để màng tự xoắn)." %
             (math.degrees(W.beta), abs(P["wing"]["hind_incidence_deg"]), math.degrees(W.hind_extra_anhedral)),
             "Góc nhị diện %.0f° do khớp nối tay servo tạo sẵn. Dán màng hơi chùng; keo 3M Super 77 (mylar) hoặc B7000 (vải)." % P["wing"]["dihedral_deg"],
             "Kiểm tra trước khi cắt: thước 100 mm và ô 50 mm phải đúng kích thước sau khi in."]
    ax.text(x, yy - 6, "\n".join(lines), fontsize=6.3, va="top", linespacing=1.5)


def title_block(fig, size_mm, sheet, of):
    """Engineering title block, bottom-right corner of the sheet (figure coordinates in mm)."""
    w, h = 120, 26
    x0, y0 = size_mm[0] - 10 - w, 10
    tb = fig.add_axes([x0 / size_mm[0], y0 / size_mm[1], w / size_mm[0], h / size_mm[1]])
    tb.set_xlim(0, w)
    tb.set_ylim(0, h)
    tb.axis("off")
    tb.add_patch(Rectangle((0, 0), w, h, fill=False, ec=INK, lw=0.8))
    for yy in (9, 17):
        tb.plot([0, w], [yy, yy], color=INK, lw=0.4)
    tb.plot([78, 78], [0, 17], color=INK, lw=0.4)
    tb.text(3, 21.5, "BƯỚM RC · 2 SERVO · v3 — MẪU CẮT CÁNH", fontsize=8, family="Jura", color=INK, va="center")
    tb.text(3, 13, "tỉ lệ 1 : 1 · in 100 % / Actual size", fontsize=6.5, color=INK, va="center")
    tb.text(3, 4.5, "nguồn: butterfly_params.json · wing_geometry.py", fontsize=5.5, family="IBM Plex Mono", color=INK2, va="center")
    tb.text(81, 13, "tờ %d / %d" % (sheet, of), fontsize=6.5, family="IBM Plex Mono", color=INK, va="center")
    tb.text(81, 4.5, "2026-10-05 · mm", fontsize=6, family="IBM Plex Mono", color=INK2, va="center")


def page(fig_size_mm, window, mirror, title, with_notes=True):
    fig = plt.figure(figsize=(fig_size_mm[0] * IN, fig_size_mm[1] * IN))
    m = 10
    ax = fig.add_axes([m / fig_size_mm[0], m / fig_size_mm[1], 1 - 2 * m / fig_size_mm[0], 1 - 2 * m / fig_size_mm[1]])
    x0, y0 = window
    ax.set_xlim(x0, x0 + fig_size_mm[0] - 2 * m)
    ax.set_ylim(y0, y0 + fig_size_mm[1] - 2 * m)
    ax.set_aspect("equal")
    ax.axis("off")
    draw_wing(ax, mirror, title)
    if with_notes:
        scale_bar(ax, -290, -480 if not mirror else -150)
        notes(ax, -290, -398 if not mirror else -28)
    return fig, ax


def main():
    sides = [(False, "CÁNH PHẢI — nhìn từ trên, mép trước bên phải, tỉ lệ 1:1"),
             (True, "CÁNH TRÁI — nhìn từ trên, mép trước bên phải, tỉ lệ 1:1")]
    # A2 full size: drawing window chosen so the wing (x -290..45, |y| 0..390) and the notes fit
    with PdfPages(OUT / "wing_template_A2.pdf") as pdf:
        for mirror, title in sides:
            window = (-300, -500) if not mirror else (-300, -180)
            fig, _ = page(A2, window, mirror, title)
            title_block(fig, A2, 1 if not mirror else 2, 2)
            pdf.savefig(fig)
            plt.close(fig)
    # A4 tiles with 10 mm overlap
    with PdfPages(OUT / "wing_template_A4_tiles.pdf") as pdf:
        for mirror, title in sides:
            xmin, xmax = -300, 50
            ymin, ymax = (-400, 20) if not mirror else (-20, 400)
            vw, vh = A4[0] - 20, A4[1] - 20
            step_x, step_y = vw - 10, vh - 10
            nx = math.ceil((xmax - xmin - 10) / step_x)
            ny = math.ceil((ymax - ymin - 10) / step_y)
            for j in range(ny):
                for i in range(nx):
                    wx, wy = xmin + i * step_x, ymax - vh - j * step_y
                    fig, ax = page(A4, (wx, wy), mirror, title, with_notes=False)
                    # overlap / join marks
                    for xx in (wx + 10, wx + vw - 10):
                        ax.axvline(xx, color="#888888", lw=0.4, ls=":")
                    for yy in (wy + 10, wy + vh - 10):
                        ax.axhline(yy, color="#888888", lw=0.4, ls=":")
                    for cx, cy in ((wx + 5, wy + 5), (wx + vw - 5, wy + 5), (wx + 5, wy + vh - 5), (wx + vw - 5, wy + vh - 5)):
                        ax.plot([cx - 3, cx + 3], [cy, cy], "k", lw=0.5)
                        ax.plot([cx, cx], [cy - 3, cy + 3], "k", lw=0.5)
                    ax.text(wx + 12, wy + vh - 14, "%s — trang %s%d  (cột %d/%d, hàng %d/%d)  ghép chồng 10 mm theo nét chấm" %
                            ("PHẢI" if not mirror else "TRÁI", "ABCD"[j], i + 1, i + 1, nx, j + 1, ny), fontsize=6.5)
                    ax.add_patch(Rectangle((wx + 12, wy + 12), 50, 3, fc="black"))
                    ax.text(wx + 12, wy + 17, "50 mm", fontsize=6)
                    pdf.savefig(fig)
                    plt.close(fig)
    # cut list markdown
    rows = cut_list()
    md = ["# Danh sách cắt que carbon — mỗi cánh (nhân 2 cho cả bướm)", "",
          "| Que | Vật liệu | Dài thiết kế (mm) | **Chiều dài cắt (mm)** | Tấm | Gắn vào | Góc với que gốc |",
          "|---|---|---|---|---|---|---|"]
    for r in rows:
        md.append("| %s | %s | %.1f | **%.1f** | %s | %s | %s |" % (r["name"], r["mat"], r["L"], r["cut"], r["panel"], r["where"], r["ang"] or "—"))
    fa, ha = W.areas()
    md += ["", "- Chiều dài cắt = dài thiết kế trừ phần nằm trong lỗ khớp (khớp nối tay servo: lỗ bắt đầu cách R %.0f mm; khớp gân: cách mặt que gốc %.0f mm)." % (SOCKET_BORE_START, CONN_BORE_START),
           "- Màng mỗi bên: %.0f cm² (tấm trước %.0f, tấm sau %.0f) + mép bọc %d mm quanh que cạnh trước và que gốc." % ((fa + ha) / 100, fa / 100, ha / 100, WRAP),
           "- Gấp: phần sau gập xuống %.2f° quanh que gấp R–N → cánh sau cúi %.1f°, rủ thêm %.1f°." % (math.degrees(W.beta), abs(P["wing"]["hind_incidence_deg"]), math.degrees(W.hind_extra_anhedral)),
           "- Xương sống: ống carbon vuông %.0f mm, dài %.0f mm (1 cây)." % (P["body"]["spine"]["section"], P["body"]["spine"]["length"])]
    (OUT / "rod_cut_list.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
