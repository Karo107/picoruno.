"""たまご片手わり：素材レンダリング。

朝の台所。白い陶器のボウル（ここにたまごを割り入れる）、奥に卵のパック。
out/bg.png       からのボウル
out/bg_ok.png    黄身がきれいなまま入ったボウル
out/bg_bad.png   黄身がくずれたボウル
out/egg.png      横にした卵（透明背景、ゲームで動かす・割る）
out/geo.json     ボウルのふち・中身の位置・1cm の大きさ
720x1080 を 1.5 倍。1 = 1cm。
"""
import json, math, os, sys, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "common"))
import bpy, mathutils
from bpy_extras.object_utils import world_to_camera_view
import bl

OUT = os.path.join(os.path.dirname(__file__), "out")
os.makedirs(OUT, exist_ok=True)
FAST = "--fast" in sys.argv
S = 24 if FAST else 128
RIM_R, RIM_Z = 9.2, 6.55


def lathe(points, name, segs=96, sub=2):
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
    if sub:
        m = o.modifiers.new("s", 'SUBSURF'); m.levels = m.render_levels = sub
    return o


def shell_mat():
    m = bl.mat("shell", (0.86, 0.68, 0.52), 0.55, Subsurface_Weight=0.15)
    N, L, b = bl.nodes(m)
    # こまかい斑点と、ざらっとした表面
    tc = N.new("ShaderNodeTexCoord"); nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 6; nz.inputs["Detail"].default_value = 8
    L.new(tc.outputs["Object"], nz.inputs["Vector"])
    cr = N.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].position = 0.45; cr.color_ramp.elements[0].color = (0.78, 0.52, 0.33, 1)
    cr.color_ramp.elements[1].position = 0.7; cr.color_ramp.elements[1].color = (0.82, 0.57, 0.37, 1)
    L.new(nz.outputs["Fac"], cr.inputs["Fac"]); L.new(cr.outputs["Color"], b.inputs["Base Color"])
    bl.noise_bump(m, scale=40, strength=0.015)
    return m


def egg(loc, rot=(0, 0, 0), r=2.15, m=None):
    e = bl.sphere(r, loc); e.scale = (1, 1, 1.3)
    e.rotation_euler = [math.radians(a) for a in rot]
    # とがった方を少し細く
    sd = e.modifiers.new("t", 'SIMPLE_DEFORM'); sd.deform_method = 'TAPER'; sd.factor = 0.18; sd.deform_axis = 'Z'
    bl.assign(e, m or shell_mat())
    return e


def bowl():
    prof = [(0, 0), (3.6, 0), (4.3, 0.35), (6.8, 2.1), (8.4, 4.4), (9.05, 6.0), (RIM_R, RIM_Z), (8.85, 6.62), (8.55, 5.8), (7.5, 3.5), (5.4, 1.4), (3, 0.78), (0, 0.72)]
    b = lathe(prof, "bowl", segs=128)
    m = bl.mat("glaze", (0.95, 0.94, 0.9), 0.12, Coat_Weight=0.6)
    N, L, bs = bl.nodes(m)
    # ふちに藍の線を一本
    tc = N.new("ShaderNodeTexCoord"); sep = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Object"], sep.inputs[0])
    mr = N.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = 5.6; mr.inputs["From Max"].default_value = 5.75
    L.new(sep.outputs["Z"], mr.inputs["Value"])
    mr2 = N.new("ShaderNodeMapRange"); mr2.inputs["From Min"].default_value = 6.05; mr2.inputs["From Max"].default_value = 5.9
    L.new(sep.outputs["Z"], mr2.inputs["Value"])
    mul = N.new("ShaderNodeMath"); mul.operation = 'MULTIPLY'; L.new(mr.outputs[0], mul.inputs[0]); L.new(mr2.outputs[0], mul.inputs[1])
    mix = N.new("ShaderNodeMix"); mix.data_type = 'RGBA'
    mix.inputs[6].default_value = (0.95, 0.94, 0.9, 1); mix.inputs[7].default_value = (0.12, 0.22, 0.48, 1)
    L.new(mul.outputs[0], mix.inputs[0]); L.new(mix.outputs[2], bs.inputs["Base Color"])
    bl.assign(b, m)


def contents(kind):
    if kind is None: return
    wm = bl.mat("white", (1.0, 0.99, 0.94), 0.01, Transmission_Weight=1.0, IOR=1.36, Coat_Weight=0.5)
    N, L, b = bl.nodes(wm)
    vol = N.new("ShaderNodeVolumeAbsorption"); vol.inputs["Color"].default_value = (0.95, 0.92, 0.7, 1); vol.inputs["Density"].default_value = 0.04
    L.new(vol.outputs[0], N["Material Output"].inputs["Volume"])
    ym = bl.mat("yolk", (1.0, 0.42, 0.02), 0.05, Subsurface_Weight=0.5, Coat_Weight=1.0)
    ym.node_tree.nodes["Principled BSDF"].inputs["Subsurface Radius"].default_value = (1.0, 0.4, 0.1)
    tex = bpy.data.textures.new("lump", 'CLOUDS'); tex.noise_scale = 0.9
    for (loc, sc_) in (((0.2, 0.4, 1.0), (4.8, 4.1, 0.5)), ((0.1, 0.2, 1.1), (2.8, 2.5, 0.72))):   # 水様卵白・濃厚卵白
        w = bl.sphere(1, loc); w.scale = sc_
        d = w.modifiers.new("d", 'DISPLACE'); d.texture = tex; d.strength = 0.25; d.direction = 'X'
        d2 = w.modifiers.new("d2", 'DISPLACE'); d2.texture = tex; d2.strength = 0.25; d2.direction = 'Y'; d2.mid_level = 0.45
        bl.assign(w, wm)
    if kind == "ok":
        y = bl.sphere(1.75, (-0.2, 0.0, 1.6)); y.scale = (1, 1, 0.72); bl.assign(y, ym)
    else:
        y = bl.sphere(1, (-0.4, -0.3, 1.55)); y.scale = (2.6, 1.8, 0.26)
        d = y.modifiers.new("d", 'DISPLACE'); d.texture = bpy.data.textures.new("ly", 'CLOUDS'); d.texture.noise_scale = 0.6; d.strength = 0.5; d.direction = 'X'
        bl.assign(y, ym)
        y2 = bl.sphere(1, (0.9, 0.9, 1.5)); y2.scale = (1.3, 0.9, 0.22); bl.assign(y2, ym)


def kitchen():
    top = bl.cube((200, 120, 4), (0, 20, -2))
    bl.assign(top, bl.wood("counter", light=(0.6, 0.42, 0.27), dark=(0.4, 0.26, 0.15), scale=0.08, rough=0.35, bump=0.06, stretch=20))
    wall = bl.plane((200, 100), (0, 45, 50), rot=(90, 0, 0))
    wm = bl.mat("tile", (0.93, 0.92, 0.88), 0.15)
    N, L, b = bl.nodes(wm)
    tc = N.new("ShaderNodeTexCoord"); br = N.new("ShaderNodeTexBrick")
    br.inputs["Scale"].default_value = 1; br.inputs["Mortar Size"].default_value = 0.025
    br.inputs["Color1"].default_value = (0.86, 0.9, 0.88, 1); br.inputs["Color2"].default_value = (0.83, 0.88, 0.86, 1)
    br.inputs["Mortar"].default_value = (0.72, 0.74, 0.72, 1)
    br.offset = 0.0; br.squash = 1.0
    mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1 / 10, 1 / 10, 1)
    L.new(tc.outputs["Object"], mp.inputs["Vector"]); L.new(mp.outputs["Vector"], br.inputs["Vector"])
    L.new(br.outputs["Color"], b.inputs["Base Color"])
    bp = N.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.3
    L.new(br.outputs["Fac"], bp.inputs["Height"]); L.new(bp.outputs["Normal"], b.inputs["Normal"])
    bl.assign(wall, wm)
    # 奥の壁：木の棚と、びん・小さな鉢
    shelf = bl.cube((90, 12, 1.6), (0, 39, 7)); bl.bevel(shelf, 0.3, 3)
    bl.assign(shelf, bl.wood("shelf", light=(0.55, 0.38, 0.24), dark=(0.36, 0.23, 0.13), scale=0.1))
    glass = bl.mat("jar", (0.95, 0.97, 1.0), 0.03, Transmission_Weight=1.0, IOR=1.45)
    fills = [((0.9, 0.75, 0.35), 0.6), ((0.55, 0.25, 0.15), 0.7), ((0.95, 0.93, 0.88), 0.9)]
    for i, (x, h) in enumerate([(-22, 11), (-13, 8), (-5, 13)]):
        j = bl.cyl(3.4, h, (x, 39, 7.8 + h / 2), verts=64); bl.bevel(j, 0.5, 3); bl.assign(j, glass)
        f = bl.cyl(3.1, h * 0.7, (x, 39, 7.9 + h * 0.35), verts=64); bl.assign(f, bl.mat(f"fill{i}", fills[i][0], fills[i][1]))
        lid = bl.cyl(3.5, 1.2, (x, 39, 8.4 + h), verts=64); bl.bevel(lid, 0.3, 2)
        bl.assign(lid, bl.wood(f"lid{i}", light=(0.7, 0.52, 0.34), dark=(0.5, 0.34, 0.2), scale=0.3))
    pot = bl.cyl(3.6, 6, (14, 39, 10.8)); bl.bevel(pot, 0.4, 3); bl.assign(pot, bl.mat("pot", (0.85, 0.82, 0.76), 0.6))
    rr = random.Random(4)
    for i in range(9):
        lf = bl.sphere(1.6, (14 + rr.uniform(-3, 3), 39 + rr.uniform(-2, 2), 15 + rr.uniform(0, 5))); lf.scale = (1, 0.6, 1.5)
        lf.rotation_euler = (rr.uniform(-0.5, 0.5), rr.uniform(-0.6, 0.6), rr.uniform(0, 3)); bl.assign(lf, bl.mat(f"leaf{i}", (0.2, 0.42, 0.18), 0.5))
    # 奥：卵のパック（紙）
    pm = bl.mat("pulp", (0.72, 0.7, 0.66), 0.95); bl.noise_bump(pm, scale=30, strength=0.25)
    tray = bl.cube((24, 11, 2.2), (17, 26, 1.1)); bl.bevel(tray, 0.4, 3); bl.assign(tray, pm)
    sm = shell_mat()
    for i in range(5):
        for j in range(2):
            if (i, j) in ((1, 0), (3, 1), (4, 0)): continue
            egg((17 - 9.6 + i * 4.8, 26 - 2.6 + j * 5.2, 3.6), rot=(0, 0, 0), m=sm)
    # 左：小皿と、木べら
    dish = lathe([(0, 0), (3.5, 0), (5.2, 0.9), (5.4, 1.1), (5.1, 1.1), (3.4, 0.35), (0, 0.3)], "dish", segs=96)
    dish.location = (-17, 10, 0); bl.assign(dish, bl.mat("dish", (0.55, 0.62, 0.58), 0.2, Coat_Weight=0.5))
    sp = bl.cube((26, 3.2, 0.8), (-12, 24, 0.4), rot=(0, 0, 18)); bl.bevel(sp, 0.35, 3)
    bl.assign(sp, bl.wood("spoon", light=(0.82, 0.66, 0.46), dark=(0.66, 0.5, 0.32), scale=0.4))
    cloth = bl.cube((12, 9, 0.6), (21, 4, 0.3), rot=(0, 0, -10)); bl.bevel(cloth, 0.25, 3)
    clm = bl.mat("cloth", (0.9, 0.82, 0.62), 0.9); bl.noise_bump(clm, scale=8, strength=0.3); bl.assign(cloth, clm)


def lights():
    bl.world((0.9, 0.93, 0.98), 0.25)
    fm = bl.mat("frame", (0.3, 0.3, 0.3), 0.8)   # 窓わく（光の中に置いて、壁に影を落とす）
    for x in (-70, -40, -10):
        b = bl.cube((1.4, 1.4, 70), (x, -30, 60), rot=(0, 0, 0)); bl.assign(b, fm); b.visible_camera = False
    for z in (45, 75):
        b = bl.cube((70, 1.4, 1.4), (-40, -30, z)); bl.assign(b, fm); b.visible_camera = False
    bl.light('AREA', (-50, -20, 50), 120000, rot_deg=(55, 0, -65), size=50, color=(1, 0.93, 0.82))
    bl.light("SUN", (0, 0, 50), 2.5, rot_deg=(45, 0, -55), angle=4, color=(1, 0.9, 0.75))
    bl.light('AREA', (30, -50, 30), 40000, rot_deg=(60, 0, 30), size=60, color=(0.9, 0.94, 1))


def proj(sc, cam, p):
    v = world_to_camera_view(sc, cam, mathutils.Vector(p))
    return [round(v.x * 720, 1), round((1 - v.y) * 1080, 1)]


def setup_cam():
    cam = bl.camera((0, -52, 36), rot_deg=(65, 0, 0), lens=40)
    cam.data.sensor_fit = 'VERTICAL'; cam.data.sensor_height = 24
    cam.data.dof.use_dof = True; cam.data.dof.focus_distance = 64; cam.data.dof.aperture_fstop = 0.25
    return cam


geo = None
for kind in ([None] if "--one" in sys.argv else [None, "ok", "bad"]):
    sc = bl.reset(); sc.view_settings.exposure = -0.7
    sc.cycles.transmission_bounces = 12; sc.cycles.max_bounces = 16
    kitchen(); lights(); bowl(); contents(kind)
    cam = setup_cam()
    sc.render.resolution_x, sc.render.resolution_y = 1080, 1620
    bpy.context.view_layer.update()
    if geo is None:
        geo = {"c": proj(sc, cam, (0, 0, RIM_Z)), "bottom": proj(sc, cam, (0, 0, 1.2)),
               "ring": [proj(sc, cam, (RIM_R * math.cos(a / 48 * 6.283), RIM_R * math.sin(a / 48 * 6.283), RIM_Z)) for a in range(48)],
               "hit": proj(sc, cam, (RIM_R * math.cos(-0.25), RIM_R * math.sin(-0.25), RIM_Z)),
               "ppc": round(proj(sc, cam, (1, 0, RIM_Z))[0] - proj(sc, cam, (0, 0, RIM_Z))[0], 2),
               "front": proj(sc, cam, (0, -RIM_R, RIM_Z)), "back": proj(sc, cam, (0, RIM_R, RIM_Z))}
        json.dump(geo, open(os.path.join(OUT, "geo.json"), "w")); print(geo)
        if "--geo" in sys.argv: sys.exit(0)
    bl.render(os.path.join(OUT, "bg.png" if kind is None else f"bg_{kind}.png"), 1080, 1620, samples=S)

# 卵ひとつ（横向き、透明背景）
if "--one" not in sys.argv or "--egg" in sys.argv:
    sc = bl.reset(); sc.view_settings.exposure = 0.0
    lights()
    egg((0, 0, 0), rot=(0, 90, 0))
    cam = bl.camera((0, -30, 0), rot_deg=(90, 0, 0), ortho=8.4)
    bl.render(os.path.join(OUT, "egg.png"), 720, 560, samples=S, transparent=True)
print("done")
