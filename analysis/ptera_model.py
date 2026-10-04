"""Ptera Software model of the butterfly, built from the same design file as the Fusion model.

Fore wing and exposed hind wing are separate lifting surfaces; the hind wing carries the design's
nose-down incidence. Both flap about the servo shaft axis. The CG, mass and inertia come from
design/fusion_mass_properties.json, so the simulation always matches the current drawing.
"""
import math

import pterasoftware as ps

from butterfly_aero import catmull, intervals_at
from design_link import (FORE, HIND, ROOT_Y, FLAP_AXIS_Y, R0, DIHEDRAL, HIND_DIHEDRAL, HIND_INCIDENCE, FLIGHT,
                         MASS_KG, CG_BEHIND_LE, CG_BELOW_ROOT, WING_GEOM)

G0 = 9.80665


def sections(which):
    """(span y, LE x, TE x) in wing-local mm. The hind wing keeps only the part not covered by the fore wing."""
    fore, hind = catmull(FORE, 1), catmull(HIND, 1)
    out = []
    if which == "fore":
        for y in [2, 30, 70, 110, 150, 190, 230, 270, 310, 345, 375, 384]:
            iv = intervals_at(fore, y)
            out.append((y, max(b for a, b in iv), min(a for a, b in iv)))
    else:
        for y in [3, 10, 18, 30, 45, 60, 90, 120, 150, 180, 205, 225]:
            ih = intervals_at(hind, y)          # hind panel starts at the fold line: no overlap with the fore panel
            out.append((y, max(b for a, b in ih), min(a for a, b in ih)))
    return out


def make_wing(which, cg_aft=CG_BEHIND_LE, cg_below=CG_BELOW_ROOT):
    sec = sections(which)
    y0, le0, _ = sec[0]
    wcs, prev = [], None
    for i, (y, le, te) in enumerate(sec):
        if i == 0:
            lp = (0.0, 0.0, 0.0)
        else:
            dy = (y - prev[0]) / 1000
            dih = HIND_DIHEDRAL if which == "hind" else DIHEDRAL
            lp = (-(le - prev[1]) / 1000, dy, dy * math.tan(math.radians(dih)))
        last = i == len(sec) - 1
        wcs.append(ps.geometry.wing_cross_section.WingCrossSection(
            airfoil=ps.geometry.airfoil.Airfoil(name="naca0012"), num_spanwise_panels=None if last else 2,
            chord=max(le - te, 5) / 1000, Lp_Wcsp_Lpp=lp, control_surface_symmetry_type="symmetric",
            spanwise_spacing=None if last else "uniform"))
        prev = (y, le)
    hind = which == "hind"
    z_fold = WING_GEOM.fold((le0, y0), hind)[2] / 1000       # hind root LE sits on the folded panel
    z = cg_below + y0 / 1000 * math.tan(math.radians(DIHEDRAL)) + z_fold
    return ps.geometry.wing.Wing(
        wing_cross_sections=wcs, name=which, Ler_Gs_Cgs=(-cg_aft - le0 / 1000, ROOT_Y / 1000 + y0 / 1000, z),
        angles_Gs_to_Wn_ixyz=(0.0, HIND_INCIDENCE if hind else 0.0, 0.0), symmetric=True, mirror_only=False,
        symmetryNormal_G=(0.0, 1.0, 0.0), symmetryPoint_G_Cg=(0.0, 0.0, 0.0),
        num_chordwise_panels=5, chordwise_spacing="uniform")


def airplane(cg_aft=CG_BEHIND_LE):
    return ps.geometry.airplane.Airplane(wings=[make_wing("fore", cg_aft), make_wing("hind", cg_aft)],
                                         name="RC butterfly", weight=MASS_KG * G0)


def movement(plane, f=None, amp=None, eta=None, U=3.5, amp_left=None):
    """Prescribed flapping (+ passive feathering) for every wing; f=0 -> static wings."""
    f = FLIGHT["f_hz"] if f is None else f
    amp = FLIGHT["amp_deg"] if amp is None else amp
    eta = FLIGHT["eta"] if eta is None else eta
    kinds = ["fore", "fore", "hind", "hind"]          # right, reflected left, for each symmetric wing
    sides = [0, 1, 0, 1]
    wms = []
    for w, kind, side in zip(plane.wings, kinds, sides):
        a = amp if (side == 0 or amp_left is None) else amp_left
        sec = sections(kind)
        csm, beta_prev = [], 0.0
        moving_wing = f > 0 and a > 0
        period, omega = (1 / f, 2 * math.pi * f) if f > 0 else (0.0, 0.0)
        for i, c in enumerate(w.wing_cross_sections):
            r = (R0 + sec[i][0]) / 1000
            beta = math.degrees(eta * math.atan(r * math.radians(a) * omega / U)) if (i > 0 and moving_wing) else 0.0
            d, beta_prev = beta - beta_prev, beta     # cross-section angles are cumulative along the span
            mv = abs(d) > 1e-6
            csm.append(ps.movements.wing_cross_section_movement.WingCrossSectionMovement(
                base_wing_cross_section=c,
                ampAngles_Wcsp_to_Wcs_ixyz=(0.0, d, 0.0) if mv else (0.0, 0.0, 0.0),
                periodAngles_Wcsp_to_Wcs_ixyz=(0.0, period, 0.0) if mv else (0.0, 0.0, 0.0),
                phaseAngles_Wcsp_to_Wcs_ixyz=(0.0, 90.0, 0.0) if mv else (0.0, 0.0, 0.0)))
        y_root = ROOT_Y + sec[0][0]
        dz = -WING_GEOM.fold((sec[0][1], sec[0][0]), kind == "hind")[2] / 1000   # back up to the flap axis height
        wms.append(ps.movements.wing_movement.WingMovement(
            base_wing=w, wing_cross_section_movements=csm,
            ampAngles_Gs_to_Wn_ixyz=(a, 0.0, 0.0) if moving_wing else (0.0, 0.0, 0.0),
            periodAngles_Gs_to_Wn_ixyz=(period, 0.0, 0.0) if moving_wing else (0.0, 0.0, 0.0),
            rotationPointOffset_Gs_Ler=(0.0, -(y_root - FLAP_AXIS_Y) / 1000, dz)))
    return ps.movements.airplane_movement.AirplaneMovement(base_airplane=plane, wing_movements=wms)
