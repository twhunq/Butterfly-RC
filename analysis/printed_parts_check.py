"""Strength check of the printed parts (wing hub sockets, vein connectors, horn clamp screws).

Loads: worst-case LE-rod root moment and peak servo torque from results/results.json (butterfly_aero.py).
Sizes: design/butterfly_params.json -> "printed". Material: PETG, 100 % infill, printed with the socket
axes lying in the bed plane (bending stress runs along the extrusions, not across the layers).

Run:  .venv/Scripts/python printed_parts_check.py
"""
import json
import math
from pathlib import Path

from design_link import PARAMS

HERE = Path(__file__).parent
R = json.loads((HERE / "results" / "results.json").read_text(encoding="utf-8"))
PR = PARAMS["printed"]
HB = PR["hub"]
LAYER_STRENGTH = 25.0     # MPa, PETG across layers (typ. 20-30)
FATIGUE_ALLOW = 8.0       # MPa, PETG ~1e6 cycles at R=-1, with print defects


def tube_z(D, d):
    return math.pi * (D ** 4 - d ** 4) / (32 * D)          # mm^3


def main():
    le = PARAMS["wing"]["le_rod"]
    rods = [x for x in R["le_rod"] if abs(x["od"] * 1000 - le["od"]) < 1e-6 and abs(x["idd"] * 1000 - le["id"]) < 1e-6]
    M_le = max(abs(x["Mroot"]) for x in rods) * 1000          # N.mm, all fore-panel load on the LE rod
    M_rod = 0.35 * M_le                                         # fold / root rods share of the hind/fore loads
    tau = R["design_point"]["tau_peak"] * 1000                  # N.mm, peak servo torque
    rows = []
    # tapered sockets: the boss moment is ~M at the hub root and falls ~linearly to ~0 at the mouth,
    # so check the root (full M, root OD) and mid-engagement (M/2, interpolated OD)
    mid = lambda a, b: (a + b) / 2
    for name, D, d, M in (("hub LE socket, root", HB["le_boss_od"], le["od"] + 0.05, M_le),
                          ("hub LE socket, mid", mid(HB["le_boss_od"], HB["le_boss_tip_od"]), le["od"] + 0.05, M_le / 2),
                          ("hub fold/root socket, root", HB["rod_boss_od"], 1.05, M_rod),
                          ("hub fold/root socket, mid", mid(HB["rod_boss_od"], HB["rod_boss_tip_od"]), 1.05, M_rod / 2),
                          ("vein connector side boss (Ø1.0)", 1.05 + 2 * PR["conn_wall"], 1.05, 0.12 * M_le)):
        s = M / tube_z(D, d)
        rows.append((name, D, d, M / 1000, s, FATIGUE_ALLOW / s))
    print("%-34s %6s %6s %8s %8s %6s" % ("part", "OD", "ID", "M N.m", "σ MPa", "SF"))
    for n, D, d, M, s, sf in rows:
        print("%-34s %6.2f %6.2f %8.3f %8.1f %6.1f%s" % (n, D, d, M, s, sf, "" if sf >= 1.5 else "  <-- too weak"))
    # horn clamp: torque carried by 2 screws in shear + slot bearing
    r1, r2 = [(PARAMS["wing"]["root"][1] - y - PARAMS["servo"]["shaft_y"]) for y in HB["screw_y_from_root"]]
    F = tau / (r1 + r2)
    A = math.pi * (2.0 / 2) ** 2 * 0.6                          # M2 root area, shear
    print("\nhorn clamp: peak torque %.0f N.mm, screws at %.1f / %.1f mm from shaft -> %.1f N each, M2 shear %.1f MPa"
          % (tau, r1, r2, F, F / A))
    bearing = F / (HB["screw_d"] * HB["clamp_wall"])
    print("bearing on the %.1f mm clamp wall round each screw: %.1f MPa (allow ~%.0f)" % (HB["clamp_wall"], bearing, FATIGUE_ALLOW))


if __name__ == "__main__":
    main()
