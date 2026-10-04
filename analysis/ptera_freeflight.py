"""6-DOF free flight of the current drawing: Ptera UVLM + MuJoCo.

Geometry from design/butterfly_params.json, mass / CG / inertia from design/fusion_mass_properties.json.
Two prescribed flap cycles, then free flight. Wing inertial reaction on the body is not modelled.

Run:  .venv/Scripts/python ptera_freeflight.py [free_steps] [U0] [alpha0] [amp_deg] [f_hz]
"""
import sys
from pathlib import Path

import numpy as np
import pterasoftware as ps

import ptera_model as pm
from design_link import MASS_KG, INERTIA, FLIGHT, MASSPROPS

OUT = Path(__file__).parent / "results" / "freeflight"
OUT.mkdir(parents=True, exist_ok=True)

FREE_STEPS = int(sys.argv[1]) if len(sys.argv) > 1 else 192
U0 = float(sys.argv[2]) if len(sys.argv) > 2 else 3.6
A0 = float(sys.argv[3]) if len(sys.argv) > 3 else 9.0
AMP = float(sys.argv[4]) if len(sys.argv) > 4 else FLIGHT["amp_deg"]
F = float(sys.argv[5]) if len(sys.argv) > 5 else FLIGHT["f_hz"]


def main():
    plane = pm.airplane()
    am = pm.movement(plane, f=F, amp=AMP, U=U0)
    op = ps.operating_point.OperatingPoint(rho=1.2, vCg__E=U0, alpha=A0, beta=0.0, angles_E_to_BP1_izyx=(0.0, A0, 0.0),
                                           nu=15.06e-6, g_E=(0.0, 0.0, pm.G0))
    opm = ps.movements.free_flight_operating_point_movement.FreeFlightOperatingPointMovement(base_operating_point=op)
    dt = 1 / F / 32
    mv = ps.movements.free_flight_movement.FreeFlightMovement(
        airplane_movements=[am], operating_point_movement=opm, delta_time=dt,
        prescribed_num_steps=64, free_num_steps=FREE_STEPS, max_wake_rows=64)
    prob = ps.problems.FreeFlightUnsteadyProblem(movement=mv, mass=MASS_KG, I_BP1_CgP1=INERTIA)
    solver = ps.free_flight_unsteady_ring_vortex_lattice_method.FreeFlightUnsteadyRingVortexLatticeMethodSolver(
        free_flight_unsteady_problem=prob)
    tag = "cg%.0f_f%.1f_a%.0f_U%.1f" % (MASSPROPS["cg_behind_le_mm"], F, AMP, U0)
    status = "completed"
    try:
        solver.run(prescribed_wake=True, calculate_streamlines=False, show_progress=False)
    except ValueError as e:          # body tumbled past the Euler-angle range: keep the history up to here
        status = "diverged: %s" % e
    rows = []
    for i, sp in enumerate(prob.steady_problems):
        o = sp.operating_point
        rows.append([i * dt, o.vCg__E, o.alpha, o.beta, *np.asarray(o.angles_E_to_BP1_izyx, float),
                     *np.asarray(o.CgP1_E_Eo, float)])
    rows = np.array(rows)
    np.savetxt(OUT / f"{tag}.csv", rows, delimiter=",", comments="", fmt="%.5f",
               header="t_s,V_m_s,alpha_deg,beta_deg,yaw_deg,pitch_deg,roll_deg,x_m,y_m,z_m")
    last = rows[rows[:, 0] >= rows[-1, 0] - 0.4]
    climb = -(last[-1, 9] - last[0, 9]) / max(last[-1, 0] - last[0, 0], 1e-9)
    print("%s %s steps %d | last 0.4 s: pitch %.1f deg, alpha %.1f deg, V %.2f m/s, climb %.2f m/s, roll %.1f, yaw %.1f"
          % (tag, status, len(rows), last[:, 5].mean(), last[:, 2].mean(), last[:, 1].mean(), climb,
             last[:, 6].mean(), last[:, 4].mean()), flush=True)


if __name__ == "__main__":
    main()
