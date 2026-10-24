"""流れ星に3回：素材レンダリング。

out/land.png  夜の丘と遠くの町（空は透明。星空はゲーム側で描く）720x1080 を 1.5 倍
1 = 1m。
"""
import math, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "common"))
import bpy
import bl

OUT = os.path.join(os.path.dirname(__file__), "out")
os.makedirs(OUT, exist_ok=True)
FAST = "--fast" in sys.argv
S = 24 if FAST else 128

sc = bl.reset()
sc.view_settings.exposure = 0.0
bl.world((0.05, 0.08, 0.18), 0.6)

# 地面（手前の丘）
def hill(size, loc, disp, scale, col, name, sub=7):
    p = bl.plane(size, loc)
    md = p.modifiers.new("s", 'SUBSURF'); md.subdivision_type = 'SIMPLE'; md.levels = md.render_levels = sub
    tx = bpy.data.textures.new(name, 'CLOUDS'); tx.noise_scale = scale; tx.noise_depth = 3
    d = p.modifiers.new("d", 'DISPLACE'); d.texture = tx; d.strength = disp; d.mid_level = 0.3
    m = bl.mat(name, col, 0.9)
    bl.noise_color(m, tuple(c * 0.7 for c in col), col, scale=0.05, detail=6)
    bl.assign(p, m); bl.smooth(p)
    return p

hill((300, 120), (0, 40, -2), 6, 18, (0.05, 0.09, 0.07), "near")
hill((900, 500), (0, 420, -6), 26, 80, (0.03, 0.05, 0.07), "far", sub=6)

# 一本の木（丘の右の上）
tree_m = bl.mat("tree", (0.02, 0.035, 0.03), 0.9)
trunk = bl.cyl(0.25, 4, (14, 46, 3.2)); bl.assign(trunk, tree_m)
rnd = random.Random(7)
for i in range(14):
    s = bl.sphere(1.4 + rnd.random() * 1.2, (14 + rnd.uniform(-2.4, 2.4), 46 + rnd.uniform(-1.5, 1.5), 6 + rnd.uniform(-0.8, 2.6)))
    bl.assign(s, tree_m)

# 遠くの町のあかり
win = [bl.emission(f"w{i}", c, 18) for i, c in enumerate([(1, 0.72, 0.38), (1, 0.85, 0.6), (0.95, 0.6, 0.3)])]
bm = bl.mat("bld", (0.02, 0.025, 0.04), 0.8)
for i in range(70):
    x = rnd.uniform(-160, 120); y = rnd.uniform(180, 260); h = rnd.uniform(2, 9)
    b = bl.cube((rnd.uniform(3, 7), 3, h), (x, y, h / 2 - 1)); bl.assign(b, bm)
    for k in range(rnd.randint(1, 4)):
        if rnd.random() < 0.7:
            w = bl.cube((0.7, 0.2, 0.6), (x + rnd.uniform(-1.5, 1.5), y - 1.6, rnd.uniform(0.5, h - 1)))
            bl.assign(w, win[rnd.randrange(3)])
# 月あかり
bl.light('SUN', (0, 0, 50), 0.35, rot_deg=(70, 0, -150), angle=1, color=(0.6, 0.72, 1))
bl.light('AREA', (-40, 120, 20), 3000, rot_deg=(-80, 0, 20), size=80, color=(1, 0.6, 0.35))

cam = bl.camera((0, -10, 7), rot_deg=(92, 0, 0), lens=26)
cam.data.sensor_fit = 'VERTICAL'; cam.data.sensor_height = 24
cam.data.shift_y = 0.14
bl.render(os.path.join(OUT, "land.png"), 1080, 1620, samples=S, transparent=True)
print("done")
