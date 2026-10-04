"""Build the RC butterfly in Fusion from design/butterfly_params.json and export its mass properties.

Run inside Fusion (Scripts and Add-Ins, or the MCP loader): build() rebuilds every component of the
active design, creates the flap joints, and writes design/fusion_mass_properties.json, which the
simulations read. The wing geometry comes from design/wing_geometry.py, the same module the
simulations use. Model frame: mm, x forward, y right, z up, x=0 at the wing-root leading edge.
"""
import importlib.util
import json
import math
import os

import adsk.core
import adsk.fusion

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else \
    r"C:\Users\Admin\orca\projects\Butterfly_RC\design"
MM = 0.1   # Fusion internal length unit is cm


def _wing_geometry():
    spec = importlib.util.spec_from_file_location("wing_geometry", os.path.join(HERE, "wing_geometry.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build():
    app = adsk.core.Application.get()
    des = adsk.fusion.Design.cast(app.activeProduct)
    root = des.rootComponent
    wg = _wing_geometry()
    prm = wg.load_params()
    WG, SV, BD = prm["wing"], prm["servo"], prm["body"]
    wing = wg.Wing(prm)
    yup = app.preferences.generalPreferences.defaultModelingOrientation == \
        adsk.core.DefaultModelingOrientations.YUpModelingOrientation

    for j in list(root.asBuiltJoints):
        j.deleteMe()
    for g in list(root.rigidGroups):
        g.deleteMe()
    for occ in list(root.occurrences):
        occ.deleteMe()

    tbm = adsk.fusion.TemporaryBRepManager.get()
    UNION = adsk.fusion.BooleanTypes.UnionBooleanType
    DIFF = adsk.fusion.BooleanTypes.DifferenceBooleanType

    # ------------------------------------------------------------------ helpers (model frame -> Fusion)
    def P(x, y, z):
        return adsk.core.Point3D.create(x * MM, z * MM, -y * MM) if yup else adsk.core.Point3D.create(x * MM, y * MM, z * MM)

    def to_model(p):     # Fusion point (cm) -> model (mm)
        return (p.x / MM, -p.z / MM, p.y / MM) if yup else (p.x / MM, p.y / MM, p.z / MM)

    def box(x0, x1, y0, y1, z0, z1):
        c = P((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
        lx, ly, lz = abs(x1 - x0) * MM, abs(y1 - y0) * MM, abs(z1 - z0) * MM
        wY, hZ = (lz, ly) if yup else (ly, lz)
        return tbm.createBox(adsk.core.OrientedBoundingBox3D.create(
            c, adsk.core.Vector3D.create(1, 0, 0), adsk.core.Vector3D.create(0, 1, 0), lx, wY, hZ))

    def cyl(p1, p2, r):
        return tbm.createCylinderOrCone(P(*p1), r * MM, P(*p2), r * MM)

    def add(a, b):
        tbm.booleanOperation(a, b, UNION)
        return a

    def sub(a, b):
        tbm.booleanOperation(a, b, DIFF)
        return a

    def along(s, d, t):
        return (s[0] + d[0] * t, s[1] + d[1] * t, s[2] + d[2] * t)

    def norm(v):
        n = math.sqrt(sum(c * c for c in v))
        return tuple(c / n for c in v)

    def new_comp(name):
        occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        occ.component.name = name
        return occ.component

    def put(comp, bodies):
        bf = comp.features.baseFeatures.add()
        bf.startEdit()
        for nm, b in bodies:
            comp.bRepBodies.add(b, bf).name = nm
        bf.finishEdit()

    def appearance(name, rgb=None, base="Plastic - Matte (White)"):
        ap = des.appearances.itemByName(name)
        if ap:
            return ap
        lib = app.materialLibraries.itemByName("Fusion Appearance Library")
        ap = des.appearances.addByCopy(lib.appearances.itemByName(name if rgb is None else base), name)
        if rgb:
            for i in range(ap.appearanceProperties.count):
                cp = adsk.core.ColorProperty.cast(ap.appearanceProperties.item(i))
                if cp:
                    try:
                        cp.value = adsk.core.Color.create(rgb[0], rgb[1], rgb[2], 255)
                    except Exception:
                        pass
        return ap

    AP = {"orange": appearance("Butterfly Orange", (245, 130, 30)), "black": appearance("Plastic - Matte (Black)"),
          "carbon": appearance("Carbon Fiber - Plain"), "white": appearance("Plastic - Matte (White)")}

    # ------------------------------------------------------------------ parameters
    ROOT = tuple(WG["root"])
    Sx, Sy, Sz = ROOT
    L, Wd, H = SV["L"], SV["W"], SV["H"]
    CL = 0.2
    OF = SV["output_face_x"]
    SHY, SHZ = SV["shaft_y"], SV["shaft_z"]
    HX0 = OF - SV["shaft_len"] - SV["horn_thickness"]            # horn arm aft face
    HT = SV["horn_thickness"]

    def M(p2, sgn, hind=False):
        """flat wing point -> folded (hind panel rotated about the fold line) -> model frame."""
        return wg.to_model(wing, wing.fold(p2, hind), sgn, ROOT)

    def mdir(a2, b2, sgn, hind=False):
        a, b = M(a2, sgn, hind), M(b2, sgn, hind)
        return norm(tuple(b[i] - a[i] for i in range(3)))

    def face(poly2, sgn, hind):
        pts = [P(*M(p, sgn, hind)) for p in poly2]
        curves = [adsk.core.Line3D.create(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts))]
        res = tbm.createWireFromCurves(curves)
        wire = res[0] if isinstance(res, (list, tuple)) else res
        return tbm.createFaceFromPlanarWires([wire])

    # ------------------------------------------------------------------ servos (output shaft points aft)
    c = new_comp("REF_Servo_%s_x2" % SV["model"].replace(" ", ""))
    bl = []
    for sgn, nm in ((1, "R"), (-1, "L")):
        y0, y1 = sorted((sgn * CL, sgn * (CL + Wd)))
        b = box(OF, OF + H, y0, y1, CL, CL + L)
        ex = OF + SV["ear_from_output_face"]
        add(b, box(ex, ex + 2, y0, y1, CL - SV["ear_overhang"], CL + L + SV["ear_overhang"]))
        add(b, cyl((OF, sgn * SHY, SHZ), (OF - SV["shaft_len"], sgn * SHY, SHZ), 2.5))
        bl.append(("Servo_" + nm, b))
    put(c, bl)

    # ------------------------------------------------------------------ frame: servo band + spine clamp
    c = new_comp("PRINT_Frame_ServoMount")
    IY, IZ0, IZ1, Wl = Wd + CL, 0.0, L + 2 * CL, 1.2
    bx0, bx1 = OF + H - 12, OF + H - 2
    f = box(bx0, bx1, -(IY + Wl), IY + Wl, IZ0 - Wl, IZ1 + Wl)
    sub(f, box(bx0 - 1, bx1 + 1, -IY, IY, IZ0, IZ1))
    xm = (bx0 + bx1) / 2
    sub(f, cyl((xm, -20, 12), (xm, 20, 12), 3.5))
    sub(f, cyl((xm, 0, -10), (xm, 0, 40), 3.0))
    sp = BD["spine"]
    hs = sp["section"] / 2 + 0.075
    zc = sp["z_centre"]
    add(f, box(OF + 2, OF + H + 1.5, -2.2, 2.2, zc - 2.2, -0.6))
    sub(f, box(OF + 1, OF + H + 2.5, -hs, hs, zc - hs, zc + hs))
    put(c, [("Frame_ServoMount", f)])

    # ------------------------------------------------------------------ spine
    c = new_comp("REF_Spine_2mm_tube")
    xf, s2 = sp["x_front"], sp["section"] / 2
    put(c, [("Spine_%dmm_tube_%d" % (sp["section"], sp["length"]), box(xf - sp["length"], xf, -s2, s2, zc - s2, zc + s2))])

    # ------------------------------------------------------------------ tray (abdomen): ESP32 + buck on top, battery below
    tr, bt = BD["tray"], BD["battery"]
    tc, tl, tw = tr["centre_x"], tr["length"], tr["width"] / 2
    c = new_comp("PRINT_Tray_Abdomen")
    t = box(tc - tl / 2, tc + tl / 2, -2.2, 2.2, zc - 2.2, -0.6)
    add(t, box(tc - tl / 2, tc + tl / 2, -tw, tw, -0.6, 0.2))
    esp_x1 = tc + tl / 2 - 5
    esp_x0 = esp_x1 - tr["esp32"][0]
    buck_x1 = esp_x0 - 4
    buck_x0 = buck_x1 - tr["buck"][0]

    def posts(x0, x1, hy):
        for xx in (x0 - 1.2, x1):
            for yy in (hy, -hy - 1.2):
                add(t, box(xx, xx + 1.2, yy, yy + 1.2, 0.2, 1.9))
    posts(esp_x0, esp_x1, tr["esp32"][1] / 2 + 0.1)
    posts(buck_x0, buck_x1, tr["buck"][1] / 2 + 0.1)
    bx = bt["centre_x"]
    for xx in (bx - bt["size"][0] / 2 - 3.5, bx + bt["size"][0] / 2 + 0.5):      # zip-tie slots at the battery ends
        sub(t, box(xx, xx + 3, 3.5, 8.5, -6, 2))
        sub(t, box(xx, xx + 3, -8.5, -3.5, -6, 2))
    sub(t, box(tc - tl / 2 - 1, tc + tl / 2 + 1, -hs, hs, zc - hs, zc + hs))
    put(c, [("Tray_Abdomen", t)])
    c = new_comp("REF_Battery_2S_180mAh")
    bL, bW, bH = bt["size"]
    put(c, [("Battery", box(bx - bL / 2, bx + bL / 2, -bW / 2, bW / 2, zc - 2.2 - 0.6 - bH, zc - 2.2 - 0.6))])

    # ------------------------------------------------------------------ wings: one folded membrane + rods per side
    rods = wing.rods()
    rod = {r["name"]: r for r in rods}
    le_od, le_id = rod["LE"]["od"], rod["LE"]["id"]
    LE_BORE = le_od / 2 + 0.025
    fore_poly, hind_poly = wing.fore_panel(), wing.hind_panel()
    for sgn, side in ((1, "R"), (-1, "L")):
        c = new_comp("WING_%s_Assembly" % side)
        S = M(wing.R, sgn)
        # horn adapter: clamps the outer end of the stock horn arm (slot) + M2 screw; LE, fold and root-rod sockets
        y0, y1 = sorted((sgn * (Sy - 10), sgn * Sy))
        a = box(HX0 - 1.5, HX0 + HT + 1.0, y0, y1, SHZ - 4, SHZ + 4)
        sy0, sy1 = sorted((sgn * (Sy - 11.2), sgn * (Sy - 2.0)))
        sub(a, box(HX0 - 0.05, HX0 + HT + 0.05, sy0, sy1, SHZ - SV["horn_width"] / 2 - 0.1, SHZ + SV["horn_width"] / 2 + 0.1))
        sub(a, cyl((HX0 - 3, sgn * (Sy - 5.2), SHZ), (HX0 + HT + 3, sgn * (Sy - 5.2), SHZ), 1.1))
        for nm, boss_r, bore_r, blen in (("LE", LE_BORE + 0.9, LE_BORE, 16), ("Fold", 1.4, rod["Fold"]["od"] / 2 + 0.025, 13),
                                         ("Root", 1.4, rod["Root"]["od"] / 2 + 0.025, 13)):
            d = mdir(rod[nm]["a"], rod[nm]["b"], sgn, nm in wing.HIND_RODS)
            add(a, cyl(S, along(S, d, blen), boss_r))
            sub(a, cyl(along(S, d, 3), along(S, d, blen + 1), bore_r))
        hy0, hy1 = sorted((sgn * (SHY - 3), sgn * (SHY + SV["horn_len"])))
        horn = box(HX0, HX0 + HT, hy0, hy1, SHZ - 2.75, SHZ + 2.75)
        add(horn, cyl((HX0, sgn * SHY, SHZ), (HX0 + HT, sgn * SHY, SHZ), 3.5))
        bodies = [("PRINT_HornAdapter_" + side, a), ("REF_ServoHorn_" + side, horn)]
        for r in rods:
            hr = r["name"] in wing.HIND_RODS
            A3, B3 = M(r["a"], sgn, hr), M(r["b"], sgn, hr)
            d = norm(tuple(B3[i] - A3[i] for i in range(3)))
            start = A3 if r["on"] is None else along(A3, d, rod[r["on"]]["od"] / 2)
            body = cyl(start, B3, r["od"] / 2)
            if r["id"] > 0:
                sub(body, cyl(along(A3, d, -1), along(B3, d, 1), r["id"] / 2))
            bodies.append(("%s_%.1fmm_%s" % (r["name"], r["od"], side), body))
            if r["on"] is not None:      # printed connector sleeve on the host rod + side socket
                host = rod[r["on"]]
                hd = mdir(host["a"], host["b"], sgn, host["name"] in wing.HIND_RODS)
                hb = host["od"] / 2 + 0.025
                k = cyl(along(A3, hd, -6), along(A3, hd, 6), hb + 0.8)
                add(k, cyl(A3, along(A3, d, host["od"] / 2 + 9), r["od"] / 2 + 0.8))
                sub(k, cyl(along(A3, hd, -7), along(A3, hd, 7), hb))
                sub(k, cyl(along(A3, d, host["od"] / 2 + 1.0), along(A3, d, host["od"] / 2 + 10), r["od"] / 2 + 0.025))
                bodies.append(("PRINT_Conn%s_%s" % (r["name"][-1], side), k))
        bodies += [("Membrane_ForePanel_" + side, face(fore_poly, sgn, False)), ("Membrane_HindPanel_" + side, face(hind_poly, sgn, True))]
        put(c, bodies)

    # ------------------------------------------------------------------ 1:1 flat pattern (one piece, fold line, rods)
    wp = new_comp("WING_Pattern_1to1")
    pin = wp.constructionPlanes.createInput()
    pin.setByOffset(wp.xZConstructionPlane if yup else wp.xYConstructionPlane, adsk.core.ValueInput.createByReal(-60 * MM))
    pl = wp.constructionPlanes.add(pin)
    pl.name = "Pattern_Plane"
    sk = wp.sketches.add(pl)
    sk.name = "Wing_Template_1to1"

    def spt(p, sgn):
        return sk.modelToSketchSpace(P(Sx + p[0], sgn * (Sy + p[1]), -60))
    lines = sk.sketchCurves.sketchLines
    for sgn in (1, -1):
        lines.addByTwoPoints(spt(wing.R, sgn), spt(wing.LE_END, sgn))
        for curve in (wing.fore_curve, wing.hind_curve):
            col = adsk.core.ObjectCollection.create()
            for p in curve:
                col.add(spt(p, sgn))
            sk.sketchCurves.sketchFittedSplines.add(col)
        lines.addByTwoPoints(spt(wing.E, sgn), spt(wing.R, sgn))
        lines.addByTwoPoints(spt(wing.R, sgn), spt(wing.N, sgn)).isConstruction = True      # fold line
        for r in rods:
            if r["name"] not in ("LE", "Fold", "Root"):
                lines.addByTwoPoints(spt(r["a"], sgn), spt(r["b"], sgn)).isConstruction = True
    root.occurrences.itemByName("WING_Pattern_1to1:1").isLightBulbOn = False

    # ------------------------------------------------------------------ joints
    servo = [o for o in root.occurrences if o.component.name.startswith("REF_Servo")][0]
    servo.isGrounded = True
    body_occ = [o for o in root.occurrences if o.component.name.startswith(("REF_Servo", "PRINT_Frame", "PRINT_Tray", "REF_Spine", "REF_Battery"))]
    root.rigidGroups.add(adsk.core.ObjectCollection.createWithArray(body_occ), False).name = "Body_Rigid"
    for side in ("R", "L"):
        occ = root.occurrences.itemByName("WING_%s_Assembly:1" % side)
        hb = [b for b in occ.bRepBodies if b.name.startswith("REF_ServoHorn")][0]
        fc = next(f_ for f_ in hb.faces if adsk.core.Cylinder.cast(f_.geometry)
                  and abs(adsk.core.Cylinder.cast(f_.geometry).radius - 0.35) < 1e-4)
        ji = root.asBuiltJoints.createInput(occ, servo, adsk.fusion.JointGeometry.createByNonPlanarFace(
            fc, adsk.fusion.JointKeyPointTypes.StartKeyPoint))
        ji.setAsRevoluteJointMotion(adsk.fusion.JointDirections.ZAxisJointDirection)
        j = root.asBuiltJoints.add(ji)
        j.name = "Flap_%s" % side
        lim = adsk.fusion.RevoluteJointMotion.cast(j.jointMotion).rotationLimits
        lim.isMinimumValueEnabled = True
        lim.minimumValue = math.radians(-45)
        lim.isMaximumValueEnabled = True
        lim.maximumValue = math.radians(45)

    # ------------------------------------------------------------------ paint (bodies looked up again by name) + hide joint glyphs
    for occ in root.occurrences:
        for b in occ.component.bRepBodies:
            n = b.name
            if n.startswith(("PRINT_", "Frame_", "Tray_")):
                b.appearance = AP["orange"]
            elif n.startswith("Membrane_"):
                b.appearance = AP["orange"]
                b.opacity = 0.45
            elif n.startswith(("LE_", "Fold_", "Root_", "Vein", "Spine")):
                b.appearance = AP["carbon"]
            elif n.startswith("Servo_"):
                b.appearance = AP["black"]
            elif n.startswith(("REF_ServoHorn", "Battery")):
                b.appearance = AP["white"]
    try:
        root.isJointsFolderLightBulbOn = False
    except Exception:
        pass

    # ------------------------------------------------------------------ mass properties -> json
    dens_pla, dens_cf = prm["materials_g_cm3"]["PLA"], prm["materials_g_cm3"]["carbon"]
    dens = {"PRINT": dens_pla, "Frame": dens_pla, "Tray": dens_pla,
            "LE": dens_cf, "Fold": dens_cf, "Root": dens_cf, "Vein": dens_cf, "Spine": dens_cf}

    def poly_centroid(poly):
        A = cx = cy = 0.0
        for i in range(len(poly)):
            x0, y0 = poly[i]
            x1, y1 = poly[(i + 1) % len(poly)]
            cr = x0 * y1 - x1 * y0
            A += cr
            cx += (x0 + x1) * cr
            cy += (y0 + y1) * cr
        A /= 2
        return abs(A), (cx / (6 * A), cy / (6 * A))
    fA, fC = poly_centroid(fore_poly)
    hA, hC = poly_centroid(hind_poly)
    gsm = WG["membrane_gsm"] * (1 + 0.0)          # wrap margins are cut extra and folded round the rods
    items = []
    for occ in root.occurrences:
        for b in occ.bRepBodies:
            nm = b.name
            pp = b.physicalProperties
            pos = to_model(pp.centerOfMass)
            sgn = 1 if nm.endswith("_R") else -1
            if nm.startswith("Servo_"):
                m = SV["mass_g"]
            elif nm.startswith("Battery"):
                m = BD["battery"]["mass_g"]
            elif nm.startswith("REF_ServoHorn"):
                m = SV["horn_mass_g"]
            elif nm.startswith("Membrane_ForePanel"):
                m, pos = fA * gsm * 1e-6, M(fC, sgn)
            elif nm.startswith("Membrane_HindPanel"):
                m, pos = hA * gsm * 1e-6, M(hC, sgn, True)
            else:
                key = next((k for k in dens if nm.startswith(k)), None)
                if key is None:
                    continue
                m = pp.volume * dens[key]
            items.append((nm, m, pos))
    items.append(("ESP32-C3 Super Mini", BD["esp32_mass_g"], ((esp_x0 + esp_x1) / 2, 0.0, 1.0)))
    items.append(("Buck 5V", BD["buck_mass_g"], ((buck_x0 + buck_x1) / 2, 0.0, 1.0)))
    items.append(("Wires/glue", BD["wires"]["mass_g"], (BD["wires"]["x"], 0.0, 8.0)))
    Mt = sum(m for _, m, _ in items)
    cg = [sum(m * p[i] for _, m, p in items) / Mt for i in range(3)]
    I = [[0.0] * 3 for _ in range(3)]
    for _, m, p in items:   # body axes: x fwd, y right, z down (kg m^2)
        d = [(p[0] - cg[0]) / 1000, (p[1] - cg[1]) / 1000, -(p[2] - cg[2]) / 1000]
        r2 = sum(v * v for v in d)
        for i in range(3):
            for k in range(3):
                I[i][k] += m / 1000 * ((r2 if i == k else 0.0) - d[i] * d[k])
    out = {"mass_g": round(Mt, 3), "cg_mm": [round(v, 2) for v in cg],
           "cg_behind_le_mm": round(Sx - cg[0], 2), "cg_below_wing_root_mm": round(Sz - cg[2], 2),
           "inertia_body_frd_kgm2": [[round(v, 9) for v in row] for row in I],
           "membrane_area_per_side_cm2": {"fore_panel": round(fA / 100, 1), "hind_panel": round(hA / 100, 1)},
           "fold_angle_deg": round(math.degrees(wing.beta), 2),
           "items": [{"name": n, "mass_g": round(m, 3), "pos_mm": [round(v, 1) for v in p]} for n, m, p in items]}
    with open(os.path.join(HERE, "fusion_mass_properties.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    app.activeViewport.fit()
    return out


def run(_context):
    res = build()
    print("mass %.1f g, CG %s mm, %.1f mm behind wing-root LE" % (res["mass_g"], res["cg_mm"], res["cg_behind_le_mm"]))
