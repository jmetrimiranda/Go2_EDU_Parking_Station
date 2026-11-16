# Fonte das peças e dos desenhos

Código Python que gera todas as STLs, os renders e os desenhos com medidas. Use quando uma medida mudar (por exemplo, a altura do botão).

| Arquivo | O que gera |
|---|---|
| `parts.py` | Todas as peças imprimíveis (STL, em mm). Os parâmetros estão no topo do arquivo |
| `go2_pose.py` | O Go2 oficial (MuJoCo Menagerie) deitado e em pé |
| `assemble.py` | A montagem completa, os renders PNG e os modelos GLB |
| `drawings.py` | A planta da base e a vista lateral do poste com medidas |
| `esquema.html` | O esquema elétrico (abra no navegador ou capture com o Playwright) |

## Parâmetros mais prováveis de mudar (`parts.py`)

| Parâmetro | Padrão | Significado |
|---|---|---|
| `RZ` | 125 mm | Altura do eixo do êmbolo acima do topo do MDF (= altura do botão com o robô deitado) |
| `RACK_LEN` | 175 mm | Comprimento da cremalheira |
| `MOD`, `NZ` | 1,5 / 32 | Módulo e número de dentes do pinhão |
| `ESP_L`, `ESP_W` | 53 / 28,6 mm | Tamanho do ESP32 DevKit (para a caixa) |
| `AD_L`, `AD_W`, `AD_HOLES` | 42 / 33 / (37, 28) mm | Placa da Waveshare e furação |

## Como rodar

```bash
pip install trimesh manifold3d numpy mujoco scipy matplotlib pillow rtree fast-simplification
python3 parts.py ./stl                         # só as STLs
# renders (precisa do modelo do Go2 do MuJoCo Menagerie e da imagem da AprilTag):
python3 go2_pose.py <mujoco_menagerie>/unitree_go2/go2.xml ./out
MUJOCO_GL=egl python3 assemble.py ./out ./out/go2_deitado.ply ./out/go2_em_pe.ply <apriltag-imgs>/tag36h11/tag36_11_00000.png
DUMP2D=./out/layout2d.json MUJOCO_GL=egl python3 assemble.py ./out ./out/go2_deitado.ply ./out/go2_em_pe.ply <tag.png>
python3 drawings.py ./out/layout2d.json ./out
```

O `assemble.py` também tem um modo de checagem de colisão entre o robô e as peças (`CHECK=1`).
