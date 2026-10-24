"""線香花火のこり：素材レンダリング。

夏の夜の庭先を、しゃがんだ目の高さから。手前の地面はぼかす（被写界深度）。蚊やりぶた、飛び石、トタンのバケツ、奥に竹垣と植えこみ。
out/dark.png  月あかりだけ
out/lit.png   火の玉の位置に橙の灯りを置いたもの（ゲームで火花の強さに合わせて重ねる）
out/geo.json  火の玉の画面位置
世界座標 1920x1080（x=-600〜1320。まん中の 0〜720 がスマホの縦画面）を 1.5 倍。1 = 1cm。
"""
import json, math, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "common"))
import bpy
from bpy_extras.object_utils import world_to_camera_view
import bl

OUT = os.path.join(os.path.dirname(__file__), "out")
os.makedirs(OUT, exist_ok=True)
FAST = "--fast" in sys.argv
S = 24 if FAST else 80
rnd = random.Random(3)

sc = bl.reset()
bl.world((0.03, 0.045, 0.1), 0.6)

# 地面：土＋草
g = bl.plane((900, 600), (0, 150, 0))
md = g.modifiers.new("s", 'SUBSURF'); md.subdivision_type = 'SIMPLE'; md.levels = md.render_levels = 6
tx = bpy.data.textures.new("gd", 'CLOUDS'); tx.noise_scale = 30
d = g.modifiers.new("d", 'DISPLACE'); d.texture = tx; d.strength = 3
soil = bl.mat("soil", (0.08, 0.07, 0.05), 0.95)
bl.noise_color(soil, (0.04, 0.035, 0.025), (0.11, 0.09, 0.06), scale=0.05, detail=8)
bl.noise_bump(soil, scale=0.4, strength=0.4)
bl.assign(g, soil); bl.smooth(g)
grass_m = bl.mat("grass", (0.09, 0.2, 0.05), 0.6)
g.data.materials.append(grass_m)
ps = g.modifiers.new("grass", 'PARTICLE_SYSTEM').particle_system
pst = ps.settings
pst.type = 'HAIR'; pst.count = 8000 if FAST else 30000; pst.hair_length = 5; pst.material = 2
pst.use_advanced_hair = True; pst.brownian_factor = 0.5; pst.factor_random = 0.6
pst.root_radius = 0.3; pst.tip_radius = 0.0; pst.radius_scale = 1
pst.child_type = 'INTERPOLATED'; pst.child_percent = 4 if FAST else 8; pst.rendered_child_count = 4 if FAST else 8
pst.roughness_2 = 0.8; pst.clump_factor = 0.3; pst.length_random = 0.7

# 飛び石
stone = bl.mat("stone", (0.22, 0.21, 0.2), 0.75)
bl.noise_color(stone, (0.1, 0.1, 0.1), (0.3, 0.29, 0.27), scale=0.15, detail=6)
bl.noise_bump(stone, scale=0.5, strength=0.5)
for i, (x, y, r) in enumerate([(-6, -120, 15), (14, -70, 14), (-8, -26, 13), (10, 20, 12), (-4, 64, 11)]):
    s = bl.sphere(r, (x, y, 0.5))
    s.scale = (1.0, 0.8 + rnd.random() * 0.2, 0.22)
    stx = bpy.data.textures.new(f"st{i}", 'CLOUDS'); stx.noise_scale = 6
    dd = s.modifiers.new("d", 'DISPLACE'); dd.texture = stx; dd.strength = 2.5
    s.rotation_euler[2] = rnd.random() * 3
    bl.assign(s, stone)

# トタンのバケツ（水入り）
zinc = bl.mat("zinc", (0.55, 0.57, 0.58), 0.35, 1.0)
bl.noise_color(zinc, (0.45, 0.46, 0.47), (0.66, 0.67, 0.66), scale=0.3, detail=8)
bx, by = 40, -5
bpy.ops.mesh.primitive_cone_add(vertices=96, radius1=11, radius2=14, depth=24, location=(bx, by, 12), end_fill_type='NOTHING')
b = bl.active(); bl.smooth(b)
so = b.modifiers.new("t", 'SOLIDIFY'); so.thickness = 0.3
bl.assign(b, zinc)
for z, r in [(4, 11.8), (12, 12.6), (20, 13.4)]:
    bpy.ops.mesh.primitive_torus_add(major_radius=r + 0.15, minor_radius=0.35, location=(bx, by, z), major_segments=96)
    bl.assign(bl.smooth(bl.active()), zinc)
bot = bl.cyl(11, 0.4, (bx, by, 0.3)); bl.assign(bot, zinc)
water = bl.cyl(13.0, 0.2, (bx, by, 18.5)); bl.assign(water, bl.mat("water", (0.02, 0.03, 0.04), 0.03, 0, IOR=1.33, Transmission_Weight=0.4))
handle = bpy.data.curves.new("h", 'CURVE'); handle.dimensions = '3D'; handle.bevel_depth = 0.3
sp = handle.splines.new('NURBS'); sp.points.add(4)
for i, (x, z) in enumerate([(-14, 23), (-12, 31), (0, 35), (12, 31), (14, 23)]):
    sp.points[i].co = (bx + x, by - 2, z, 1)
sp.use_endpoint_u = True; sp.order_u = 3
ho = bpy.data.objects.new("h", handle); bl.link(ho); handle.materials.append(zinc)
# 燃えかすの線香花火が2本、バケツのふちに
stick = bl.mat("stick", (0.5, 0.12, 0.25), 0.7)
for k in range(2):
    c = bl.cyl(0.25, 16, (bx - 4 + k * 3, by - 10, 22), verts=12)
    c.rotation_euler = (math.radians(-60), math.radians(12 - 20 * k), 0); bl.assign(c, stick)

# 蚊やりぶた（素焼き、かなりデフォルメ）
clay = bl.mat("clay", (0.55, 0.36, 0.22), 0.8)
bl.noise_color(clay, (0.45, 0.28, 0.17), (0.6, 0.4, 0.25), scale=0.6, detail=5)
px, py = -30, -45
Z0 = 0
body = bl.sphere(11, (px, py, Z0 + 11)); body.scale = (1, 1.15, 0.95); bl.assign(body, clay)
bool_c = bl.cyl(7.5, 12, (px, py - 12, Z0 + 11)); bool_c.rotation_euler = (math.radians(90), 0, 0)
bm = body.modifiers.new("b", 'BOOLEAN'); bm.object = bool_c; bm.operation = 'DIFFERENCE'
bl.hide([bool_c])
bpy.ops.mesh.primitive_torus_add(major_radius=7.6, minor_radius=1.0, location=(px, py - 11.2, Z0 + 11), rotation=(math.radians(90), 0, 0), major_segments=64)
bl.assign(bl.smooth(bl.active()), clay)
for sx in (-1, 1):
    bpy.ops.mesh.primitive_cone_add(radius1=3, radius2=0.5, depth=4.5, location=(px + sx * 6, py - 2, Z0 + 21), rotation=(math.radians(-15), math.radians(sx * 25), 0))
    bl.assign(bl.smooth(bl.active()), clay)
    for fy in (-6, 6):
        l = bl.cyl(2, 3, (px + sx * 6, py + fy, Z0 + 1.5)); bl.assign(l, clay)
# 中の蚊取り線香（うずまき）と火
coil = bpy.data.curves.new("coil", 'CURVE'); coil.dimensions = '3D'; coil.bevel_depth = 0.35
sp = coil.splines.new('POLY'); n = 160; sp.points.add(n - 1)
for i in range(n):
    a = i / n * math.pi * 2 * 3.2; r = 1 + i / n * 5.4
    sp.points[i].co = (px + r * math.cos(a), py - 5, Z0 + 11 + r * math.sin(a), 1)
co = bpy.data.objects.new("coil", coil); bl.link(co); coil.materials.append(bl.mat("coilm", (0.08, 0.22, 0.08), 0.8))
ember = bl.sphere(0.5, (px + 6.4 * math.cos(math.pi * 2 * 3.2), py - 5.3, Z0 + 11 + 6.4 * math.sin(math.pi * 2 * 3.2)))
bl.assign(ember, bl.emission("ember", (1, 0.3, 0.05), 30))
EMBER = ember.location.copy()

# 奥：竹垣と植えこみ
bamboo = bl.mat("bamboo", (0.42, 0.36, 0.2), 0.5)
bl.noise_color(bamboo, (0.32, 0.27, 0.15), (0.5, 0.43, 0.25), scale=0.2, detail=4)
for i in range(-80, 81):
    x = i * 4.2
    c = bl.cyl(2.0, 130, (x, 150, 65), verts=24); bl.assign(c, bamboo)
for z in (24, 70, 112):
    c = bl.cyl(1.4, 700, (0, 147, z), verts=16); c.rotation_euler = (0, math.radians(90), 0); bl.assign(c, bl.mat("rope", (0.08, 0.06, 0.04), 0.9))
leaf = bl.mat("leaf", (0.03, 0.08, 0.035), 0.6)
bl.noise_color(leaf, (0.015, 0.04, 0.02), (0.05, 0.12, 0.05), scale=1.5, detail=6)
bl.noise_bump(leaf, scale=1.2, strength=0.8)
for i in range(40):
    x = rnd.uniform(-340, 340)
    s = bl.sphere(rnd.uniform(14, 24), (x, 135 + rnd.uniform(-6, 6), rnd.uniform(4, 22)))
    tx2 = bpy.data.textures.new(f"lf{i}", 'CLOUDS'); tx2.noise_scale = 2; tx2.noise_depth = 4
    s.modifiers.new("sd", 'SUBSURF').levels = 1
    dd = s.modifiers.new("d", 'DISPLACE'); dd.texture = tx2; dd.strength = 5
    bl.assign(s, leaf)

# 月あかり（青く弱く）と、奥の家の窓のにじみ
bl.light('SUN', (0, 0, 100), 0.5, rot_deg=(50, 0, 160), angle=3, color=(0.55, 0.65, 1))
bl.light('AREA', (-60, 260, 70), 9e5, rot_deg=(-75, 0, 0), size=60, color=(1, 0.75, 0.45))
bl.light('POINT', EMBER + __import__("mathutils").Vector((0, -1.5, 0)), 3000, size=0.5, color=(1, 0.45, 0.15))

cam = bl.camera((0, -205, 62), rot_deg=(76, 0, 0), lens=24)
cam.data.dof.use_dof = True; cam.data.dof.aperture_fstop = 0.05
cam.data.sensor_fit = 'VERTICAL'; cam.data.sensor_height = 24
sc.render.resolution_x, sc.render.resolution_y = 2880, 1620   # 横長。スマホではまん中の 1080 を使う
bpy.context.view_layer.update()

# 火の玉の位置（ゲームの基準）。この下を照らす
BALL = (0, -110, 52)
cam.data.dof.focus_distance = 98
v = world_to_camera_view(sc, cam, __import__("mathutils").Vector(BALL))
def scr(p):
    v = world_to_camera_view(sc, cam, __import__("mathutils").Vector(p))
    return [round(v.x * 1920 - 600, 1), round((1 - v.y) * 1080, 1)]
geo = {"ball": scr(BALL), "smoke": scr(EMBER + __import__("mathutils").Vector((0, -2, 9))), "ground": scr((BALL[0], BALL[1], 1))}
json.dump(geo, open(os.path.join(OUT, "geo.json"), "w"))
print(geo)
if "--geo" in sys.argv:
    sys.exit(0)

sc.view_settings.exposure = 0.3
bl.render(os.path.join(OUT, "dark.png"), 2880, 1620, samples=S)
L = bl.light('POINT', BALL, 1.4e5, size=1.0, color=(1, 0.55, 0.2))
bl.render(os.path.join(OUT, "lit.png"), 2880, 1620, samples=S)
print("done")
