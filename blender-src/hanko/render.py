"""ハンコまっすぐ選手権の素材を Blender でレンダリングする。

出力（out/）:
  bg.png     机の俯瞰（1080x1620）。紙は別素材なので中央はあけておく
  paper.png  紙（影つき・透過）
  hanko.png  真上から見たハンコ（透過）
  hero.png   タイトル用：朱肉とハンコの斜めカット
単位は 1 = 1cm。画面は 18cm x 27cm を 60px/cm で描く。
"""
import math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "common"))
import bpy
import bl
import seal
seal.make(os.path.join(os.path.dirname(__file__), "seal_tex.png"))

OUT = os.path.join(os.path.dirname(__file__), "out")
os.makedirs(OUT, exist_ok=True)
FAST = "--fast" in sys.argv
S = 24 if FAST else 128


def desk_scene():
    desk = bl.plane((80, 80), (0, 0, 0))
    bl.assign(desk, bl.wood("desk", light=(0.58, 0.38, 0.23), dark=(0.36, 0.2, 0.11), scale=0.25, rough=0.4, bump=0.05))
    return desk


def sun():
    bl.world((0.95, 0.93, 0.9), 0.35)
    bl.light('SUN', (0, 0, 30), 4.2, rot_deg=(-30, -20, 0), angle=6, color=(1, 0.96, 0.9))
    bl.light('AREA', (-20, 20, 30), 1200, rot_deg=(-30, -30, 0), size=25, color=(0.92, 0.95, 1))


def inkpad(x, y, r=3.4):
    case = bl.cyl(r, 1.1, (x, y, 0.55))
    bl.bevel(case, 0.12, 4)
    bl.smooth(case)
    bl.assign(case, bl.mat("case", (0.03, 0.03, 0.035), 0.2))
    rim = bl.cyl(r * 0.88, 0.2, (x, y, 1.05))
    bl.assign(rim, bl.mat("rimgold", (0.85, 0.65, 0.32), 0.25, 1.0))
    ink = bl.cyl(r * 0.84, 0.2, (x, y, 1.08))
    m = bl.mat("shuniku", (0.62, 0.05, 0.04), 0.75)
    bl.noise_color(m, (0.45, 0.02, 0.02), (0.72, 0.08, 0.05), scale=120, detail=10)
    bl.noise_bump(m, 260, 0.25, 12)
    bl.assign(ink, m)
    return [case, rim, ink]


def yunomi(x, y):
    outer = bl.cyl(3.6, 7, (x, y, 3.5))
    md = outer.modifiers.new("solid", 'SOLIDIFY')
    # 内側をくりぬく
    inner = bl.cyl(3.15, 7, (x, y, 4.1))
    bo = outer.modifiers.new("bool", 'BOOLEAN')
    bo.object = inner
    bo.operation = 'DIFFERENCE'
    outer.modifiers.remove(md)
    bpy.context.view_layer.objects.active = outer
    bpy.ops.object.modifier_apply(modifier="bool")
    bpy.data.objects.remove(inner)
    bl.bevel(outer, 0.15, 4)
    bl.smooth(outer)
    m = bl.mat("glaze", (0.55, 0.6, 0.58), 0.12)
    bl.noise_color(m, (0.36, 0.45, 0.47), (0.75, 0.74, 0.66), scale=3, detail=10, lo=0.3, hi=0.7)
    bl.noise_bump(m, 40, 0.05)
    bl.assign(outer, m)
    tea = bl.cyl(3.16, 0.1, (x, y, 5.9))
    bl.assign(tea, bl.mat("tea", (0.32, 0.36, 0.06), 0.02, Transmission_Weight=0.3))
    return [outer, tea]


def pen(x, y, ang):
    body = bl.cyl(0.55, 13, (0, 0, 0), rotation=(0, math.radians(90), 0))
    bl.smooth(body)
    bl.assign(body, bl.mat("pen", (0.04, 0.08, 0.22), 0.15))
    cap = bl.sphere(0.55, (6.5, 0, 0))
    cap.scale = (1.4, 1, 1)
    bl.assign(cap, bl.mat("pen2", (0.04, 0.08, 0.22), 0.15))
    tip = bl.sphere(0.55, (-6.5, 0, 0))
    tip.scale = (2.0, 0.8, 0.8)
    bl.assign(tip, bl.mat("pen3", (0.04, 0.08, 0.22), 0.15))
    ring = bl.cyl(0.58, 0.5, (2.5, 0, 0), rotation=(0, math.radians(90), 0))
    gold = bl.mat("gold", (0.9, 0.7, 0.35), 0.22, 1.0)
    bl.assign(ring, gold)
    clip = bl.cube((4.2, 0.28, 0.12), (4.4, 0, 0.62))
    bl.bevel(clip, 0.05, 3)
    bl.assign(clip, gold)
    parts = [body, cap, tip, ring, clip]
    empty = bpy.data.objects.new("pen", None)
    bl.link(empty)
    for p in parts:
        p.parent = empty
    empty.location = (x, y, 0.58)
    empty.rotation_euler = (0, 0, math.radians(ang))
    return parts


def fusen(x, y, ang):
    objs = []
    cols = [(0.98, 0.82, 0.35), (0.96, 0.62, 0.62), (0.6, 0.8, 0.9)]
    for i, c in enumerate(cols):
        f = bl.cube((5.0, 5.0, 0.6), (x + i * 0.25, y - i * 0.2, 0.3 + i * 0.6), rot=(0, 0, ang + i * 6))
        bl.bevel(f, 0.03, 2)
        m = bl.mat(f"fusen{i}", c, 0.7)
        bl.noise_bump(m, 300, 0.05)
        bl.assign(f, m)
        objs.append(f)
    return objs


def hanko(x=0, y=0, z=0, rot=(0, 0, 0)):
    """柘（つげ）のハンコ。アタリ（向きの目印）は +Y 側の天面の赤い点。"""
    body = bl.cyl(1.3, 5.6, (0, 0, 2.8))
    bl.bevel(body, 0.08, 4)
    bl.smooth(body)
    m = bl.wood("tsuge", light=(0.92, 0.70, 0.38), dark=(0.78, 0.52, 0.26), scale=1.2, rough=0.25, bump=0.01, stretch=10, rings=0.15)
    bl.assign(body, m)
    top = bl.sphere(1.12, (0, 0, 5.6))
    top.scale = (1, 1, 0.42)
    bl.assign(top, m)
    band = bl.cyl(1.32, 0.18, (0, 0, 5.2))
    bl.assign(band, bl.mat("band", (0.12, 0.08, 0.06), 0.3))
    dot = bl.sphere(0.2, (0, 0.72, 5.94))
    dot.scale = (1, 1, 0.5)
    bl.assign(dot, bl.mat("atari", (0.75, 0.08, 0.06), 0.3))
    face = bl.cyl(1.25, 0.06, (0, 0, 0.03))
    bl.assign(face, bl.mat("face", (0.55, 0.04, 0.03), 0.8))
    parts = [body, top, band, dot, face]
    e = bpy.data.objects.new("hanko", None)
    bl.link(e)
    for p in parts:
        p.parent = e
    e.location = (x, y, z)
    e.rotation_euler = [math.radians(a) for a in rot]
    return parts, e


# ---------- 1) 机 ----------
sc = bl.reset()
sc.view_settings.exposure = 0.35
desk_scene()
sun()
inkpad(-7.2, -11.2)
yunomi(7.6, 11.6)
pen(8.6, -5.0, 78)
fusen(-8.0, 11.2, 12)
bl.camera((0, 0, 60), ortho=27)
bl.render(os.path.join(OUT, "bg.png"), 1080, 1620, samples=S)

# ---------- 2) 紙（影つき・透過） ----------
sc = bl.reset()
sc.view_settings.exposure = 0.35
sun()
bl.shadow_catcher(80, 0)
paper = bl.plane((15, 21), (0, 0, 0.25))
sub = paper.modifiers.new("sub", "SUBSURF")
sub.subdivision_type = 'SIMPLE'
sub.levels = sub.render_levels = 6
disp_tex = bpy.data.textures.new("curl", 'CLOUDS')
disp_tex.noise_scale = 1.2
dp = paper.modifiers.new("disp", 'DISPLACE')
dp.texture = disp_tex
dp.strength = 0.12
pm = bl.mat("paper", (0.93, 0.91, 0.86), 0.85)
bl.noise_color(pm, (0.90, 0.87, 0.81), (0.96, 0.94, 0.90), scale=40, detail=12)
bl.noise_bump(pm, 400, 0.06, 12)
bl.assign(paper, pm)
bl.camera((0, 0, 60), ortho=24)
bl.render(os.path.join(OUT, "paper.png"), 1080, 1440, samples=S, transparent=True)

# ---------- 3) 真上から見たハンコ ----------
sc = bl.reset()
bl.world((0.95, 0.93, 0.9), 0.5)
bl.light('AREA', (-6, 6, 20), 2600, rot_deg=(-18, -18, 0), size=8, color=(1, 0.96, 0.9))
bl.light('AREA', (8, -4, 12), 500, rot_deg=(20, 35, 0), size=6, color=(0.9, 0.95, 1))
hanko()
bl.camera((0, 0, 20), lens=100)
bl.render(os.path.join(OUT, "hanko.png"), 420, 420, samples=S, transparent=True)

# ---------- 4) タイトル用ヒーロー ----------
sc = bl.reset()
desk_scene()
bl.world((0.95, 0.93, 0.9), 0.4)
bl.light('AREA', (-10, -6, 18), 4000, rot_deg=(25, -35, 0), size=14, color=(1, 0.95, 0.88))
bl.light('AREA', (10, 8, 10), 900, rot_deg=(-40, 40, 0), size=10, color=(0.85, 0.92, 1))
inkpad(-3.2, 1.0)
hanko(5.6, 2.2, 0, rot=(0, 0, 20))
# 押したあとの印影っぽい紙
pp = bl.plane((14, 10), (4, -3, 0.02), rot=(0, 0, -8))
pm2 = bl.noise_bump(bl.mat("paper2", (0.93, 0.91, 0.86), 0.85), 400, 0.06)
N, L, b = bl.nodes(pm2)
tx = N.new("ShaderNodeTexImage")
tx.image = bpy.data.images.load(os.path.join(os.path.dirname(__file__), "seal_tex.png"))
tx.extension = 'CLIP'
L.new(tx.outputs["Color"], b.inputs["Base Color"])
bl.assign(pp, pm2)
cam = bl.camera((0, -19, 15), rot_deg=(52, 0, 0), lens=55)
sc.cycles.use_denoising = True
cam.data.dof.use_dof = True
cam.data.dof.focus_distance = 23
cam.data.dof.aperture_fstop = 2.8
bl.render(os.path.join(OUT, "hero.png"), 900, 900, samples=S)
print("done")
