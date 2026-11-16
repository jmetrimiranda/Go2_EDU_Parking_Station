# Source for the parts and drawings

Python code that generates all the STLs, the renders and the dimensioned drawings. Use it when a measurement changes (for example, the button height).

| File | What it generates |
|---|---|
| `parts.py` | All printable parts (STL, in mm). The parameters are at the top of the file |
| `go2_pose.py` | The official Go2 model (MuJoCo Menagerie) lying down and standing |
| `assemble.py` | The full assembly, the PNG renders and the GLB models |
| `drawings.py` | The base plan and the side view of the post, with dimensions |
| `wiring_diagram.html` | The wiring diagram (open it in a browser, or take a screenshot with headless Chrome or Playwright) |
| `wiring_diagram_v2_pigtail.html` | The same diagram, using a P4 pigtail and two Wago lever connectors instead of the Conex 1000 |

## Parameters most likely to change (`parts.py`)

| Parameter | Default | Meaning |
|---|---|---|
| `RZ` | 125 mm | Height of the plunger axis above the top of the MDF (= button height with the robot lying down) |
| `RACK_LEN` | 175 mm | Rack length |
| `MOD`, `NZ` | 1.5 / 32 | Module and number of teeth of the pinion |
| `ESP_L`, `ESP_W` | 53 / 28.6 mm | ESP32 DevKit size (for the box) |
| `AD_L`, `AD_W`, `AD_HOLES` | 42 / 33 / (37, 28) mm | Waveshare board and its hole pattern |

## How to run

```bash
pip install trimesh manifold3d numpy mujoco scipy matplotlib pillow rtree fast-simplification
python3 parts.py ./stl                         # STLs only
# renders (need the Go2 model from MuJoCo Menagerie and the AprilTag image):
python3 go2_pose.py <mujoco_menagerie>/unitree_go2/go2.xml ./out
MUJOCO_GL=egl python3 assemble.py ./out ./out/go2_lying.ply ./out/go2_standing.ply <apriltag-imgs>/tag36h11/tag36_11_00000.png
DUMP2D=./out/layout2d.json MUJOCO_GL=egl python3 assemble.py ./out ./out/go2_lying.ply ./out/go2_standing.ply <tag.png>
python3 drawings.py ./out/layout2d.json ./out
# wiring diagrams (1600 × 1060 page, saved at 1.5× like the images in ../images):
google-chrome --headless=new --force-device-scale-factor=1.5 --window-size=1600,1060 --screenshot=wiring_diagram.png "file://$PWD/wiring_diagram.html"
```

`assemble.py` writes the renders to `./out/img/` and the GLBs to `./out/glb/`; `drawings.py` writes `base_plan_dimensions.png` and `apriltag_post_dimensions.png`. Copy them to `../images/`.

`assemble.py` also has a collision-check mode between the robot and the parts (`CHECK=1`).
