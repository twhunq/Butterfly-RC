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
        for (nm, _), b in zip(bodies, comp.bRepBodies):   # STEP-derived bodies get their old names back on finishEdit
            b.name = nm

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

    # ------------------------------------------------------------------ servos: vendor STEP model, output shaft points aft
    # Both servos are the same part: the shaft sits mid-width, so the left one is the right one moved across
    # (no mirror). STEP frame: x along the case length, y up through the spline, z across the width.
    CAD = SV["cad"]

    def V(x, y, z):
        return adsk.core.Vector3D.create(x, z, -y) if yup else adsk.core.Vector3D.create(x, y, z)
    n0 = root.occurrences.count
    app.importManager.importToTarget(app.importManager.createSTEPImportOptions(os.path.join(HERE, CAD["step"])), root)
    step_occ = root.occurrences.item(n0)
    servo_occ = {}
    for sgn, nm in ((1, "R"), (-1, "L")):
        y0 = CL + (Wd - CAD["case_width"]) / 2 if sgn > 0 else -(CL + (Wd + CAD["case_width"]) / 2)
        m = adsk.core.Matrix3D.create()
        m.setWithCoordinateSystem(P(OF + CAD["top_y"], y0, CL + L + CAD["shaft_end_x"]),
                                  V(0, 0, -1), V(-1, 0, 0), V(0, 1, 0))
        bl = []
        for k, sb in enumerate(step_occ.component.bRepBodies):
            b = tbm.copy(sb)
            tbm.transform(b, m)
            bl.append(("Servo_%s_%d" % (nm, k + 1), b))
        cname = "REF_Servo_%s_%s" % (nm, SV["model"].replace(" ", ""))
        put(new_comp(cname), bl)
        servo_occ[nm] = root.occurrences.itemByName(cname + ":1")
    step_occ.deleteMe()

    # ------------------------------------------------------------------ frame: servo band + round spine sleeve
    PR = prm["printed"]
    LY = wg.body_layout(prm)
    zc, RB, SW, RC = LY["zc"], LY["rb"], LY["r_frame"], LY["r_clip"]      # spine centre runs just under the servo ears
    c = new_comp("PRINT_Frame_ServoMount")
    IY, IZ0, IZ1, Wl = Wd + CL, 0.0, L + 2 * CL, PR["frame_wall"]
    EX = OF + SV["ear_from_output_face"] + SV["ear_thickness"]        # ear seat: the ears' servo-bottom face
    EP = PR["ear_plate"]
    ez0, ez1 = CL - SV["ear_overhang"], CL + L + SV["ear_overhang"]
    bx0, bx1 = EX, OF + H - 2                                          # band runs from the ear plate to the servo bottom
    f = box(bx0, bx1, -(IY + Wl), IY + Wl, IZ0 - Wl, IZ1 + Wl)
    add(f, box(EX, EX + EP, -(IY + Wl), IY + Wl, ez0 - 1.0, ez1))    # ear plate: the ears seat on it and are screwed down
    sub(f, box(bx0 - 1, bx1 + 1, -IY, IY, IZ0, IZ1))                  # window / slot for both cases
    xm = (EX + EP + bx1) / 2
    sub(f, box(EX + EP + 1.5, bx1 - 3.0, -20, 20, IZ0 + 3.0, IZ1 - 3.0))   # side windows (rear 3 mm stays a closed ring)
    sub(f, box(EX + EP + 1.5, bx1 - 3.0, -2.8, 2.8, 10, 40))         # top window only; the bottom stays solid over the sleeve
    add(f, box(bx0, bx1, -SW, SW, zc, IZ0 - Wl + 0.2))                 # web: only under the band, clear of the ears
    add(f, cyl((OF + 2, 0, zc), (OF + H + 1.5, 0, zc), SW))             # sleeve below the ears
    sub(f, cyl((OF + 1, 0, zc), (OF + H + 2.5, 0, zc), RB))
    for sgn in (1, -1):
        for zh in (ez0 + SV["ear_hole_from_end"], ez1 - SV["ear_hole_from_end"]):   # pilot holes under the ear slots
            sub(f, cyl((EX - 1, sgn * SHY, zh), (EX + EP + 1, sgn * SHY, zh), PR["screw_pilot_d"] / 2))
        we = SV["wire_exit"]                             # the lead leaves the shaft-end face next to the servo bottom
        y0, y1 = sorted((sgn * (SHY - we["width"] / 2 - 0.6), sgn * (SHY + we["width"] / 2 + 0.6)))
        sub(f, box(OF + H - we["from_bottom"] - 0.6, bx1 + 1, y0, y1, IZ1 - 0.1, IZ1 + Wl + 0.1))
    put(c, [("Frame_ServoMount", f)])

    # ------------------------------------------------------------------ spine: round carbon tube
    sp = BD["spine"]
    xr, xf = LY["spine_x"]
    c = new_comp("REF_Spine_carbon_tube")
    t = cyl((xr, 0, zc), (xf, 0, zc), sp["od"] / 2)
    sub(t, cyl((xr - 1, 0, zc), (xf + 1, 0, zc), sp["id"] / 2))
    put(c, [("Spine_%gx%gmm_tube_%.0f" % (sp["od"], sp["id"], LY["spine_length"]), t)])

    # ------------------------------------------------------------------ battery clip: sleeve + plate, battery hangs under it
    bt = BD["battery"]
    bx = bt["centre_x"]
    bL, bW, bH = bt["size"]
    c = new_comp("PRINT_BattMount")
    zp1 = zc - RC + 0.6                                # plate top dips into the sleeve bottom
    zp0 = zc - RC - 1.0
    k = cyl((bx - 8, 0, zc), (bx + 8, 0, zc), RC)
    add(k, box(bx - bL / 2 + 3, bx + bL / 2 - 3, -bW / 2 + 1, bW / 2 - 1, zp0, zp1))
    for xx in (bx - 11.5, bx + 11.5):                  # zip-tie notches: each tie wraps battery + plate + bare tube
        for sy in (1, -1):
            y0, y1 = sorted((sy * (bW / 2 - 2), sy * (bW / 2)))
            sub(k, box(xx - 1.5, xx + 1.5, y0, y1, zp0 - 1, zp1 + 1))
    sub(k, cyl((bx - 9, 0, zc), (bx + 9, 0, zc), RB))
    put(c, [("PRINT_BattMount", k)])
    c = new_comp("REF_Battery_2S_180mAh")
    zbt = zp0 - bt["foam_gap"]
    put(c, [("Battery", box(bx - bL / 2, bx + bL / 2, -bW / 2, bW / 2, zbt - bH, zbt))])

    # ------------------------------------------------------------------ avionics clip: Arduino Nano on top, NRF24 behind it
    na, nr = BD["nano"], BD["nrf24"]
    nx0, nx1 = LY["nano_x"]
    rx0, rx1 = LY["nrf_x"]
    zb = LY["z_board"]                                 # underside of both boards
    zt = zb + na["board"][2]
    hw = na["board"][1] / 2 + 0.15                     # board slot half width
    hr = nr["board"][1] / 2 + 0.15
    tr_ = nr["board"][2]
    PW = 1.2                                           # post / rail wall
    c = new_comp("PRINT_AvionicsMount")
    a = cyl((nx1 - 6, 0, zc), (nx1, 0, zc), RC)                                         # front saddle
    add(a, box(nx1 - 2.5, nx1, -(hw + PW), hw + PW, zc, zb))
    add(a, cyl((xr - 1.5, 0, zc), (nx0 + 6, 0, zc), RC))                                # rear sleeve, capped over the tube end
    add(a, box(nx0, nx0 + 2.5, -(hw + PW), hw + PW, zc, zb))                            # rear crossbar
    for sy in (1, -1):
        y0, y1 = sorted((sy * hw, sy * (hw + PW)))
        add(a, box(nx0, nx1, y0, y1, zb - 1.8, zb))                                     # side rails
        y0, y1 = sorted((sy * (hw - 0.75), sy * (hw + PW)))
        add(a, box(nx1 - 2.5, nx1 + 1.0, y0, y1, zb - 0.5, zt + 0.95))                  # front corners: lip + end stop
        add(a, box(nx0 - 1.0, nx0 + 2.5, y0, y1, zb - 0.5, zt + 0.15))                  # rear corners: guide + end stop
        y0, y1 = sorted((sy * (hr - 0.6), sy * (hr + PW)))
        add(a, box(rx0 - 1.0, rx0 + 2.5, y0, y1, zb - 0.5, zb + tr_ + 0.95))            # NRF antenna-end lips
        y0, y1 = sorted((sy * hr, sy * (hr + PW)))
        add(a, box(rx1 - 3.0, rx1, y0, y1, zb - 0.5, zb + tr_ + 0.15))                  # NRF header-end guides
    add(a, box(rx0 - 1.0, nx0 + 2.5, -(hr + PW), hr + PW, zb - 1.2, zb))               # NRF tongue (plastic under the antenna)
    add(a, box(xr - 1.5, nx0 + 2.5, -1.5, 1.5, zc, zb - 1.19))                         # web: tongue to rear sleeve
    sub(a, box(rx0 + 2.5, xr - 2.0, -(hr - 1.5), hr - 1.5, zb - 2, zb + 1))            # window in the tongue behind the tube
    sub(a, box(nx0 - 0.15, nx1 + 0.15, -hw, hw, zb, zt + 0.15))                        # Nano keep-out
    sub(a, box(rx0 - 0.15, rx1 + 0.15, -hr, hr, zb, zb + tr_ + 0.15))                  # NRF keep-out
    sub(a, cyl((xr - 0.5, 0, zc), (nx1 + 1, 0, zc), RB))                               # tube bore, blind at the tail
    put(c, [("PRINT_AvionicsMount", a)])
    c = new_comp("REF_Electronics")
    nb = box(nx0, nx1, -na["board"][1] / 2, na["board"][1] / 2, zb, zt)
    add(nb, box(nx1 - 9, nx1 + 1.5, -3.9, 3.9, zt, zt + 4.0))                          # mini-USB socket, facing forward
    add(nb, box(nx0 + 14, nx0 + 26, -3.5, 3.5, zt, zt + 1.6))                          # ATmega328P
    rbd = box(rx0, rx1, -nr["board"][1] / 2, nr["board"][1] / 2, zb, zb + tr_)
    add(rbd, box(rx1 - 14, rx1 - 9, -2.5, 2.5, zb + tr_, zb + tr_ + 0.9))              # nRF24L01+ chip
    put(c, [("Nano_board", nb), ("NRF24_board", rbd)])

    # ------------------------------------------------------------------ wings: one folded membrane + rods per side
    rods = wing.rods()
    rod = {r["name"]: r for r in rods}
    le_od, le_id = rod["LE"]["od"], rod["LE"]["id"]
    LE_BORE = le_od / 2 + 0.025
    fore_poly, hind_poly = wing.fore_panel(), wing.hind_panel()
    for sgn, side in ((1, "R"), (-1, "L")):
        c = new_comp("WING_%s_Assembly" % side)
        S = M(wing.R, sgn)
        # wing hub (one solid printed part): clamp block round the outer end of the stock horn arm (2 x M2 through),
        # tapered LE / fold / root sockets fused to a core sphere at the root point, with webs between them
        HB = PR["hub"]
        cw = HB["clamp_wall"]
        hx0 = HX0 - cw
        hx1 = min(HX0 + HT + cw, OF - HB["clearance_to_servo_face"])
        yin = SHY + HB["clamp_y_start_from_shaft"]                     # clear of the horn's central disc
        y0, y1 = sorted((sgn * yin, sgn * (Sy + 2.5)))
        hz = HB["clamp_half_height"]
        a = box(hx0, hx1, y0, y1, SHZ - hz, SHZ + hz)                   # clamp block
        add(a, tbm.createSphere(P(*S), (HB["le_boss_od"] / 2 + HB["core_sphere_extra"]) * MM))     # core at the root point
        dirs = {nm: mdir(rod[nm]["a"], rod[nm]["b"], sgn, nm in wing.HIND_RODS) for nm in ("LE", "Fold", "Root")}
        # tapered sockets: bending moment is largest at the root (hub) and falls towards the mouth
        geo = {"LE": (HB["le_boss_od"] / 2, HB["le_boss_tip_od"] / 2, LE_BORE, HB["le_boss_len"]),
               "Fold": (HB["rod_boss_od"] / 2, HB["rod_boss_tip_od"] / 2, rod["Fold"]["od"] / 2 + 0.025, HB["rod_boss_len"]),
               "Root": (HB["rod_boss_od"] / 2, HB["rod_boss_tip_od"] / 2, rod["Root"]["od"] / 2 + 0.025, HB["rod_boss_len"])}
        for nm, (r0, r1, _, bl) in geo.items():
            p0, p1 = along(S, dirs[nm], -1.5), along(S, dirs[nm], bl)
            add(a, tbm.createCylinderOrCone(P(*p0), r0 * MM, P(*p1), r1 * MM))
        for n1, n2 in (("LE", "Fold"), ("Fold", "Root")):                # webs between neighbouring sockets
            for t in HB["web_stations"]:
                add(a, cyl(along(S, dirs[n1], t), along(S, dirs[n2], t), HB["web_radius"]))
        sy0, sy1 = sorted((sgn * (yin - 1.0), sgn * (Sy - 1.0)))         # horn slot, open towards the shaft
        sub(a, box(HX0 - 0.05, HX0 + HT + 0.05, sy0, sy1, SHZ - SV["horn_width"] / 2 - 0.1, SHZ + SV["horn_width"] / 2 + 0.1))
        for ys in HB["screw_y_from_root"]:
            sub(a, cyl((hx0 - 1, sgn * (Sy - ys), SHZ), (hx1 + 1, sgn * (Sy - ys), SHZ), HB["screw_d"] / 2))
        for nm, (_, _, bore, bl) in geo.items():                          # rod bores, cut last
            sub(a, cyl(along(S, dirs[nm], HB["bore_start"]), along(S, dirs[nm], bl + 1), bore))
        hy0, hy1 = sorted((sgn * (SHY - 3), sgn * (SHY + SV["horn_len"])))
        horn = box(HX0, HX0 + HT, hy0, hy1, SHZ - 2.75, SHZ + 2.75)
        add(horn, cyl((HX0, sgn * SHY, SHZ), (HX0 + HT, sgn * SHY, SHZ), 3.5))
        bodies = [("PRINT_WingHub_" + side, a), ("REF_ServoHorn_" + side, horn)]
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
                cwl, sl = PR["conn_wall"], PR["conn_sleeve_len"] / 2
                k = cyl(along(A3, hd, -sl), along(A3, hd, sl), hb + PR["conn_sleeve_wall"])
                add(k, cyl(A3, along(A3, d, host["od"] / 2 + 11), r["od"] / 2 + 0.025 + cwl))
                add(k, tbm.createSphere(P(*along(A3, d, host["od"] / 2 + 0.6)), (r["od"] / 2 + cwl + 0.4) * MM))   # fillet the T-joint
                sub(k, cyl(along(A3, hd, -sl - 1), along(A3, hd, sl + 1), hb))
                sub(k, cyl(along(A3, d, host["od"] / 2 + 1.0), along(A3, d, host["od"] / 2 + 12), r["od"] / 2 + 0.025))
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
    BODY_COMPS = ("REF_Servo", "PRINT_Frame", "REF_Spine", "PRINT_BattMount", "REF_Battery", "PRINT_AvionicsMount",
                  "REF_Electronics")
    for o in servo_occ.values():
        o.isGrounded = True
    body_occ = [o for o in root.occurrences if o.component.name.startswith(BODY_COMPS)]
    root.rigidGroups.add(adsk.core.ObjectCollection.createWithArray(body_occ), False).name = "Body_Rigid"
    for side in ("R", "L"):
        occ = root.occurrences.itemByName("WING_%s_Assembly:1" % side)
        hb = [b for b in occ.bRepBodies if b.name.startswith("REF_ServoHorn")][0]
        fc = next(f_ for f_ in hb.faces if adsk.core.Cylinder.cast(f_.geometry)
                  and abs(adsk.core.Cylinder.cast(f_.geometry).radius - 0.35) < 1e-4)
        ji = root.asBuiltJoints.createInput(occ, servo_occ[side], adsk.fusion.JointGeometry.createByNonPlanarFace(
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
    # created here, not at the top: the STEP import purges appearances that no body uses yet
    AP = {"orange": appearance("Butterfly Orange", (245, 130, 30)), "black": appearance("Plastic - Matte (Black)"),
          "carbon": appearance("Carbon Fiber - Plain"), "white": appearance("Plastic - Matte (White)"),
          "pcb": appearance("PCB Green", (20, 110, 60))}
    for occ in root.occurrences:
        for b in occ.component.bRepBodies:
            n = b.name
            if n.startswith(("PRINT_", "Frame_")):
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
            elif n.endswith("_board"):
                b.appearance = AP["pcb"]
    try:
        root.isJointsFolderLightBulbOn = False
    except Exception:
        pass

    # ------------------------------------------------------------------ static interference (body parts with each other)
    statics = [(o.component.name + "/" + b.name, b) for o in root.occurrences
               if o.component.name.startswith(BODY_COMPS + ("WING_",))
               for b in o.bRepBodies if b.isSolid and not b.name.startswith(("REF_ServoHorn",))]
    clashes = []
    for i in range(len(statics)):
        for k in range(i + 1, len(statics)):
            (n1, b1), (n2, b2) = statics[i], statics[k]
            if n1.split("/")[0] == n2.split("/")[0]:
                continue                                  # parts of one component touch by design (rods in sockets, servo case halves)
            a_ = tbm.copy(b1)
            tbm.booleanOperation(a_, tbm.copy(b2), adsk.fusion.BooleanTypes.IntersectionBooleanType)
            if a_.volume > 1e-6:
                clashes.append("%s x %s (%.4f cm3)" % (n1, n2, a_.volume))

    # ------------------------------------------------------------------ mass properties -> json
    dens_pla, dens_cf = prm["materials_g_cm3"]["PLA"], prm["materials_g_cm3"]["carbon"]
    dens = {"PRINT": prm["materials_g_cm3"]["PETG"], "Frame": dens_pla,
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
                continue                                  # added once per servo below
            elif nm.startswith("Battery"):
                m = BD["battery"]["mass_g"]
            elif nm == "Nano_board":
                m, pos = BD["nano"]["mass_g"], ((nx0 + nx1) / 2, 0.0, zt + 1.0)
            elif nm == "NRF24_board":
                m, pos = BD["nrf24"]["mass_g"], ((rx0 + rx1) / 2, 0.0, zb + 1.0)
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
    for nm, o in servo_occ.items():                    # servo mass at the volume centroid of its STEP bodies
        vs = [(b.physicalProperties.volume, to_model(b.physicalProperties.centerOfMass)) for b in o.bRepBodies]
        vt = sum(v for v, _ in vs)
        items.append(("Servo_" + nm, SV["mass_g"], tuple(sum(v * c[i] for v, c in vs) / vt for i in range(3))))
    items.append(("LDO 3.3V + caps (NRF24 supply)", BD["ldo_mass_g"], (rx1 + 2, 0.0, zb + 1.5)))
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
           "spine_z_centre_mm": round(zc, 2), "spine_length_mm": round(LY["spine_length"], 1),
           "static_clashes": clashes,
           "printed_parts": {b.name: {"lumps": b.lumps.count, "volume_cm3": round(b.physicalProperties.volume, 3)}
                             for o in root.occurrences for b in o.bRepBodies if b.name.startswith(("PRINT_", "Frame_"))},
           "items": [{"name": n, "mass_g": round(m, 3), "pos_mm": [round(v, 1) for v in p]} for n, m, p in items]}
    with open(os.path.join(HERE, "fusion_mass_properties.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    app.activeViewport.fit()
    return out


def run(_context):
    res = build()
    print("mass %.1f g, CG %s mm, %.1f mm behind wing-root LE" % (res["mass_g"], res["cg_mm"], res["cg_behind_le_mm"]))
