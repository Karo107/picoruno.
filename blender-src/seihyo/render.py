"""製氷皿ひとふで：素材レンダリング。

ステンレスのシンクを斜め上から。上から蛇口が下りてきて、水はゲーム側で描く。
out/bg.png    シンクと蛇口（製氷皿なし）
out/tray.png  製氷皿（影つき・背景は透明）。ゲームの中で動かす
out/geo.json  16マスの四すみ（底・仕切りの高さ・ふちの高さ）の画面位置と、水の落ちる点
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

# 製氷皿の寸法
TW, TL, TH = 11.0, 26.0, 3.0      # 外の幅・長さ・高さ
WALL, DIV, FLOOR = 0.35, 0.3, 0.35
DIVH = 2.35                      # 仕切りの高さ（ふちより低い）
COLS, ROWS = 2, 8
TRAY_Y = -3.0                    # 置いたときの中心
cw = (TW - 2 * WALL - (COLS - 1) * DIV) / COLS
ch = (TL - 2 * WALL - (ROWS - 1) * DIV) / ROWS
NOZ = (0, 9.5, 24.0)             # 蛇口の口


def boolean(obj, cutter, op='DIFFERENCE'):
    m = obj.modifiers.new("b", 'BOOLEAN'); m.object = cutter; m.operation = op; m.solver = 'EXACT'
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.data.objects.remove(cutter, do_unlink=True)


def cell_rect(c, r):
    x0 = -TW / 2 + WALL + c * (cw + DIV); y0 = TRAY_Y - TL / 2 + WALL + r * (ch + DIV)
    return x0, y0, x0 + cw, y0 + ch


def tray():
    t = bl.cube((TW, TL, TH), (0, TRAY_Y, TH / 2))
    for c in range(COLS):
        for r in range(ROWS):
            x0, y0, x1, y1 = cell_rect(c, r)
            k = bl.cube((x1 - x0, y1 - y0, TH), ((x0 + x1) / 2, (y0 + y1) / 2, FLOOR + TH / 2))
            bl.bevel(k, 0.5, 4)
            bpy.context.view_layer.objects.active = k; bpy.ops.object.modifier_apply(modifier="bevel")
            boolean(t, k)
    slab = bl.cube((TW - 2 * WALL, TL - 2 * WALL, 2), (0, TRAY_Y, DIVH + 1))
    boolean(t, slab)
    bl.bevel(t, 0.12, 3)
    m = bl.mat("plastic", (0.42, 0.78, 0.68), 0.3, Subsurface_Weight=0.3, Subsurface_Radius=(0.4, 0.6, 0.5), Coat_Weight=0.4)
    bl.assign(t, m)
    return t


def sink():
    steel = bl.mat("steel", (0.78, 0.78, 0.8), 0.32, 1.0)
    bl.noise_color(steel, (0.62, 0.62, 0.64), (0.82, 0.82, 0.84), scale=0.08, detail=6)
    bl.noise_bump(steel, scale=3, strength=0.05)
    block = bl.cube((140, 140, 24), (0, 0, 10))
    basin = bl.cube((46, 56, 40), (0, 2, 20 + 0.0))
    bl.bevel(basin, 5, 10)
    bpy.context.view_layer.objects.active = basin; bpy.ops.object.modifier_apply(modifier="bevel")
    boolean(block, basin)
    bl.assign(block, steel)
    # 排水口
    ring = bl.cyl(5.5, 0.6, (13, 20, 0.1)); bl.assign(ring, bl.mat("ring", (0.7, 0.7, 0.72), 0.2, 1.0)); bl.bevel(ring, 0.25, 3)
    hole = bl.cyl(4.6, 0.2, (13, 20, 0.45)); bl.assign(hole, bl.mat("plate", (0.72, 0.72, 0.74), 0.25, 1.0))
    dark = bl.mat("holes", (0.0, 0.0, 0.0), 0.6)
    for rad, n in ((1.2, 8), (2.2, 14), (3.2, 20), (4.1, 26)):
        for i in range(n):
            a = i / n * 6.283
            h = bl.cyl(0.22, 0.1, (13 + rad * math.cos(a), 20 + rad * math.sin(a), 0.56), verts=12); bl.assign(h, dark)
    # 水滴（シンクの底にぽつぽつ）
    wat = bl.mat("drop", (0.9, 0.95, 1.0), 0.02, IOR=1.33, Transmission_Weight=1.0)
    import random
    rr = random.Random(5)
    for i in range(40):
        x, y = rr.uniform(-21, 21), rr.uniform(-24, 26)
        if (x - 13) ** 2 + (y - 20) ** 2 < 40: continue
        d = bl.sphere(rr.uniform(0.15, 0.45), (x, y, 0)); d.scale = (1, rr.uniform(0.8, 1.3), 0.45); bl.assign(d, wat)
    # 水のしずくのあと（すこしだけ）
    # 蛇口：奥から上に立ち上がり、口が真下を向くグースネック
    chrome = bl.mat("chrome", (0.9, 0.9, 0.92), 0.08, 1.0)
    cu = bpy.data.curves.new("neck", 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = 1.1; cu.bevel_resolution = 8
    sp = cu.splines.new('NURBS')
    pts = [(0, 34, 20), (0, 34, 46), (0, 31, 54), (0, 22, 56), (0, 13, 50), (0, 9.5, 40), (0, 9.5, NOZ[2] + 0.5)]
    sp.points.add(len(pts) - 1)
    for p, c in zip(sp.points, pts): p.co = (*c, 1)
    sp.order_u = 3; sp.use_endpoint_u = True
    o = bpy.data.objects.new("neck", cu); bl.link(o); o.data.materials.append(chrome)
    nz = bl.cyl(1.35, 1.5, (NOZ[0], NOZ[1], NOZ[2] + 0.75)); bl.bevel(nz, 0.3, 3); bl.smooth(nz); bl.assign(nz, chrome)
    ae = bl.cyl(0.9, 0.1, (NOZ[0], NOZ[1], NOZ[2] - 0.02)); bl.assign(ae, bl.mat("aerator", (0.15, 0.15, 0.16), 0.5, 0.6))
    # 奥のカウンターにスポンジ
    sg = bl.cube((9, 6, 3.5), (-30, 30, 21.75)); bl.bevel(sg, 0.8, 4)
    sm = bl.mat("sponge", (0.95, 0.78, 0.25), 0.9); bl.noise_bump(sm, scale=6, strength=0.6); bl.assign(sg, sm)
    sg2 = bl.cube((9, 6, 1.2), (-30, 30, 20.6)); bl.bevel(sg2, 0.4, 3); bl.assign(sg2, bl.mat("scrub", (0.2, 0.5, 0.25), 0.9))


def lights():
    bl.world((0.85, 0.88, 0.92), 0.7)
    bl.light('AREA', (-30, -20, 80), 160000, rot_deg=(15, -20, 0), size=60, color=(1, 0.96, 0.9))
    bl.light('AREA', (40, 10, 60), 40000, rot_deg=(10, 35, 0), size=40, color=(0.88, 0.92, 1))


def cam_setup(sc):
    cam = bl.camera((0, -42, 100), rot_deg=(24, 0, 0), lens=42)
    cam.data.sensor_fit = 'VERTICAL'; cam.data.sensor_height = 24
    sc.render.resolution_x, sc.render.resolution_y = 1080, 1620
    bpy.context.view_layer.update()
    return cam


def proj(sc, cam, p):
    v = world_to_camera_view(sc, cam, mathutils.Vector(p))
    return [round(v.x * 720, 1), round((1 - v.y) * 1080, 1)]


sc = bl.reset(); sc.view_settings.exposure = -0.25
sink(); lights(); cam = cam_setup(sc)
geo = {"cells": [], "noz": proj(sc, cam, NOZ), "hit": proj(sc, cam, (NOZ[0], NOZ[1], DIVH)), "floor": proj(sc, cam, (NOZ[0], NOZ[1], 0)),
       "rows": ROWS, "cols": COLS}
for r in range(ROWS):
    for c in range(COLS):
        x0, y0, x1, y1 = cell_rect(c, r)
        q = lambda z: [proj(sc, cam, (x, y, z)) for x, y in ((x0, y1), (x1, y1), (x1, y0), (x0, y0))]   # 奥左・奥右・手前右・手前左
        geo["cells"].append({"r": r, "c": c, "bot": q(FLOOR), "div": q(DIVH), "rim": q(TH)})
# 製氷皿を 1cm 動かしたときの画面の動き（ゲームの中で平行移動させる）
o = proj(sc, cam, (0, TRAY_Y, DIVH)); ox = proj(sc, cam, (1, TRAY_Y, DIVH)); oy = proj(sc, cam, (0, TRAY_Y + 1, DIVH))
geo["center"] = o; geo["ex"] = [ox[0] - o[0], ox[1] - o[1]]; geo["ey"] = [oy[0] - o[0], oy[1] - o[1]]
geo["outer"] = [proj(sc, cam, (x, TRAY_Y + y, TH)) for x, y in ((-TW / 2, TL / 2), (TW / 2, TL / 2), (TW / 2, -TL / 2), (-TW / 2, -TL / 2))]
json.dump(geo, open(os.path.join(OUT, "geo.json"), "w"))
print("noz", geo["noz"], "hit", geo["hit"], "center", o)
if "--geo" in sys.argv: sys.exit(0)
bl.render(os.path.join(OUT, "bg.png"), 1080, 1620, samples=S)
# 製氷皿だけ（シンクは影を受ける面だけにする）
for ob in list(sc.objects):
    if ob.type == 'MESH' or ob.type == 'CURVE':
        ob.hide_render = True
t = tray()
catcher = bl.shadow_catcher(200, 0.0)
bl.render(os.path.join(OUT, "tray.png"), 1080, 1620, samples=S, transparent=True)
print("done")
