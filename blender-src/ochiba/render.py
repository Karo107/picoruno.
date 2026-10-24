"""落ち葉はき：素材レンダリング。

秋のお寺の石だたみを、ほぼ真上から。もみじの木もれ日が落ちている。
out/bg.png      石だたみ（葉っぱはゲームで置く）
out/leaves.png  落ち葉 8 種（4x2 のマス、透明背景）
out/broom.png   竹ぼうき（穂先が下、柄が上。透明背景）
out/geo.json    1cm の大きさ、かごの位置
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
rr = random.Random(12)
VW, VH = 400, 600          # 見える範囲 cm（だいたい）


def granite(name, base):
    m = bl.mat(name, base, 0.75)
    bl.noise_color(m, tuple(c * 0.7 for c in base), tuple(min(1, c * 1.12) for c in base), scale=0.12, detail=10)
    bl.noise_bump(m, scale=0.9, strength=0.6)
    return m


def ground():
    # 苔と土
    moss = bl.plane((900, 1100), (0, 0, -1))
    mm = bl.mat("moss", (0.2, 0.32, 0.1), 0.9)
    bl.noise_color(mm, (0.14, 0.24, 0.07), (0.32, 0.4, 0.14), scale=0.05, detail=6)
    bl.noise_bump(mm, scale=0.8, strength=0.6)
    bl.assign(moss, mm)
    # 石だたみ：大小の長方形の御影石を、目地をあけて並べる（左右の端は苔）
    mats = [granite(f"g{i}", c) for i, c in enumerate([(0.42, 0.4, 0.37), (0.5, 0.47, 0.42), (0.36, 0.35, 0.34), (0.47, 0.42, 0.36), (0.4, 0.38, 0.33)])]
    y = -VH / 2 - 60
    while y < VH / 2 + 60:
        h = rr.choice([34, 42, 50, 58])
        x = -150 - rr.uniform(0, 40)
        while x < 150:
            w = rr.uniform(36, 90)
            x1 = min(x + w, 150 + rr.uniform(0, 30))
            if x1 - x > 20:
                s = bl.cube((x1 - x - rr.uniform(2.5, 4.5), h - rr.uniform(2.5, 4.5), 8), ((x + x1) / 2, y + h / 2, 2 + rr.uniform(-0.6, 0.6)), rot=(rr.uniform(-0.4, 0.4), rr.uniform(-0.4, 0.4), rr.uniform(-0.6, 0.6)))
                bl.bevel(s, 2.4, 3); bl.assign(s, rr.choice(mats))
            x = x1
        y += h
    # 両わき：白い砂利（熊手の線）
    for side in (-1, 1):
        g = bl.cube((60, 1100, 2), (side * 200, 0, 0.5))
        gm = bl.mat(f"grav{side}", (0.62, 0.6, 0.55), 0.85)
        N, L, b = bl.nodes(gm)
        tc = N.new("ShaderNodeTexCoord"); vo = N.new("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = 0.9
        L.new(tc.outputs["Object"], vo.inputs["Vector"])
        cr = N.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].color = (0.45, 0.43, 0.4, 1); cr.color_ramp.elements[1].color = (0.72, 0.7, 0.66, 1)
        L.new(vo.outputs["Distance"], cr.inputs["Fac"]); L.new(cr.outputs["Color"], b.inputs["Base Color"])
        bp = N.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.9; bp.invert = True
        L.new(vo.outputs["Distance"], bp.inputs["Height"]); L.new(bp.outputs["Normal"], b.inputs["Normal"])
        bl.assign(g, gm)
        # 縁石
        k = bl.cube((10, 1100, 9), (side * 168, 0, 3)); bl.bevel(k, 1.5, 2); bl.assign(k, granite(f"curb{side}", (0.45, 0.44, 0.42)))
    # 左：苔むした庭石
    for (x, y, r) in ((-215, 210, 38), (-235, 150, 22), (225, -60, 30)):
        st = bl.sphere(r, (x, y, 0)); st.scale = (1, 0.8, 0.45)
        d = st.modifiers.new("d", 'DISPLACE'); d.texture = bpy.data.textures.new("rk", 'CLOUDS'); d.texture.noise_scale = 0.4; d.strength = 6
        rm = bl.mat(f"rock{x}", (0.36, 0.36, 0.33), 0.8); bl.noise_color(rm, (0.3, 0.3, 0.28), (0.25, 0.36, 0.12), scale=0.1, detail=6); bl.noise_bump(rm, scale=0.6, strength=0.8)
        bl.assign(st, rm)
    # 砂利と苔の上の落ち葉（飾り。石だたみの上には置かない）
    lm = [leaf_mat(f"dl{i}", c1, c2) for i, (c1, c2) in enumerate([((0.75, 0.08, 0.04), (0.55, 0.04, 0.03)), ((0.9, 0.35, 0.05), (0.8, 0.18, 0.04)), ((0.95, 0.7, 0.12), (0.85, 0.5, 0.06))])]
    for i in range(70):
        side = rr.choice((-1, 1)); x = side * rr.uniform(172, 260); y = rr.uniform(-380, 380)
        o, st_ = leaf_mesh("maple" if rr.random() < 0.7 else "oval", rr.uniform(7, 10))
        m = rr.choice(lm); bl.assign(o, m); bl.assign(st_, m)
        rz = rr.uniform(0, 6.28)
        for ob in (o, st_):
            ob.location = mathutils.Matrix.Rotation(rz, 4, 'Z') @ ob.location + mathutils.Vector((x, y, 2.5)); ob.rotation_euler.z += rz
    # 右下：竹かご（ここに集める）
    basket()


def basket():
    bm = bl.mat("bamboo", (0.72, 0.58, 0.36), 0.6)
    N, L, b = bl.nodes(bm)
    tc = N.new("ShaderNodeTexCoord"); br = N.new("ShaderNodeTexChecker"); br.inputs["Scale"].default_value = 0.6
    br.inputs["Color1"].default_value = (0.72, 0.58, 0.36, 1); br.inputs["Color2"].default_value = (0.58, 0.44, 0.26, 1)
    L.new(tc.outputs["Object"], br.inputs["Vector"]); L.new(br.outputs["Color"], b.inputs["Base Color"])
    bp = N.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.6
    L.new(br.outputs["Fac"], bp.inputs["Height"]); L.new(bp.outputs["Normal"], b.inputs["Normal"])
    c = bl.cyl(34, 36, BASKET + (18,), verts=64)
    so = c.modifiers.new("s", 'SOLIDIFY'); so.thickness = 1.5
    # 底だけ残す：上の面を消す
    bpy.context.view_layer.objects.active = c; c.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='DESELECT'); bpy.ops.object.mode_set(mode='OBJECT')
    for p in c.data.polygons:
        if p.normal.z > 0.9: p.select = True
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.delete(type='FACE'); bpy.ops.object.mode_set(mode='OBJECT')
    bl.assign(c, bm)
    rim = bpy.ops.mesh.primitive_torus_add(major_radius=34, minor_radius=1.6, location=(BASKET[0], BASKET[1], 36)); bl.assign(bl.active(), bm)
    inner = bl.cyl(32, 1, (BASKET[0], BASKET[1], 6), verts=64); bl.assign(inner, bl.mat("bin", (0.3, 0.22, 0.13), 0.8))


BASKET = (100, -200)


def lights():
    bl.world((0.85, 0.9, 1.0), 0.35)
    sun = bl.light("SUN", (0, 0, 300), 5.5, rot_deg=(32, 0, 40), angle=2.5, color=(1, 0.8, 0.55))
    # もみじの枝葉（カメラには写らない）で木もれ日をつくる
    occ = bl.mat("occ", (0.1, 0.2, 0.05), 0.8)
    for i in range(1700):
        x = rr.uniform(-520, 320); y = rr.uniform(-420, 640)
        if (x + 250) ** 2 / 560 ** 2 + (y - 350) ** 2 / 620 ** 2 > 1: continue
        s = bl.sphere(rr.uniform(4, 11), (x, y, rr.uniform(260, 340)))
        s.scale = (1, 1, 0.2); bl.assign(s, occ); s.visible_camera = False
    bl.light('AREA', (0, -200, 600), 2.0e6, rot_deg=(20, 0, 0), size=600, color=(0.85, 0.9, 1.0))


def proj(sc, cam, p):
    v = world_to_camera_view(sc, cam, mathutils.Vector(p))
    return [round(v.x * 720, 1), round((1 - v.y) * 1080, 1)]


def leaf_mesh(kind, size):
    pts = []
    n = 120
    for i in range(n):
        t = i / n * 2 * math.pi
        if kind == "maple":
            # 7つのとがった裂片、ふちは細かいぎざぎざ
            lobe = abs(math.cos(3.5 * (t - math.pi / 2))) ** 3
            r = 0.38 + 0.62 * lobe + 0.03 * math.sin(t * 60)
            if math.sin(t) < -0.85: r *= 0.35          # 葉柄の付け根のへこみ
        elif kind == "ginkgo":
            a = (t - math.pi / 2 + math.pi) % (2 * math.pi) - math.pi   # 上向き 0
            if abs(a) < 1.1: r = 0.95 + 0.06 * math.sin(a * 25) - (0.25 if abs(a) < 0.12 else 0)
            else: r = max(0.08, 0.95 * max(0.0, 1 - (abs(a) - 1.1) / 2.04) ** 1.6)
        else:   # 桜・けやき：先のとがった卵形
            sn = math.sin(t)
            pts.append((0.42 * math.cos(t) * (1 - 0.3 * max(0, sn) ** 3) * size * (1 + 0.02 * math.sin(t * 50)), sn * (0.95 if sn > 0 else 0.6) * size))
            continue
        pts.append((math.cos(t) * r * size, math.sin(t) * r * size))
    me = bpy.data.meshes.new(kind); bm_ = bmesh.new()
    c = bm_.verts.new((0, 0, 0))
    vs = [bm_.verts.new((x, y, 0)) for x, y in pts]
    for i in range(n): bm_.faces.new((c, vs[i], vs[(i + 1) % n]))
    # 葉柄
    bm_.to_mesh(me); bm_.free()
    o = bpy.data.objects.new(kind, me); bl.link(o)
    sd = o.modifiers.new("t", 'SOLIDIFY'); sd.thickness = 0.12
    st = bl.cyl(0.14, size * 0.55, (0, -size * 0.5, 0.05), verts=8); st.rotation_euler = (math.radians(90), 0, 0)
    return o, st


def leaf_mat(name, c1, c2):
    m = bl.mat(name, c1, 0.5)
    bl.noise_color(m, c1, c2, scale=0.6, detail=5)
    bl.noise_bump(m, scale=3, strength=0.2)
    return m


def broom():
    tw = bl.mat("twig", (0.55, 0.45, 0.28), 0.7)
    for i in range(110):
        a = rr.uniform(-0.42, 0.42); L = rr.uniform(55, 70)
        c = bl.cyl(rr.uniform(0.18, 0.35), L, (math.sin(a) * L / 2, -math.cos(a) * L / 2 + 0, rr.uniform(0, 3)), verts=6)
        c.rotation_euler = (math.radians(90), 0, a + rr.uniform(-0.05, 0.05)); bl.assign(c, tw)
    h = bl.cyl(1.8, 80, (0, 40, 1.5), verts=24); h.rotation_euler = (math.radians(90), 0, 0)
    hm = bl.mat("handle", (0.75, 0.66, 0.42), 0.4); bl.assign(h, hm)
    for y in (2, 8, 14):
        bpy.ops.mesh.primitive_torus_add(major_radius=3.2, minor_radius=0.5, location=(0, -y, 1.5), rotation=(math.radians(90), 0, 0))
        bl.assign(bl.active(), bl.mat("cord", (0.25, 0.18, 0.12), 0.8))


part = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else "all"

if part in ("all", "bg"):
    sc = bl.reset(); sc.view_settings.exposure = -0.5
    ground(); lights()
    cam = bl.camera((0, -170, 900), rot_deg=(11, 0, 0), lens=32)
    cam.data.sensor_fit = 'VERTICAL'; cam.data.sensor_height = 24; cam.data.clip_end = 5000
    sc.render.resolution_x, sc.render.resolution_y = 1080, 1620
    bpy.context.view_layer.update()
    c0 = proj(sc, cam, (0, 0, 2)); c1 = proj(sc, cam, (100, 0, 2)); c2 = proj(sc, cam, (0, 100, 2))
    geo = {"c": c0, "ex": [round((c1[0] - c0[0]) / 100, 3), round((c1[1] - c0[1]) / 100, 3)], "ey": [round((c2[0] - c0[0]) / 100, 3), round((c2[1] - c0[1]) / 100, 3)],
           "basket": proj(sc, cam, (BASKET[0], BASKET[1], 36)), "basketR": round(proj(sc, cam, (BASKET[0] + 34, BASKET[1], 36))[0] - proj(sc, cam, BASKET + (36,))[0], 1),
           "path": [proj(sc, cam, (-160, 0, 2))[0], proj(sc, cam, (160, 0, 2))[0]]}
    json.dump(geo, open(os.path.join(OUT, "geo.json"), "w")); print(geo)
    if "--geo" in sys.argv: sys.exit(0)
    bl.render(os.path.join(OUT, "bg.png"), 1080, 1620, samples=S)

if part in ("all", "leaves"):
    sc = bl.reset(); sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'; sc.view_settings.exposure = -0.3
    kinds = [("maple", (0.75, 0.08, 0.04), (0.55, 0.04, 0.03)), ("maple", (0.9, 0.35, 0.05), (0.8, 0.18, 0.04)), ("maple", (0.95, 0.65, 0.1), (0.85, 0.45, 0.06)),
             ("ginkgo", (0.95, 0.78, 0.15), (0.88, 0.68, 0.1)), ("ginkgo", (0.9, 0.7, 0.12), (0.75, 0.6, 0.15)),
             ("oval", (0.6, 0.35, 0.15), (0.45, 0.26, 0.12)), ("oval", (0.8, 0.45, 0.12), (0.65, 0.3, 0.1)), ("maple", (0.6, 0.12, 0.08), (0.4, 0.08, 0.05))]
    for i, (k, c1, c2) in enumerate(kinds):
        o, st = leaf_mesh(k, 4.2 if k != "oval" else 4.6)
        m = leaf_mat(f"lf{i}", c1, c2); bl.assign(o, m); bl.assign(st, m)
        cx_, cy_ = (i % 4) * 10 - 15, (1 - i // 4) * 10 - 5
        for ob in (o, st):
            ob.location = (ob.location.x + cx_, ob.location.y + cy_, ob.location.z)
        bd = o.modifiers.new("b", 'SIMPLE_DEFORM'); bd.deform_method = 'BEND'; bd.angle = math.radians(rr.uniform(15, 35)); bd.deform_axis = 'Y'
    bl.world((0.9, 0.9, 0.95), 0.25)
    bl.light('SUN', (0, 0, 50), 4.0, rot_deg=(20, 0, 30), angle=3, color=(1, 0.9, 0.75))
    cam = bl.camera((0, 0, 100), rot_deg=(0, 0, 0)); cam.data.type = 'ORTHO'; cam.data.ortho_scale = 40
    bl.render(os.path.join(OUT, "leaves.png"), 1024, 512, samples=S, transparent=True)

if part in ("all", "broom"):
    sc = bl.reset(); sc.view_settings.exposure = 0.0
    broom()
    bl.world((0.9, 0.9, 0.95), 0.6)
    bl.light('SUN', (0, 0, 50), 3.5, rot_deg=(20, 0, 30), angle=3)
    cam = bl.camera((0, 5, 100), rot_deg=(0, 0, 0)); cam.data.type = 'ORTHO'; cam.data.ortho_scale = 150; cam.data.sensor_fit = 'VERTICAL'
    bl.render(os.path.join(OUT, "broom.png"), 360, 1080, samples=S, transparent=True)
print("done")
