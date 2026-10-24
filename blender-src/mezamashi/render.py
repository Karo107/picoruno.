"""目覚ましぜんぶ止め：素材レンダリング。

朝の寝室をななめ上から。1 = 1cm。床 z=0、奥の壁 y=200、左右の壁 x=±190。
画面（ゲームの単位）は横 1600 × 縦 1080。スマホではまんなかの 540 幅（x 530..1070）を見る。
out/room.png     部屋（2400x1620 = 1.5 倍）
out/bell.png     ベルの目覚まし 5 色 × 3 コマ（まんなか・左・右のハンマー）
out/digi.png     デジタル時計 2 台 × 2 コマ（消灯・点灯）
out/phone.png    スマホ 2 コマ（消灯・アラーム画面）
out/runner.png   にげる目覚まし 8 方向
out/geo.json     置き場所（画面座標と 1cm の大きさ）、床の射影
"""
import json, math, os, sys, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "common"))
import bpy, bmesh, mathutils
import numpy as np
from bpy_extras.object_utils import world_to_camera_view
import bl

OUT = os.path.join(os.path.dirname(__file__), "out")
os.makedirs(OUT, exist_ok=True)
FAST = "--fast" in sys.argv
S = 24 if FAST else 160
PART = next((a for a in sys.argv[1:] if not a.startswith("-")), "all")
rr = random.Random(7)
WW, WH = 1600, 1080          # ゲーム座標での部屋の大きさ
OX = 530                     # スマホで見るまんなかの左端
CAM = dict(loc=(22, -255, 430), rot=(34, 0, 0), lens=18.5)

# 目覚ましの置き場所（x, y, z = 置く面の高さ）
SPOTS = {
    "pillow":  (-104, 172, 62),
    "night":   (-23, 176, 56),
    "sill":    (98, 194, 99),
    "shelf":   (-100, 191, 153),
    "desk":    (52, 158, 76),
    "phone":   (118, 150, 76),
    "dresser": (118, -12, 86),
    "basket":  (100, -128, 42),
    "floor":   (-74, -96, 0),
    "rug":     (18, -4, 1.2),
}


def look(sc, exp=0.0):
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Base Contrast'; sc.view_settings.exposure = exp


def M(name, col, rough=0.5, **kw):
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    return bl.mat(name, col, rough, **kw)


def box(size, loc, m, bev=0.6, rot=(0, 0, 0)):
    b = bl.cube(size, loc, rot)
    if bev:
        bl.bevel(b, bev, 3)
    bl.assign(b, m)
    return b


def fabric(name, col, scale=40, bump=0.25):
    m = bl.mat(name, col, 0.85, Sheen_Weight=0.8)
    bl.noise_bump(m, scale=scale, strength=bump, detail=4)
    return m


def soft(o, lv=2, disp=0.0, sc=0.05):
    bl.subsurf(o, lv); bl.smooth(o)
    if disp:
        t = bpy.data.textures.new("d" + o.name, 'CLOUDS'); t.noise_scale = 1 / sc
        d = o.modifiers.new("disp", 'DISPLACE'); d.texture = t; d.strength = disp; d.texture_coords = 'GLOBAL'
    return o


# ---------------- 部屋 ----------------
def floor():
    w = 14.0
    for i in range(-11, 11):
        x = i * w + w / 2
        y = -600 - rr.uniform(0, 60)
        while y < 200:
            ln = rr.uniform(70, 140)
            b = bl.cube((w - 0.3, ln - 0.3, 2), (x, y + ln / 2, -1)); bl.bevel(b, 0.15, 2)
            t = rr.uniform(0, 1)
            m = bl.wood(f"fl{i}_{int(y)}", light=(0.7 - t * 0.1, 0.5 - t * 0.08, 0.32 - t * 0.06), dark=(0.5 - t * 0.08, 0.33 - t * 0.06, 0.2 - t * 0.04), scale=0.08, stretch=18, rough=0.32, bump=0.06)
            N, L, bsdf = bl.nodes(m)
            mp = next(n for n in N if n.type == 'MAPPING'); mp.inputs["Rotation"].default_value = (0, 0, math.radians(90)); mp.inputs["Location"].default_value = (rr.uniform(0, 50), rr.uniform(0, 50), 0)
            bl.assign(b, m)
            y += ln


def walls():
    wall = bl.mat("wall", (0.93, 0.89, 0.82), 0.9); bl.noise_bump(wall, scale=60, strength=0.08)
    side = bl.mat("wallside", (0.86, 0.9, 0.88), 0.9); bl.noise_bump(side, scale=60, strength=0.08)
    H = 460
    # 奥の壁（まど穴あき：x -30..130, z 100..210）
    wx0, wx1, wz0, wz1 = 20, 140, 100, 210
    for (x0, x1, z0, z1) in [(-170, wx0, 0, H), (wx1, 170, 0, H), (wx0, wx1, 0, wz0), (wx0, wx1, wz1, H)]:
        box((x1 - x0, 10, z1 - z0), ((x0 + x1) / 2, 205, (z0 + z1) / 2), wall, 0)
    for sx in (-1, 1):
        box((10, 900, H), (sx * 155, -250, H / 2), side, 0)
    # はば木
    bb = M("baseboard", (0.96, 0.95, 0.92), 0.4)
    box((300, 1.5, 8), (0, 199.2, 4), bb, 0.3)
    for sx in (-1, 1):
        box((1.5, 900, 8), (sx * 149.2, -250, 4), bb, 0.3)
    # まど：わく・十字・ガラス・外の空
    fr = M("frame", (0.97, 0.97, 0.95), 0.35)
    for (sx, sy, x, z) in [(126, 6, 80, wz0 + 3), (126, 6, 80, wz1 - 3), (6, 104, wx0 + 3, 155), (6, 104, wx1 - 3, 155), (4, 104, 80, 155)]:
        box((sx, 8, sy), (x, 203, z), fr, 0)
    sill = box((136, 14, 4), (80, 194, wz0 - 2), fr, 0.5)
    sky = bl.plane((900, 500), (80, 270, 160), rot=(90, 0, 0))
    m = bpy.data.materials.new("sky"); m.use_nodes = True; N, L = m.node_tree.nodes, m.node_tree.links
    N.remove(N["Principled BSDF"]); e = N.new("ShaderNodeEmission"); e.inputs[1].default_value = 1.3
    tc = N.new("ShaderNodeTexCoord"); sep = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Generated"], sep.inputs[0])
    cr = N.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].color = (1.0, 0.8, 0.58, 1); cr.color_ramp.elements[1].color = (0.36, 0.62, 0.95, 1); cr.color_ramp.elements[0].position = 0.35; cr.color_ramp.elements[1].position = 0.75
    L.new(sep.outputs[1], cr.inputs[0]); L.new(cr.outputs[0], e.inputs[0]); L.new(e.outputs[0], N["Material Output"].inputs[0]); bl.assign(sky, m)
    sky.visible_shadow = False
    # カーテン（波うつ布を左右に）
    cur = fabric("curtain", (0.95, 0.82, 0.62), 30, 0.15)
    cur.node_tree.nodes["Principled BSDF"].inputs["Transmission Weight"].default_value = 0.0
    for sx in (-1, 1):
        x0 = 80 + sx * 70
        bpy.ops.mesh.primitive_grid_add(x_subdivisions=60, y_subdivisions=4, size=1, location=(x0, 196, 150))
        c = bl.active(); c.scale = (26, 140, 1); c.rotation_euler = (math.radians(90), 0, 0)
        bpy.ops.object.transform_apply(scale=True, rotation=True)
        for v in c.data.vertices:
            v.co.y += 3 * math.sin((v.co.x) * 0.55) - 2
        sol = c.modifiers.new("s", 'SOLIDIFY'); sol.thickness = 0.6
        bl.smooth(c); bl.assign(c, cur)
    rod = bl.cyl(1.2, 200, (80, 194, 224), verts=24, rotation=(0, math.radians(90), 0)); bl.assign(rod, M("metal", (0.7, 0.66, 0.6), 0.3, metal=1.0))
    # 壁の絵（抽象の色面）
    for (x, z, w, h, c) in [(-36, 170, 30, 38, (0.45, 0.62, 0.66)), (-6, 160, 20, 26, (0.9, 0.62, 0.45))]:
        box((w + 4, 2.5, h + 4), (x, 198.5, z), M("pframe" + str(x), (0.3, 0.22, 0.16), 0.4), 0.3)
        box((w, 1, h), (x, 197, z), bl.mat("pic" + str(x), c, 0.9), 0)
    # ドア（左の壁、手前）
    door = M("door", (0.86, 0.78, 0.66), 0.5)
    box((3, 84, 200), (-148, -260, 100), door, 0.4)
    knob = bl.sphere(3, (-145, -230, 98)); bl.assign(knob, M("metal", (0.7, 0.66, 0.6), 0.3, metal=1.0))


def bed():
    wd = bl.wood("bedwood", light=(0.66, 0.46, 0.3), dark=(0.46, 0.3, 0.18), scale=0.12, rough=0.35, bump=0.06)
    X = -104
    box((92, 186, 24), (X, 108, 20), wd, 1.0)
    box((96, 6, 86), (X, 199, 43), wd, 1.5)
    mt = box((86, 178, 18), (X, 110, 40), M("mattress", (0.94, 0.93, 0.9), 0.8), 4)
    # かけぶとん（すこしめくれている）
    dv = bl.cube((94, 124, 9), (X, 70, 52)); bl.bevel(dv, 4, 4)
    sd = dv.modifiers.new("sd", 'SUBSURF'); sd.subdivision_type = 'SIMPLE'; sd.levels = sd.render_levels = 3
    t = bpy.data.textures.new("dvt", 'CLOUDS'); t.noise_scale = 18
    d = dv.modifiers.new("disp", 'DISPLACE'); d.texture = t; d.strength = 2.4; d.texture_coords = 'GLOBAL'; bl.smooth(dv)
    bl.assign(dv, fabric("duvet", (0.42, 0.58, 0.76), 18, 0.35))
    fold = bl.cube((94, 18, 10), (X, 136, 53)); bl.bevel(fold, 4, 4); bl.smooth(fold); bl.assign(fold, fabric("duvetin", (0.93, 0.9, 0.84), 22, 0.3))
    pw = bl.cube((60, 32, 8), (X, 172, 54)); bl.bevel(pw, 4, 5); bl.smooth(pw); bl.assign(pw, fabric("pillow", (0.96, 0.94, 0.9), 26, 0.3))
    # 床のスリッパ
    for (x, r) in [(-44, -14), (-31, -4)]:
        s = bl.cube((9, 24, 3), (x, 10, 1.5), rot=(0, 0, r)); soft(s, 2); bl.assign(s, fabric("slip", (0.85, 0.5, 0.45), 30, 0.3))


def nightstand():
    wd = bl.wood("nswood", light=(0.74, 0.55, 0.36), dark=(0.54, 0.37, 0.24), scale=0.12, rough=0.35, bump=0.05)
    box((34, 34, 54), (-23, 180, 27), wd, 1.0)
    box((28, 1, 16), (-23, 162.6, 40), M("nsdraw", (0.8, 0.62, 0.42), 0.4), 0.4)
    k = bl.sphere(1.6, (-23, 161.5, 40)); bl.assign(k, M("metal", (0.7, 0.66, 0.6), 0.3, metal=1.0))


def desk():
    wd = bl.wood("deskwood", light=(0.8, 0.62, 0.42), dark=(0.62, 0.45, 0.3), scale=0.1, rough=0.3, bump=0.05)
    box((112, 54, 4), (90, 172, 74), wd, 0.6)
    for (x, y) in [(37, 148), (143, 148), (37, 196), (143, 196)]:
        box((4, 4, 72), (x, y, 36), M("deskleg", (0.25, 0.24, 0.23), 0.4), 0.3)
    bs = bl.cyl(6, 2, (138, 190, 77), verts=48); bl.assign(bs, M("lamp", (0.3, 0.42, 0.38), 0.4))
    arm = bl.cyl(0.8, 34, (138, 190, 93), verts=16); bl.assign(arm, M("lamp", (0, 0, 0)))
    bpy.ops.mesh.primitive_cone_add(radius1=9, radius2=3.5, depth=11, location=(132, 184, 108), vertices=48)
    sh = bl.active(); sh.rotation_euler = (math.radians(-25), math.radians(-15), 0); bl.smooth(sh)
    sol = sh.modifiers.new("s", 'SOLIDIFY'); sol.thickness = 0.5; bl.assign(sh, M("lamp", (0, 0, 0)))
    cols = [(0.62, 0.2, 0.16), (0.2, 0.32, 0.5), (0.9, 0.8, 0.55)]
    z = 76
    for i, c in enumerate(cols):
        h = 3 + i * 0.5
        box((20, 26, h), (84, 184 + i, z + h / 2), M(f"dbook{i}", c, 0.6), 0.5, rot=(0, 0, rr.uniform(-6, 6))); z += h
    mug = bl.cyl(4.0, 9, (24 + 76, 160, 80.5), verts=48); bl.bevel(mug, 0.4, 2); bl.assign(mug, M("mug", (0.92, 0.86, 0.72), 0.25))
    bpy.ops.mesh.primitive_torus_add(major_radius=2.8, minor_radius=0.8, location=(104.5, 160, 81), rotation=(math.radians(90), 0, 0)); bl.assign(bl.active(), M("mug", (0, 0, 0)))
    ch = M("chair", (0.4, 0.58, 0.55), 0.6)
    box((40, 38, 4), (88, 124, 46), ch, 1.2)
    box((40, 4, 32), (88, 104, 68), ch, 1.2)
    for (x, y) in [(71, 106), (105, 106), (71, 141), (105, 141)]:
        box((3, 3, 44), (x, y, 22), M("deskleg", (0, 0, 0)), 0.3)


def shelf():
    wd = bl.wood("shelfwood", light=(0.8, 0.62, 0.42), dark=(0.62, 0.45, 0.3), scale=0.1, rough=0.3, bump=0.05)
    box((76, 18, 3), (-104, 191, 151.5), wd, 0.5)
    cols = [(0.5, 0.2, 0.2), (0.24, 0.38, 0.5), (0.85, 0.72, 0.4), (0.3, 0.45, 0.35), (0.7, 0.5, 0.6)]
    x = -90
    for i, c in enumerate(cols):
        w = rr.uniform(3, 4.5); h = rr.uniform(18, 24)
        box((w, 15, h), (x, 192, 153 + h / 2), M(f"sbook{i}", c, 0.6), 0.3); x += w + 0.4
    pot = bl.cyl(4.5, 8, (-134, 192, 157), verts=40); bl.assign(pot, M("pot", (0.85, 0.5, 0.36), 0.6))
    for k in range(9):
        a = k * 0.7
        l = bl.sphere(4, (-134 + 4 * math.cos(a), 192 + 3 * math.sin(a), 164 + rr.uniform(0, 5)))
        l.scale = (0.6, 1.6, 0.35); l.rotation_euler = (rr.uniform(-0.6, 0.6), rr.uniform(-0.6, 0.6), a); bl.assign(l, M("leaf", (0.24, 0.48, 0.26), 0.5))


def dresser():
    wd = bl.wood("drwood", light=(0.9, 0.86, 0.78), dark=(0.8, 0.74, 0.64), scale=0.1, rough=0.4, bump=0.03)
    box((40, 90, 84), (130, 8, 42), wd, 1.0)
    for i in range(3):
        z = 16 + i * 26
        box((1, 82, 22), (109.6, 8, z), M("drfront", (0.93, 0.9, 0.84), 0.45), 0.5)
        k = bl.cyl(1.4, 2, (108.5, 8, z), verts=24, rotation=(0, math.radians(90), 0)); bl.assign(k, M("metal", (0, 0, 0)))
    v = bl.cyl(3.6, 14, (136, 40, 91), verts=40); bl.assign(v, bl.mat("vase", (0.5, 0.7, 0.78), 0.1))
    for k in range(3):
        st = bl.cyl(0.3, 16, (136 + k - 1, 40, 104), verts=8, rotation=(rr.uniform(-0.2, 0.2), rr.uniform(-0.2, 0.2), 0)); bl.assign(st, M("leaf", (0, 0, 0)))
        f = bl.sphere(2.2, (136 + (k - 1) * 2.5, 40 + rr.uniform(-1, 1), 113 + rr.uniform(-1, 2))); bl.assign(f, M("flower", (0.98, 0.78, 0.4), 0.6))


def rug():
    r = bl.cube((130, 110, 1.2), (14, -6, 0.6)); bl.bevel(r, 0.4, 2)
    m = bl.mat("rug", (0.9, 0.86, 0.78), 0.95, Sheen_Weight=1.0)
    N, L, b = bl.nodes(m); tc = N.new("ShaderNodeTexCoord")
    wv = N.new("ShaderNodeTexWave"); wv.inputs["Scale"].default_value = 0.035; wv.bands_direction = 'Y'; wv.wave_profile = 'SAW'
    L.new(tc.outputs["Object"], wv.inputs["Vector"])
    cr = N.new("ShaderNodeValToRGB"); cr.color_ramp.interpolation = 'CONSTANT'; cr.color_ramp.elements[0].color = (0.86, 0.8, 0.7, 1); cr.color_ramp.elements[1].position = 0.8; cr.color_ramp.elements[1].color = (0.36, 0.5, 0.56, 1)
    L.new(wv.outputs["Fac"], cr.inputs["Fac"]); L.new(cr.outputs["Color"], b.inputs["Base Color"])
    bl.noise_bump(m, scale=4, strength=0.5)
    bl.assign(r, m)


def basket():
    X, Y = 106, -128
    b = bl.cyl(24, 40, (X, Y, 20), verts=64)
    bm = bmesh.new(); bm.from_mesh(b.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.normal.z > 0.9], context='FACES'); bm.to_mesh(b.data); bm.free()
    sol = b.modifiers.new("s", 'SOLIDIFY'); sol.thickness = 1.4
    m = bl.mat("basket", (0.78, 0.62, 0.42), 0.7)
    N, L, bs = bl.nodes(m); tc = N.new("ShaderNodeTexCoord")
    ch = N.new("ShaderNodeTexChecker"); ch.inputs["Scale"].default_value = 1.4
    L.new(tc.outputs["Object"], ch.inputs["Vector"]); ch.inputs[1].default_value = (0.78, 0.6, 0.4, 1); ch.inputs[2].default_value = (0.58, 0.42, 0.27, 1)
    L.new(ch.outputs["Color"], bs.inputs["Base Color"])
    bp = N.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.5; L.new(ch.outputs["Fac"], bp.inputs["Height"]); L.new(bp.outputs["Normal"], bs.inputs["Normal"])
    bl.assign(b, m)
    for (x, y, c) in [(-8, 6, (0.95, 0.95, 0.94)), (8, -4, (0.5, 0.62, 0.8)), (0, -10, (0.95, 0.7, 0.55)), (-6, -8, (0.9, 0.86, 0.6))]:
        cl = bl.cube((20, 18, 9), (X + x, Y + y, 36)); soft(cl, 2, 2.0, 0.08); bl.assign(cl, fabric("cloth" + str(x), c, 30, 0.3))


def plant():
    X, Y = -122, -150
    pot = bl.cyl(14, 30, (X, Y, 15), verts=64); bl.bevel(pot, 0.6, 2); bl.assign(pot, M("bigpot", (0.9, 0.88, 0.84), 0.5))
    for k in range(18):
        a = k * 2.4; r = rr.uniform(4, 14)
        l = bl.sphere(9, (X + r * math.cos(a), Y + r * math.sin(a), 46 + rr.uniform(0, 36)))
        l.scale = (0.45, 1.5, 0.12); l.rotation_euler = (rr.uniform(-0.8, 0.8), rr.uniform(-0.5, 0.5), a); bl.assign(l, M("bigleaf", (0.2, 0.42, 0.24), 0.45))


def room_scene():
    sc = bl.reset(); look(sc, 0.0)
    bl.world((0.85, 0.88, 0.95), 0.25)
    floor(); walls(); bed(); nightstand(); desk(); shelf(); dresser(); rug(); basket(); plant()
    # 朝日：まどから差しこむ太陽（奥から手前へ）
    bl.light('SUN', (0, 400, 400), 7.0, rot_deg=(-58, 0, -14), angle=2.0, color=(1.0, 0.84, 0.62))
    # 部屋のやわらかい明かり
    bpy.ops.object.light_add(type='AREA', location=(0, -200, 420)); a = bl.active(); a.data.energy = 5.0e4; a.data.size = 260; a.data.color = (0.92, 0.94, 1.0)
    a.rotation_euler = (math.radians(-20), 0, 0)
    bpy.ops.object.light_add(type='AREA', location=(80, 180, 160)); a = bl.active(); a.data.energy = 1.2e4; a.data.size = 110; a.data.color = (1.0, 0.88, 0.7); a.rotation_euler = (math.radians(70), 0, 0)
    a.visible_camera = False
    cam = bl.camera(CAM["loc"], CAM["rot"], lens=CAM["lens"]); cam.data.sensor_fit = 'VERTICAL'; cam.data.sensor_height = 24; cam.data.clip_end = 5000
    sc.render.resolution_x, sc.render.resolution_y = int(WW * 1.5), int(WH * 1.5)
    return sc, cam


def proj(sc, cam, p):
    v = world_to_camera_view(sc, cam, mathutils.Vector(p))
    return (v.x * WW - OX, (1 - v.y) * WH)


GEO = {}
gp = os.path.join(OUT, "geo.json")
if os.path.exists(gp):
    GEO = json.load(open(gp))

if PART in ("all", "room"):
    sc, cam = room_scene()
    bpy.context.view_layer.update()
    spots = {}
    for k, (x, y, z) in SPOTS.items():
        c = proj(sc, cam, (x, y, z)); a = proj(sc, cam, (x - 5, y, z)); b = proj(sc, cam, (x + 5, y, z))
        spots[k] = {"x": round(c[0], 1), "y": round(c[1], 1), "s": round(math.hypot(b[0] - a[0], b[1] - a[1]) / 10, 3)}
    # 床 z=0 → 画面 の射影（ホモグラフィ）
    src = [(-150, -250), (150, -250), (150, 150), (-150, 150), (0, 0), (-80, 60)]
    A = []; B = []
    for (x, y) in src:
        u, v = proj(sc, cam, (x, y, 0))
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); B.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); B.append(v)
    h = np.linalg.lstsq(np.array(A), np.array(B), rcond=None)[0]
    GEO["room"] = {"w": WW, "h": WH, "ox": OX, "spots": spots, "floorH": [round(float(t), 8) for t in h]}
    # にげる目覚ましが走れる床（ラグのまわり）
    GEO["room"]["run"] = {"x0": -60, "x1": 100, "y0": -90, "y1": 70}
    bl.render(os.path.join(OUT, "room.png"), int(WW * 1.5), int(WH * 1.5), samples=S)


# ---------------- 目覚まし（透明・影つき。ななめ上から正投影） ----------------
def sprite_scene(ortho):
    sc = bl.reset(); look(sc, 0.1)
    bl.world((0.85, 0.88, 0.95), 0.35)
    bpy.ops.object.light_add(type='AREA', location=(-30, -40, 80)); a = bl.active(); a.data.energy = 2.2e3; a.data.size = 60
    a.rotation_euler = (math.radians(35), math.radians(-25), 0)
    bpy.ops.object.light_add(type='AREA', location=(10, 30, 90)); b = bl.active(); b.data.energy = 1.6e3; b.data.size = 80; b.data.color = (1.0, 0.9, 0.78)
    sh = bl.shadow_catcher(200)
    pitch = CAM["rot"][0]
    d = 200
    cam = bl.camera((0, -d * math.sin(math.radians(pitch)), d * math.cos(math.radians(pitch)) + 8), (pitch, 0, 0), ortho=ortho)
    cam.data.clip_end = 1000
    return sc, cam


def bell_clock(col):
    body = M("bbody" + str(col), col, 0.25, Coat_Weight=1.0)
    metal = M("chrome", (0.9, 0.9, 0.92), 0.12, metal=1.0)
    face = M("face", (0.98, 0.97, 0.93), 0.4)
    blk = M("ink", (0.12, 0.1, 0.1), 0.4)
    g = []
    c = bl.cyl(6, 4.2, (0, 0, 8.5), verts=64, rotation=(math.radians(90), 0, 0)); bl.bevel(c, 0.8, 4); bl.assign(c, body); g.append(c)
    f = bl.cyl(5.1, 0.4, (0, -2.1, 8.5), verts=64, rotation=(math.radians(90), 0, 0)); bl.assign(f, face); g.append(f)
    for k in range(12):
        a = k * math.pi / 6
        t = box((0.35, 0.2, 0.9 if k % 3 else 1.4), (4.3 * math.sin(a), -2.35, 8.5 + 4.3 * math.cos(a)), blk, 0, rot=(0, math.degrees(a), 0)); g.append(t)
    for (ln, ang, w) in [(2.6, -60, 0.45), (3.8, 0, 0.3)]:
        a = math.radians(ang)
        t = box((w, 0.2, ln), (ln / 2 * math.sin(a), -2.45, 8.5 + ln / 2 * math.cos(a)), blk, 0, rot=(0, ang, 0)); g.append(t)
    cn = bl.cyl(0.45, 0.4, (0, -2.6, 8.5), verts=16, rotation=(math.radians(90), 0, 0)); bl.assign(cn, body); g.append(cn)
    # ベル 2 つ・足 2 本・取っ手
    for sx in (-1, 1):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=2.5, location=(sx * 4.0, 0, 14.2), segments=48, ring_count=24)
        b = bl.smooth(bl.active()); bm = bmesh.new(); bm.from_mesh(b.data)
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -0.6], context='VERTS'); bm.to_mesh(b.data); bm.free()
        b.rotation_euler = (0, math.radians(sx * 38), 0); s = b.modifiers.new("s", 'SOLIDIFY'); s.thickness = 0.3; bl.assign(b, metal); g.append(b)
        lg = bl.cyl(0.5, 4.5, (sx * 3.6, 0, 2.2), verts=16, rotation=(0, math.radians(sx * 22), 0)); bl.assign(lg, metal); g.append(lg)
        ft = bl.sphere(0.9, (sx * 4.4, 0, 0.6)); bl.assign(ft, metal); g.append(ft)
    bpy.ops.mesh.primitive_torus_add(major_radius=2.6, minor_radius=0.35, location=(0, 1.5, 15.2), rotation=(math.radians(90), 0, 0))
    hd = bl.active(); bl.assign(hd, metal); g.append(hd)
    # ハンマー（ベルの間でゆれる）
    hm = bl.cyl(0.25, 4.0, (0, 0, 15.2), verts=12); bl.assign(hm, metal)
    hb = bl.sphere(0.6, (0, 0, 17.2)); bl.assign(hb, metal)
    pv = bpy.data.objects.new("pv", None); bl.link(pv); pv.location = (0, 0, 13.2)
    bpy.context.view_layer.update()
    for o in (hm, hb):
        o.parent = pv; o.matrix_parent_inverse = pv.matrix_world.inverted()
    return pv


def digi_clock(col, scr):
    body = M("dbody" + str(col), col, 0.3, Coat_Weight=0.6)
    d = box((16, 7, 9), (0, 0, 4.5), body, 1.6, rot=(-12, 0, 0))
    lcd = box((12.4, 0.6, 5.4), (0, -3.7, 4.9), M("lcdbg", (0.06, 0.08, 0.07), 0.15), 0.3, rot=(-12, 0, 0))
    if scr:
        bpy.ops.object.text_add(location=(0, -4.25, 4.9), rotation=(math.radians(90 - 12), 0, 0))
        t = bl.active(); t.data.body = "7:00"; t.data.size = 4.6; t.data.align_x = 'CENTER'; t.data.align_y = 'CENTER'; t.data.extrude = 0.02
        t.data.space_character = 1.1
        bl.assign(t, bl.emission("lcd" + str(scr), (1.0, 0.36, 0.22) if scr == 2 else (0.5, 0.2, 0.15), 6 if scr == 2 else 0.6))
    btn = box((5, 3, 1.2), (0, 0.6, 9.4), M("dbtn", (0.95, 0.95, 0.95), 0.4), 0.4, rot=(-12, 0, 0))


def phone(on):
    box((7.6, 15.6, 0.8), (0, 0, 0.4), M("phbody", (0.18, 0.18, 0.2), 0.3), 0.9)
    if on:
        s = bl.plane((7.0, 15.0), (0, 0, 0.82))
        m = bpy.data.materials.new("scr"); m.use_nodes = True; N, L = m.node_tree.nodes, m.node_tree.links
        N.remove(N["Principled BSDF"]); e = N.new("ShaderNodeEmission"); e.inputs[1].default_value = 0.9
        tc = N.new("ShaderNodeTexCoord"); sep = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["UV"], sep.inputs[0])
        cr = N.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].color = (0.98, 0.6, 0.45, 1); cr.color_ramp.elements[1].color = (0.45, 0.55, 0.95, 1)
        L.new(sep.outputs[1], cr.inputs[0]); L.new(cr.outputs[0], e.inputs[0]); L.new(e.outputs[0], N["Material Output"].inputs[0]); bl.assign(s, m)
        bpy.ops.object.text_add(location=(0, 3.6, 0.86)); t = bl.active(); t.data.body = "7:00"; t.data.size = 2.6; t.data.align_x = 'CENTER'; t.data.align_y = 'CENTER'
        bl.assign(t, bl.emission("phtxt", (1, 1, 1), 3))
        sl = box((5.6, 1.6, 0.1), (0, -4.6, 0.86), bl.emission("slider", (1, 1, 1), 1.2), 0.0)
        kn = bl.cyl(0.7, 0.12, (-2.0, -4.6, 0.92), verts=24); bl.assign(kn, bl.emission("knob", (0.95, 0.45, 0.35), 2))
    else:
        s = bl.plane((7.0, 15.0), (0, 0, 0.82)); bl.assign(s, M("scroff", (0.03, 0.03, 0.04), 0.08))


def runner():
    """車輪つきでにげる目覚まし（ドラム形の体を、左右の大きな車輪ではさむ）。"""
    body = M("rbody", (0.95, 0.66, 0.08), 0.25, Coat_Weight=1.0)
    c = bl.cyl(5.0, 9.0, (0, 0, 6.0), verts=64, rotation=(0, math.radians(90), 0)); bl.bevel(c, 1.2, 4); bl.assign(c, body)
    # 文字盤：原点で XZ 面に作ってから、前のななめ上（35°上向き）へ
    parts = []
    face = bl.cyl(3.6, 0.6, (0, 0, 0), verts=64, rotation=(math.radians(90), 0, 0)); bl.assign(face, M("face", (0.98, 0.97, 0.93), 0.4)); parts.append(face)
    bpy.ops.mesh.primitive_torus_add(major_radius=3.6, minor_radius=0.35, location=(0, 0, 0), rotation=(math.radians(90), 0, 0)); bl.assign(bl.active(), M("chrome", (0.9, 0.9, 0.92), 0.12, metal=1.0)); parts.append(bl.active())
    blk = M("ink", (0.12, 0.1, 0.1), 0.4)
    for (ln, ang, w) in [(1.9, -60, 0.4), (2.8, 0, 0.28)]:
        r = math.radians(ang)
        parts.append(box((w, 0.2, ln), (ln / 2 * math.sin(r), -0.4, ln / 2 * math.cos(r)), blk, 0, rot=(0, ang, 0)))
    for k in range(12):
        r = k * math.pi / 6
        parts.append(box((0.3, 0.2, 0.7), (2.9 * math.sin(r), -0.35, 2.9 * math.cos(r)), blk, 0, rot=(0, math.degrees(r), 0)))
    fe = bpy.data.objects.new("fe", None); bl.link(fe); bpy.context.view_layer.update()
    for o in parts:
        o.parent = fe; o.matrix_parent_inverse = fe.matrix_world.inverted()
    fe.location = (0, -4.1, 8.9); fe.rotation_euler = (math.radians(-35), 0, 0)
    tire = M("tire", (0.16, 0.16, 0.17), 0.7)
    for sx in (-1, 1):
        w = bl.cyl(6.2, 2.4, (sx * 5.9, 0, 6.2), verts=48, rotation=(0, math.radians(90), 0)); bl.bevel(w, 0.7, 3); bl.assign(w, tire)
        hb = bl.cyl(2.6, 2.6, (sx * 6.0, 0, 6.2), verts=32, rotation=(0, math.radians(90), 0)); bl.assign(hb, M("chrome", (0, 0, 0)))
    kb = bl.cyl(1.4, 1.2, (0, 2.0, 11.0), verts=24); bl.bevel(kb, 0.3, 2); bl.assign(kb, M("rbtn", (0.9, 0.25, 0.2), 0.3))


def cell_render(name, frames, cw, ch, ortho, build):
    """frames: [(label, setup)] を 1 枚ずつ描いて横にならべる。"""
    from PIL import Image
    ims = []
    for i, fr in enumerate(frames):
        sc, cam = sprite_scene(ortho)
        build(fr)
        p = os.path.join(OUT, f"_{name}{i}.png")
        bl.render(p, cw, ch, samples=S, transparent=True)
        ims.append(Image.open(p))
    w, h = ims[0].size
    sheet = Image.new("RGBA", (w * len(ims), h))
    for i, im in enumerate(ims):
        px = np.array(im.convert("RGBA")); px[..., 3][px[..., 3] < 10] = 0   # 影受けのうすいくもりを消す
        sheet.paste(Image.fromarray(px), (i * w, 0))
    sheet.save(os.path.join(OUT, name + ".png"))
    return {"cw": w, "ch": h, "n": len(ims), "pxcm": round(w / ortho, 4)}


def tilt_all(deg=15):
    """カメラ側へすこし倒して、文字盤を見やすくする（足もとを支点に）。"""
    piv = bpy.data.objects.new("tilt", None); bl.link(piv); bpy.context.view_layer.update()
    for o in list(bpy.context.scene.objects):
        if o.parent is None and o is not piv and o.type in ('MESH', 'EMPTY', 'FONT') and not getattr(o, "is_shadow_catcher", False):
            mw = o.matrix_world.copy(); o.parent = piv; o.matrix_parent_inverse = piv.matrix_world.inverted()
    piv.rotation_euler.x = math.radians(-deg)


BELL_COLS = [(0.75, 0.07, 0.05), (0.16, 0.52, 0.42), (0.95, 0.6, 0.06), (0.09, 0.17, 0.45), (0.9, 0.38, 0.5)]
SPR = 260   # 1 コマの大きさ（最終）
if PART in ("all", "bell"):
    fr = [(c, a) for c in range(5) for a in (0, -24, 24)]

    def b(f):
        pv = bell_clock(BELL_COLS[f[0]]); pv.rotation_euler = (0, math.radians(f[1]), 0)
        tilt_all()
    GEO["bell"] = cell_render("bell", fr, SPR, SPR, 30, b)

if PART in ("all", "digi"):
    fr = [(c, s) for c in ((0.95, 0.95, 0.93), (0.22, 0.24, 0.27)) for s in (1, 2)]
    GEO["digi"] = cell_render("digi", fr, SPR, SPR, 30, lambda f: digi_clock(*f))

if PART in ("all", "phone"):
    GEO["phone"] = cell_render("phone", [0, 1], SPR, SPR, 30, phone)

if PART in ("all", "runner"):
    def rn(a):
        runner(); bpy.ops.object.select_all(action='SELECT')
        for o in bpy.context.selected_objects:
            if o.type == 'MESH' and not o.is_shadow_catcher:
                o.rotation_euler.z += 0
        piv = bpy.data.objects.new("rp", None); bl.link(piv); bpy.context.view_layer.update()
        for o in list(bpy.context.scene.objects):
            if o.type in ('MESH', 'EMPTY') and o is not piv and o.parent is None and not getattr(o, "is_shadow_catcher", False):
                o.parent = piv; o.matrix_parent_inverse = piv.matrix_world.inverted()
        piv.rotation_euler.z = math.radians(a)
    GEO["runner"] = cell_render("runner", [k * 45 for k in range(8)], SPR, SPR, 30, rn)

json.dump(GEO, open(gp, "w"), indent=1)
print("done")
