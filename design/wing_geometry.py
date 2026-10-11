"""Wing geometry shared by the Fusion build and every simulation (pure Python, no numpy).

One continuous membrane per side, cut flat from a single template and folded along a straight
fold rod (root -> notch). Everything forward of the fold is the fore panel, in the wing plane;
the hind panel is rotated about the fold line so that it gets the design nose-down incidence.

Wing-local frame (mm): x forward, y spanwise from the root point R (the horn adapter), z up
(normal to the fore panel). Outline segments:
    R --(straight, along the LE rod)--> LE end --(fore curve)--> notch N
      --(hind curve)--> root-edge end E --(straight, along the root rod)--> R
"""
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def load_params(path=None):
    with open(path or os.path.join(HERE, "butterfly_params.json"), encoding="utf-8") as fh:
        return json.load(fh)


def catmull_open(pts, n):
    """Centripetal-free uniform Catmull-Rom through pts (open curve, end tangents from mirrored points)."""
    p = [tuple(map(float, q)) for q in pts]
    ext = [(2 * p[0][0] - p[1][0], 2 * p[0][1] - p[1][1])] + p + [(2 * p[-1][0] - p[-2][0], 2 * p[-1][1] - p[-2][1])]
    out = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        for k in range(n):
            t = k / n
            out.append(tuple(0.5 * (2 * p1[j] + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t * t
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t ** 3) for j in range(2)))
    out.append(p[-1])
    return out


def line(a, b, step=2.0):
    n = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / step))
    return [(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n) for k in range(n + 1)]


class Wing:
    def __init__(self, prm=None):
        prm = prm or load_params()
        w = prm["wing"]
        self.prm = prm
        self.R = (0.0, 0.0)
        self.LE_END = tuple(w["le_rod"]["end"])
        self.N = tuple(w["outline"]["notch"])
        self.E = tuple(w["outline"]["root_edge_end"])
        self.fore_curve = [self.LE_END] + [tuple(p) for p in w["outline"]["fore_curve"]] + [self.N]
        self.hind_curve = [self.N] + [tuple(p) for p in w["outline"]["hind_curve"]] + [self.E]
        self.dihedral = math.radians(w["dihedral_deg"])
        # fold axis (unit, wing plane) and fold angle giving the requested hind-panel incidence
        L = math.hypot(*self.N)
        self.u = (self.N[0] / L, self.N[1] / L)
        self.incidence = math.radians(w["hind_incidence_deg"])          # negative = nose down
        self.beta = abs(self.incidence) / abs(self.u[1])                # fold angle about the fold line
        self.hind_extra_anhedral = self.beta * abs(self.u[0])           # roll component of the fold
        # rods lying in the hind panel: the root rod and every vein that branches off the fold rod
        self.HIND_RODS = ("Root",) + tuple("Vein" + v["name"] for v in w["veins"] if v["on"] == "Fold")

    # -------------------------------------------------------------- 2D (flat template)
    def outline(self, n=12):
        """Closed flat outline (list of points, no repeat), counter-clockwise from R."""
        pts = line(self.R, self.LE_END)[:-1]
        pts += catmull_open(self.fore_curve, n)[:-1]
        pts += catmull_open(self.hind_curve, n)[:-1]
        pts += line(self.E, self.R)[:-1]
        return pts

    def fore_panel(self, n=12):
        return line(self.R, self.LE_END)[:-1] + catmull_open(self.fore_curve, n)[:-1] + line(self.N, self.R)[:-1]

    def hind_panel(self, n=12):
        return line(self.R, self.N)[:-1] + catmull_open(self.hind_curve, n)[:-1] + line(self.E, self.R)[:-1]

    def is_hind(self, p):
        """True if a flat point lies aft of the fold line (left of R->N when looking along it)."""
        return self.u[0] * p[1] - self.u[1] * p[0] > 1e-9

    # -------------------------------------------------------------- folding
    def fold(self, p, hind=None):
        """Flat point (x, y) -> wing-local 3D (x, y, z). Points of the hind panel rotate rigidly about the
        fold line. Pass hind=True/False when the panel is known (part of the hind lobe lies beyond the
        notch, on the far side of the extended fold line); otherwise the side of the fold line decides."""
        x, y = p[0], p[1]
        if hind is None:
            hind = self.is_hind(p)
        if not hind:
            return (x, y, 0.0)
        g = -self.beta                         # sign chosen so the hind trailing edge goes down
        ux, uy = self.u
        c, s = math.cos(g), math.sin(g)
        dot = ux * x + uy * y
        cx, cy, cz = 0.0, 0.0, ux * y - uy * x  # u x v (u, v in plane)
        return (x * c + cx * s + ux * dot * (1 - c), y * c + cy * s + uy * dot * (1 - c), cz * s)

    # -------------------------------------------------------------- rods (flat endpoints)
    def rods(self):
        w = self.prm["wing"]
        le = w["le_rod"]
        L = math.hypot(*self.LE_END)
        d = (self.LE_END[0] / L, self.LE_END[1] / L)
        out = [dict(name="LE", a=self.R, b=self.LE_END, od=le["od"], id=le["id"], on=None)]
        out.append(dict(name="Fold", a=self.R, b=self.N, od=w["fold_rod"]["d"], id=0.0, on=None))
        out.append(dict(name="Root", a=self.R, b=self.E, od=w["root_rod"]["d"], id=0.0, on=None))
        fu = self.u
        for v in w["veins"]:
            host_dir, host = (d, "LE") if v["on"] == "LE" else (fu, "Fold")
            a = (host_dir[0] * v["t"], host_dir[1] * v["t"])
            out.append(dict(name="Vein" + v["name"], a=a, b=tuple(v["end"]), od=v["d"], id=0.0, on=host, t=v["t"]))
        for r in out:
            r["length"] = math.hypot(r["b"][0] - r["a"][0], r["b"][1] - r["a"][1])
        return out

    def areas(self):
        def area(poly):
            s = 0.0
            for i in range(len(poly)):
                x0, y0 = poly[i]
                x1, y1 = poly[(i + 1) % len(poly)]
                s += x0 * y1 - x1 * y0
            return abs(s) / 2
        return area(self.fore_panel()), area(self.hind_panel())


def body_layout(prm=None):
    """Abdomen layout (model frame, mm) shared by the Fusion build and the drawings.

    The round carbon spine runs from x_front aft; its centre sits under the servo mounting ears. The
    AvionicsMount clip carries the Nano (USB forward) and, behind it, the NRF24 module; the spine stops
    carbon_under_header mm under the NRF24 so the PCB antenna overhangs clear of carbon."""
    prm = prm or load_params()
    bd, sv, pr = prm["body"], prm["servo"], prm["printed"]
    sp, nano, nrf = bd["spine"], bd["nano"], bd["nrf24"]
    rb = sp["od"] / 2 + sp["bore_clearance"]                        # bore radius in every printed sleeve
    r_frame = rb + pr["spine_sleeve_wall"]                          # servo-frame sleeve
    r_clip = rb + pr["clip_wall"]                                   # light clips
    ear_bottom = 0.2 - sv["ear_overhang"]                           # servo case sits 0.2 mm above z=0
    zc = ear_bottom - sp["ear_clearance"] - r_frame
    nx0, nx1 = nano["centre_x"] - nano["board"][0] / 2, nano["centre_x"] + nano["board"][0] / 2
    z_board = zc + r_clip + nano["under_clearance"]                 # underside of both boards
    rx1 = nx0 - nrf["gap_to_nano"]                                  # NRF24 header end (forward)
    rx0 = rx1 - nrf["board"][0]                                     # antenna end (aft)
    x_rear = rx1 - nrf["carbon_under_header"]
    return dict(rb=rb, r_frame=r_frame, r_clip=r_clip, zc=zc, ear_bottom=ear_bottom, z_board=z_board,
                nano_x=(nx0, nx1), nrf_x=(rx0, rx1), spine_x=(x_rear, sp["x_front"]),
                spine_length=sp["x_front"] - x_rear)


def to_model(wing, p_local3, sgn, root):
    """Wing-local 3D -> model frame (x fwd, y right, z up) with dihedral, for side sgn (+1 right, -1 left)."""
    x, y, z = p_local3
    cD, sD = math.cos(wing.dihedral), math.sin(wing.dihedral)
    return (root[0] + x, sgn * (root[1] + y * cD - z * sD), root[2] + y * sD + z * cD)
