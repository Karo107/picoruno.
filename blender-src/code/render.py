"""コードほどき：素材レンダリング。

トートバッグの中を真上から。キャンバス地の底に、からまった充電ケーブル（ケーブルはゲームで描く）。
out/bg.png       バッグの中（ふちに財布・鍵・リップ）
out/plugs.png    プラグ 4 種（上向き）。陰影（白いプラスチック）を横にならべた帯
out/plugm.png    同じ形の「色をぬる所」マスク（白＝プラスチック、黒＝金属）
out/geo.json
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
rr = random.Random(33)
VH = 90                       # 画面のたて 90cm（よこ 60cm）
PCELL = 6                     # プラグ1つの絵：6cm 四方
PPX = 40                      # プラグの絵の 1cm = 40px


def canvas_mat(name, col):
    m = bl.mat(name, col, 0.95, Sheen_Weight=0.5)
    N, L, b = bl.nodes(m)
    tc = N.new("ShaderNodeTexCoord")
    # 平織り：たて糸とよこ糸
    def wave(axis, sc):
        sep = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Object"], sep.inputs[0])
        m1 = N.new("ShaderNodeMath"); m1.operation = 'MULTIPLY'; m1.inputs[1].default_value = sc; L.new(sep.outputs[axis], m1.inputs[0])
        sn = N.new("ShaderNodeMath"); sn.operation = 'SINE'; L.new(m1.outputs[0], sn.inputs[0])
        return sn.outputs[0]
    a = wave("X", 2 * math.pi * 7); c = wave("Y", 2 * math.pi * 7)
    mu = N.new("ShaderNodeMath"); mu.operation = 'MULTIPLY'; L.new(a, mu.inputs[0]); L.new(c, mu.inputs[1])
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.6; nz.inputs["Detail"].default_value = 8
    L.new(tc.outputs["Object"], nz.inputs["Vector"])
    ad = N.new("ShaderNodeMath"); ad.operation = 'ADD'; L.new(mu.outputs[0], ad.inputs[0]); L.new(nz.outputs["Fac"], ad.inputs[1])
    bp = N.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.35; L.new(ad.outputs[0], bp.inputs["Height"]); L.new(bp.outputs["Normal"], b.inputs["Normal"])
    cr = N.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].color = (*[c_ * 0.85 for c_ in col], 1); cr.color_ramp.elements[1].color = (*col, 1)
    L.new(nz.outputs["Fac"], cr.inputs["Fac"]); L.new(cr.outputs["Color"], b.inputs["Base Color"])
    return m


FX, FY = 27, 41            # バッグの底の半はば・半たて


def bag():
    # 底：しわのよったキャンバス地（オリーブ）
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=180, y_subdivisions=270, size=1, location=(0, 0, 0))
    g = bl.active(); g.scale = (FX * 2 + 2, FY * 2 + 2, 1); bpy.ops.object.transform_apply(scale=True)
    d = g.modifiers.new("d", 'DISPLACE'); tx = bpy.data.textures.new("wr", 'CLOUDS'); tx.noise_scale = 15; tx.noise_depth = 2; d.texture = tx; d.strength = 2.6
    d2 = g.modifiers.new("d2", 'DISPLACE'); tx2 = bpy.data.textures.new("wr2", 'CLOUDS'); tx2.noise_scale = 4; d2.texture = tx2; d2.strength = 0.3
    bl.smooth(g); bl.assign(g, canvas_mat("canvas", (0.36, 0.35, 0.25)))
    # 側面：まっすぐ立った布の壁。上のふちは折り返し
    wm = canvas_mat("wall", (0.33, 0.32, 0.23))
    for (x, y, sx, sy) in ((-FX - 0.5, 0, 1, FY * 2 + 2), (FX + 0.5, 0, 1, FY * 2 + 2), (0, -FY - 0.5, FX * 2 + 2, 1), (0, FY + 0.5, FX * 2 + 2, 1)):
        w = bl.cube((sx, sy, 32), (x, y, 15)); bl.assign(w, wm)
    # 底の縫い目
    sm = bl.mat("seam", (0.28, 0.27, 0.19), 0.9)
    for (x, y, sx, sy) in ((-FX + 0.6, 0, 0.5, FY * 2), (FX - 0.6, 0, 0.5, FY * 2), (0, -FY + 0.6, FX * 2, 0.5), (0, FY - 0.6, FX * 2, 0.5)):
        e = bl.cube((sx, sy, 0.8), (x, y, 0.4)); bl.bevel(e, 0.2, 2); bl.assign(e, sm)
    # すみの小物
    lt = bl.mat("leather", (0.42, 0.2, 0.09), 0.45); bl.noise_bump(lt, scale=2.5, strength=0.25)
    wl = bl.cube((15, 9, 2.2), (-17, -35, 2.4), rot=(0, 0, 10)); bl.bevel(wl, 0.9, 4); bl.assign(wl, lt)
    st = bl.cube((13.6, 0.4, 0.3), (-17, -34.6, 3.55), rot=(0, 0, 10)); bl.assign(st, bl.mat("stitch", (0.85, 0.75, 0.55), 0.6))
    lc = bl.cyl(0.9, 7, (20, -36, 2.0), verts=32); lc.rotation_euler = (math.radians(90), 0, math.radians(70)); bl.assign(lc, bl.mat("lip", (0.85, 0.45, 0.5), 0.3))
    cap = bl.cyl(0.95, 2.5, (24.5, -37.6, 2.05), verts=32); cap.rotation_euler = (math.radians(90), 0, math.radians(70)); bl.assign(cap, bl.mat("lipcap", (0.95, 0.95, 0.93), 0.25))
    met = bl.mat("brass", (0.8, 0.62, 0.3), 0.25, metal=1.0)
    bpy.ops.mesh.primitive_torus_add(major_radius=1.6, minor_radius=0.18, location=(19, 36, 1.6)); bl.assign(bl.active(), bl.mat("steel", (0.75, 0.75, 0.78), 0.2, metal=1.0))
    for i, a in enumerate((-30, 20)):
        k = bl.cube((1.6, 5.5, 0.25), (19 + math.sin(math.radians(a)) * 4.4, 36 - math.cos(math.radians(a)) * 4.4, 1.6), rot=(0, 0, a)); bl.bevel(k, 0.2, 2); bl.assign(k, met)
        hd = bl.cyl(1.3, 0.3, (19 + math.sin(math.radians(a)) * 2.4, 36 - math.cos(math.radians(a)) * 2.4, 1.7), verts=32); bl.assign(hd, met)
    ch = bl.cube((4.5, 4.5, 2.8), (-20, 35, 2.4), rot=(0, 0, -8)); bl.bevel(ch, 0.6, 4); bl.assign(ch, bl.mat("brick", (0.92, 0.92, 0.9), 0.3))


def plug(kind, x0):
    """上向きのプラグ。白いプラスチック（mat_p）と金属（mat_m）。原点＝ケーブルとのつなぎ目"""
    parts = []
    def add(o, metal):
        parts.append((o, metal)); o.location.x += x0; return o
    # ケーブルの根元（ひずみよけ）
    sr = add(bl.cyl(0.3, 1.5, (0, 0.6, 0.35), verts=32), False); sr.rotation_euler = (math.radians(90), 0, 0)
    if kind == "usbc":
        b = add(bl.cube((1.15, 2.3, 0.7), (0, 2.0, 0.35)), False); bl.bevel(b, 0.3, 4)
        m = add(bl.cube((0.84, 0.75, 0.26), (0, 3.5, 0.35)), True); bl.bevel(m, 0.12, 4)
    elif kind == "light":
        b = add(bl.cube((1.0, 2.2, 0.62), (0, 1.95, 0.33)), False); bl.bevel(b, 0.26, 4)
        m = add(bl.cube((0.78, 0.85, 0.15), (0, 3.45, 0.33)), True); bl.bevel(m, 0.07, 3)
        for i in range(4):
            c = add(bl.cube((0.1, 0.3, 0.02), (-0.27 + i * 0.18, 3.5, 0.415)), True)
    elif kind == "usba":
        b = add(bl.cube((1.7, 2.6, 0.9), (0, 2.1, 0.45)), False); bl.bevel(b, 0.3, 4)
        m = add(bl.cube((1.24, 1.3, 0.48), (0, 4.0, 0.45)), True); bl.bevel(m, 0.04, 2)
        for i in (-1, 1):
            h = add(bl.cube((0.22, 0.22, 0.05), (i * 0.3, 4.15, 0.69)), False)
    else:   # イヤホンのミニプラグ
        b = add(bl.cyl(0.42, 1.9, (0, 1.85, 0.42), verts=32), False); b.rotation_euler = (math.radians(90), 0, 0); bl.bevel(b, 0.12, 3)
        m = add(bl.cyl(0.18, 1.4, (0, 3.5, 0.42), verts=24), True); m.rotation_euler = (math.radians(90), 0, 0)
        tip = add(bl.sphere(0.18, (0, 4.2, 0.42)), True)
        for y in (3.1, 3.55):
            r_ = add(bl.cyl(0.19, 0.06, (0, y, 0.42), verts=24), False); r_.rotation_euler = (math.radians(90), 0, 0)
    return parts


KINDS = ["usbc", "light", "usba", "jack"]


def studio():
    """プラグとケーブル共通の光：左上のキーライト＋金属に映る光の帯"""
    bl.world((0.9, 0.92, 1), 0.12)
    bl.light('AREA', (-5, -5, 12), 420, rot_deg=(22, -22, 0), size=8, color=(1, 0.97, 0.92))
    bl.light('AREA', (7, 7, 9), 50, rot_deg=(-35, 35, 0), size=6, color=(0.9, 0.95, 1))
    for (x, a) in ((-6, -30), (5, 25)):
        st = bl.plane((1.5, 60), (x, 0, 14), rot=(0, a, 0)); bl.assign(st, bl.emission("strip", (1, 1, 1), 6)); st.visible_camera = False; st.visible_diffuse = False


def proj(sc, cam, p):
    v = world_to_camera_view(sc, cam, mathutils.Vector(p))
    return [round(v.x * 720, 1), round((1 - v.y) * 1080, 1)]


part = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else "all"

if part in ("all", "bg"):
    sc = bl.reset(); sc.view_settings.exposure = -0.2
    bag()
    bl.world((0.85, 0.9, 1.0), 0.35)
    bl.light('AREA', (0, 0, 160), 1.0e5, size=50, color=(1, 0.97, 0.92))
    bl.light('SUN', (0, 0, 100), 3.2, rot_deg=(32, -24, 0), angle=4, color=(1, 0.9, 0.75))
    cam = bl.camera((0, 0, 130), lens=36 * 130 / VH * 0.965); cam.data.sensor_fit = 'VERTICAL'; cam.data.sensor_height = 36; cam.data.clip_end = 5000
    sc.render.resolution_x, sc.render.resolution_y = 1080, 1620
    bpy.context.view_layer.update()
    c0 = proj(sc, cam, (0, 0, 1)); c1 = proj(sc, cam, (10, 0, 1))
    geo = {"c": c0, "ppc": round((c1[0] - c0[0]) / 10, 3), "inner": [proj(sc, cam, (-FX, FY, 0)), proj(sc, cam, (FX, -FY, 0))]}
    json.dump(geo, open(os.path.join(OUT, "geo_bg.json"), "w")); print(geo)
    if "--geo" in sys.argv: sys.exit(0)
    bl.render(os.path.join(OUT, "bg.png"), 1080, 1620, samples=S)

if part in ("all", "plugs"):
    for mode in ("s", "m"):
        sc = bl.reset()
        allp = []
        for i, k in enumerate(KINDS):
            allp += plug(k, (i - 1.5) * PCELL)
        # 絵のまんなか（たて）に、プラグのまんなかが来るように
        for o, _ in allp: o.location.y -= 2.2
        if mode == "s":
            sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'
            pm = bl.mat("plastic", (0.72, 0.72, 0.72), 0.32, Coat_Weight=0.4)
            mm = bl.mat("metal", (0.85, 0.85, 0.87), 0.18, metal=1.0)
            for o, metal in allp: bl.assign(o, mm if metal else pm)
            studio()
            samples = S
        else:
            sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'; sc.cycles.use_denoising = False
            for o, metal in allp: bl.assign(o, bl.emission("e%d" % metal, (0, 0, 0) if metal else (1, 1, 1), 1))
            bl.world((0, 0, 0), 0); samples = 4
        cam = bl.camera((0, 0, 50), ortho=PCELL * 4); cam.data.sensor_fit = 'HORIZONTAL'
        bl.render(os.path.join(OUT, f"plug{mode}.png"), PCELL * PPX * 4, PCELL * PPX, samples=samples, transparent=True)

try:
    g = json.load(open(os.path.join(OUT, "geo_bg.json"))); g.update({"pcell": PCELL, "kinds": KINDS, "plugLen": {"usbc": 3.9, "light": 3.9, "usba": 4.7, "jack": 4.4}})
    json.dump(g, open(os.path.join(OUT, "geo.json"), "w"))
except FileNotFoundError:
    pass
print("done")
