"""
Assemble the Go2 power-button dock concept: builds GLBs for the web viewer and renders PNGs with MuJoCo.
usage: MUJOCO_GL=egl python3 -I assemble.py <outdir> <go2_lying.ply> <go2_standing.ply> <tag36h11_png>
"""
import sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # find parts.py even with python3 -I
import numpy as np, trimesh, mujoco
from PIL import Image, ImageDraw, ImageFont
import parts as P

OUT, PLY_LIE, PLY_STAND, TAG_PNG = sys.argv[1:5]
os.makedirs(f"{OUT}/glb", exist_ok=True); os.makedirs(f"{OUT}/img", exist_ok=True)

# ------------------------------------------------------------- world layout (metres, z up, robot faces +x)
PT = 0.012                      # MDF base plate thickness
X_B = -0.070                    # plunger axis x (button target, see side-map analysis)
Y_T = 0.205                     # tower inner face y
Z_AX = PT + P.RZ / 1000         # plunger axis height
Y_FACE = 0.097                  # trunk side face (battery end face) when lying
TIP_EXT = Y_FACE - 0.003        # tip pushes 3 mm into the button
TIP_RET = Y_T + 0.010           # tip hidden 10 mm inside the tower
TIP_LOCAL = -0.0199             # rack-local y of the TPU dome front
PIN_W = np.array([X_B + P.PIN_X / 1000, Y_T + P.PIN_Y / 1000, PT + P.PIN_Z0 / 1000])
RP = P.RP / 1000

C = {  # colours (rgba 0-1)
    "mdf": (0.80, 0.66, 0.50, 1), "print": (0.93, 0.42, 0.18, 1), "print_dark": (0.20, 0.22, 0.25, 1),
    "tpu": (0.08, 0.08, 0.08, 1), "servo": (0.12, 0.12, 0.13, 1), "alu": (0.75, 0.77, 0.80, 1),
    "white": (0.95, 0.95, 0.93, 1), "pcb": (0.08, 0.09, 0.10, 1), "term": (0.20, 0.62, 0.30, 1), "capcol": (0.12, 0.22, 0.55, 1), "chip": (0.55, 0.57, 0.60, 1),
    "oled": (0.05, 0.05, 0.08, 1), "cable": (0.05, 0.05, 0.05, 1), "cable_red": (0.75, 0.10, 0.10, 1),
    "ups": (0.92, 0.92, 0.94, 1), "target": (0.95, 0.80, 0.10, 1),
}


def T(m, s=0.001):
    """manifold (mm) -> trimesh (m)"""
    t = P.to_tm(m); t.apply_scale(s); return t


def place(t, R=np.eye(3), p=(0, 0, 0)):
    t = t.copy(); M = np.eye(4); M[:3, :3] = R; M[:3, 3] = p; t.apply_transform(M); return t


def Rz(a):
    c, s = math.cos(a), math.sin(a); return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


MIR_Y = np.diag([1, -1, 1.0])

# ------------------------------------------------------------- build static parts
static = []   # (name, trimesh, colour key)

plate = trimesh.creation.box(extents=(1.60, 0.84, PT)); plate.apply_translation((0, 0, PT / 2))
static.append(("base_mdf", plate, "mdf"))
ramp = trimesh.Trimesh(vertices=[[-0.80, -0.42, 0], [-0.80, 0.42, 0], [-0.80, -0.42, PT], [-0.80, 0.42, PT], [-0.86, -0.42, 0], [-0.86, 0.42, 0]],
                       faces=[[0, 1, 3], [0, 3, 2], [4, 2, 3], [4, 3, 5], [4, 0, 2], [5, 3, 1], [4, 5, 1], [4, 1, 0]])
ramp.fix_normals(); static.append(("ramp", ramp, "mdf"))

cradle = T(P.cradle_half())
static.append(("cradle_left", place(cradle, p=(0, 0, PT)), "print_dark"))
static.append(("cradle_right", place(cradle, MIR_Y, (0, 0, PT)), "print_dark"))

rail = T(P.rail(200)); rail_long = T(P.rail(283))
for side in (1, -1):
    for k in range(4):
        r = place(rail, p=(-0.50 + 0.2 * k, 0.185, PT))
        static.append((f"rail_{side}_{k}", place(r, MIR_Y) if side < 0 else r, "print_dark"))
    ang = math.atan2(0.185 - 0.335, -0.50 + 0.74)
    f = place(rail_long, Rz(ang), (-0.74, 0.335, PT))
    static.append((f"funnel_{side}", place(f, MIR_Y) if side < 0 else f, "print_dark"))

tower = T(P.tower()); static.append(("tower", place(tower, p=(X_B, Y_T, PT)), "print"))
static.append(("servo_sts3215", place(T(P.servo_dummy()), p=(X_B, Y_T, PT)), "servo"))
static.append(("horn", place(T(P.horn_dummy()), p=(X_B, Y_T, PT)), "alu"))

# AprilTag post
foot = T(P.post_foot()); static.append(("post_foot", place(foot, p=(0.68, 0, PT)), "print"))
prof = trimesh.creation.box(extents=(0.020, 0.020, 0.420)); prof.apply_translation((0.68, 0, PT + 0.003 + 0.21))
static.append(("profile_20x20", prof, "alu"))
R_TAG = np.array([[0, 1, 0], [-1, 0, 0], [0, 0, 1.0]])   # local X->-y? (cols: X->(0,-1,0), Y->(1,0,0), Z->z)
R_TAG = np.column_stack([(0, -1, 0), (1, 0, 0), (0, 0, 1)]).astype(float)
TAG_X0, TAG_Z = 0.68 - 0.019, PT + 0.300
static.append(("tag_plate", place(T(P.tag_plate()), R_TAG, (TAG_X0, 0, TAG_Z)), "white"))

# electronics: box rotated 180 deg -> P4 notch faces away from the robot, servo notch faces the rails/tower,
# ESP32 USB-C notch faces the 12 V -> 5 V converter.  local (lx, ly) -> world (BOX_X0 + BX - lx, BOX_Y0 + BY - ly)
R180 = Rz(math.pi); BX = P.BOX_X / 1000; BY = P.BOX_Y / 1000
BOX_X0, BOX_Y0 = 0.030, 0.215
box_p = (BOX_X0 + BX, BOX_Y0 + BY, PT)
W = lambda lx, ly, lz: (BOX_X0 + BX - lx / 1000, BOX_Y0 + BY - ly / 1000, PT + lz / 1000)
static.append(("electronics_box", place(T(P.esp_box()), R180, box_p), "print"))
bd = P.board_dummy()
static.append(("pcb", place(T(bd["pcb"]), R180, box_p), "pcb"))
static.append(("esp32", place(T(bd["esp"]), R180, box_p), "chip"))
static.append(("board_p4_jack", place(T(bd["oled"]), R180, box_p), "oled"))
static.append(("green_terminal", place(T(bd["term"]), R180, box_p), "term"))
static.append(("capacitor", place(T(bd["cap"]), R180, box_p), "capcol"))
lid = place(T(P.esp_lid()), R180, (box_p[0], box_p[1], PT + P.BOX_Z / 1000))
static.append(("lid", lid, "print"))
conv = place(T(P.conv_dummy()), p=(0.165, 0.225, PT)); static.append(("usb_converter", conv, "servo"))
conex = place(T(P.conex_dummy()), p=(0.228, 0.2925, PT)); static.append(("conex_p4", conex, "oled"))
cterm = trimesh.creation.box(extents=(0.010, 0.016, 0.011)); cterm.apply_translation((0.233, 0.2925, PT + 0.0205))
static.append(("conex_terminal", cterm, "term"))
UPS_P = (0.272, 0.300, PT)
ups = T(P.ups_dummy()); static.append(("mini_ups", place(ups, p=UPS_P), "ups"))
led = trimesh.creation.box(extents=(0.002, 0.03, 0.006)); led.apply_translation((UPS_P[0] - 0.0005, UPS_P[1] + 0.039, PT + 0.02))
static.append(("ups_led", led, "pcb"))


def cable(pts, r=0.0028):
    segs = []
    pts = [np.array(p) for p in pts]
    for a, b in zip(pts[:-1], pts[1:]):
        segs.append(trimesh.creation.cylinder(radius=r, segment=[a, b], sections=12))
        segs.append(trimesh.creation.icosphere(subdivisions=1, radius=r).apply_translation(b))
    return trimesh.util.concatenate(segs)


def plug(center, ext):
    b = trimesh.creation.box(extents=ext); b.apply_translation(center); return b


servo_exit = (X_B + P.PIN_X / 1000, Y_T + (P.SERVO_Y0 + P.SERVO_L) / 1000 + 0.004, PT + 0.160)
sn = W(82.0, P.BOX_Y + 2.0, 26.0)
static.append(("cable_servo", cable([W(82.0, 60.0, 14.0), sn, (0.020, sn[1] - 0.004, sn[2]), (0.018, 0.302, PT + 0.04),
                                    (0.015, 0.302, PT + 0.15), (servo_exit[0], 0.302, servo_exit[2]), servo_exit]), "cable"))
# 12 V: mini UPS -> Y cable -> (a) P4 jack of the Bus Servo Adapter, (b) Conex P4 female -> converter
jack_w = W(78.5, -3.0, 14.5)
ysplit = (0.250, 0.345, PT + 0.004)
static.append(("cable_12v_ups", cable([(UPS_P[0], UPS_P[1] + 0.06, PT + 0.012), (0.262, 0.345, PT + 0.004), ysplit], 0.0025), "cable"))
static.append(("cable_y_board", cable([ysplit, (jack_w[0], 0.345, PT + 0.004), (jack_w[0], jack_w[1] + 0.03, jack_w[2]), (jack_w[0], jack_w[1] + 0.012, jack_w[2])], 0.0022), "cable"))
static.append(("plug_p4_board", plug((jack_w[0], jack_w[1] + 0.006, jack_w[2]), (0.010, 0.014, 0.010)), "cable"))
static.append(("cable_y_conex", cable([ysplit, (0.275, 0.345, PT + 0.004), (0.275, 0.2925, PT + 0.0075), (0.268, 0.2925, PT + 0.0075)], 0.0022), "cable"))
static.append(("wires_converter_red", cable([(0.230, 0.288, PT + 0.020), (0.226, 0.262, PT + 0.012), (0.223, 0.244, PT + 0.009)], 0.0012), "cable_red"))
static.append(("wires_converter_black", cable([(0.230, 0.297, PT + 0.020), (0.227, 0.266, PT + 0.012), (0.223, 0.238, PT + 0.009)], 0.0012), "cable"))
usb_w = W(-2.0, P.ESP_YC, P.LEDGE_Z + 3.2)
static.append(("cable_usbc", cable([(0.165, 0.242, PT + 0.009), (0.160, 0.242, PT + 0.03), (usb_w[0] + 0.012, usb_w[1], usb_w[2])], 0.0018), "cable"))
static.append(("plug_usbc", plug((usb_w[0] + 0.006, usb_w[1], usb_w[2]), (0.014, 0.010, 0.006)), "cable"))
static.append(("cable_mains", cable([(UPS_P[0] + 0.125, UPS_P[1] + 0.04, PT + 0.012), (0.43, 0.34, PT + 0.004), (0.45, 0.418, PT + 0.004), (0.45, 0.428, 0.003), (0.45, 0.75, 0.003)], 0.003), "cable"))

# target marker (where the battery button is assumed to be)
tgt = trimesh.creation.cylinder(radius=0.006, height=0.002, sections=32)
tgt.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, (1, 0, 0)))
tgt.apply_translation((X_B, Y_FACE + 0.001, Z_AX))

# moving parts (local frames)
rack_local = trimesh.util.concatenate([T(P.rack())])
tip_local = place(T(P.tpu_tip()), p=(0, -0.012, 0))
pinion_local = T(P.pinion())


def rack_pose(tip_front_y):
    y0 = tip_front_y - TIP_LOCAL
    return np.array([X_B, y0, Z_AX])


def pinion_angle(tip_front_y):
    y0 = tip_front_y - TIP_LOCAL
    c = (PIN_W[1] - y0) * 1000                 # rack-local contact coordinate (mm)
    p = math.pi * P.MOD
    e = ((c - P.TEETH_Y0) + p / 2) % p - p / 2
    return (e / 1000) / RP


# ------------------------------------------------------------- robot meshes
def robot_groups(path):
    m = trimesh.load(path, process=False)
    m.apply_translation((0, 0, PT))
    fc = m.visual.face_colors
    out = []
    for col in np.unique(fc, axis=0):
        idx = np.where((fc == col).all(1))[0]
        sub = m.submesh([idx], append=True)
        out.append((tuple(int(c) for c in col), sub))
    return out


robot = {"lying": robot_groups(PLY_LIE), "standing": robot_groups(PLY_STAND)}
ROBOT_RGBA = {(0, 0, 0): (0.06, 0.06, 0.07, 1), (171, 176, 197): (0.80, 0.82, 0.86, 1),
              (229, 242, 242): (0.92, 0.94, 0.95, 1), (255, 255, 255): (0.97, 0.97, 0.97, 1)}

# ------------------------------------------------------------- GLB export (three.js frame: y up)
TO_THREE = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0], [0, 0, 0, 1.0]])


def pbr(rgba, metal=0.0, rough=0.6):
    return trimesh.visual.material.PBRMaterial(baseColorFactor=[int(255 * c) for c in rgba], metallicFactor=metal, roughnessFactor=rough)


def glb(items, path, origin=(0, 0, 0)):
    sc = trimesh.Scene()
    for name, mesh, rgba, metal, rough in items:
        mm = mesh.copy(); mm.apply_translation(-np.asarray(origin)); mm.apply_transform(TO_THREE)
        if not isinstance(mm.visual, trimesh.visual.TextureVisuals) or mm.visual.uv is None:
            mm.visual = trimesh.visual.TextureVisuals(material=pbr(rgba, metal, rough))
        sc.add_geometry(mm, node_name=name, geom_name=name)
    sc.export(path)
    return os.path.getsize(path)


METAL = {"alu": (0.85, 0.35), "servo": (0.1, 0.5), "horn": (0.8, 0.3)}
items = [(n, m, C[c], *METAL.get(c, (0.0, 0.65))) for n, m, c in static]
items.append(("button_target", tgt, C["target"], 0, 0.5))

# AprilTag quad with texture
tag_img = Image.open(TAG_PNG).convert("RGB").resize((720, 720), Image.NEAREST)
tag_img.save(f"{OUT}/glb/apriltag36h11_id0.png")
S = 0.180 / 2; xq = TAG_X0 - 0.0006   # paper glued on the flat front face
quad = trimesh.Trimesh(vertices=[[xq, S, TAG_Z - S], [xq, -S, TAG_Z - S], [xq, -S, TAG_Z + S], [xq, S, TAG_Z + S]], faces=[[0, 1, 2], [0, 2, 3]], process=False)
quad.visual = trimesh.visual.TextureVisuals(uv=[[0, 0], [1, 0], [1, 1], [0, 1]], image=tag_img)
items.append(("apriltag", quad, (1, 1, 1, 1), 0, 0.8))
sizes = {"dock": glb(items, f"{OUT}/glb/dock.glb")}

rack0 = rack_pose(TIP_RET)
sizes["plunger"] = glb([("rack", rack_local, C["print"], 0, 0.6), ("tpu_tip", tip_local, C["tpu"], 0, 0.9)], f"{OUT}/glb/plunger.glb")
sizes["pinion"] = glb([("pinion", pinion_local, C["print"], 0, 0.6)], f"{OUT}/glb/pinion.glb")

for pose, groups in robot.items():
    its = []
    for col, sub in groups:
        target = max(800, int(len(sub.faces) * 0.17))
        try:
            dec = sub.simplify_quadric_decimation(face_count=target)
        except Exception:
            dec = sub
        rgba = ROBOT_RGBA.get(col[:3], (0.8, 0.8, 0.8, 1))
        its.append((f"go2_{col[0]}", dec, rgba, 0.15 if col[:3] == (171, 176, 197) else 0.0, 0.45))
    sizes[f"go2_{pose}"] = glb(its, f"{OUT}/glb/go2_{pose}.glb")

layout = {"TIP_EXT": TIP_EXT, "TIP_RET": TIP_RET, "TIP_LOCAL": TIP_LOCAL, "X_B": X_B, "Z_AX": Z_AX, "PIN_W": PIN_W.tolist(),
          "RP": RP, "MOD": P.MOD, "TEETH_Y0": P.TEETH_Y0, "Y_FACE": Y_FACE, "glb_bytes": sizes}
json.dump(layout, open(f"{OUT}/glb/layout.json", "w"), indent=1)
print("GLB sizes", sizes)

# ------------------------------------------------------------- 2D dump for the dimensioned drawings (DUMP2D=path)
if os.environ.get("DUMP2D"):
    from scipy.spatial import ConvexHull
    out = {"static": [], "const": {"PT": PT, "X_B": X_B, "Y_T": Y_T, "Z_AX": Z_AX, "TAG_X0": TAG_X0, "TAG_Z": TAG_Z,
                                   "TIP_EXT": TIP_EXT, "TIP_RET": TIP_RET, "Y_FACE": Y_FACE, "BOX_X0": BOX_X0, "BOX_Y0": BOX_Y0}}
    for n, m, ck in static:
        if n.startswith(("cable", "wires", "plug")):
            continue
        xy = m.vertices[:, :2]
        h = ConvexHull(xy)
        out["static"].append({"name": n, "ck": ck, "hull": xy[h.vertices].round(5).tolist(), "zmax": float(m.bounds[1][2])})
    rk = trimesh.util.concatenate([place(rack_local, p=rack_pose(TIP_EXT)), place(tip_local, p=rack_pose(TIP_EXT))])
    h = ConvexHull(rk.vertices[:, :2]); out["static"].append({"name": "plunger_extended", "ck": "print", "hull": rk.vertices[h.vertices][:, :2].round(5).tolist(), "zmax": 0})
    for pose, groups in robot.items():
        mm = trimesh.util.concatenate([g for _, g in groups])
        try:
            mm = mm.simplify_quadric_decimation(face_count=12000)
        except Exception:
            pass
        out["robot_" + pose] = {"v": mm.vertices.round(4).tolist(), "f": mm.faces.tolist()}
    json.dump(out, open(os.environ["DUMP2D"], "w"))
    print("dumped", os.environ["DUMP2D"]); sys.exit(0)

# ------------------------------------------------------------- interference check (CHECK=1)
if os.environ.get("CHECK"):
    solid = [(n, m) for n, m, ck in static if m.is_watertight and not n.startswith(("cable", "base_mdf", "ramp"))]
    for pose, groups in robot.items():
        V = np.vstack([g.vertices for _, g in groups])
        V = V[np.random.default_rng(0).choice(len(V), min(len(V), 120000), replace=False)]
        for n, m in solid:
            lo, hi = m.bounds[0] - 0.002, m.bounds[1] + 0.002
            cand = V[np.all((V > lo) & (V < hi), axis=1)]
            hits = int(m.contains(cand).sum()) if len(cand) else 0
            if hits: print(f"[{pose}] robot penetrates {n}: {hits} vertices")
        # clearance robot <-> rack (retracted) and tip (extended)
        for label, tip in (("retracted", TIP_RET), ("extended", TIP_EXT)):
            rk = trimesh.util.concatenate([place(rack_local, p=rack_pose(tip)), place(tip_local, p=rack_pose(tip))])
            lo, hi = rk.bounds[0] - 0.003, rk.bounds[1] + 0.003
            cand = V[np.all((V > lo) & (V < hi), axis=1)]
            hits = int(rk.contains(cand).sum()) if len(cand) else 0
            dmin = float(np.min(np.linalg.norm(cand[:, None, :2] - [[X_B, tip]], axis=2))) if len(cand) else None
            print(f"[{pose}] plunger {label}: {hits} robot vertices inside, {len(cand)} near")
    plate_top = PT
    for pose, groups in robot.items():
        zmin = min(g.vertices[:, 2].min() for _, g in groups)
        print(f"[{pose}] robot zmin={zmin:.4f} (plate top {plate_top})")
    sys.exit(0)

# ------------------------------------------------------------- MuJoCo render scene
def build_model(pose, tip_front_y, show_target=True, show_lid=True):
    spec = mujoco.MjSpec()
    spec.compiler.degree = False
    g = spec.visual.global_; g.offwidth, g.offheight = 1800, 1200; g.fovy = 38
    q = spec.visual.quality; q.shadowsize = 8192; q.offsamples = 8
    hl = spec.visual.headlight; hl.ambient = [0.30, 0.30, 0.32]; hl.diffuse = [0.32, 0.32, 0.32]; hl.specular = [0.1, 0.1, 0.1]
    spec.visual.rgba.haze = [0.93, 0.94, 0.96, 1]
    sk = spec.add_texture(name="sky", type=mujoco.mjtTexture.mjTEXTURE_SKYBOX, builtin=mujoco.mjtBuiltin.mjBUILTIN_GRADIENT,
                          rgb1=[0.97, 0.97, 0.98], rgb2=[0.86, 0.88, 0.91], width=512, height=3072)
    fl = spec.add_texture(name="floor", type=mujoco.mjtTexture.mjTEXTURE_2D, builtin=mujoco.mjtBuiltin.mjBUILTIN_CHECKER,
                          rgb1=[0.86, 0.86, 0.85], rgb2=[0.82, 0.82, 0.81], width=512, height=512)
    fm = spec.add_material(name="floor"); fm.textures[mujoco.mjtTextureRole.mjTEXROLE_RGB] = "floor"; fm.texrepeat = [6, 6]; fm.reflectance = 0.05
    tt = spec.add_texture(name="tag", type=mujoco.mjtTexture.mjTEXTURE_2D, file=os.path.abspath(f"{OUT}/glb/apriltag36h11_id0.png"))
    tm = spec.add_material(name="tag"); tm.textures[mujoco.mjtTextureRole.mjTEXROLE_RGB] = "tag"
    wb = spec.worldbody
    wb.add_geom(type=mujoco.mjtGeom.mjGEOM_PLANE, size=[4, 4, 0.1], material="floor", contype=0, conaffinity=0)
    for pos, d, diff in [((-1.2, 1.4, 2.6), (0.4, -0.45, -1), 0.45), ((1.5, -1.0, 2.0), (-0.6, 0.4, -1), 0.22), ((0.0, 0.0, 3.0), (0, 0, -1), 0.12)]:
        wb.add_light(pos=pos, dir=d, diffuse=[diff] * 3, specular=[0.15] * 3, castshadow=True)

    def add(name, mesh, rgba, texcoord=None, material=None, spec_=0.3, shin=0.4):
        mh = spec.add_mesh(name=name)
        mh.uservert = np.asarray(mesh.vertices, dtype=np.float64).ravel().tolist()
        mh.userface = np.asarray(mesh.faces, dtype=np.int32).ravel().tolist()
        if texcoord is not None:
            mh.usertexcoord = np.asarray(texcoord, dtype=np.float64).ravel().tolist()
        mh.inertia = mujoco.mjtMeshInertia.mjMESH_INERTIA_SHELL
        if material is None:
            mat = spec.add_material(name="m_" + name, rgba=list(rgba)); mat.specular = spec_; mat.shininess = shin
            material = "m_" + name
        wb.add_geom(type=mujoco.mjtGeom.mjGEOM_MESH, meshname=name, material=material, contype=0, conaffinity=0)

    for n, mesh, ck in static:
        if n == "lid" and not show_lid:
            continue
        add(n, mesh, C[ck], spec_=0.6 if ck in ("alu", "servo") else 0.25)
    if show_target and tip_front_y > 0.15:
        add("target", tgt, C["target"])
    add("tag", quad, (1, 1, 1, 1), texcoord=[[0, 0], [1, 0], [1, 1], [0, 1]], material="tag")
    p0 = rack_pose(tip_front_y)
    add("rack", place(rack_local, p=p0), C["print"])
    add("tip", place(tip_local, p=p0), C["tpu"])
    add("pinion", place(pinion_local, Rz(pinion_angle(tip_front_y)), PIN_W), C["print"])
    if pose:
        for col, sub in robot[pose]:
            add(f"go2_{col[0]}_{col[1]}", sub, ROBOT_RGBA.get(col[:3], (0.8, 0.8, 0.8, 1)), spec_=0.5, shin=0.6)
    return spec.compile()


def cam_project(cam, W, H, fovy, pts):
    az, el = math.radians(cam["az"]), math.radians(cam["el"])
    fwd = np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)])
    pos = np.array(cam["lookat"]) - cam["dist"] * fwd
    right = np.cross(fwd, (0, 0, 1)); right /= np.linalg.norm(right); up = np.cross(right, fwd)
    f = (H / 2) / math.tan(math.radians(fovy) / 2)
    out = []
    for p in pts:
        v = np.array(p) - pos
        x, y, z = v @ right, v @ up, v @ fwd
        out.append((W / 2 + f * x / z, H / 2 - f * y / z))
    return out


try:
    FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 26)
    FONT_B = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 34)
except OSError:
    FONT = FONT_B = ImageFont.load_default()


def draw_labels(d, W, H, pts, labels):
    """labels go to left/right columns, sorted by anchor height, no overlaps."""
    items = []
    for (anchor, text, side), (u, v) in zip(labels, pts):
        bb = d.textbbox((0, 0), text, font=FONT); tw, th = bb[2] - bb[0], bb[3] - bb[1]
        side = side or ("L" if u < W / 2 else "R")
        items.append(dict(u=u, v=v, text=text, tw=tw, th=th, side=side))
    for side in ("L", "R"):
        col = sorted([it for it in items if it["side"] == side], key=lambda it: it["v"])
        y = 120
        for it in col:
            it["by"] = max(y, min(it["v"] - it["th"] / 2 - 8, H - 70))
            y = it["by"] + it["th"] + 16 + 18
        # if pushed off the bottom, shift column up
        over = (col[-1]["by"] + col[-1]["th"] + 16 - (H - 30)) if col else 0
        if over > 0:
            for it in col: it["by"] -= over
    for it in items:
        bw, bh = it["tw"] + 24, it["th"] + 18
        bx = 36 if it["side"] == "L" else W - 36 - bw
        ex = bx + bw if it["side"] == "L" else bx
        ey = it["by"] + bh / 2
        mx = ex + (40 if it["side"] == "L" else -40)
        d.line([(ex, ey), (mx, ey), (it["u"], it["v"])], fill=(30, 30, 35), width=3, joint="curve")
        d.ellipse([it["u"] - 7, it["v"] - 7, it["u"] + 7, it["v"] + 7], fill=(240, 110, 40), outline=(30, 30, 35), width=2)
        d.rounded_rectangle([bx, it["by"], bx + bw, it["by"] + bh], radius=8, fill=(255, 255, 255), outline=(30, 30, 35), width=2)
        d.text((bx + 12, it["by"] + 6), it["text"], font=FONT, fill=(25, 25, 30))


def render(name, pose, tip, cam, labels=(), title=None, W=1800, H=1200, show_lid=True):
    model = build_model(pose, tip, show_lid=show_lid)
    data = mujoco.MjData(model); mujoco.mj_forward(model, data)
    r = mujoco.Renderer(model, H, W)
    c = mujoco.MjvCamera(); c.lookat[:] = cam["lookat"]; c.distance = cam["dist"]; c.azimuth = cam["az"]; c.elevation = cam["el"]
    r.update_scene(data, c)
    r.scene.flags[mujoco.mjtRndFlag.mjRND_SHADOW] = True
    img = Image.fromarray(r.render())
    d = ImageDraw.Draw(img)
    if labels:
        pts = cam_project(cam, W, H, model.vis.global_.fovy, [l[0] for l in labels])
        draw_labels(d, W, H, pts, labels)
    if title:
        bb = d.textbbox((0, 0), title, font=FONT_B)
        d.rounded_rectangle([30, 26, 30 + bb[2] + 30, 26 + bb[3] + 24], radius=10, fill=(25, 27, 32))
        d.text((45, 34), title, font=FONT_B, fill=(255, 255, 255))
    img.save(f"{OUT}/img/{name}.png")
    del r
    return f"{OUT}/img/{name}.png"


servo_c = (X_B + P.PIN_X / 1000, Y_T + 0.056, PT + 0.175)
LB = {
    "tag": ((TAG_X0 - 0.002, 0.03, TAG_Z + 0.03), "AprilTag 36h11: the robot aligns to it", None),
    "tag_back": ((TAG_X0 + 0.006, 0.0, TAG_Z + 0.05), "AprilTag plate", None),
    "servo": (servo_c, "Servo STS3215 12 V", None),
    "tower": ((X_B + 0.062, Y_T + 0.045, PT + 0.122), "Printed tower: pinion + guide", None),
    "plunger": ((X_B, 0.150, Z_AX), "Plunger (rack) + TPU tip", None),
    "cradle": ((-0.02, -0.112, PT + 0.083), "Cradle: centers the body when lying down", None),
    "cradle_l": ((-0.02, 0.112, PT + 0.083), "Cradle: centers the body when lying down", None),
    "rail": ((-0.62, -0.27, PT + 0.03), "Funnel-shaped guide rails", None),
    "rail_l": ((-0.62, 0.27, PT + 0.03), "Funnel-shaped guide rails", None),
    "box": ((0.090, 0.248, PT + 0.046), "Box: ESP32 + Waveshare board", None),
    "ups": ((0.33, 0.339, PT + 0.031), "Qualitronix 12 V mini UPS", None),
    "conv": ((0.194, 0.242, PT + 0.018), "12 V → 5 V USB-C converter", None),
    "conex": ((0.245, 0.2925, PT + 0.015), "Y cable + P4 female w/ screw terminal", None),
    "esp32": (W(28.0, P.ESP_YC, P.LEDGE_Z + 4.8), "ESP32 DevKit (pins facing down)", None),
    "adapt": (W(93.0, 22.0, 9.0), "Bus Servo Adapter (A), jumpers on A", None),
    "cap": (W(86.0, 21.0, 15.0), "2200 µF capacitor on DC+/DC− terminal", None),
    "usbp": (W(-6.0, P.ESP_YC, P.LEDGE_Z + 3.2), "Converter USB-C plug", None),
    "p4p": ((jack_w[0], jack_w[1] + 0.008, jack_w[2]), "P4 plug (12 V) into the board", None),
    "mdf": ((-0.40, 0.33, PT), "MDF base (1.60 x 0.84 m)", None),
    "tag_r": ((TAG_X0 - 0.002, -0.06, TAG_Z + 0.03), "AprilTag 36h11: the robot aligns to it", "R"),
    "target": ((X_B, Y_FACE + 0.001, Z_AX), "Battery button (target)", None),
    "pinion": ((X_B + P.PIN_X / 1000 + 0.024, Y_T + P.PIN_Y / 1000, PT + 0.123), "Pinion m1.5 z32 (window)", None),
}

renders = []
renders.append(render("01_overview", "lying", TIP_RET,
                      {"lookat": (0.0, 0.0, 0.12), "dist": 2.3, "az": -38, "el": -27},
                      [LB["tag"], LB["servo"], LB["tower"], LB["rail_l"], LB["box"], LB["conv"], LB["ups"], LB["mdf"]],
                      "Go2 power on/off station — concept v0.2"))
renders.append(render("02_mechanism_pressing", "lying", TIP_EXT,
                      {"lookat": (X_B + 0.01, 0.17, Z_AX), "dist": 0.62, "az": 205, "el": -22},
                      [LB["servo"], LB["pinion"], LB["plunger"], LB["box"]],
                      "Plunger extended, pressing the button"))
renders.append(render("03_mechanism_retracted", "lying", TIP_RET,
                      {"lookat": (X_B + 0.01, 0.17, Z_AX), "dist": 0.62, "az": 205, "el": -22},
                      [LB["target"], LB["servo"]],
                      "Plunger retracted inside the tower"))
renders.append(render("04_robot_standing_released", "standing", TIP_RET,
                      {"lookat": (0.05, 0.02, 0.20), "dist": 2.1, "az": -32, "el": -17},
                      [LB["tag"], LB["servo"], LB["rail_l"]],
                      "After power-on: the Go2 stands up and leaves without touching anything"))
renders.append(render("05_top_view", "lying", TIP_EXT,
                      {"lookat": (0.0, 0.0, 0.0), "dist": 2.55, "az": 90.0, "el": -89.9},
                      [LB["rail"], LB["cradle"], LB["plunger"], LB["box"], LB["tag_back"]],
                      "Top view"))
renders.append(render("06_station_without_robot", None, TIP_EXT,
                      {"lookat": (-0.02, 0.0, 0.10), "dist": 1.75, "az": -40, "el": -30},
                      [LB["tag_r"], LB["cradle"], LB["plunger"], LB["servo"], LB["box"], LB["ups"], LB["rail_l"]],
                      "Station only (no robot)"))
renders.append(render("07_electronics_open", None, TIP_RET,
                      {"lookat": (0.12, 0.262, PT + 0.02), "dist": 0.50, "az": 250, "el": -64},
                      [LB["esp32"], LB["adapt"], LB["cap"], LB["usbp"], LB["p4p"], LB["conv"], LB["conex"], LB["ups"]],
                      "Electronics with the lid off", show_lid=False))
print("\n".join(renders))
