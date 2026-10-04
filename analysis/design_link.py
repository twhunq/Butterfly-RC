"""Link between the Fusion drawing and the simulations.

Geometry comes from design/wing_geometry.py + design/butterfly_params.json (the same code and file
fusion_build.py builds the CAD from); mass, CG and inertia from design/fusion_mass_properties.json
(exported by fusion_build.py after it builds the model). Rebuild in Fusion after editing the params.
"""
import json
import math
import sys
from pathlib import Path

DESIGN = Path(__file__).resolve().parents[1] / "design"
sys.path.insert(0, str(DESIGN))
import wing_geometry  # noqa: E402

PARAMS = wing_geometry.load_params()
MASSPROPS = json.loads((DESIGN / "fusion_mass_properties.json").read_text(encoding="utf-8"))
WING_GEOM = wing_geometry.Wing(PARAMS)

WING = PARAMS["wing"]
SERVO = PARAMS["servo"]
FLIGHT = PARAMS["flight"]

# flat panels (dense polygons, wing-local mm): fore panel ahead of the fold line, hind panel behind it
FORE = WING_GEOM.fore_panel()
HIND = WING_GEOM.hind_panel()
ROOT_X, ROOT_Y, ROOT_Z = WING["root"]                 # mm
FLAP_AXIS_Y, FLAP_AXIS_Z = SERVO["shaft_y"], SERVO["shaft_z"]
R0 = ROOT_Y - FLAP_AXIS_Y                              # mm, flap axis -> wing root
DIHEDRAL = WING["dihedral_deg"]
HIND_INCIDENCE = WING["hind_incidence_deg"]
HIND_DIHEDRAL = DIHEDRAL - math.degrees(WING_GEOM.hind_extra_anhedral)

MASS_KG = MASSPROPS["mass_g"] / 1000
CG_BEHIND_LE = MASSPROPS["cg_behind_le_mm"] / 1000     # m
CG_BELOW_ROOT = MASSPROPS["cg_below_wing_root_mm"] / 1000
INERTIA = MASSPROPS["inertia_body_frd_kgm2"]


def rods():
    """(name, length mm, od mm, id mm, start (x,y), end (x,y)) for every carbon rod of one wing (flat coords)."""
    return [(r["name"], r["length"], r["od"], r["id"], tuple(r["a"]), tuple(r["b"])) for r in WING_GEOM.rods()]


def mass_breakdown_g():
    groups = {}
    for it in MASSPROPS["items"]:
        n = it["name"]
        key = ("servo" if n.startswith("Servo") else "battery" if n.startswith("Battery") else
               "wings" if n.endswith(("_R", "_L")) else n.split("_")[0])
        groups[key] = round(groups.get(key, 0.0) + it["mass_g"], 2)
    return groups
