"""Longitudinal static stability of the current drawing (Ptera UVLM, static wings).

Sweeps alpha at the Fusion CG, finds the neutral point, the trim alpha and the static margin,
and checks the flapping cycle-mean forces at the design flap settings.

Run:  .venv/Scripts/python ptera_stability.py
"""
import json
from pathlib import Path

import numpy as np
import pterasoftware as ps

import ptera_model as pm
from design_link import CG_BEHIND_LE, MASS_KG, FLIGHT

OUT = Path(__file__).parent / "results"
OUT.mkdir(exist_ok=True)


def loads(alpha, U=3.5, flapping=False):
    plane = pm.airplane()
    am = pm.movement(plane, f=None if flapping else 0, U=U)
    op = ps.operating_point.OperatingPoint(rho=1.2, vCg__E=U, alpha=alpha, beta=0.0, nu=15.06e-6)
    opm = ps.movements.operating_point_movement.OperatingPointMovement(base_operating_point=op)
    kw = dict(num_cycles=3) if flapping else dict(num_chords=6)
    prob = ps.problems.UnsteadyProblem(movement=ps.movements.movement.Movement(
        airplane_movements=[am], operating_point_movement=opm, **kw))
    ps.unsteady_ring_vortex_lattice_method.UnsteadyRingVortexLatticeMethodSolver(unsteady_problem=prob).run(
        prescribed_wake=True, show_progress=False)
    F = (prob.finalMeanForces_W if flapping else prob.finalForces_W)[0]
    M = (prob.finalMeanMoments_W_CgP1 if flapping else prob.finalMoments_W_CgP1)[0]
    return float(-F[2]), float(F[0]), float(M[1])          # lift, thrust (+fwd), pitching moment (+ nose up)


def main():
    W = MASS_KG * 9.80665
    alphas = [2.0, 6.0, 10.0]
    L, My = np.array([loads(a)[0] for a in alphas]), np.array([loads(a)[2] for a in alphas])
    dL, dM = np.polyfit(alphas, L, 1)[0], np.polyfit(alphas, My, 1)[0]
    x_np = CG_BEHIND_LE - dM / dL                                  # neutral point behind wing-root LE (m)
    k = np.polyfit(alphas, My, 1)
    a_trim = -k[1] / k[0]
    L_trim = np.interp(a_trim, alphas, L)
    res = dict(cg_mm=round(CG_BEHIND_LE * 1000, 1), neutral_point_mm=round(x_np * 1000, 1),
               static_margin_mm=round((x_np - CG_BEHIND_LE) * 1000, 1), alpha_trim_glide=round(float(a_trim), 2),
               glide_speed_m_s=round(3.5 * float(np.sqrt(W / L_trim)), 2), dMy_dalpha=float(dM),
               static_alpha=alphas, static_lift_N=L.round(4).tolist(), static_My=My.round(5).tolist())
    lf, tf, mf = loads(float(a_trim), U=res["glide_speed_m_s"], flapping=True)
    res["flapping_at_trim"] = dict(f=FLIGHT["f_hz"], amp=FLIGHT["amp_deg"], lift_over_W=round(lf / W, 3),
                                   thrust_N=round(tf, 4), My=round(mf, 5))
    print(json.dumps(res, indent=1))
    (OUT / "stability.json").write_text(json.dumps(res, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
