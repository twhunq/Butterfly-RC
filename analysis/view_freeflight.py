"""Interactive 3D replay of the free-flight simulations (results/freeflight/*.csv).

The butterfly is drawn from the same geometry as the CAD and the simulation (wing_geometry.py +
butterfly_params.json, CG from fusion_mass_properties.json). Body pose comes from the CSV; the wings
flap with the prescribed sine (amplitude / frequency read from the file name, e.g. _a12.5_L14.5).

Run:  .venv/Scripts/python view_freeflight.py [csv ...]      (default: every cg23_*.csv)
Playback follows the wall clock: x1 = real time (2.5 Hz = 0.4 s per wing beat); up/down halve or double it.
Keys: space play/pause · left/right step · up/down speed · r reload file list · drag to rotate · click a time plot to jump.
"""
import glob
import math
import re
import sys
import time
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.widgets import RadioButtons
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from design_link import WING_GEOM, WING, SERVO, MASSPROPS, PARAMS
import wing_geometry

HERE = Path(__file__).parent
FF = HERE / "results" / "freeflight"
RELEASE = 0.8                              # s: prescribed body motion -> free flight (ptera_freeflight.py)
ROOT = tuple(WING["root"])
AXIS_Y, AXIS_Z = SERVO["shaft_y"], SERVO["shaft_z"]
CG = np.array(MASSPROPS["cg_mm"])
BODY = wing_geometry.body_layout(PARAMS)

FORE_C, HIND_C, BODY_C = "#eb6834", "#2a78d6", "#222222"


def _base_panels():
    """Fore / hind panels of each side in the model frame (mm), unflapped: computed once."""
    out = []
    for sgn in (1, -1):
        for poly, hind in ((WING_GEOM.fore_panel(n=6), False), (WING_GEOM.hind_panel(n=6), True)):
            out.append((sgn, np.array([wing_geometry.to_model(WING_GEOM, WING_GEOM.fold(p, hind), sgn, ROOT)
                                       for p in poly])))
    return out


BASE = _base_panels()


def panels(theta_r, theta_l):
    """Wing panels in the body frame (m, x fwd, y right, z up, origin at the CG) for flap angles in rad."""
    out = []
    for sgn, pts in BASE:
        a = (theta_r if sgn > 0 else theta_l) * sgn   # right wing: +x rotation lifts the tip; left: mirrored
        c, s = math.cos(a), math.sin(a)
        y0, z0 = pts[:, 1] - sgn * AXIS_Y, pts[:, 2] - AXIS_Z
        q = np.column_stack((pts[:, 0], sgn * AXIS_Y + y0 * c - z0 * s, AXIS_Z + y0 * s + z0 * c))
        out.append((q - CG) / 1000)
    return out


def body_line():
    x0, x1 = BODY["spine_x"]
    return (np.array([[x1, 0, BODY["zc"]], [x0, 0, BODY["zc"]]]) - CG) / 1000


def rot(yaw, pitch, roll):
    """Body FRD -> Earth NED (deg), z-y-x order as in the CSV."""
    y, p, r = map(math.radians, (yaw, pitch, roll))
    cy, sy, cp, sp, cr, sr = math.cos(y), math.sin(y), math.cos(p), math.sin(p), math.cos(r), math.sin(r)
    return np.array([[cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
                     [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
                     [-sp, cp * sr, cp * cr]])


FLU2FRD = np.diag([1.0, 1.0, -1.0])        # body model frame (z up) <-> FRD
NED2PLOT = np.diag([1.0, 1.0, -1.0])        # plot: x fwd, y right, z up (right-handed view flipped below)


def parse(f):
    n = Path(f).stem
    amp = float(re.search(r"_a([\d.]+)", n).group(1))
    m = re.search(r"_L([\d.]+)", n)
    freq = float(re.search(r"_f([\d.]+)", n).group(1))
    return amp, (float(m.group(1)) if m else amp), freq


def label(f):
    a, al, fr = parse(f)
    return ("±%g° %g Hz" % (a, fr)) if a == al else ("P %g° / T %g°" % (a, al))


class Viewer:
    """Blitted animation: axes, panes and plots are drawn once and cached; each frame only redraws the
    moving artists (wings, body, trail, cursors, readout). A full redraw (rotate, resize, new run)
    re-captures the cache through the draw_event."""

    def __init__(self, files):
        self.files = files
        self.k = 0
        self.speed = 1.0                                    # x real time
        self.playing = True
        self.bg = None
        self.t_sim = 0.0
        self.last_wall = time.perf_counter()
        self.fig = plt.figure(figsize=(14, 7.5))
        self.fig.canvas.manager.set_window_title("Butterfly RC - bay tự do (Ptera UVLM + MuJoCo)")
        ax = self.ax = self.fig.add_axes([0.17, 0.04, 0.46, 0.95], projection="3d")
        ax.set_proj_type("ortho")
        ax.set_xlim(-0.5, 0.5); ax.set_ylim(0.5, -0.5); ax.set_zlim(-0.45, 0.55)
        ax.set_box_aspect((1, 1, 1))
        ax.set_xlabel("x trước (m)"); ax.set_ylabel("y phải (m)"); ax.set_zlabel("z lên (m)")
        ax.view_init(elev=24, azim=-145)
        self.ts = [self.fig.add_axes([0.66, 0.70 - 0.22 * i, 0.32, 0.18]) for i in range(3)]
        self.rax = self.fig.add_axes([0.005, 0.62, 0.16, 0.34], frameon=False)
        self.hud = self.fig.text(0.01, 0.06, "", family="monospace", fontsize=9.5, animated=True)
        self.build_radio()
        self.wings = [Poly3DCollection([np.zeros((3, 3))], alpha=0.55, edgecolor="k", linewidths=0.4,
                                       facecolor=c, animated=True) for c in (FORE_C, HIND_C, FORE_C, HIND_C)]
        for w in self.wings:
            ax.add_collection3d(w)
        self.spine, = ax.plot([], [], [], color=BODY_C, lw=3, animated=True)
        self.trail, = ax.plot([], [], [], color="#1baf7a", lw=1.2, animated=True)
        self.shadow, = ax.plot([], [], [], color="#999999", lw=1, ls=":", animated=True)
        self.grid = [ax.plot([], [], [], color="#bbbbbb", lw=0.6, animated=True)[0] for _ in range(26)]
        self.fig.canvas.mpl_connect("draw_event", self.on_draw)
        self.fig.canvas.mpl_connect("key_press_event", self.key)
        self.fig.canvas.mpl_connect("button_press_event", self.click)
        self.load()
        self.timer = self.fig.canvas.new_timer(interval=50)
        self.timer.add_callback(self.tick)
        self.timer.start()

    def build_radio(self):
        self.rax.clear()
        self.radio = RadioButtons(self.rax, [label(f) for f in self.files], active=self.k)
        self.radio.on_clicked(lambda lab: self.select([label(f) for f in self.files].index(lab)))

    def select(self, k):
        self.k = k
        self.load()

    def load(self):
        f = self.files[self.k]
        d = np.loadtxt(f, delimiter=",", skiprows=1)
        # a diverged run ends with a few rows of numerical blow-up (MuJoCo NaN): cut them off
        jump = np.nonzero(np.abs(np.diff(d[:, 1])) > 0.5)[0]
        self.d = d[: jump[0] + 1] if len(jump) else d
        self.diverged = len(jump) > 0 or len(d) < 250
        self.amp_r, self.amp_l, self.freq = parse(f)
        self.i = 0
        self.t_sim = 0.0
        d = self.d
        for ax, (col, name) in zip(self.ts, ((9, "độ cao (m)"), (6, "góc nghiêng roll (°)"), (5, "góc chúc pitch (°)"))):
            ax.clear()
            y = -d[:, col] if col == 9 else d[:, col]
            ax.plot(d[:, 0], y, color="#2a78d6", lw=1.4)
            ax.axvline(RELEASE, color="#888888", lw=0.8, ls=":")
            ax.set_title(name, loc="left", fontsize=9)
            ax.grid(color="#eeeeee")
            ax.tick_params(labelsize=8)
            ax.cursor = ax.axvline(0, color="#eb6834", lw=1.2, animated=True)
            if col == 6:                                    # roll: at least +-2 deg so numerical noise looks flat
                lo, hi = ax.get_ylim()
                ax.set_ylim(min(lo, -2), max(hi, 2))
        self.ts[-1].set_xlabel("thời gian (s) · nét chấm: thả tự do · bấm vào biểu đồ để tua", fontsize=8)
        self.fig.suptitle(Path(f).name + ("   (mô phỏng dừng sớm: bướm mất ổn định)" if self.diverged else ""),
                          x=0.62, ha="left", fontsize=10)
        self.update()
        self.fig.canvas.draw_idle()                         # full redraw -> on_draw re-captures the cache

    def animated(self):
        return self.wings + [self.spine, self.trail, self.shadow] + self.grid

    def on_draw(self, _):
        self.bg = self.fig.canvas.copy_from_bbox(self.fig.bbox)
        self.paint()

    def paint(self):
        for a in self.animated():
            if hasattr(a, "do_3d_projection"):
                a.do_3d_projection()
            self.ax.draw_artist(a)
        for a in self.ts:
            a.draw_artist(a.cursor)
        self.fig.draw_artist(self.hud)

    def blit(self):
        if self.bg is None:
            self.fig.canvas.draw_idle()
            return
        self.fig.canvas.restore_region(self.bg)
        self.paint()
        self.fig.canvas.blit(self.fig.bbox)

    def click(self, e):
        if e.inaxes in self.ts and e.xdata is not None:
            self.i = int(np.clip(np.searchsorted(self.d[:, 0], e.xdata), 0, len(self.d) - 1))
            self.t_sim = self.d[self.i, 0]
            self.update(); self.blit()

    def key(self, e):
        if e.key == " ":
            self.playing = not self.playing
        elif e.key == "right":
            self.i = min(self.i + 1, len(self.d) - 1)
            self.t_sim = self.d[self.i, 0]
        elif e.key == "left":
            self.i = max(self.i - 1, 0)
            self.t_sim = self.d[self.i, 0]
        elif e.key == "up":
            self.speed = min(self.speed * 2, 4.0)
        elif e.key == "down":
            self.speed = max(self.speed / 2, 1 / 16)
        elif e.key == "r":
            cur = self.files[self.k]
            self.files = default_files()
            self.k = self.files.index(cur) if cur in self.files else 0
            self.build_radio()
            self.load()
            return
        self.update(); self.blit()

    def tick(self):
        now = time.perf_counter()
        dt, self.last_wall = now - self.last_wall, now
        if self.playing:                                    # advance by the real elapsed time, so a slow
            self.t_sim += min(dt, 0.25) * self.speed        # redraw drops frames instead of slowing time
            if self.t_sim > self.d[-1, 0]:
                self.t_sim = 0.0
            self.i = int(min(np.searchsorted(self.d[:, 0], self.t_sim), len(self.d) - 1))
            self.update()
            self.blit()

    def update(self):
        row = self.d[self.i]
        t, V, alpha, beta, yaw, pitch, roll = row[:7]
        pos = row[7:10]                                     # NED, m
        R = rot(yaw, pitch, roll)
        ph = 2 * math.pi * self.freq * t
        th_r, th_l = math.radians(self.amp_r) * math.sin(ph), math.radians(self.amp_l) * math.sin(ph)

        def world(p_body):                                  # body (z up) -> plot frame, relative to CG
            return (NED2PLOT @ (R @ (FLU2FRD @ p_body.T))).T

        for w, p in zip(self.wings, panels(th_r, th_l)):
            w.set_verts([world(p)])
        sp = world(body_line())
        self.spine.set_data_3d(sp[:, 0], sp[:, 1], sp[:, 2])

        past = self.d[: self.i + 1, 7:10] - pos              # trail relative to the current CG
        past = past @ NED2PLOT
        self.trail.set_data_3d(past[:, 0], past[:, 1], past[:, 2])
        floor = -0.45
        self.shadow.set_data_3d(past[:, 0], past[:, 1], np.full(len(past), floor))
        # world-fixed floor grid, scrolls past as the butterfly flies
        gx = np.arange(math.floor(pos[0] / 0.1) * 0.1 - 0.6, pos[0] + 0.7, 0.1) - pos[0]
        lines = [([x, x], [-0.5, 0.5]) for x in gx[:13]] + [([-0.5, 0.5], [y, y]) for y in np.linspace(-0.5, 0.5, 11)]
        for g, (xs, ys) in zip(self.grid, lines + [([], [])] * (len(self.grid) - len(lines))):
            g.set_data_3d(xs, ys, [floor] * len(xs))

        climb = 0.0
        j = np.searchsorted(self.d[:, 0], t - 0.4)
        if self.i - j > 2:
            climb = -(pos[2] - self.d[j, 9]) / (t - self.d[j, 0])
        self.hud.set_text(
            "%s\n t      %5.2f s  %s\n V      %5.2f m/s\n alpha  %5.1f°\n pitch  %5.1f°\n roll   %5.1f°\n yaw    %5.1f°\n"
            " leo    %+5.2f m/s (0,4 s)\n đã bay %5.1f m, độ cao %+5.2f m\n vỗ %.1f Hz = %.2f s/nhịp\n"
            " phát x%s thời gian thực (↑↓) · space dừng"
            % (label(self.files[self.k]), t, "THẢ TỰ DO" if t >= RELEASE else "giữ cố định", V, alpha, pitch, roll,
               yaw, climb, pos[0], -pos[2], self.freq, 1 / self.freq,
               ("%g" % self.speed) if self.speed >= 1 else "1/%d" % round(1 / self.speed)))
        for a in self.ts:
            a.cursor.set_xdata([t, t])


def default_files():
    fs = sorted(glob.glob(str(FF / "cg23_*.csv")), key=lambda f: (parse(f)[0] != parse(f)[1], parse(f)[0]))
    return fs


if __name__ == "__main__":
    files = sys.argv[1:] or default_files()
    if not files:
        sys.exit("no results/freeflight/cg23_*.csv yet")
    Viewer(files)
    plt.show()
