"""
Parametric parts for the Go2 power-button station (power on/off dock).
All part geometry is in millimetres (slicer units). Run: python3 parts.py <outdir>
Writes printable STLs + non-printed reference models (as .stl) and parts.json with constants.
"""
import sys, json, math
import numpy as np
import trimesh
from manifold3d import Manifold as M, CrossSection as CS, set_circular_segments

set_circular_segments(64)
OUT = sys.argv[1] if len(sys.argv) > 1 else "."

# ---------------------------------------------------------------- constants (mm)
RZ = 125.0          # plunger axis height above the base-plate top (robot lying, measured on official model)
MOD, NZ = 1.5, 32   # gear module / pinion teeth
PA = math.radians(20)
RP = MOD * NZ / 2   # pitch radius 24 mm -> 150.8 mm of plunger travel per revolution
RACK_HALF = 6.0     # rack body 12 x 12 mm
RACK_LEN = 175.0
TEETH_Y0, TEETH_Y1 = 10.0, 165.0
ROOT_X = RACK_HALF
TIP_X = ROOT_X + 2.25 * MOD
PITCH_X = TIP_X - MOD
PIN_X = PITCH_X + RP          # pinion axis x (tower local)
PIN_Y = 45.0                  # pinion axis y (tower local, from inner face)
PIN_Z0, PIN_Z1 = RZ - 6, RZ + 2   # pinion 8 mm thick
HORN_Z1 = RZ + 6
PLATE_Z0, PLATE_Z1 = RZ + 7, RZ + 11
SERVO_L, SERVO_W, SERVO_H = 45.2, 24.7, 35.0
SHAFT_FROM_END = 11.5
TOWER_X0, TOWER_X1, TOWER_Y1 = -22.0, 62.0, 90.0


def to_tm(m: M, color=None) -> trimesh.Trimesh:
    mesh = m.to_mesh()
    t = trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts), process=True)
    if color is not None:
        t.visual.face_colors = color
    return t


def box(x0, x1, y0, y1, z0, z1) -> M:
    return M.cube((x1 - x0, y1 - y0, z1 - z0)).translate((x0, y0, z0))


def cyl_z(cx, cy, z0, z1, r, seg=0) -> M:
    return M.cylinder(z1 - z0, r, r, seg).translate((cx, cy, z0))


def cyl_y(cx, cz, y0, y1, r) -> M:
    # cylinder along +y
    return M.cylinder(y1 - y0, r).rotate((-90, 0, 0)).translate((cx, y0, cz))


def slot_z(x0, x1, cy, z0, z1, r) -> M:
    return M.batch_hull([cyl_z(x0, cy, z0, z1, r), cyl_z(x1, cy, z0, z1, r)])


def extrude_yz_along_x(poly_yz, x0, x1) -> M:
    """poly given in (y, z); extruded along x from x0 to x1."""
    cs = CS([poly_yz])
    return M.extrude(cs, x1 - x0).rotate((90, 0, 90)).translate((x0, 0, 0))


# ---------------------------------------------------------------- involute pinion
def gear_polygon(m, z, pa, samples=10):
    r = m * z / 2; rb = r * math.cos(pa); ra = r + m; rf = r - 1.25 * m
    inv = lambda a: math.tan(a) - a
    half = math.pi / (2 * z) + inv(pa)
    r_start = max(rb, rf)
    radii = np.linspace(r_start, ra, samples)
    flank = []
    for R in radii:
        aR = math.acos(min(1.0, rb / R))
        flank.append((R, -half + inv(aR)))
    pts = []
    for k in range(z):
        c = 2 * math.pi * k / z
        if rf < rb:
            pts.append((rf * math.cos(c - half), rf * math.sin(c - half)))
        for R, ph in flank:
            pts.append((R * math.cos(c + ph), R * math.sin(c + ph)))
        for R, ph in reversed(flank):
            pts.append((R * math.cos(c - ph), R * math.sin(c - ph)))
        if rf < rb:
            pts.append((rf * math.cos(c + half), rf * math.sin(c + half)))
        # root arc to next tooth
        a0, a1 = c + half, c + 2 * math.pi / z - half
        for a in np.linspace(a0, a1, 4)[1:-1]:
            pts.append((rf * math.cos(a), rf * math.sin(a)))
    return pts


def pinion() -> M:
    g = M.extrude(CS([gear_polygon(MOD, NZ, PA)]), PIN_Z1 - PIN_Z0)
    hub = cyl_z(0, 0, 0, PIN_Z1 - PIN_Z0, 9)
    g = g - cyl_z(0, 0, -1, 20, 3.2)                      # spline screw clearance
    for k in range(4):                                     # horn bolt circle (verify on your horn)
        a = math.pi / 4 + k * math.pi / 2
        g = g - cyl_z(8 * math.cos(a), 8 * math.sin(a), -1, 20, 1.2)
    for k in range(6):                                     # lightening holes
        a = k * math.pi / 3
        g = g - cyl_z(15.5 * math.cos(a), 15.5 * math.sin(a), -1, 20, 3.0)
    return g  # local: axis at origin, z from 0 to 8


# ---------------------------------------------------------------- rack + finger
def rack() -> M:
    p = math.pi * MOD
    root_w = p / 2 + 2 * 1.25 * MOD * math.tan(PA)
    tip_w = p / 2 - 2 * MOD * math.tan(PA)
    pts = [(-RACK_HALF, 0.0), (RACK_HALF, 0.0), (RACK_HALF, TEETH_Y0)]
    n = int((TEETH_Y1 - TEETH_Y0) // p)
    for k in range(n):
        yc = TEETH_Y0 + (k + 0.5) * p
        pts += [(ROOT_X, yc - root_w / 2), (TIP_X, yc - tip_w / 2), (TIP_X, yc + tip_w / 2), (ROOT_X, yc + root_w / 2)]
    pts += [(RACK_HALF, RACK_LEN), (-RACK_HALF, RACK_LEN)]
    body = M.extrude(CS([pts]), 2 * RACK_HALF).translate((0, 0, -RACK_HALF))
    # nose at the front (-y), socket for TPU tip
    nose = cyl_y(0, 0, -12, 0.5, RACK_HALF)
    r = body + nose
    r = r - cyl_y(0, 0, -13, -5, 2.6)          # 5.2 mm socket for the TPU tip post
    r = r - cyl_y(0, 0, RACK_LEN - 12, RACK_LEN + 1, 1.4)   # M3 tap hole for an end-stop screw
    return r  # local: axis along y, front of nose at y=-12


def tpu_tip() -> M:
    post = cyl_y(0, 0, -2, 7, 2.5)                       # goes back into the 5.2 mm socket of the nose
    head = cyl_y(0, 0, -4, 0, 6)
    dome = M.sphere(6).scale((1, 0.65, 1)).translate((0, -4, 0))
    return (head + dome + post).translate((0, 0, 0))     # front of dome at y ~ -7.9


# ---------------------------------------------------------------- tower (servo + rack guide)
SERVO_X0 = PIN_X - SERVO_W / 2
SERVO_Y0 = PIN_Y - SHAFT_FROM_END


def tower() -> M:
    t = box(TOWER_X0, TOWER_X1, 0, TOWER_Y1, 0, PLATE_Z1)
    # flange with slots (x-adjust +/-12 mm)
    t = t + box(TOWER_X0 - 18, TOWER_X1 + 18, 0, TOWER_Y1, 0, 6)
    for xs, xe in [(TOWER_X0 - 9, TOWER_X0 - 9), (TOWER_X1 + 9, TOWER_X1 + 9)]:
        for yy in (14, TOWER_Y1 - 14):
            t = t - slot_z(xs - 0.01, xe + 0.01, yy, -1, 8, 2.3) - slot_z(xs, xe, yy, -1, 8, 2.3)
    # hollow pedestal, open at the back for cables
    # pocket with a 45-degree peaked roof so it prints without supports
    px0, px1, ptop = TOWER_X0 + 7, TOWER_X1 - 7, RZ - 14
    half = (px1 - px0) / 2
    roof = [(px0, 7), (px1, 7), (px1, ptop - half), ((px0 + px1) / 2, ptop), (px0, ptop - half)]
    t = t - M.extrude(CS([roof]), TOWER_Y1 + 1 - 7).rotate((90, 0, 0)).translate((0, TOWER_Y1 + 1, 0))
    # rack slot (through, along y)
    t = t - box(-RACK_HALF - 0.6, TIP_X + 1.8, -1, TOWER_Y1 + 1, RZ - RACK_HALF - 0.6, RZ + RACK_HALF + 0.6)
    # pinion + horn cavity
    t = t - cyl_z(PIN_X, PIN_Y, PIN_Z0 - 1.5, PLATE_Z0, RP + MOD + 2.0)
    # side window: wide enough to slide the 51 mm pinion (+ horn) in from the +x side
    t = t - box(PIN_X - 2, TOWER_X1 + 1, PIN_Y - 27, PIN_Y + 27, PIN_Z0 - 1.5, PLATE_Z0)
    # access hole from the hollow pedestal for the horn centre screw (screwdriver from below)
    t = t - cyl_z(PIN_X, PIN_Y, 0, PIN_Z0, 6.0)
    # spline hole through the top plate
    t = t - cyl_z(PIN_X, PIN_Y, PLATE_Z0 - 1, PLATE_Z1 + 1, 6.5)
    # servo cradle rim on top
    rim = box(SERVO_X0 - 3, SERVO_X0 + SERVO_W + 3, SERVO_Y0 - 3, SERVO_Y0 + SERVO_L + 3, PLATE_Z1, PLATE_Z1 + 18)
    rim = rim - box(SERVO_X0 - 0.3, SERVO_X0 + SERVO_W + 0.3, SERVO_Y0 - 0.3, SERVO_Y0 + SERVO_L + 0.3, PLATE_Z1 - 1, PLATE_Z1 + 20)
    rim = rim - box(SERVO_X0 + 4, SERVO_X0 + SERVO_W - 4, SERVO_Y0 + SERVO_L - 1, SERVO_Y0 + SERVO_L + 5, PLATE_Z1 + 6, PLATE_Z1 + 20)  # cable exit
    t = t + rim
    # guide lips that keep the rack from lifting (bridged over the slot front)
    return t


def servo_dummy() -> M:
    s = box(SERVO_X0, SERVO_X0 + SERVO_W, SERVO_Y0, SERVO_Y0 + SERVO_L, PLATE_Z1, PLATE_Z1 + SERVO_H)
    s = s + cyl_z(PIN_X, PIN_Y, PLATE_Z0 - 0.2, PLATE_Z1, 5.5)       # output spline (pointing down)
    return s


def horn_dummy() -> M:
    return cyl_z(PIN_X, PIN_Y, PIN_Z1, HORN_Z1, 10)


# ---------------------------------------------------------------- cradle half, +y side
def cradle_half() -> M:
    L0, L1 = -125.0, 75.0
    slab = box(L0, L1, 0, 124, 0, 6)
    lip = extrude_yz_along_x([(99, 0), (124, 0), (124, 85), (120, 85), (99, 64)], L0, -32.0)   # stops before the folded front calf
    c = slab + lip
    for xx in (L0 + 20, L1 - 20):
        for yy in (25, 70):
            c = c - cyl_z(xx, yy, -1, 7, 2.3) - M.cylinder(3.2, 2.3, 4.6).translate((xx, yy, 3.0))
    c = c - box(L0 + 40, L1 - 40, 10, 90, 3, 7)   # shallow pocket (filament saver)
    return c


# ---------------------------------------------------------------- guide rail segment
def rail(length=200.0) -> M:
    prof = [(-10, 0), (10, 0), (10, 20)] + [(10 * math.cos(a), 20 + 10 * math.sin(a)) for a in np.linspace(0, math.pi, 17)[1:-1]] + [(-10, 20)]
    r = extrude_yz_along_x(prof, 0, length)
    for xx in (30, length - 30):
        r = r - cyl_z(xx, 0, -1, 31, 2.3) - cyl_z(xx, 0, 8, 31, 4.6)
    # end chamfers so a foot slides off
    return r


# ---------------------------------------------------------------- AprilTag plate + post foot
TAG_PLATE = 200.0
TAG_BLACK = 144.0       # outer black square of tag36h11 (print the tag at exactly this size; full image incl. white ring = 180 mm)


def tag_plate() -> M:
    # local: X across (world y), Z up (world z), Y = thickness (world x); front face at y = 0
    p = box(-TAG_PLATE / 2, TAG_PLATE / 2, 0, 5, -TAG_PLATE / 2, TAG_PLATE / 2)
    # flat front face: print face-down on the bed, glue the 180 mm paper tag centred (10 mm margin)
    clip = box(-14, 14, 5, 29, -40, 40) - box(-10.2, 10.2, 8.8, 30, -41, 41)
    p = p + clip
    for zz in (-25, 25):
        p = p - cyl_y(0, zz, 4, 30, 2.3)
    return p


def post_foot() -> M:
    f = box(-50, 50, -50, 50, 0, 6)
    sock = box(-14.5, 14.5, -14.5, 14.5, 0, 46) - box(-10.2, 10.2, -10.2, 10.2, 3, 47)
    f = f + sock
    for xx in (-38, 38):
        for yy in (-38, 38):
            f = f - cyl_z(xx, yy, -1, 7, 2.3)
    for k in (0, 1):  # gussets
        g = box(-2, 2, 14.5, 46, 6, 36)
        g = g ^ extrude_yz_along_x([(14.5, 6), (46, 6), (14.5, 36)], -2, 2)
        f = f + g.rotate((0, 0, 90 * k)) + g.rotate((0, 0, 90 * k + 180))
    return f


# ---------------------------------------------------------------- electronics box: ESP32 DevKit (30 pin) + Waveshare Bus Servo Adapter (A)
# Box local frame: x along length, y depth, z up. Left wall (x=0): ESP32 USB-C notch. Front wall (y=0): P4 notch.
# Back wall (y=BOX_Y): servo-cable notch. Board sizes from listings: ESP32 DevKit ~51.5-53 x 28-28.5 mm,
# Bus Servo Adapter (A) 42 x 33 mm, holes 2.5 mm on 37 x 28 mm.
BOX_X, BOX_Y, BOX_Z, WALL = 120.0, 66.0, 44.0, 2.4
ESP_L, ESP_W = 53.0, 28.6          # ESP32 DevKit outline (generous)
ESP_X0 = WALL + 1.5                # USB end of the board, close to the left wall
ESP_YC = 38.0                      # board centre line (y)
LEDGE_Z = 26.0                     # top of the end ledges: leaves room for dupont housings under the pins
AD_X0, AD_Y0 = 72.0, WALL + 3.0    # Bus Servo Adapter (A) corner; DC jack edge faces the front wall
AD_L, AD_W, AD_HOLES = 42.0, 33.0, (37.0, 28.0)
STANDOFF = 5.0
NOTCHES = {  # (wall, centre along wall, width, bottom z)
    "usb":   ("left",  ESP_YC, 16.0, LEDGE_Z + 0.5),
    "p4":    ("front", AD_X0 + 11.0, 24.0, WALL + STANDOFF),
    "servo": ("back",  AD_X0 + 10.0, 14.0, 18.0),
}


def _notch_cut(kind, extra=0.0):
    wall, c, w, zb = NOTCHES[kind]
    if wall == "left":
        return box(-1, WALL + 1 + extra, c - w / 2, c + w / 2, zb, BOX_Z + 5)
    if wall == "front":
        return box(c - w / 2, c + w / 2, -1, WALL + 1 + extra, zb, BOX_Z + 5)
    return box(c - w / 2, c + w / 2, BOX_Y - WALL - 1 - extra, BOX_Y + 1, zb, BOX_Z + 5)


def esp_box() -> M:
    b = box(0, BOX_X, 0, BOX_Y, 0, BOX_Z) - box(WALL, BOX_X - WALL, WALL, BOX_Y - WALL, WALL, BOX_Z + 1)
    # ESP32 cradle: two end ledges (pins stay free underneath for the dupont jumpers) + side fences
    y0, y1 = ESP_YC - ESP_W / 2, ESP_YC + ESP_W / 2
    b = b + box(WALL, ESP_X0 + 5.0, y0 + 1, y1 - 1, WALL, LEDGE_Z)                       # USB end ledge
    b = b + box(ESP_X0 + ESP_L - 6.0, ESP_X0 + ESP_L + 3.0, y0 + 1, y1 - 1, WALL, LEDGE_Z)  # antenna end ledge (fits 50-56 mm boards)
    for xa, xb in ((WALL, ESP_X0 + 5.0), (ESP_X0 + ESP_L - 6.0, ESP_X0 + ESP_L + 3.0)):
        for ya, yb in ((y0 - 2.4, y0 - 0.4), (y1 + 0.4, y1 + 2.4)):
            b = b + box(xa, xb, ya, yb, WALL, LEDGE_Z + 4.0)
    # Bus Servo Adapter standoffs (M2.5 self-tapping, or just foam tape)
    hx, hy = AD_HOLES
    ox, oy = AD_X0 + (AD_L - hx) / 2, AD_Y0 + (AD_W - hy) / 2
    for dx in (0, hx):
        for dy in (0, hy):
            b = b + cyl_z(ox + dx, oy + dy, WALL, WALL + STANDOFF, 3.0) - cyl_z(ox + dx, oy + dy, WALL + 0.8, WALL + STANDOFF + 1, 1.05)
    for k in NOTCHES:
        b = b - _notch_cut(k)
    for xx in (10.0, BOX_X - 10.0):  # floor screws to the MDF (4 mm wood screws)
        b = b - cyl_z(xx, 12.0, -1, WALL + 1, 2.3) - M.cylinder(2.0, 2.3, 4.4).translate((xx, 12.0, WALL - 2.0 + 0.001))
    # side vents
    for k in range(6):
        b = b - box(64.0 + k * 6.0, 66.0 + k * 6.0, BOX_Y - WALL - 1, BOX_Y + 1, 28.0, 38.0)
    return b


def esp_lid() -> M:
    l = box(0, BOX_X, 0, BOX_Y, 0, 2.0)
    lip = box(WALL + 0.3, BOX_X - WALL - 0.3, WALL + 0.3, BOX_Y - WALL - 0.3, -3, 0) - box(WALL + 1.8, BOX_X - WALL - 1.8, WALL + 1.8, BOX_Y - WALL - 1.8, -4, 1)
    for k in NOTCHES:   # clear the cable notches in the lip
        lip = lip - box(*_notch_xy(k), -5, 0.5)
    l = l + lip
    for k in range(8):
        l = l - box(12 + k * 5, 14.5 + k * 5, 12, BOX_Y - 12, -4, 3)          # vents over the ESP32
    return l


def _notch_xy(kind):
    wall, c, w, zb = NOTCHES[kind]
    if wall == "left":
        return (-1, WALL + 4, c - w / 2 - 1, c + w / 2 + 1)
    if wall == "front":
        return (c - w / 2 - 1, c + w / 2 + 1, -1, WALL + 4)
    return (c - w / 2 - 1, c + w / 2 + 1, BOX_Y - WALL - 4, BOX_Y + 1)


def board_dummy() -> dict:
    y0 = ESP_YC - ESP_W / 2
    pz = LEDGE_Z
    esp_pcb = box(ESP_X0, ESP_X0 + ESP_L, y0, y0 + ESP_W, pz, pz + 1.6)
    esp_can = box(ESP_X0 + ESP_L - 26.0, ESP_X0 + ESP_L - 1.0, ESP_YC - 9.0, ESP_YC + 9.0, pz + 1.6, pz + 4.8)
    usb = box(ESP_X0 - 1.0, ESP_X0 + 7.0, ESP_YC - 4.5, ESP_YC + 4.5, pz + 1.6, pz + 4.8)
    pins = M()
    for side in (-1, 1):
        pins = pins + box(ESP_X0 + 7.5, ESP_X0 + 45.6, ESP_YC + side * 12.7 - 1.27, ESP_YC + side * 12.7 + 1.27, pz - 8.5, pz)
    az = WALL + STANDOFF
    ad_pcb = box(AD_X0, AD_X0 + AD_L, AD_Y0, AD_Y0 + AD_W, az, az + 1.6)
    jack = box(AD_X0 + 2.0, AD_X0 + 11.0, AD_Y0 - 2.0, AD_Y0 + 12.0, az + 1.6, az + 12.6)
    term = box(AD_X0 + 14.0, AD_X0 + 24.0, AD_Y0 + 0.5, AD_Y0 + 8.0, az + 1.6, az + 11.6)
    cap = M.cylinder(26.0, 6.5).rotate((0, 90, 0)).translate((AD_X0 + 14.0, AD_Y0 + 16.0, az + 8.6))
    hdr = box(AD_X0 + 30.0, AD_X0 + 38.0, AD_Y0 + AD_W - 4.0, AD_Y0 + AD_W - 1.4, az + 1.6, az + 10.0)
    servo_port = box(AD_X0 + 13.0, AD_X0 + 23.0, AD_Y0 + AD_W - 6.0, AD_Y0 + AD_W, az + 1.6, az + 7.6)
    return {"pcb": esp_pcb + ad_pcb, "esp": esp_can + usb + pins + hdr, "oled": jack + servo_port, "term": term, "cap": cap}


def conv_dummy() -> M:
    """12 V -> 5 V USB-C converter (sealed box with mounting ears), local origin at a corner."""
    c = box(0, 58, 0, 34, 0, 18) + box(-8, 66, 10, 24, 0, 3)
    for xx in (-4, 62):
        c = c - cyl_z(xx, 17, -1, 4, 1.8)
    return c


def conex_dummy() -> M:
    """Intelbras Conex 1000 P4 female with screw terminal (along +x)."""
    return box(0, 34, -7.5, 7.5, 0, 15)


def tip_wide() -> M:
    """Optional wide flat pusher (20 mm) for more tolerance on the button position."""
    post = cyl_y(0, 0, -2, 7, 2.5)
    pad = cyl_y(0, 0, -6, 0, 10)
    return pad + post


def ups_dummy() -> M:
    u = box(0, 125, 0, 78, 0, 30)
    return u


if __name__ == "__main__":
    printable = {
        "01_servo_tower": tower(),
        "02_rack_plunger": rack(),
        "03_pinion_m1.5_z32": pinion(),
        "04_plunger_tip_TPU": tpu_tip(),
        "04b_wide_tip_20mm": tip_wide(),
        "05_cradle_left": cradle_half(),
        "06_cradle_right": cradle_half().mirror((0, 1, 0)),
        "07_guide_rail_200mm": rail(200),
        "07b_funnel_rail_83mm": rail(83),
        "08_apriltag_plate": tag_plate(),
        "09_tag_post_foot": post_foot(),
        "10_electronics_box": esp_box(),
        "11_electronics_box_lid": esp_lid(),
    }
    summary = {}
    for name, m in printable.items():
        t = to_tm(m)
        assert t.is_watertight, name
        t.export(f"{OUT}/{name}.stl")
        ext = (t.bounds[1] - t.bounds[0]).round(1).tolist()
        summary[name] = {"bbox_mm": ext, "volume_cm3": round(t.volume / 1000, 1)}
    consts = dict(RZ=RZ, PIN_X=PIN_X, PIN_Y=PIN_Y, PIN_Z0=PIN_Z0, PIN_Z1=PIN_Z1, RP=RP, RACK_LEN=RACK_LEN,
                  TEETH_Y0=TEETH_Y0, TEETH_Y1=TEETH_Y1, TOWER_Y1=TOWER_Y1, BOX=[BOX_X, BOX_Y, BOX_Z])
    json.dump({"parts": summary, "const": consts}, open(f"{OUT}/parts.json", "w"), indent=1)
    print(json.dumps(summary, indent=1))
