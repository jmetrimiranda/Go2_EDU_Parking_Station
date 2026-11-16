"""Dimensioned drawings (top view of the base, side view of the AprilTag post) from layout2d.json.
usage: python3 -I drawings.py <layout2d.json> <outdir>"""
import sys, json, math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle, Circle
from matplotlib.collections import PolyCollection

L = json.load(open(sys.argv[1])); OUT = sys.argv[2]
C = L["const"]; PT = C["PT"] * 1000
INK = "#1d2430"; DIM = "#c2410c"; MUTED = "#5b6573"
COL = {"print": "#e8692c", "print_dark": "#3b4049", "servo": "#222326", "alu": "#aeb4bb", "white": "#f6f6f2",
       "ups": "#e9e9ee", "oled": "#1a1b1e", "mdf": "#e3c9a4", "term": "#3aa35a"}
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11})


def dim(ax, p1, p2, off, text, side=1, fs=10.5, color=DIM, ext=True, rot=None, z=9):
    """aligned dimension between p1 and p2 (mm), offset perpendicular by off."""
    p1, p2 = np.array(p1, float), np.array(p2, float)
    d = p2 - p1; n = np.array([-d[1], d[0]]) / (np.linalg.norm(d) + 1e-9)
    a, b = p1 + n * off, p2 + n * off
    if ext:
        for p, q in ((p1, a), (p2, b)):
            ax.plot([p[0], q[0] + n[0] * 6 * np.sign(off or 1)], [p[1], q[1] + n[1] * 6 * np.sign(off or 1)], color=color, lw=0.8, alpha=0.8)
    ax.annotate("", xy=b, xytext=a, arrowprops=dict(arrowstyle="<|-|>", color=color, lw=1.2, shrinkA=0, shrinkB=0, mutation_scale=10), zorder=z)
    m = (a + b) / 2
    ang = math.degrees(math.atan2(d[1], d[0])) if rot is None else rot
    if ang > 90: ang -= 180
    if ang < -90: ang += 180
    ax.text(m[0] + n[0] * 9 * side, m[1] + n[1] * 9 * side, text, color=color, fontsize=fs, ha="center", va="center", rotation=ang,
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.9), zorder=z + 1)


def note(ax, xy, xytext, text, fs=10.5, ha=None):
    ax.annotate(text, xy=xy, xytext=xytext, fontsize=fs, color=INK, ha=ha or ("left" if xytext[0] >= xy[0] else "right"), va="center", zorder=12,
                arrowprops=dict(arrowstyle="-", color=INK, lw=0.8, shrinkA=2, shrinkB=2),
                bbox=dict(boxstyle="round,pad=0.25", fc="white", ec=INK, lw=0.6))


def robot_patches(key, plane):
    v = np.array(L[key]["v"]) * 1000; f = np.array(L[key]["f"])
    if plane == "xy":
        P = v[:, [0, 1]]
    else:
        P = v[:, [0, 2]]; P[:, 1] -= PT
    return P[f]


# ================================================================ top view
fig, ax = plt.subplots(figsize=(19, 11), dpi=125)
ax.set_aspect("equal"); ax.set_xlim(-960, 960); ax.set_ylim(-560, 690); ax.axis("off")
ax.add_patch(Rectangle((-800, -420), 1600, 840, fc=COL["mdf"], ec=INK, lw=1.2, zorder=0))
ax.add_patch(Polygon([(-860, -420), (-800, -420), (-800, 420), (-860, 420)], fc="#d6b98f", ec=INK, lw=0.8, zorder=0))
ax.text(-830, 0, "rampa", rotation=90, ha="center", va="center", fontsize=9, color=MUTED)
skip = {"base_mdf", "rampa", "pcb", "esp32", "conector_p4_placa", "borne_verde", "capacitor", "tampa", "ups_led", "horn", "conex_borne"}
for s in L["static"]:
    if s["name"] in skip:
        continue
    ck = s["ck"]; col = COL.get(ck, "#888")
    ax.add_patch(Polygon(np.array(s["hull"]) * 1000, closed=True, fc=col, ec=INK, lw=0.7, alpha=0.95, zorder=3 if ck != "print_dark" else 2))
pc = PolyCollection(robot_patches("robot_deitado", "xy"), fc="#d3d7dd", ec="#d3d7dd", lw=0.3, alpha=0.8, zorder=4)
ax.add_collection(pc)
ax.text(470, -135, "Go2 deitado\n(silhueta cinza)", ha="center", va="center", fontsize=10, color=MUTED, zorder=5)
# centre + axes
ax.plot([-800, 800], [0, 0], color=MUTED, lw=0.8, ls=(0, (8, 4, 2, 4)), zorder=1)
ax.plot([0, 0], [-420, 420], color=MUTED, lw=0.8, ls=(0, (8, 4, 2, 4)), zorder=1)
ax.add_patch(Circle((0, 0), 9, fc="white", ec=DIM, lw=1.5, zorder=6)); ax.plot([-14, 14], [0, 0], color=DIM, lw=1.2, zorder=7); ax.plot([0, 0], [-14, 14], color=DIM, lw=1.2, zorder=7)
ax.annotate("", xy=(620, -525), xytext=(420, -525), arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.5))
ax.text(400, -525, "frente do robô (x)", ha="right", va="center", fontsize=10, color=INK)
# plunger axis
xb = C["X_B"] * 1000
ax.plot([xb, xb], [97, 215], color=DIM, lw=1.2, ls="--", zorder=8)
# dimensions
dim(ax, (-800, -420), (800, -420), -48, "1600 (MDF)")
dim(ax, (-800, -420), (-800, 420), 70, "840", rot=90)
dim(ax, (0, -360), (C["TAG_X0"] * 1000, -360), 0, "661 do centro até a face da tag", ext=False)
dim(ax, (680, 270), (800, 270), 0, "120", ext=False)
ax.plot([680, 680], [-60, 280], color=DIM, lw=0.8, ls=":")
dim(ax, (0, 470), (xb, 470), 0, "70", ext=False)
ax.plot([xb, xb], [215, 480], color=DIM, lw=0.8, ls=":"); ax.plot([0, 0], [420, 480], color=DIM, lw=0.8, ls=":")
note(ax, (xb, 160), (-560, 565), "Eixo do êmbolo: 70 mm atrás do centro\n(= posição do botão da bateria, a confirmar)", ha="left")
dim(ax, (-210, 0), (-210, C["Y_T"] * 1000), 0, "205", ext=False, rot=90)
ax.plot([-230, -40], [205, 205], color=DIM, lw=0.8, ls=":")
dim(ax, (200, -175), (200, 175), 0, "350 entre os trilhos", ext=False, rot=90)
dim(ax, (-500, -255), (300, -255), 0, "800 (trilhos retos)", ext=False)
dim(ax, (-740, -325), (-740, 325), 0, "650 na boca do funil", ext=False, rot=90)
note(ax, (-25, 118), (-330, 330), "Berço (05 + 06): 200 × 248")
note(ax, (90, 248), (250, 500), "Caixa da eletrônica (10/11)")
note(ax, (194, 242), (420, 470), "Conversor 12 V → 5 V USB-C")
note(ax, (245, 292), (470, 410), "Conex P4 fêmea + cabo Y")
note(ax, (335, 340), (520, 350), "Nobreak Qualitronix")
note(ax, (-40, 250), (-470, 470), "Torre do servo (01)", ha="left")
note(ax, (680, 40), (720, 180), "Pé do poste (09) + tag")
note(ax, (-600, 185), (-930, 470), "Trilhos 07 (10×) e 07b (2×)", ha="left")
ax.text(-940, 680, "Planta da base — vista de cima (medidas em mm)", fontsize=17, fontweight="bold", color=INK, va="top")
ax.text(-940, 645, "⊕ = origem (0, 0): centro do berço = centro do robô deitado. Trilhos e berço são simétricos em relação à linha de centro.", fontsize=11, color=MUTED, va="top")
fig.savefig(f"{OUT}/planta_base_cotas.png", bbox_inches="tight", facecolor="white"); plt.close(fig)

# ================================================================ side view of the post
fig, ax = plt.subplots(figsize=(16, 8.6), dpi=125)
ax.set_aspect("equal"); ax.set_xlim(-470, 1010); ax.set_ylim(-70, 600); ax.axis("off")
ax.add_patch(Rectangle((-800, -15), 1600, 15, fc=COL["mdf"], ec=INK, lw=1))
ax.text(-440, -40, "MDF 15–18 mm (as alturas abaixo são medidas a partir do topo do MDF)", fontsize=10, color=MUTED)
pc = PolyCollection(robot_patches("robot_deitado", "xz"), fc="#d3d7dd", ec="#d3d7dd", lw=0.4, alpha=1.0)
ax.add_collection(pc)
ax.text(-60, 110, "Go2 deitado", ha="center", fontsize=10, color=INK)
# foot, post, plate, tag
ax.add_patch(Rectangle((630, 0), 100, 6, fc=COL["print"], ec=INK, lw=0.8))
ax.add_patch(Rectangle((665.5, 0), 29, 46, fc=COL["print"], ec=INK, lw=0.8))
ax.add_patch(Rectangle((670, 3), 20, 420, fc=COL["alu"], ec=INK, lw=0.8))
ax.add_patch(Rectangle((661, 200), 5, 200, fc=COL["white"], ec=INK, lw=0.8))
ax.add_patch(Rectangle((666, 260), 24, 80, fc=COL["print"], ec=INK, lw=0.8, alpha=0.9))
ax.plot([659.5, 659.5], [210, 390], color="#bbbbbb", lw=4, solid_capstyle="butt")
ax.plot([659.5, 659.5], [228, 372], color="black", lw=4, solid_capstyle="butt")
for zz in (275, 325):
    ax.plot([668, 692], [zz, zz], color=INK, lw=1)
# camera marks (estimates)
ax.plot([327], [170], marker="o", ms=8, mfc=DIM, mec=INK)
ax.plot([327], [355], marker="o", ms=8, mfc="white", mec=DIM, mew=2)
ax.plot([327, 655], [355, 300], color=DIM, lw=0.9, ls="--")
ax.plot([327, 655], [170, 300], color=DIM, lw=0.9, ls="--")
note(ax, (327, 355), (60, 450), "Câmera com o robô em pé ≈ 355 (estimado)")
note(ax, (327, 170), (40, 250), "Câmera com o robô deitado ≈ 170")
ax.plot([600, 700], [300, 300], color=DIM, lw=0.8, ls=":")
# dimensions
dim(ax, (780, 0), (780, 300), 0, "300 centro da tag", ext=False, rot=90)
ax.plot([700, 790], [300, 300], color=DIM, lw=0.8, ls=":")
dim(ax, (860, 200), (860, 400), 0, "200 placa", ext=False, rot=90)
ax.plot([668, 870], [200, 200], color=DIM, lw=0.8, ls=":"); ax.plot([668, 870], [400, 400], color=DIM, lw=0.8, ls=":")
dim(ax, (940, 3), (940, 423), 0, "420 poste", ext=False, rot=90)
ax.plot([692, 950], [423, 423], color=DIM, lw=0.8, ls=":")
dim(ax, (620, 228), (620, 372), 0, "144", ext=False, rot=90, fs=9.5)
dim(ax, (0, 470), (661, 470), 0, "661 do centro do robô até a face da tag", ext=False)
ax.plot([0, 0], [0, 480], color=MUTED, lw=0.8, ls=(0, (8, 4, 2, 4)))
ax.plot([661, 661], [400, 480], color=DIM, lw=0.8, ls=":")
dim(ax, (330, 30), (661, 30), 0, "≈ 330 livre", ext=False)
dim(ax, (630, -55), (730, -55), 0, "100", ext=False, fs=9.5)
note(ax, (680, 30), (860, 70), "Pé do poste (09) ou cantoneira")
note(ax, (678, 300), (720, 470), "Encaixe deslizante (2 parafusos M4)")
note(ax, (659, 330), (480, 400), "Tag 36h11 ID 0: preto 144, papel 180")
ax.text(-460, 598, "Poste da AprilTag — vista lateral (medidas em mm)", fontsize=17, fontweight="bold", color=INK, va="top")
ax.text(-460, 566, "A placa desliza no poste: ajuste a altura olhando a imagem da câmera (veja a Parte 1).", fontsize=11, color=MUTED, va="top")
fig.savefig(f"{OUT}/poste_apriltag_cotas.png", bbox_inches="tight", facecolor="white"); plt.close(fig)
print("ok")
