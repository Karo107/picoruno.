"""くつしたペア：素材レンダリング。

日曜の朝、日のあたるフローリングに、とりこんだ洗濯物。真上から。
out/bg.png       床（くつしたはゲームで置く）。左上に洗濯かご、下にたたんだ靴下を置く木のトレイ
out/sock_s.png   くつしたの陰影（白いニット）3種を横にならべた帯（短い・ふつう・長い）
out/sock_d.png   同じ形の「しるし」: R=つま先からの長さ方向 u、G=まわり方向 v、B=部位（0 本体 / 64 はき口 / 128 かかと / 192 つま先）
out/geo.json     1cm の大きさ、トレイの位置、くつしたの形の情報
720x1080 を 1.5 倍。1 = 1cm。
"""
import json, math, os, sys, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "common"))
import bpy, bmesh, mathutils
from bpy_extras.object_utils import world_to_camera_view
import bl

OUT = os.path.join(os.path.dirname(__file__), "out")
os.makedirs(OUT, exist_ok=True)
FAST = "--fast" in sys.argv
S = 24 if FAST else 128
rr = random.Random(21)
VH = 180                      # 画面のたて 180cm（よこ 120cm）
TRAY = (0, -66)               # 下のトレイ（中心）
BASKET = (-46, 70)            # 左上の洗濯かご

# くつしたの形：はき口〜かかとの長さ（leg）、かかと〜つま先（foot）
SHAPES = [("short", 6, 21), ("crew", 15, 21), ("long", 27, 21)]
HW, HT, R_BEND = 4.6, 1.3, 4.5
CELL = 46                     # 1つのくつしたの絵：46cm 四方
PX = 9                        # 絵の 1cm = 9px（ゲームでは 1cm = 6px で描く → 1.5 倍）


def sock_path(leg, foot):
    """はき口（上）→ かかと → つま先（右）への中心線。点・接線・長さ s。"""
    pts = []
    n1 = max(4, int(leg / 0.6))
    for i in range(n1):
        pts.append((0.0, R_BEND + leg - leg * i / n1))
    for i in range(14):
        a = math.pi / 2 * i / 14
        pts.append((R_BEND - R_BEND * math.cos(a), R_BEND - R_BEND * math.sin(a)))
    n2 = max(4, int(foot / 0.6))
    for i in range(n2 + 1):
        pts.append((R_BEND + foot * i / n2, 0.0))
    s = [0.0]
    for i in range(1, len(pts)):
        s.append(s[-1] + math.dist(pts[i], pts[i - 1]))
    return pts, s


def sock_mesh(name, leg, foot):
    pts, s = sock_path(leg, foot)
    L = s[-1]
    s_heel0 = leg - 2.5
    s_heel1 = leg + R_BEND * math.pi / 2 + 3.0
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    reg = bm.loops.layers.color.new("reg")
    NA = 40
    rings = []
    for i, p in enumerate(pts):
        a = pts[max(0, i - 1)]; b = pts[min(len(pts) - 1, i + 1)]
        tx, ty = b[0] - a[0], b[1] - a[1]; tl = math.hypot(tx, ty); tx, ty = tx / tl, ty / tl
        nx, ny = -ty, tx                       # 左（かかとの内がわ）
        # つま先は丸くとじる、はき口は少しひらく
        k = 1.0
        if s[i] > L - 5.5: k = math.sqrt(max(0.0, 1 - ((s[i] - (L - 5.5)) / 5.5) ** 2)) * 0.9 + 0.1 if s[i] < L else 0.1
        if s[i] < 2.5: k = 1.04
        ring = []
        for j in range(NA):
            th = j / NA * 2 * math.pi
            # ねかせた筒：上下につぶれて、ふちは少しまるい
            c, sn = math.cos(th), math.sin(th)
            # かかとは外がわに少しふくらむ
            hb = 1 + 0.22 * max(0.0, -c) * math.exp(-((s[i] - (leg + R_BEND * 0.8)) / 4.0) ** 2)
            x = p[0] + nx * c * HW * k * hb
            y = p[1] + ny * c * HW * k * hb
            z = HT * (0.25 + 0.75 * k) * sn * (1 - 0.25 * c * c) + HT
            ring.append(bm.verts.new((x, y, z)))
        rings.append(ring)
    bm.verts.ensure_lookup_table()
    for i in range(len(rings) - 1):
        for j in range(NA):
            j2 = (j + 1) % NA
            f = bm.faces.new((rings[i][j], rings[i + 1][j], rings[i + 1][j2], rings[i][j2]))
            sm = (s[i] + s[i + 1]) / 2
            thm = (j + 0.5) / NA * 2 * math.pi
            if sm < 3.2: code = 64
            elif sm > L - 5.0: code = 192
            elif s_heel0 < sm < s_heel1 and math.cos(thm) < 0.05: code = 128
            else: code = 0
            for lp, (ii, jj) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                lp[uvl].uv = (s[ii] / L, jj / NA)
                lp[reg] = (code / 255, 0, 0, 1)
    # はし：ふたをする
    for ring in (rings[0], rings[-1]):
        bm.faces.new(ring if ring is rings[-1] else list(reversed(ring)))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bl.link(o)
    bl.smooth(o)
    # ねかせた布のしわ
    d = o.modifiers.new("d", 'DISPLACE'); tx = bpy.data.textures.new(name + "w", 'CLOUDS'); tx.noise_scale = 3.5; d.texture = tx; d.strength = 0.5; d.direction = 'Z'
    return o, L, (s_heel0, s_heel1)


def knit_mat():
    """白いニット：ゲームで色と柄をかける（ここでは陰影だけ）"""
    m = bl.mat("knit", (0.78, 0.78, 0.78), 0.95, Sheen_Weight=0.6)
    N, L, b = bl.nodes(m)
    uv = N.new("ShaderNodeUVMap"); sep = N.new("ShaderNodeSeparateXYZ"); L.new(uv.outputs[0], sep.inputs[0])
    # 段（長さ方向）と目（まわり方向）
    def wave(inp, mul):
        m1 = N.new("ShaderNodeMath"); m1.operation = 'MULTIPLY'; m1.inputs[1].default_value = mul; L.new(inp, m1.inputs[0])
        sn = N.new("ShaderNodeMath"); sn.operation = 'SINE'; L.new(m1.outputs[0], sn.inputs[0])
        ab = N.new("ShaderNodeMath"); ab.operation = 'ABSOLUTE'; L.new(sn.outputs[0], ab.inputs[0])
        return ab.outputs[0]
    rows = wave(sep.outputs["X"], 2 * math.pi * 70)
    cols = wave(sep.outputs["Y"], math.pi * 34)
    mu = N.new("ShaderNodeMath"); mu.operation = 'MULTIPLY'; L.new(rows, mu.inputs[0]); L.new(cols, mu.inputs[1])
    # はき口はリブ（たてすじ）を強く
    ca = N.new("ShaderNodeVertexColor"); ca.layer_name = "reg"
    sp = N.new("ShaderNodeSeparateColor"); L.new(ca.outputs["Color"], sp.inputs[0])
    isc = N.new("ShaderNodeMath"); isc.operation = 'COMPARE'; isc.inputs[1].default_value = 64 / 255; isc.inputs[2].default_value = 0.02; L.new(sp.outputs[0], isc.inputs[0])
    mx = N.new("ShaderNodeMix"); mx.data_type = 'FLOAT'; L.new(isc.outputs[0], mx.inputs[0]); L.new(mu.outputs[0], mx.inputs[2]); L.new(cols, mx.inputs[3])
    bp = N.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.6; bp.inputs["Distance"].default_value = 0.12
    L.new(mx.outputs[0], bp.inputs["Height"]); L.new(bp.outputs["Normal"], b.inputs["Normal"])
    # けば立ち
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 3; nz.inputs["Detail"].default_value = 8
    cr = N.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].color = (0.62, 0.62, 0.62, 1); cr.color_ramp.elements[1].color = (0.74, 0.74, 0.74, 1)
    L.new(nz.outputs["Fac"], cr.inputs["Fac"]); L.new(cr.outputs["Color"], b.inputs["Base Color"])
    return m


def data_mat():
    """しるし：R=u, G=v, B=部位。そのままの値で出す。"""
    m = bpy.data.materials.new("data"); m.use_nodes = True
    N, L = m.node_tree.nodes, m.node_tree.links
    N.remove(N["Principled BSDF"])
    uv = N.new("ShaderNodeUVMap"); sep = N.new("ShaderNodeSeparateXYZ"); L.new(uv.outputs[0], sep.inputs[0])
    ca = N.new("ShaderNodeVertexColor"); ca.layer_name = "reg"
    spc = N.new("ShaderNodeSeparateColor"); L.new(ca.outputs["Color"], spc.inputs[0])
    cc = N.new("ShaderNodeCombineColor"); L.new(sep.outputs["X"], cc.inputs[0]); L.new(sep.outputs["Y"], cc.inputs[1]); L.new(spc.outputs[0], cc.inputs[2])
    e = N.new("ShaderNodeEmission"); e.inputs[1].default_value = 1.0; L.new(cc.outputs[0], e.inputs[0])
    L.new(e.outputs[0], N["Material Output"].inputs[0])
    return m


def socks_scene():
    objs = []
    info = []
    for i, (nm, leg, foot) in enumerate(SHAPES):
        o, L, heel = sock_mesh(nm, leg, foot)
        # 絵のまんなかに、形のまんなかをあわせる
        xs = [v.co.x for v in o.data.vertices]; ys = [v.co.y for v in o.data.vertices]
        cx_, cy_ = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        o.location = (i * CELL - cx_ - CELL, -cy_, 0)
        objs.append(o)
        info.append({"name": nm, "L": round(L, 2), "heel": [round(heel[0], 2), round(heel[1], 2)], "w": round(max(xs) - min(xs), 1), "h": round(max(ys) - min(ys), 1)})
    return objs, info


def floor():
    # フローリング：はば 14cm の板、長さはばらばら
    mats = [bl.wood(f"oak{i}", light=(0.8 - 0.05 * i, 0.56 - 0.04 * i, 0.33 - 0.03 * i), dark=(0.6, 0.38, 0.2), scale=0.05 + 0.015 * i, rough=0.35, bump=0.05) for i in range(3)]
    x = -80
    while x < 80:
        y = -120 - rr.uniform(0, 80)
        while y < 120:
            ln = rr.uniform(70, 160)
            p = bl.cube((13.7, ln - 0.3, 2), (x + 7, y + ln / 2, -1)); bl.bevel(p, 0.25, 2); bl.assign(p, rr.choice(mats))
            p.rotation_euler.z = math.radians(rr.uniform(-0.05, 0.05))
            y += ln
        x += 14
    under = bl.plane((400, 400), (0, 0, -2.2)); bl.assign(under, bl.mat("gap", (0.12, 0.08, 0.05), 0.9))


def basket():
    # 洗濯かご（ラタン）。ふちだけ画面にのぞく
    wk = bl.mat("rattan", (0.72, 0.56, 0.34), 0.7)
    N, L, b = bl.nodes(wk)
    tc = N.new("ShaderNodeTexCoord"); ch = N.new("ShaderNodeTexChecker"); ch.inputs["Scale"].default_value = 0.9
    ch.inputs["Color1"].default_value = (0.75, 0.6, 0.38, 1); ch.inputs["Color2"].default_value = (0.6, 0.45, 0.26, 1)
    L.new(tc.outputs["Object"], ch.inputs["Vector"]); L.new(ch.outputs["Color"], b.inputs["Base Color"])
    bp = N.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.7; L.new(ch.outputs["Fac"], bp.inputs["Height"]); L.new(bp.outputs["Normal"], b.inputs["Normal"])
    c = bl.cyl(30, 34, (BASKET[0], BASKET[1], 17), verts=64)
    so = c.modifiers.new("s", 'SOLIDIFY'); so.thickness = 1.6
    for p in c.data.polygons:
        p.select = p.normal.z > 0.9
    bpy.context.view_layer.objects.active = c
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.delete(type='FACE'); bpy.ops.object.mode_set(mode='OBJECT')
    bl.assign(c, wk)
    bpy.ops.mesh.primitive_torus_add(major_radius=30, minor_radius=1.8, location=(BASKET[0], BASKET[1], 34)); bl.assign(bl.active(), wk)
    # 中：たたむ前のタオル（白とうすい水色）
    for i, col in enumerate([(0.92, 0.92, 0.9), (0.7, 0.82, 0.88), (0.95, 0.9, 0.8)]):
        t = bl.sphere(16, (BASKET[0] + [-8, 9, 0][i], BASKET[1] + [5, -4, 10][i], 22 + i * 2)); t.scale = (1, 0.8, 0.45)
        d = t.modifiers.new("d", 'DISPLACE'); tx = bpy.data.textures.new(f"tw{i}", 'CLOUDS'); tx.noise_scale = 4; d.texture = tx; d.strength = 3
        tm = bl.mat(f"towel{i}", col, 1.0, Sheen_Weight=1.0); bl.noise_bump(tm, scale=4, strength=0.5); bl.assign(t, tm)


def tray():
    # たたんだ靴下を置く、浅い木のトレイ
    tw = bl.wood("tray", light=(0.72, 0.52, 0.32), dark=(0.5, 0.32, 0.18), scale=0.15, rough=0.4)
    w, h = 96, 26
    base = bl.cube((w, h, 1.2), (TRAY[0], TRAY[1], 0.6)); bl.bevel(base, 0.4, 2); bl.assign(base, tw)
    for (sx, sy, lx, ly) in ((w, 1.4, 0, h / 2), (w, 1.4, 0, -h / 2), (1.4, h, w / 2, 0), (1.4, h, -w / 2, 0)):
        e = bl.cube((sx, sy, 3.4), (TRAY[0] + lx, TRAY[1] + ly, 1.7)); bl.bevel(e, 0.5, 2); bl.assign(e, tw)
    # 内がわの布
    cl = bl.cube((w - 3, h - 3, 0.3), (TRAY[0], TRAY[1], 1.35)); cm = bl.mat("linen", (0.95, 0.9, 0.8), 1.0); bl.noise_bump(cm, scale=8, strength=0.3); bl.assign(cl, cm)


def deco():
    # 右上：たたんだタオルの山と、木の洗濯ばさみ
    for i, col in enumerate([(0.93, 0.92, 0.9), (0.62, 0.72, 0.62), (0.9, 0.86, 0.78)]):
        t = bl.cube((30, 22, 3.6), (44, 74, 1.9 + i * 3.7), rot=(0, 0, rr.uniform(-4, 4))); bl.bevel(t, 1.6, 4)
        tm = bl.mat(f"ft{i}", col, 1.0, Sheen_Weight=1.0); bl.noise_bump(tm, scale=5, strength=0.5); bl.assign(t, tm)
    pm = bl.mat("peg", (0.82, 0.68, 0.48), 0.5)
    for i in range(3):
        x, y, a = 20 + i * 5, 40 - i * 3, rr.uniform(-40, 40)
        p = bl.cube((1.4, 7, 1.2), (x, y, 0.6), rot=(0, 0, a)); bl.bevel(p, 0.4, 2); bl.assign(p, pm)


def lights():
    bl.world((0.85, 0.9, 1.0), 0.6)
    rot = (40, 0, -130)
    sun = bl.light("SUN", (0, 0, 300), 6.5, rot_deg=rot, angle=1.0, color=(1, 0.86, 0.68))
    bpy.context.view_layer.update()
    d = sun.matrix_world.to_quaternion() @ mathutils.Vector((0, 0, -1))       # 光の進む向き
    up = lambda x, y: (x - d.x * 160 / -d.z, y - d.y * 160 / -d.z)
    # 窓：ゆかの上の日だまり（よこ 100 × たて 120cm、まんなかより少し上）を、窓の穴として上に写す
    fm = bl.mat("frame", (0.2, 0.2, 0.2), 0.8)
    x0, x1, y0, y1 = -55, 52, -92, 85
    def board(ax, ay, bx, by, w):
        (px, py), (qx, qy) = up(ax, ay), up(bx, by)
        L = math.hypot(qx - px, qy - py)
        o = bl.cube((L + w, w, 1), ((px + qx) / 2, (py + qy) / 2, 160), rot=(0, 0, math.degrees(math.atan2(qy - py, qx - px))))
        bl.assign(o, fm); o.visible_camera = False
    # まわりの壁（大きい板）と、わく・桟
    cx_, cy_ = up((x0 + x1) / 2, (y0 + y1) / 2)
    for (ox, oy, w, h) in ((-1, 0, 600, 1200), (1, 0, 600, 1200), (0, -1, 2000, 600), (0, 1, 2000, 600)):
        pass
    corners = [up(x0, y0), up(x1, y0), up(x1, y1), up(x0, y1)]
    xs = [c[0] for c in corners]; ys = [c[1] for c in corners]
    for (bx0, bx1, by0, by1) in ((min(xs) - 900, min(xs), -900, 900), (max(xs), max(xs) + 900, -900, 900), (min(xs), max(xs), -900, min(ys)), (min(xs), max(xs), max(ys), 900)):
        o = bl.cube((bx1 - bx0, by1 - by0, 1), ((bx0 + bx1) / 2, (by0 + by1) / 2, 160)); bl.assign(o, fm); o.visible_camera = False
    board((x0 + x1) / 2, y0, (x0 + x1) / 2, y1, 4)
    board(x0, (y0 + y1) / 2, x1, (y0 + y1) / 2, 4)
    # 窓の外の木の葉のゆらぎ（少しだけ）
    for i in range(40):
        lx, ly = rr.uniform(x0, x1), rr.uniform(y0, y1)
        if rr.random() < 0.6: continue
        px, py = up(lx, ly)
        sp = bl.sphere(rr.uniform(2, 5), (px, py, 170)); sp.scale = (1, 1, 0.2); bl.assign(sp, fm); sp.visible_camera = False
    bl.light('AREA', (0, 0, 120), 0.9e5, size=300, color=(0.95, 0.96, 1.0))


def proj(sc, cam, p):
    v = world_to_camera_view(sc, cam, mathutils.Vector(p))
    return [round(v.x * 720, 1), round((1 - v.y) * 1080, 1)]


part = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else "all"

if part in ("all", "bg"):
    sc = bl.reset(); sc.view_settings.exposure = 0.0
    floor(); basket(); tray(); deco(); lights()
    cam = bl.camera((0, 0, 1000), ortho=VH); cam.data.sensor_fit = 'VERTICAL'; cam.data.clip_end = 5000
    sc.render.resolution_x, sc.render.resolution_y = 1080, 1620
    bpy.context.view_layer.update()
    c0 = proj(sc, cam, (0, 0, 0)); c1 = proj(sc, cam, (100, 0, 0))
    geo = {"c": c0, "ppc": round((c1[0] - c0[0]) / 100, 3), "tray": proj(sc, cam, TRAY + (2,)), "trayW": round(proj(sc, cam, (TRAY[0] + 46, TRAY[1], 2))[0] - proj(sc, cam, TRAY + (2,))[0], 1) * 2,
           "trayH": round(proj(sc, cam, (TRAY[0], TRAY[1] - 12, 2))[1] - proj(sc, cam, TRAY + (2,))[1], 1) * 2, "basket": proj(sc, cam, BASKET + (34,))}
    json.dump(geo, open(os.path.join(OUT, "geo_bg.json"), "w")); print(geo)
    if "--geo" in sys.argv: sys.exit(0)
    bl.render(os.path.join(OUT, "bg.png"), 1080, 1620, samples=S)

if part in ("all", "socks"):
    for mode in ("s", "d"):
        sc = bl.reset()
        objs, info = socks_scene()
        if mode == "s":
            sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'; sc.view_settings.exposure = 0.0
            m = knit_mat()
            for o in objs: bl.assign(o, m)
            bl.world((1, 1, 1), 0.25)
            bl.light('SUN', (0, 0, 50), 1.5, rot_deg=(35, 0, -130), angle=10)
            samples = S
        else:
            sc.view_settings.view_transform = 'Raw' if 'Raw' in [i.identifier for i in sc.view_settings.bl_rna.properties['view_transform'].enum_items] else 'Standard'
            sc.view_settings.look = 'None'; sc.cycles.use_denoising = False
            sc.render.filter_size = 0.01
            m = data_mat()
            for o in objs: bl.assign(o, m)
            bl.world((0, 0, 0), 0)
            samples = 1
        cam = bl.camera((0, 0, 100), ortho=CELL * 3); cam.data.sensor_fit = 'HORIZONTAL'
        sc.render.resolution_x, sc.render.resolution_y = CELL * PX * 3, CELL * PX
        bl.render(os.path.join(OUT, f"sock_{mode}.png"), CELL * PX * 3, CELL * PX, samples=samples, transparent=True)
    geo = {"cell": CELL, "px": PX, "shapes": info}
    json.dump(geo, open(os.path.join(OUT, "geo_sock.json"), "w")); print(geo)

# 2つの geo をまとめる
try:
    g = json.load(open(os.path.join(OUT, "geo_bg.json"))); g.update(json.load(open(os.path.join(OUT, "geo_sock.json"))))
    json.dump(g, open(os.path.join(OUT, "geo.json"), "w"))
except FileNotFoundError:
    pass
print("done")
