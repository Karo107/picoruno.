"""テープのはし：素材レンダリング。

out/scene.png  引っ越し部屋の床に立てたテープのロール（ゲーム座標 x:-120〜840, y:0〜1080 を 1.5 倍で）
out/box0.png   ふたが開いた段ボール（透過）
out/box1.png   テープで閉じた段ボール（透過）
ロールの軸は X。カメラは -Y 側から見る。1 = 1cm。
"""
import math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "common"))
import bpy
import bl

OUT = os.path.join(os.path.dirname(__file__), "out")
os.makedirs(OUT, exist_ok=True)
FAST = "--fast" in sys.argv
S = 24 if FAST else 160


def kraft(name, c=(0.55, 0.38, 0.22)):
    m = bl.mat(name, c, 0.8)
    bl.noise_color(m, (c[0] * 0.86, c[1] * 0.84, c[2] * 0.82), (c[0] * 1.06, c[1] * 1.06, c[2] * 1.05), scale=18, detail=10)
    bl.noise_bump(m, 120, 0.12, 8)
    return m


def amber_tape(name="tape"):
    m = bl.mat(name, (1.0, 0.78, 0.42), 0.06, Transmission_Weight=1.0, IOR=1.45)
    return m


def box(x, y, z, sx, sy, sz, rot=0, taped=False, open_=False, name="box"):
    parts = []
    m = kraft(name + "m")
    b = bl.cube((sx, sy, sz), (0, 0, sz / 2))
    bl.bevel(b, 0.25, 3)
    bl.assign(b, m)
    parts.append(b)
    # 天面の合わせ目
    seam = bl.cube((sx * 1.002, 0.12, 0.05), (0, 0, sz + 0.005))
    bl.assign(seam, bl.mat(name + "seam", (0.18, 0.12, 0.07), 0.9))
    parts.append(seam)
    if open_:
        seam.hide_render = True
        for sgn in (-1, 1):
            d, al = sy / 2, math.radians(35)
            f = bl.cube((sx * 0.98, d, 0.3), (0, 0, 0))
            bl.bevel(f, 0.1, 2)
            bl.assign(f, m)
            f.location = (0, sgn * (sy / 2 + math.sin(al) * d / 2), sz + math.cos(al) * d / 2)
            f.rotation_euler = (sgn * (math.pi / 2 - al), 0, 0)
            parts.append(f)
        hole = bl.cube((sx * 0.94, sy * 0.94, 0.2), (0, 0, sz - 0.05))
        bl.assign(hole, bl.mat(name + "dark", (0.08, 0.05, 0.03), 1))
        parts.append(hole)
    if taped:
        t = bl.cube((sx + 0.6, 5.0, 0.04), (0, 0, sz + 0.03))
        bl.assign(t, bl.mat(name + "tp", (0.85, 0.62, 0.32), 0.12, Transmission_Weight=0.6))
        parts.append(t)
        for sgn in (-1, 1):
            t2 = bl.cube((0.04, 5.0, 6), (sgn * (sx / 2 + 0.03), 0, sz - 3))
            bl.assign(t2, bl.mat(name + "tp2", (0.85, 0.62, 0.32), 0.12, Transmission_Weight=0.6))
            parts.append(t2)
    e = bpy.data.objects.new(name, None)
    bl.link(e)
    for p in parts:
        p.parent = e
    e.location = (x, y, z)
    e.rotation_euler = (0, 0, math.radians(rot))
    return e


def roll(x=0, y=0, z=5.2):
    R, r, W = 5.0, 3.85, 5.0
    t = bl.cyl(R, W, (0, 0, 0), rotation=(0, math.radians(90), 0), verts=160)
    hole = bl.cyl(r, W + 1, (0, 0, 0), rotation=(0, math.radians(90), 0), verts=160)
    bo = t.modifiers.new("b", 'BOOLEAN'); bo.object = hole; bo.operation = 'DIFFERENCE'
    bpy.context.view_layer.objects.active = t
    bpy.ops.object.modifier_apply(modifier="b")
    bpy.data.objects.remove(hole)
    bl.bevel(t, 0.06, 3)
    bl.smooth(t)
    m = amber_tape()
    # 側面の層（同心円）
    N, L, b = bl.nodes(m)
    tc = N.new("ShaderNodeTexCoord")
    mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (0, 1, 1)
    L.new(tc.outputs["Object"], mp.inputs["Vector"])
    wv = N.new("ShaderNodeTexWave"); wv.wave_type = 'RINGS'; wv.inputs["Scale"].default_value = 3
    wv.inputs["Distortion"].default_value = 0.6
    L.new(mp.outputs["Vector"], wv.inputs["Vector"])
    cr = N.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].color = (0.96, 0.7, 0.36, 1); cr.color_ramp.elements[1].color = (1.0, 0.82, 0.5, 1)
    L.new(wv.outputs["Fac"], cr.inputs["Fac"]); L.new(cr.outputs["Color"], b.inputs["Base Color"])
    bl.assign(t, m)
    # 白っぽい不透明の層（テープの接着面の曇り）
    core = bl.cyl(r, W, (0, 0, 0), rotation=(0, math.radians(90), 0), verts=160)
    hole2 = bl.cyl(r - 0.38, W + 1, (0, 0, 0), rotation=(0, math.radians(90), 0), verts=160)
    bo = core.modifiers.new("b", 'BOOLEAN'); bo.object = hole2; bo.operation = 'DIFFERENCE'
    bpy.context.view_layer.objects.active = core
    bpy.ops.object.modifier_apply(modifier="b")
    bpy.data.objects.remove(hole2)
    bl.bevel(core, 0.04, 2)
    bl.smooth(core)
    km = kraft("core", (0.82, 0.74, 0.6))
    bl.assign(core, km)
    e = bpy.data.objects.new("roll", None)
    bl.link(e)
    t.parent = e; core.parent = e
    e.location = (x, y, z)
    return e


def room():
    floor = bl.plane((200, 200), (0, 0, 0))
    bl.assign(floor, bl.wood("floor", light=(0.62, 0.45, 0.3), dark=(0.42, 0.28, 0.17), scale=0.15, rough=0.35, bump=0.04))
    wall = bl.plane((200, 120), (0, 60, 60), rot=(90, 0, 0))
    wm = bl.mat("wall", (0.86, 0.84, 0.8), 0.9)
    bl.noise_bump(wm, 60, 0.04)
    bl.assign(wall, wm)
    # 奥の段ボールの山
    box(-26, 40, 0, 34, 26, 26, rot=8, taped=True, name="b1")
    box(-22, 42, 26, 28, 22, 20, rot=-4, taped=True, name="b2")
    box(18, 38, 0, 30, 30, 30, rot=-10, taped=False, open_=True, name="b3")
    box(40, 26, 0, 24, 20, 18, rot=24, taped=True, name="b4")
    box(-48, 20, 0, 22, 22, 22, rot=-18, taped=True, name="b5")


def lights():
    bl.world((0.95, 0.92, 0.88), 0.45)
    bl.light('AREA', (-60, -20, 60), 90000, rot_deg=(20, -50, 0), size=40, color=(1, 0.93, 0.82))
    bl.light('AREA', (40, -50, 30), 15000, rot_deg=(60, 30, 0), size=30, color=(0.8, 0.88, 1))
    bl.light('AREA', (0, 10, 30), 4000, rot_deg=(-60, 0, 0), size=20, color=(1, 0.9, 0.8))  # ロールの縁を光らせる


# ---------- 1) メインの場面 ----------
sc = bl.reset()
sc.view_settings.exposure = 0.2
room()
lights()
roll(0, 0, 5.05)
cam = bl.camera((7, -33, 10.5), rot_deg=(80, 0, 12), lens=40)
cam.data.sensor_fit = 'VERTICAL'
cam.data.sensor_height = 24
cam.data.dof.use_dof = True
cam.data.dof.focus_distance = 33.5
cam.data.dof.aperture_fstop = 2.0
bl.render(os.path.join(OUT, "scene.png"), 1440, 1620, samples=S)
# ロール表面の点が画面のどこに来るか（ゲーム側の 720x1080 座標）を書き出す
import json
import mathutils
from bpy_extras.object_utils import world_to_camera_view
sc.render.resolution_percentage = 100
proj = []
for deg in range(0, 360, 5):
    a = math.radians(deg)
    row = []
    for x in (-2.5, 0, 2.5):
        # 角度 0 = カメラに一番近い面（-Y 側）、正の向き = 上へまわる
        p = mathutils.Vector((x, -5.0 * math.cos(a), 5.05 + 5.0 * math.sin(a)))
        v = world_to_camera_view(sc, cam, p)
        row.append([round(v.x * 960 - 120, 1), round((1 - v.y) * 1080, 1)])
    proj.append(row)
json.dump(proj, open(os.path.join(OUT, "proj.json"), "w"))

# ---------- 2) 段ボール（ひらいた／とじた） ----------
for i, (taped, open_) in enumerate([(False, True), (True, False)]):
    sc = bl.reset()
    sc.view_settings.exposure = 0.2
    bl.world((0.95, 0.92, 0.88), 0.6)
    bl.light('AREA', (-40, -30, 60), 60000, rot_deg=(30, -35, 0), size=40, color=(1, 0.94, 0.85))
    bl.light('AREA', (40, -30, 20), 8000, rot_deg=(60, 40, 0), size=30, color=(0.8, 0.88, 1))
    bl.shadow_catcher(200, 0)
    box(0, 0, 0, 30, 24, 22, rot=-28, taped=taped, open_=open_, name="bx")
    bl.camera((48, -62, 52), rot_deg=(55, 0, 38), lens=38)
    bl.render(os.path.join(OUT, f"box{i}.png"), 700, 700, samples=S, transparent=True)
print("done")
