"""ふちギリギリ：素材レンダリング。

キッチンのカウンターに置いたグラス（目の高さ＝ふちの高さから見る）と、上の真ちゅうの蛇口。
out/bg_<glass>.png  場面（720x1080 を 1.5 倍）
out/hl_<glass>.png  グラスのつやだけ（黒背景。ゲームで水の上に「加算」で重ねる）
out/geo.json        グラスの内側の形（画面座標）と蛇口の口の位置
1 = 1cm。
"""
import json, math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "common"))
import bpy, mathutils
from bpy_extras.object_utils import world_to_camera_view
import bl

OUT = os.path.join(os.path.dirname(__file__), "out")
os.makedirs(OUT, exist_ok=True)
FAST = "--fast" in sys.argv
S = 24 if FAST else 96

# グラスの内側の形：(高さcm, 内側の半径cm) のリスト。外側は壁の厚さぶん外へ
GLASSES = {
    "tumbler": {"prof": [(0.8, 3.3), (10.0, 3.7)], "wall": 0.22, "base": 0.8},
    "ochoko":  {"prof": [(0.6, 1.6), (2.2, 2.6), (4.2, 3.2)], "wall": 0.3, "base": 0.6},
    "flute":   {"prof": [(4.0, 0.2), (5.0, 1.6), (9.0, 2.2), (14.0, 2.0)], "wall": 0.12, "base": 0.0, "stem": 4.0},
}


def lathe(points, name, segs=128):
    """(r, z) の折れ線を Z 軸まわりに回した面。"""
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
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    o = bpy.data.objects.new(name, me)
    bl.link(o)
    bl.smooth(o)
    sub = o.modifiers.new("s", 'SUBSURF'); sub.levels = sub.render_levels = 2
    return o


def glass_obj(g):
    G = GLASSES[g]
    prof, w = G["prof"], G["wall"]
    top = prof[-1][0]
    # 外側：下から上、ふちを丸めて内側へ、内側を上から下へ
    pts = []
    if G.get("stem"):
        pts += [(0.0, 0.0), (3.0, 0.0), (3.0, 0.15), (0.35, 0.4), (0.3, G["stem"] - 0.4)]
    else:
        pts += [(0.0, 0.0), (prof[0][1] + w - 0.1, 0.0), (prof[0][1] + w, 0.15)]
    for z, r in prof:
        pts.append((r + w, z))
    pts += [(prof[-1][1] + w * 0.5, top + 0.06)]
    for z, r in reversed(prof):
        pts.append((r, z))
    pts.append((0.0, prof[0][0]))
    o = lathe([(r, z) for r, z in pts], g)
    m = bl.mat("glass", (1, 1, 1), 0.02, Transmission_Weight=1.0, IOR=1.5)
    bl.assign(o, m)
    return o


def faucet(nz_z):
    """右から立ち上がって、グラスの真上へアーチを描く真ちゅうの蛇口。口の高さ nz_z。"""
    brass = bl.mat("brass", (0.86, 0.62, 0.32), 0.18, 1.0)
    top = nz_z + 8
    cu = bpy.data.curves.new("arch", 'CURVE'); cu.dimensions = '3D'
    cu.bevel_depth = 0.85; cu.bevel_resolution = 8
    sp = cu.splines.new('NURBS')
    pts = [(15, 6, 0), (15, 6, top - 5), (15, 5, top), (11, 3, top + 2.5), (5, 1, top + 2.5), (0.6, 0, top), (0, 0, top - 4), (0, 0, nz_z + 1)]
    sp.points.add(len(pts) - 1)
    for p, c in zip(sp.points, pts):
        p.co = (*c, 1)
    sp.order_u = 3; sp.use_endpoint_u = True
    o = bpy.data.objects.new("arch", cu); bl.link(o)
    o.data.materials.append(brass)
    base = bl.cyl(1.7, 1.6, (15, 6, 0.8)); bl.bevel(base, 0.3, 4); bl.smooth(base); bl.assign(base, brass)
    nz = bl.cyl(1.0, 1.0, (0, 0, nz_z + 0.5)); bl.bevel(nz, 0.2, 3); bl.smooth(nz); bl.assign(nz, brass)
    hole = bl.cyl(0.55, 0.1, (0, 0, nz_z - 0.02)); bl.assign(hole, bl.mat("hole", (0.02, 0.02, 0.02), 0.5))
    return (0, 0, nz_z)


def kitchen():
    top = bl.cube((240, 260, 4), (0, -60, -2))
    m = bl.mat("terrazzo", (0.86, 0.85, 0.82), 0.3)
    bl.noise_color(m, (0.7, 0.68, 0.64), (0.92, 0.91, 0.88), scale=40, detail=2, lo=0.45, hi=0.5)
    bl.assign(top, m)
    # タイルの壁
    wall = bl.plane((200, 120), (0, 32, 60), rot=(90, 0, 0))
    wm = bl.mat("tile", (0.72, 0.84, 0.78), 0.12)
    N, L, b = bl.nodes(wm)
    tc = N.new("ShaderNodeTexCoord"); br = N.new("ShaderNodeTexBrick")
    br.inputs["Scale"].default_value = 7; br.inputs["Mortar Size"].default_value = 0.012
    br.inputs["Color1"].default_value = (0.72, 0.84, 0.78, 1); br.inputs["Color2"].default_value = (0.68, 0.8, 0.75, 1)
    br.inputs["Mortar"].default_value = (0.6, 0.6, 0.58, 1)
    br.offset = 0.5; br.squash = 1.0
    mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1 / 15, 1 / 15, 1); mp.inputs["Location"].default_value = (0.21, 0, 0)
    L.new(tc.outputs["Object"], mp.inputs["Vector"]); L.new(mp.outputs["Vector"], br.inputs["Vector"])
    L.new(br.outputs["Color"], b.inputs["Base Color"])
    bp = N.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.4
    L.new(br.outputs["Fac"], bp.inputs["Height"]); L.new(bp.outputs["Normal"], b.inputs["Normal"])
    bl.assign(wall, wm)
    # 観葉植物っぽい緑のボケ（左奥）
    for i, (x, z, r) in enumerate([(-30, 30, 6), (-36, 22, 5), (-24, 40, 4), (-40, 36, 5)]):
        s = bl.sphere(r, (x, 26, z)); s.scale = (1, 0.4, 1.3)
        bl.assign(s, bl.mat(f"leaf{i}", (0.15, 0.32, 0.12), 0.5))
    # 右奥のびん
    jar = bl.cyl(4, 14, (26, 22, 7)); bl.smooth(jar); bl.bevel(jar, 0.6, 4)
    bl.assign(jar, bl.mat("jar", (0.75, 0.6, 0.35), 0.1, Transmission_Weight=0.7))


def lights():
    bl.world((0.85, 0.88, 0.92), 0.6)
    bl.light('AREA', (-40, -10, 40), 60000, rot_deg=(15, -55, 0), size=40, color=(1, 0.95, 0.88))
    bl.light('AREA', (30, -40, 20), 9000, rot_deg=(70, 0, 40), size=30, color=(0.85, 0.9, 1))
    bl.light('AREA', (0, 30, 30), 6000, rot_deg=(-70, 0, 0), size=20, color=(1, 1, 1))  # 逆光


def setup_cam(rim):
    cam = bl.camera((0, -80, rim), rot_deg=(90, 0, 0), lens=70)
    cam.data.sensor_fit = 'VERTICAL'; cam.data.sensor_height = 24
    cam.data.shift_y = -0.08
    cam.data.dof.use_dof = True; cam.data.dof.focus_distance = 80; cam.data.dof.aperture_fstop = 2.8
    return cam


def proj(sc, cam, p):
    v = world_to_camera_view(sc, cam, mathutils.Vector(p))
    return [round(v.x * 720, 1), round((1 - v.y) * 1080, 1)]


geo = {}
for g in GLASSES:
    sc = bl.reset()
    sc.view_settings.exposure = 0.15
    kitchen(); lights()
    glass_obj(g)
    rim = GLASSES[g]["prof"][-1][0]
    nozzle = faucet(rim + 8.5)
    cam = setup_cam(rim)
    bl.render(os.path.join(OUT, f"bg_{g}.png"), 1080, 1620, samples=S)
    # 内側の輪郭を画面座標で
    prof = GLASSES[g]["prof"]
    inner = []
    zs = [prof[0][0] + (rim - prof[0][0]) * k / 40 for k in range(41)]
    for z in zs:
        r = next(r0 + (r1 - r0) * (z - z0) / (z1 - z0) for (z0, r0), (z1, r1) in zip(prof, prof[1:]) if z0 <= z <= z1 + 1e-6)
        inner.append([proj(sc, cam, (-r, 0, z))[0], proj(sc, cam, (r, 0, z))[0], proj(sc, cam, (0, 0, z))[1], round(r, 3), round(z, 3)])
    px_cm = proj(sc, cam, (1, 0, rim))[0] - proj(sc, cam, (0, 0, rim))[0]
    geo[g] = {"inner": inner, "nozzle": proj(sc, cam, nozzle), "pxcm": round(px_cm, 2), "outerTop": proj(sc, cam, (prof[-1][1] + GLASSES[g]["wall"], 0, rim))[0],
              "table": proj(sc, cam, (0, -4, 0))[1]}
    # つやだけ
    for o in list(bpy.data.objects):
        if o.name != g and o.type in ('MESH', 'CURVE'):
            o.hide_render = True
    gl = bpy.data.objects[g]
    gl.hide_render = False
    m = bpy.data.materials.new("gloss"); m.use_nodes = True
    N, L = m.node_tree.nodes, m.node_tree.links
    N.remove(N["Principled BSDF"]); gs = N.new("ShaderNodeBsdfGlossy"); gs.inputs["Roughness"].default_value = 0.03
    fr = N.new("ShaderNodeFresnel"); fr.inputs["IOR"].default_value = 1.5
    em = N.new("ShaderNodeMixShader"); tr = N.new("ShaderNodeBsdfTransparent")
    L.new(fr.outputs[0], em.inputs["Fac"]); L.new(tr.outputs[0], em.inputs[1]); L.new(gs.outputs[0], em.inputs[2])
    L.new(em.outputs[0], N["Material Output"].inputs[0])
    bl.assign(gl, m)
    sc.world.node_tree.nodes["Background"].inputs[1].default_value = 0.0
    bl.render(os.path.join(OUT, f"hl_{g}.png"), 1080, 1620, samples=S, transparent=True)
json.dump(geo, open(os.path.join(OUT, "geo.json"), "w"))
print("done")
