"""わたあめ職人：素材レンダリング。

夏祭りの夜店。ななめ上から見た、わたあめ機（ステンレスの釜と、まん中で回るザラメの皿）。奥に提灯のボケ。
out/bg.png    場面（綿と割りばしはゲーム側で描く）
out/geo.json  釜のふち・内がわの底・まん中の回転皿を、平面(cm)→画面に写すための点
720x1080 を 1.5 倍。1 = 1cm。
"""
import json, math, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "common"))
import bpy, mathutils
from bpy_extras.object_utils import world_to_camera_view
import bl

OUT = os.path.join(os.path.dirname(__file__), "out")
os.makedirs(OUT, exist_ok=True)
FAST = "--fast" in sys.argv
S = 24 if FAST else 128
RIM, BOWL_H, HEAD = 30.0, 16.0, 5.0     # 釜のふちの半径・深さ・回転皿の半径
Z0 = 70.0                               # 台の高さ


def lathe(points, name, segs=128):
    verts, faces = [], []
    n = len(points)
    for i in range(segs):
        a = 2 * math.pi * i / segs
        for r, z in points:
            verts.append((r * math.cos(a), r * math.sin(a), z))
    for i in range(segs):
        j = (i + 1) % segs
        for k in range(n - 1):
            faces.append((i * n + k, j * n + k, j * n + k + 1, i * n + k + 1))
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces)
    o = bpy.data.objects.new(name, me); bl.link(o); bl.smooth(o)
    m = o.modifiers.new("s", 'SUBSURF'); m.levels = m.render_levels = 2
    return o


def machine():
    steel = bl.mat("steel", (0.82, 0.82, 0.84), 0.18, 1.0)
    bl.noise_bump(steel, scale=2, strength=0.03)
    z = Z0
    # 釜：ふちを外へ丸めたボウル
    prof = [(0, z + 0.6), (14, z + 0.6), (22, z + 2.5), (27, z + 7), (29.4, z + 13), (RIM, z + BOWL_H), (RIM + 1.2, z + BOWL_H + 0.4), (RIM + 1.4, z + BOWL_H - 0.6)]
    b = lathe(prof, "bowl"); so = b.modifiers.new("t", 'SOLIDIFY'); so.thickness = 0.25; bl.assign(b, steel)
    # 台（白いほうろうの箱）
    base = bl.cube((50, 50, 30), (0, 0, z - 15)); bl.bevel(base, 2, 4)
    bl.assign(base, bl.mat("enamel", (0.92, 0.9, 0.86), 0.25))
    # まん中の回転皿（ザラメを入れる）とモーターの軸
    hub = bl.cyl(HEAD, 3.2, (0, 0, z + 5.2), verts=64); bl.bevel(hub, 0.6, 4); bl.smooth(hub)
    bl.assign(hub, bl.mat("head", (0.7, 0.7, 0.72), 0.25, 1.0))
    band = bl.cyl(HEAD + 0.05, 1.0, (0, 0, z + 5.2), verts=64)
    bm = bl.mat("mesh", (0.25, 0.25, 0.27), 0.4, 1.0); bl.assign(band, bm)
    sh = bl.cyl(1.2, 4, (0, 0, z + 2.5), verts=32); bl.assign(sh, steel)
    # ふたのザラメ（ピンク）
    sug = bl.cyl(HEAD - 1.2, 0.4, (0, 0, z + 6.9), verts=64); bl.assign(sug, bl.mat("sugar", (0.95, 0.55, 0.7), 0.6))


def stall():
    # 台：赤白の布をかけた夜店の台
    t = bl.cube((220, 140, 4), (0, 10, Z0 - 32)); bl.assign(t, bl.wood("counter", light=(0.6, 0.42, 0.28), dark=(0.36, 0.22, 0.14), scale=0.06, stretch=20))
    cloth = bl.cube((220, 60, 1), (0, -45, Z0 - 29.5))
    cm = bl.mat("cloth", (0.8, 0.12, 0.12), 0.8)
    N, L, b = bl.nodes(cm)
    tc = N.new("ShaderNodeTexCoord"); wv = N.new("ShaderNodeTexWave"); wv.wave_type = 'BANDS'; wv.bands_direction = 'X'
    wv.inputs["Scale"].default_value = 0.08; wv.wave_profile = 'SAW'
    L.new(tc.outputs["Object"], wv.inputs["Vector"])
    cr = N.new("ShaderNodeValToRGB"); cr.color_ramp.interpolation = 'CONSTANT'
    cr.color_ramp.elements[0].color = (0.8, 0.1, 0.1, 1); cr.color_ramp.elements[1].position = 0.5; cr.color_ramp.elements[1].color = (0.95, 0.93, 0.9, 1)
    L.new(wv.outputs["Fac"], cr.inputs["Fac"]); L.new(cr.outputs["Color"], b.inputs["Base Color"])
    bl.assign(cloth, cm)
    # 横にザラメの袋と割りばしの束
    bag = bl.cube((14, 9, 18), (-48, 22, Z0 - 21)); bl.bevel(bag, 1.5, 4); bl.assign(bag, bl.mat("bag", (0.95, 0.75, 0.82), 0.6))
    for i in range(14):
        c = bl.cyl(0.4, 22, (44 + (i % 5) * 0.9, 24 + (i // 5) * 0.9, Z0 - 19), verts=8)
        bl.assign(c, bl.mat(f"stick{i}", (0.85, 0.72, 0.5), 0.7))
    # 奥：屋台の背板（紅白の幕）と、つるした提灯・電球
    back = bl.cube((300, 2, 36), (0, 82, Z0 - 14))
    bm = bl.mat("maku", (0.8, 0.1, 0.1), 0.85)
    N, L, b = bl.nodes(bm)
    tc = N.new("ShaderNodeTexCoord"); wv = N.new("ShaderNodeTexWave"); wv.wave_type = 'BANDS'; wv.bands_direction = 'X'
    wv.inputs["Scale"].default_value = 0.06; wv.wave_profile = 'SAW'
    L.new(tc.outputs["Object"], wv.inputs["Vector"])
    cr = N.new("ShaderNodeValToRGB"); cr.color_ramp.interpolation = 'CONSTANT'
    cr.color_ramp.elements[0].color = (0.75, 0.08, 0.08, 1); cr.color_ramp.elements[1].position = 0.5; cr.color_ramp.elements[1].color = (0.92, 0.9, 0.86, 1)
    L.new(wv.outputs["Fac"], cr.inputs["Fac"]); L.new(cr.outputs["Color"], b.inputs["Base Color"])
    bl.noise_bump(bm, scale=0.3, strength=0.4)
    bl.assign(back, bm)
    rr = random.Random(9)
    for i in range(5):
        x = -80 + i * 40 + rr.uniform(-4, 4); zz = Z0 + 52 + rr.uniform(-4, 6)
        lan = bl.sphere(10, (x, 75, zz)); lan.scale = (1, 1, 1.25)
        bl.assign(lan, bl.emission(f"lan{i}", (1, 0.22, 0.08) if i % 2 == 0 else (1, 0.7, 0.35), 1.6))
        for dz in (-12.5, 12.5):
            cp = bl.cyl(6, 1.6, (x, 75, zz + dz), verts=32); bl.assign(cp, bl.mat(f"lc{i}{dz}", (0.08, 0.06, 0.05), 0.6))
    for i in range(26):
        x = -130 + i * 10.4; zz = Z0 + 80 - 10 * math.cos((i - 13) / 13 * 1.4)
        s = bl.sphere(1.4, (x, 85, zz)); bl.assign(s, bl.emission(f"bulb{i}", (1, 0.8, 0.45), 20))
    # 奥の人ごみの気配：かなりデフォルメした丸い影（シルエットのみ）
    sil = bl.mat("sil", (0.02, 0.02, 0.04), 0.9)
    for i in range(7):
        x = -110 + i * 36 + rr.uniform(-8, 8)
        body = bl.cyl(12, 60, (x * 1.6, 420, Z0 - 80), verts=24); bl.assign(body, sil)
        head = bl.sphere(10, (x * 1.6, 420, Z0 - 37)); bl.assign(head, sil)
    gnd = bl.cube((2000, 1200, 2), (0, 600, Z0 - 111)); bl.assign(gnd, bl.mat("street", (0.05, 0.04, 0.035), 0.5))
    # 遠くの夜店の灯り（ボケ玉になる）
    for i in range(60):
        x = rr.uniform(-320, 320); y = rr.uniform(450, 700); zz = Z0 + rr.uniform(-95, 0)
        s = bl.sphere(3.5, (x * 1.6, y, zz)); bl.assign(s, bl.emission(f"far{i}", rr.choice([(1, 0.6, 0.3), (1, 0.85, 0.5), (1, 0.3, 0.2)]), 30))


def lights():
    bl.world((0.02, 0.025, 0.06), 0.6)
    bl.light('AREA', (-30, -40, Z0 + 90), 300000, rot_deg=(25, -15, 0), size=40, color=(1, 0.8, 0.55))     # 屋台の裸電球
    bl.light('POINT', (35, 30, Z0 + 45), 80000, size=3, color=(1, 0.55, 0.3))                             # 提灯の赤い光
    bl.light('AREA', (0, -120, Z0 + 40), 40000, rot_deg=(70, 0, 0), size=60, color=(0.6, 0.7, 1))          # 前から弱く


def proj(sc, cam, p):
    v = world_to_camera_view(sc, cam, mathutils.Vector(p))
    return [round(v.x * 720, 1), round((1 - v.y) * 1080, 1)]


sc = bl.reset(); sc.view_settings.exposure = 0.2
machine(); stall(); lights()
cam = bl.camera((0, -165, Z0 + 108), rot_deg=(64, 0, 0), lens=34)
cam.data.sensor_fit = 'VERTICAL'; cam.data.sensor_height = 24
cam.data.dof.use_dof = True; cam.data.dof.focus_distance = 190; cam.data.dof.aperture_fstop = 0.008
sc.render.resolution_x, sc.render.resolution_y = 1080, 1620
bpy.context.view_layer.update()
# 綿が育つ高さ（ふちより少し下）の平面を写す：中心と x/y 方向 1cm の動き。ゲームはこの面で動かす
ZP = Z0 + BOWL_H - 3
geo = {"c": proj(sc, cam, (0, 0, ZP)), "rim": RIM, "head": HEAD, "zp": ZP,
       "px": proj(sc, cam, (1, 0, ZP)), "py": proj(sc, cam, (0, 1, ZP)),
       "ring": [proj(sc, cam, (RIM * math.cos(a / 32 * 6.283), RIM * math.sin(a / 32 * 6.283), Z0 + BOWL_H)) for a in range(32)],
       "headTop": proj(sc, cam, (0, 0, Z0 + 7)), "cam": [0, -165, Z0 + 108]}
# 平面の点 → 画面：透視をそのまま使えるよう、格子で書き出す（ゲームで双一次補間）
G = 9
geo["grid"] = [[proj(sc, cam, (-RIM * 1.4 + 2.8 * RIM * i / (G - 1), -RIM * 1.4 + 2.8 * RIM * j / (G - 1), ZP)) for i in range(G)] for j in range(G)]
geo["gridN"] = G; geo["gridR"] = RIM * 1.4
json.dump(geo, open(os.path.join(OUT, "geo.json"), "w"))
print("c", geo["c"], "px", geo["px"], "py", geo["py"])
if "--geo" in sys.argv: sys.exit(0)
bl.render(os.path.join(OUT, "bg.png"), 1080, 1620, samples=S)
print("done")
