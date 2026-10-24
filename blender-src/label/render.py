"""ラベルきれいに：素材レンダリング。

朝の台所のカウンター。窓の光の中に、ラベルをはがす前のペットボトル（ラベルはゲーム側で巻きつけて描く）。
out/bg_<kind>.png  ボトルの中身ちがい（water / tea / soda）
out/geo.json       ラベルを巻く円筒の画面位置（中心x・半径・上下の y・楕円のふくらみ）
720x1080 を 1.5 倍。1 = 1cm。
"""
import json, math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "common"))
import bpy, mathutils
from bpy_extras.object_utils import world_to_camera_view
import bl

OUT = os.path.join(os.path.dirname(__file__), "out")
os.makedirs(OUT, exist_ok=True)
FAST = "--fast" in sys.argv
S = 24 if FAST else 128

R = 3.3                 # 胴の半径
LZ0, LZ1 = 5.85, 13.75   # ラベルの下と上（胴のへこみ全体）
KINDS = {
    "water": {"liquid": (0.92, 0.97, 1.0), "density": 0.0, "cap": (0.25, 0.55, 0.9)},
    "tea":   {"liquid": (0.75, 0.62, 0.22), "density": 0.6, "cap": (0.2, 0.5, 0.25)},
    "soda":  {"liquid": (0.86, 0.95, 0.98), "density": 0.05, "cap": (0.85, 0.2, 0.2)},
}


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


def bottle(kind):
    K = KINDS[kind]
    # 外形 (r, z)：花形の底→胴（ラベル部は少しへこむ）→肩→首
    prof = [(0.0, 0.25), (1.6, 0.0), (2.6, 0.35), (3.2, 1.0), (3.4, 2.5), (3.4, 5.6), (R, 6.0), (R, 13.6), (3.4, 14.0), (3.4, 15.0),
            (3.0, 16.8), (2.2, 18.4), (1.45, 19.4), (1.4, 20.0)]
    pet = bl.mat("pet", (0.95, 0.98, 1.0), 0.03, Transmission_Weight=1.0, IOR=1.45)
    shell = lathe(prof, "bottle")
    so = shell.modifiers.new("t", 'SOLIDIFY'); so.thickness = 0.05
    bl.assign(shell, pet)
    # 胴のリブ（横すじ）
    for z in (3.0, 4.2, 14.4):
        bpy.ops.mesh.primitive_torus_add(major_radius=3.4, minor_radius=0.08, location=(0, 0, z), major_segments=96)
        bl.assign(bl.smooth(bl.active()), pet)
    # 中身（8分目まで）
    lq = [(0.0, 0.35), (1.5, 0.12), (2.5, 0.45), (3.1, 1.1), (3.32, 2.5), (3.32, 5.6), (R - 0.07, 6.0), (R - 0.07, 13.6), (3.32, 14.0), (3.32, 15.0), (2.9, 16.6), (0.0, 16.6)]
    liq = lathe(lq, "liq")
    lm = bl.mat("liq", K["liquid"], 0.02, Transmission_Weight=1.0, IOR=1.33)
    N, L, b = bl.nodes(lm)
    if K["density"] > 0:
        out = N["Material Output"]; vol = N.new("ShaderNodeVolumeAbsorption")
        vol.inputs["Color"].default_value = (*K["liquid"], 1); vol.inputs["Density"].default_value = K["density"]
        L.new(vol.outputs[0], out.inputs["Volume"])
    bl.assign(liq, lm)
    if kind == "soda":
        import random
        rr = random.Random(2)
        bm = bl.mat("bub", (1, 1, 1), 0.02, Transmission_Weight=1.0, IOR=1.0)
        for i in range(70):
            a = rr.random() * 6.283; r = rr.random() ** 0.5 * 2.8; z = rr.uniform(1, 16)
            s = bl.sphere(rr.uniform(0.05, 0.16), (r * math.cos(a), r * math.sin(a), z)); bl.assign(s, bm)
    # キャップ
    cap = bl.cyl(1.55, 1.6, (0, 0, 20.75), verts=64); bl.bevel(cap, 0.15, 3)
    cm = bl.mat("cap", K["cap"], 0.35)
    bl.noise_bump(cm, scale=4, strength=0.2)
    bl.assign(cap, cm)
    for i in range(48):   # ギザギザ
        a = i / 48 * 6.283
        k = bl.cube((0.08, 0.12, 1.3), (1.56 * math.cos(a), 1.56 * math.sin(a), 20.75), rot=(0, 0, math.degrees(a))); bl.assign(k, cm)
    ring = bl.cyl(1.5, 0.3, (0, 0, 19.75), verts=64); bl.assign(ring, cm)
    return shell


def kitchen():
    top = bl.cube((200, 120, 4), (0, 20, -2))
    bl.assign(top, bl.wood("counter", light=(0.78, 0.62, 0.45), dark=(0.58, 0.42, 0.28), scale=0.08, rough=0.35, bump=0.06, stretch=20))
    # 奥の壁（白いタイル）と窓
    wall = bl.plane((200, 100), (0, 40, 50), rot=(90, 0, 0))
    wm = bl.mat("tile", (0.93, 0.92, 0.88), 0.15)
    N, L, b = bl.nodes(wm)
    tc = N.new("ShaderNodeTexCoord"); br = N.new("ShaderNodeTexBrick")
    br.inputs["Scale"].default_value = 1; br.inputs["Mortar Size"].default_value = 0.025
    br.inputs["Color1"].default_value = (0.93, 0.92, 0.88, 1); br.inputs["Color2"].default_value = (0.9, 0.89, 0.85, 1)
    br.inputs["Mortar"].default_value = (0.78, 0.76, 0.72, 1)
    br.offset = 0.0; br.squash = 1.0
    mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1 / 10, 1 / 10, 1)
    L.new(tc.outputs["Object"], mp.inputs["Vector"]); L.new(mp.outputs["Vector"], br.inputs["Vector"])
    L.new(br.outputs["Color"], b.inputs["Base Color"])
    bp = N.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.3
    L.new(br.outputs["Fac"], bp.inputs["Height"]); L.new(bp.outputs["Normal"], b.inputs["Normal"])
    bl.assign(wall, wm)
    # 左奥：鉢植えのハーブ（ぼける）
    pot = bl.cyl(4, 7, (-17, 28, 3.5)); bl.bevel(pot, 0.4, 3); bl.assign(pot, bl.mat("pot", (0.75, 0.45, 0.3), 0.7))
    for i, (x, z, r) in enumerate([(-17, 10, 3.5), (-19.5, 12, 2.6), (-14.5, 11.5, 2.8), (-17, 13.5, 2.4)]):
        s = bl.sphere(r, (x, 28, z)); bl.assign(s, bl.mat(f"herb{i}", (0.22, 0.45, 0.18), 0.6))
    # 右：まな板と布巾
    board = bl.cube((22, 16, 1.5), (18, 22, 0.75), rot=(0, 0, -8)); bl.bevel(board, 0.4, 3)
    bl.assign(board, bl.wood("board", light=(0.86, 0.74, 0.56), dark=(0.72, 0.58, 0.4), scale=0.2))
    cloth = bl.cube((10, 8, 0.6), (13, 6, 0.3), rot=(0, 0, 12)); bl.bevel(cloth, 0.25, 3)
    clm = bl.mat("cloth", (0.85, 0.88, 0.92), 0.9); bl.noise_bump(clm, scale=8, strength=0.3); bl.assign(cloth, clm)


def lights():
    bl.world((0.9, 0.93, 0.98), 0.5)
    # 窓わくの影（光と台所のあいだに格子を置く）
    fm = bl.mat("frame", (0.3, 0.3, 0.3), 0.8)
    for y in (-12, 8, 28):
        b = bl.cube((1.6, 1.6, 70), (-42, y, 40)); bl.assign(b, fm)
    for z in (22, 50):
        b = bl.cube((1.6, 60, 1.6), (-42, 8, z)); bl.assign(b, fm)
    bl.light('AREA', (-60, -10, 45), 120000, rot_deg=(70, 0, -80), size=50, color=(1, 0.93, 0.8))   # 窓のあかり
    bl.light('SUN', (0, 0, 50), 6.0, rot_deg=(55, 0, -62), angle=1.5, color=(1, 0.88, 0.7))              # 朝日（窓わくの影を落とす）
    bl.light('AREA', (30, -60, 30), 50000, rot_deg=(60, 0, 25), size=60, color=(0.9, 0.94, 1))


def proj(sc, cam, p):
    v = world_to_camera_view(sc, cam, mathutils.Vector(p))
    return [round(v.x * 720, 1), round((1 - v.y) * 1080, 1)]


geo = None
for kind in (["water"] if "--one" in sys.argv else KINDS):
    sc = bl.reset(); sc.view_settings.exposure = 0.0
    sc.cycles.transmission_bounces = 16; sc.cycles.max_bounces = 20
    kitchen(); lights(); bottle(kind)
    cam = bl.camera((0, -62, 12.5), rot_deg=(88, 0, 0), lens=55)
    cam.data.sensor_fit = 'VERTICAL'; cam.data.sensor_height = 24
    cam.data.dof.use_dof = True; cam.data.dof.focus_distance = 61; cam.data.dof.aperture_fstop = 0.6
    sc.render.resolution_x, sc.render.resolution_y = 1080, 1620
    bpy.context.view_layer.update()
    if geo is None:
        c0 = proj(sc, cam, (0, 0, LZ0)); c1 = proj(sc, cam, (0, 0, LZ1))
        f0 = proj(sc, cam, (0, -R, LZ0)); f1 = proj(sc, cam, (0, -R, LZ1))     # 手前のふち
        side = proj(sc, cam, (R, 0, (LZ0 + LZ1) / 2))
        geo = {"cx": c0[0], "r": round(side[0] - c0[0], 1), "y0": f1[1], "y1": f0[1], "bulge0": round(f1[1] - c1[1], 1), "bulge1": round(f0[1] - c0[1], 1),
               "capY": proj(sc, cam, (0, 0, 21.5))[1], "baseY": proj(sc, cam, (0, -3.4, 0))[1]}
        json.dump(geo, open(os.path.join(OUT, "geo.json"), "w")); print(geo)
        if "--geo" in sys.argv: sys.exit(0)
    bl.render(os.path.join(OUT, f"bg_{kind}.png"), 1080, 1620, samples=S)
print("done")
