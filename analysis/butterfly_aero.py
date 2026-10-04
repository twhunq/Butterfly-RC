"""Quasi-steady blade-element model of the 2-servo RC butterfly + carbon rod bending.

Geometry matches the Fusion model (wing outlines in wing-local coords: x forward, y span from root S).
Frames: path frame x forward (flight direction), z up. Right wing only; left wing is mirrored,
so vertical force and thrust are doubled and lateral forces cancel.

Run:  .venv/Scripts/python butterfly_aero.py
"""
import json
import math
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path(__file__).parent / "results"
OUT.mkdir(exist_ok=True)

RHO, G = 1.2, 9.81

# ---------------------------------------------------------------- geometry (mm), from design/butterfly_params.json
from design_link import (FORE, HIND, ROOT_X, R0, DIHEDRAL as DIHEDRAL_DEG, HIND_INCIDENCE, PARAMS, MASSPROPS,
                         mass_breakdown_g, rods as design_rods)

DIHEDRAL = math.radians(DIHEDRAL_DEG)
LE_DEFAULT = (PARAMS["wing"]["le_rod"]["od"] / 1000, PARAMS["wing"]["le_rod"]["id"] / 1000)


def catmull(pts, n=20):
    out, L = [], len(pts)
    for i in range(L):
        p0, p1, p2, p3 = (np.array(pts[(i + k) % L], float) for k in (-1, 0, 1, 2))
        for k in range(n):
            t = k / n
            out.append(0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t ** 2
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    return np.array(out)


def intervals_at(poly, y):
    """x-intervals where horizontal line at span y cuts the closed polygon."""
    xs = []
    for (x1, y1), (x2, y2) in zip(poly, np.roll(poly, -1, axis=0)):
        if (y1 <= y < y2) or (y2 <= y < y1):     # half-open, so a vertex on the line counts once
            xs.append(x1 + (y - y1) * (x2 - x1) / (y2 - y1))
    xs.sort()
    return [(xs[i], xs[i + 1]) for i in range(0, len(xs) - 1, 2)]


def union(iv):
    iv = sorted(iv)
    out = []
    for a, b in iv:
        if out and a <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def build_strips(dy=2.0):
    """Strips: (r [m], chord [m], x_quarter_chord_body [m], dy [m], is_fore)."""
    fore, hind = catmull(FORE, 1), catmull(HIND, 1)        # panels are already dense polygons
    strips = []
    ymax = max(fore[:, 1].max(), hind[:, 1].max())
    for y in np.arange(dy / 2, ymax, dy):
        fi, hi = intervals_at(fore, y), intervals_at(hind, y)
        for a, b in union(fi + hi):
            xle = b
            c = b - a
            is_fore = any(fa <= xle + 1e-6 and xle <= fb + 1e-6 for fa, fb in fi)
            strips.append(((R0 + y) / 1000, c / 1000, (ROOT_X + xle - c / 4) / 1000, dy / 1000, is_fore))
    return np.array(strips, dtype=float)


STRIPS = build_strips()
AREA_SIDE = float((STRIPS[:, 1] * STRIPS[:, 3]).sum())        # m^2, one side (union of fore+hind)
SPAN = 2 * (R0 + max(max(p[1] for p in FORE), max(p[1] for p in HIND))) / 1000 + 0.0124
AR = SPAN ** 2 / (2 * AREA_SIDE)

# ---------------------------------------------------------------- materials & masses
RHO_CF = 1550.0        # kg/m^3 pultruded carbon
E_CF = 120e9           # Pa (pultruded rod, 110-140 GPa)
SIG_ALLOW = 400e6      # Pa, fatigue allowable for ~1e6 cycles (UTS ~1500 MPa, SF ~3.5)
MEMBRANE_GSM = PARAMS["wing"]["membrane_gsm"]   # g/m^2 (12 um mylar + glue) ; P31N ripstop ~31 g/m^2

LE_LEN = design_rods()[0][1] / 1000              # m


def rod_props(od, idd=0.0):
    A = math.pi / 4 * (od ** 2 - idd ** 2)
    I = math.pi / 64 * (od ** 4 - idd ** 4)
    return A, I


def wing_mass_inertia(le=LE_DEFAULT, membrane_gsm=MEMBRANE_GSM):
    """Mass (kg) and flap-axis inertia (kg m^2) of one wing incl. adapter/connectors (rods from the design file)."""
    m, I = 0.0, 0.0
    dm = membrane_gsm / 1000 * STRIPS[:, 1] * STRIPS[:, 3]          # membrane, distributed like the strips
    m += dm.sum(); I += (dm * STRIPS[:, 0] ** 2).sum()
    for name, L, od, idd, p0, p1 in design_rods():
        if name == "LE":
            od, idd = le[0] * 1000, le[1] * 1000
        A, _ = rod_props(od / 1000, idd / 1000)
        s = np.linspace(0, 1, 60)
        y = p0[1] + (p1[1] - p0[1]) * s                              # spanwise position along the rod (mm)
        dmr = RHO_CF * A * (L / 1000) / 60
        m += dmr * 60; I += (dmr * ((R0 + y) / 1000) ** 2).sum()
    # adapter + 2 connectors + glue near root (PLA ~1.3 g at r~22 mm)
    m += 1.3e-3; I += 1.3e-3 * 0.022 ** 2
    return m, I


def body_mass(le=LE_DEFAULT):
    """Mass breakdown (g) and total mass (kg) as exported from the Fusion model."""
    return mass_breakdown_g(), MASSPROPS["mass_g"] / 1000


# ---------------------------------------------------------------- aero coefficients
def coeffs(alpha):
    """Blended attached / flat-plate post-stall model for a thin low-AR plate, Re~1e4-5e4."""
    a = alpha
    cla = 2 * math.pi / (1 + 2 / AR)
    cl_att = cla * a
    cd_att = 0.05 + cl_att ** 2 / (math.pi * 0.8 * AR)
    cl_sep = 2 * np.sin(a) * np.cos(a)
    cd_sep = 0.05 + 2 * np.sin(a) ** 2
    s = 1 / (1 + np.exp((np.abs(a) - math.radians(14)) / math.radians(3)))   # 1 attached, 0 separated
    return s * cl_att + (1 - s) * cl_sep, s * cd_att + (1 - s) * cd_sep


ETA = 0.6   # passive feathering ratio of the flexible membrane (0 = rigid plate, 1 = fully feathered)


def simulate(f, amp_deg, U, theta_deg, phi0_deg=DIHEDRAL_DEG, nt=240, cl_scale=1.0, le=LE_DEFAULT, eta=None):
    """Return time histories for one flap cycle (right wing; totals doubled where noted)."""
    t = np.linspace(0, 1 / f, nt, endpoint=False)
    w = 2 * math.pi * f
    A = math.radians(amp_deg)
    phi = math.radians(phi0_deg) + A * np.cos(w * t)
    dphi = -A * w * np.sin(w * t)
    ddphi = -A * w ** 2 * np.cos(w * t)
    th = math.radians(theta_deg)
    r, c, xq, dy = (STRIPS[:, k][None, :] for k in range(4))
    ut = U * math.cos(th) * np.ones_like(r)
    un = U * math.sin(th) * np.cos(phi)[:, None] - r * dphi[:, None]
    V2 = ut ** 2 + un ** 2
    V = np.sqrt(V2)
    eta = ETA if eta is None else eta
    # passive feathering: the membrane twists to cancel a fraction eta of the flap-induced angle
    alpha = np.arctan2(un, ut) - eta * np.arctan2(-r * dphi[:, None], ut)
    alpha = alpha + math.radians(HIND_INCIDENCE) * (1 - STRIPS[:, 4][None, :])   # hind wing set nose-down
    CL, CD = coeffs(alpha)
    q = 0.5 * RHO * V2 * c * dy
    L, D = cl_scale * q * CL, q * CD
    # lift is normal to the relative wind, drag along it (independent of section pitch)
    Fc = (L * un - D * ut) / V
    Fn_circ = (L * ut + D * un) / V
    ma = RHO * math.pi * c ** 2 / 4 * dy                       # added mass per strip
    Fn_am = -ma * r * ddphi[:, None]
    Fn = Fn_circ + Fn_am
    cphi = np.cos(phi)[:, None]
    T = Fc * math.cos(th) - Fn * math.sin(th) * cphi
    Z = Fc * math.sin(th) + Fn * math.cos(th) * cphi
    _, Iw = wing_mass_inertia(le)
    M_aero = (Fn * r).sum(axis=1)
    tau = Iw * ddphi - M_aero                                   # servo torque, + = drives +phi (up)
    return dict(t=t, phi=phi, dphi=dphi, ddphi=ddphi, alpha=alpha, Fn=Fn, Fn_circ=Fn_circ, Z=Z, T=T,
                Zsum=2 * Z.sum(axis=1), Tsum=2 * T.sum(axis=1), tau=tau, M_aero=M_aero, xq=xq, Iw=Iw)


# ---------------------------------------------------------------- servo model
TAU_STALL = 7.5 * G / 100     # 7.5 kg.cm -> N.m (PTK 7465Plus listing)
OMEGA0 = math.radians(60) / 0.070   # 0.070 s/60deg @8.4 V (7465MG-D datasheet; Plus assumed same)


def servo_margin(res):
    """>=1 means the linear torque-speed servo can follow the commanded cosine at every instant."""
    w, tau = res["dphi"], res["tau"]
    motoring = tau * w > 0
    need = np.abs(w) / OMEGA0 + np.abs(tau) / TAU_STALL     # <=1 feasible (motoring quadrant)
    need = np.where(motoring, need, np.abs(tau) / TAU_STALL)
    return 1 / need.max(), (tau * w).clip(min=0).mean()


def body_drag(U):
    return 0.5 * RHO * U ** 2 * 1.0 * (0.03 * 0.03)


def trim(f, amp, W, cl_scale=1.0, le=LE_DEFAULT, eta=None):
    """Find (U, theta) with mean lift = W and mean thrust = body drag. Coarse grid + refine."""
    best = None
    for U in np.arange(0.8, 6.01, 0.1):
        for th in np.arange(-5, 30.1, 1.0):
            r = simulate(f, amp, U, th, nt=72, cl_scale=cl_scale, le=le, eta=eta)
            ez = (r["Zsum"].mean() - W) / W
            ex = (r["Tsum"].mean() - body_drag(U)) / W
            e = ez ** 2 + ex ** 2
            if best is None or e < best[0]:
                best = (e, U, th)
    e, U, th = best
    return U, th, math.sqrt(e)


# ---------------------------------------------------------------- rod bending
def rod_bending(f, amp, U, th, od, idd=0.0, share=0.6, le=LE_DEFAULT, cl_scale=1.0):
    """Cantilever LE rod fixed at adapter socket (r = R0+14 mm). Load = share of fore-wing strip
    normal force (aero + added mass) + rod/membrane inertia, worst instant in the cycle."""
    res = simulate(f, amp, U, th, cl_scale=cl_scale, le=(od, idd))
    fore = STRIPS[:, 4] > 0.5
    r = STRIPS[fore, 0]
    order = np.argsort(r)
    r = r[order]
    dm_mem = (MEMBRANE_GSM / 1000 * STRIPS[fore, 1] * STRIPS[fore, 3])[order]
    A, I = rod_props(od, idd)
    r_fix = (R0 + 14) / 1000
    worst = None
    for k in range(len(res["t"])):
        Fn = res["Fn"][k, fore][order]
        inertial = -(dm_mem * share + RHO_CF * A * np.gradient(r)) * r * res["ddphi"][k]
        q = share * Fn + inertial                         # N per strip, along wing normal
        # bending moment about the fixed end
        mask = r > r_fix
        Mroot = (q[mask] * (r[mask] - r_fix)).sum()
        if worst is None or abs(Mroot) > abs(worst[0]):
            worst = (Mroot, q.copy(), k)
    Mroot, q, k = worst
    # deflection by double integration of M(x)/EI along the rod
    xs = r[r > r_fix] - r_fix
    qs = q[r > r_fix]
    M = np.array([(qs[xs > x] * (xs[xs > x] - x)).sum() for x in xs])
    slope = np.cumsum(M / (E_CF * I) * np.gradient(xs))
    defl = np.cumsum(slope * np.gradient(xs))
    sigma = abs(Mroot) * (od / 2) / I
    mass = RHO_CF * A * LE_LEN * 1000
    return dict(od=od, idd=idd, mass_g=mass, Mroot=Mroot, sigma_MPa=sigma / 1e6,
                tip_mm=abs(defl[-1]) * 1000, tip_pct=abs(defl[-1]) / xs[-1] * 100, k=k)


# ---------------------------------------------------------------- main study
def main():
    parts, W_mass = body_mass()
    W = W_mass * G
    mw, Iw = wing_mass_inertia()
    report = dict(area_one_side_dm2=AREA_SIDE * 100, total_area_dm2=2 * AREA_SIDE * 100, span_m=SPAN, AR=AR,
                  mass_breakdown_g=parts, total_mass_g=W_mass * 1000,
                  wing_loading_g_dm2=W_mass * 1000 / (2 * AREA_SIDE * 100),
                  wing_mass_g=mw * 1000, wing_inertia_kgm2=Iw,
                  servo=dict(tau_stall_Nm=TAU_STALL, omega0_rad_s=OMEGA0))

    # 1) frequency / amplitude map: trim speed, servo feasibility, power
    grid = []
    for f in (2.0, 2.5, 3.0, 3.5, 4.0):
        for amp in (25, 30, 36, 42):
            U, th, err = trim(f, amp, W)
            res = simulate(f, amp, U, th)
            margin, pmech = servo_margin(res)
            grid.append(dict(f=f, amp=amp, U=round(U, 2), theta=th, trim_err=round(err, 3),
                             servo_margin=round(margin, 2), tau_peak=round(float(np.abs(res["tau"]).max()), 3),
                             omega_peak=round(float(np.abs(res["dphi"]).max()), 2),
                             P_mech_W=round(2 * pmech, 3)))
            print(grid[-1])
    report["map"] = grid

    # slowest trimmed flight that keeps >=20 % servo headroom (slow = gentler, more butterfly-like, easier to fly)
    feasible = [g for g in grid if g["servo_margin"] >= 1.2 and g["trim_err"] < 0.05]
    pick = min(feasible, key=lambda g: (g["U"], g["P_mech_W"])) if feasible else \
        max(grid, key=lambda g: g["servo_margin"])
    report["design_point"] = pick
    f, amp, U, th = pick["f"], pick["amp"], pick["U"], pick["theta"]
    res = simulate(f, amp, U, th)

    # CG for zero mean pitching moment (vertical-force weighted quarter-chord)
    Zs = res["Z"].mean(axis=0)
    x_cg = float((Zs * res["xq"][0]).sum() / Zs.sum())
    report["cg_x_mm_from_servo_rear"] = x_cg * 1000
    report["cg_x_mm_behind_LE_root"] = (ROOT_X / 1000 - x_cg) * 1000

    # sensitivity on lift model
    sens = {}
    for k in (0.7, 1.3):
        U2, th2, e2 = trim(f, amp, W, cl_scale=k)
        sens["CLx%.1f" % k] = dict(U=round(U2, 2), theta=th2, trim_err=round(e2, 3))
    for e in (0.3, 0.5, 0.7, 0.8):
        U2, th2, e2 = trim(f, amp, W, eta=e)
        m2, p2 = servo_margin(simulate(f, amp, U2, th2, eta=e))
        sens["eta=%.1f" % e] = dict(U=round(U2, 2), theta=th2, trim_err=round(e2, 3),
                                    servo_margin=round(m2, 2), P_mech_W=round(2 * p2, 3))
    report["sensitivity"] = sens
    report["eta_assumed"] = ETA

    # 2) LE rod options
    rods = [(1.5e-3, 0), (2.0e-3, 0), (2.0e-3, 1.0e-3), (2.5e-3, 1.5e-3), (3.0e-3, 2.0e-3)]
    report["le_rod"] = []
    for od, idd in rods:
        for share in (0.6, 1.0):
            b = rod_bending(f, amp, U, th, od, idd, share=share)
            b["share"] = share
            report["le_rod"].append({k: (round(v, 5) if isinstance(v, float) else v) for k, v in b.items()})
            print(report["le_rod"][-1])

    # hind vein 1.0 mm (rough: hind-wing strips carried by the vein)
    report["notes"] = "quasi-steady; reduced frequency k~%.2f -> unsteady effects significant" % (
        math.pi * f * 0.15 / U)
    Path(OUT / "results.json").write_text(json.dumps(report, indent=2, default=float), encoding="utf-8")

    # ---------------- plots
    fig, ax = plt.subplots(2, 2, figsize=(12, 8))
    tt = res["t"] * f
    ax[0, 0].plot(tt, np.degrees(res["phi"]), label="flap angle φ (deg)")
    ax[0, 0].plot(tt, res["Zsum"] / W * 10, label="lift / weight ×10")
    ax[0, 0].plot(tt, res["Tsum"] / W * 10, label="thrust / weight ×10")
    ax[0, 0].axhline(10, ls=":", c="gray"); ax[0, 0].set_xlabel("cycle"); ax[0, 0].legend(); ax[0, 0].grid(alpha=.3)
    ax[0, 0].set_title("f=%.1f Hz, ±%d°, U=%.1f m/s, θ=%.1f°" % (f, amp, U, th))
    w_ = np.linspace(0, OMEGA0, 50)
    ax[0, 1].plot(w_, TAU_STALL * (1 - w_ / OMEGA0), "k--", label="servo limit (linear)")
    ax[0, 1].plot(np.abs(res["dphi"]), np.abs(res["tau"]), label="required |τ| vs |ω|")
    ax[0, 1].set_xlabel("ω (rad/s)"); ax[0, 1].set_ylabel("τ (N·m)"); ax[0, 1].legend(); ax[0, 1].grid(alpha=.3)
    for amp_ in (25, 30, 36, 42):
        g = [x for x in grid if x["amp"] == amp_]
        ax[1, 0].plot([x["f"] for x in g], [x["servo_margin"] for x in g], "o-", label="±%d°" % amp_)
    ax[1, 0].axhline(1, c="r", ls="--"); ax[1, 0].set_xlabel("f (Hz)"); ax[1, 0].set_ylabel("servo margin (>1 ok)")
    ax[1, 0].legend(); ax[1, 0].grid(alpha=.3)
    lr = [x for x in report["le_rod"] if x["share"] == 0.6]
    labels = ["%.1f%s" % (x["od"] * 1000, "/%.1f" % (x["idd"] * 1000) if x["idd"] else "") for x in lr]
    ax[1, 1].bar(labels, [x["tip_pct"] for x in lr], color="tab:orange", label="tip deflection % span")
    ax2 = ax[1, 1].twinx()
    ax2.plot(labels, [x["sigma_MPa"] for x in lr], "ko-", label="root stress MPa")
    ax2.axhline(SIG_ALLOW / 1e6, c="r", ls="--")
    ax[1, 1].set_xlabel("LE rod OD/ID (mm)"); ax[1, 1].set_title("LE rod, 60% of fore-wing load")
    fig.tight_layout(); fig.savefig(OUT / "aero_structure.png", dpi=120)
    print(json.dumps({k: report[k] for k in ("total_mass_g", "total_area_dm2", "AR", "wing_loading_g_dm2",
                                               "design_point", "cg_x_mm_behind_LE_root", "sensitivity")},
                     indent=1, default=float))


if __name__ == "__main__":
    main()
