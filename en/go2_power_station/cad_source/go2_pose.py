"""Pose the official Go2 model (MuJoCo Menagerie, derived from Unitree URDF) and export posed meshes."""
import sys, numpy as np, mujoco, trimesh, json
xml = sys.argv[1]; outdir = sys.argv[2]
m = mujoco.MjModel.from_xml_path(xml)
d = mujoco.MjData(m)
poses = {
    # joint order per leg: hip, thigh, calf  (FL, FR, RL, RR)
    "lying":    [0.0, 1.36, -2.65] * 4,   # StandDown/prone (values from unitree go2_stand_example)
    "standing": [0.0, 0.67, -1.30] * 4,   # stand (same example)
}
info = {}
for name, q in poses.items():
    d.qpos[:] = 0
    d.qpos[3] = 1.0
    d.qpos[7:19] = q
    mujoco.mj_forward(m, d)
    parts = []
    for g in range(m.ngeom):
        if m.geom_type[g] != mujoco.mjtGeom.mjGEOM_MESH: continue
        if m.geom_contype[g] != 0 or m.geom_conaffinity[g] != 0:  # visual geoms only
            continue
        mid = m.geom_dataid[g]
        va, vn = m.mesh_vertadr[mid], m.mesh_vertnum[mid]
        fa, fn = m.mesh_faceadr[mid], m.mesh_facenum[mid]
        v = m.mesh_vert[va:va+vn].copy()
        f = m.mesh_face[fa:fa+fn].copy()
        R = d.geom_xmat[g].reshape(3,3); p = d.geom_xpos[g]
        vw = v @ R.T + p
        matid = m.geom_matid[g]
        rgba = m.mat_rgba[matid] if matid >= 0 else m.geom_rgba[g]
        tm = trimesh.Trimesh(vw, f, process=False)
        tm.visual.face_colors = (np.array(rgba)*255).astype(np.uint8)
        parts.append(tm)
    allm = trimesh.util.concatenate(parts)
    zmin = allm.bounds[0][2]
    allm.apply_translation([0,0,-zmin])
    allm.export(f"{outdir}/go2_{name}.ply")
    # body/trunk frame info
    bid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "base")
    info[name] = {"bounds": (allm.bounds).tolist(), "base_z_after_shift": float(d.xpos[bid][2]-zmin), "zshift": float(-zmin), "nfaces": int(len(allm.faces))}
print(json.dumps(info, indent=1))
