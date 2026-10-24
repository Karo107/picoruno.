"""ドミノひとふで：素材レンダリング。

木の床を真上から。1 = 1cm。画面は 80x160cm（540x1080 を 1.5 倍で 810x1620）。
out/stage0..2.png  ステージごとの床と障害物（影つき）
out/bell.png       ゴールの呼び鈴（透明。影つき）
out/dom.png        ドミノ 4 色 × たおれる途中 10 コマ（+x へたおれる。透明）
out/geo.json       障害物の当たり（画面座標）、スタートとゴールの位置
"""
import json, math, os, sys, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "common"))
import bpy, bmesh, mathutils
import bl

OUT = os.path.join(os.path.dirname(__file__), "out")
os.makedirs(OUT, exist_ok=True)
FAST = "--fast" in sys.argv
S = 24 if FAST else 128
PART = next((a for a in sys.argv[1:] if not a.startswith("-")), "all")
rr = random.Random(11)
PX = 540 / 80          # 1cm ＝ 6.75（画面の単位）
SUN = (40, 0, -140)   # 左上から


def look(sc, exp=0.0):
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Base Contrast'; sc.view_settings.exposure = exp


def to_px(x, y):
    return [round(270 + x * PX, 1), round(540 - y * PX, 1)]


def floor():
    # フローリング：板を 1 枚ずつ（色と長さをすこしずつ変える）
    w = 12.0
    for i in range(-5, 6):
        x = i * w
        y = -100 - rr.uniform(0, 40)
        while y < 95:
            ln = rr.uniform(45, 90)
            b = bl.cube((w - 0.25, ln - 0.25, 1.5), (x, y + ln / 2, -0.75)); bl.bevel(b, 0.12, 2)
            t = rr.uniform(0, 1)
            m = bl.wood(f"fl{i}_{int(y)}", light=(0.74 - t * 0.12, 0.54 - t * 0.1, 0.34 - t * 0.08), dark=(0.52 - t * 0.1, 0.34 - t * 0.08, 0.2 - t * 0.05), scale=0.12, stretch=18, rough=0.35, bump=0.08)
            b.rotation_euler.z = 0
            # 木目をたて方向に
            N, L, bsdf = bl.nodes(m)
            mp = next(n for n in N if n.type == 'MAPPING'); mp.inputs["Rotation"].default_value = (0, 0, math.radians(90)); mp.inputs["Location"].default_value = (rr.uniform(0, 50), rr.uniform(0, 50), 0)
            bl.assign(b, m)
            y += ln


def books(x, y, rot, n=3):
    cols = [(0.55, 0.15, 0.12), (0.15, 0.3, 0.5), (0.85, 0.75, 0.5), (0.2, 0.4, 0.3)]
    z = 0
    for i in range(n):
        w, d, h = rr.uniform(15, 19), rr.uniform(21, 25), rr.uniform(2, 3.2)
        b = bl.cube((w, d, h), (x + rr.uniform(-1, 1), y + rr.uniform(-1, 1), z + h / 2), rot=(0, 0, rot + rr.uniform(-8, 8))); bl.bevel(b, 0.4, 3)
        bl.assign(b, bl.mat(f"book{i}{x}", cols[(i + int(x)) % 4], 0.6)); z += h
        pg = bl.cube((w - 0.6, d - 1.2, h - 0.7), (b.location.x + 0.4, b.location.y, b.location.z), rot=(0, 0, math.degrees(b.rotation_euler.z))); bl.assign(pg, bl.mat("pages", (0.95, 0.93, 0.86), 0.8))
    return [("rect", x, y, 21, 25, rot)]


def mug(x, y):
    m = bl.cyl(4.2, 9.5, (x, y, 4.75), verts=64); bl.bevel(m, 0.4, 3); bl.assign(m, bl.mat("mug", (0.92, 0.5, 0.35), 0.25))
    t = bl.cyl(3.7, 0.2, (x, y, 9.0), verts=64); bl.assign(t, bl.mat("coffee", (0.18, 0.09, 0.04), 0.1))
    bpy.ops.mesh.primitive_torus_add(major_radius=2.3, minor_radius=0.55, location=(x + 4.8, y, 5), rotation=(math.radians(90), 0, 0)); bl.assign(bl.active(), bpy.data.materials["mug"])
    return [("circle", x, y, 5.0)]


def blocks(x, y, n, rot=0):
    cols = [(0.9, 0.3, 0.25), (0.25, 0.5, 0.85), (0.95, 0.78, 0.2), (0.3, 0.7, 0.4)]
    out = []
    a = math.radians(rot)
    for i in range(n):
        bx, by = x + math.cos(a) * i * 6.2, y + math.sin(a) * i * 6.2
        b = bl.cube((5.6, 5.6, 5.6), (bx, by, 2.8), rot=(0, 0, rot + rr.uniform(-6, 6))); bl.bevel(b, 0.5, 3)
        bl.assign(b, bl.mat(f"blk{i}{x}{y}", cols[i % 4], 0.45))
        if i % 3 == 1:
            t = bl.cube((5.2, 5.2, 5.2), (bx + rr.uniform(-0.4, 0.4), by, 8.4), rot=(0, 0, rot + rr.uniform(-12, 12))); bl.bevel(t, 0.5, 3); bl.assign(t, bl.mat(f"blkt{i}{x}{y}", cols[(i + 2) % 4], 0.45))
        out.append(("circle", bx, by, 4.2))
    return out


def plant(x, y):
    p = bl.cyl(8, 13, (x, y, 6.5), verts=64); bl.bevel(p, 0.8, 3); bl.assign(p, bl.mat("terracotta", (0.72, 0.36, 0.22), 0.8))
    s = bl.cyl(7.2, 0.5, (x, y, 12.6), verts=48); bl.assign(s, bl.mat("soil", (0.2, 0.13, 0.08), 0.95))
    lm = bl.mat("leafp", (0.18, 0.42, 0.16), 0.45, Subsurface_Weight=0.1)
    for i in range(16):
        a = i * 2.4; ln = rr.uniform(8, 15)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(x + math.cos(a) * ln * 0.45, y + math.sin(a) * ln * 0.45, 16 + rr.uniform(0, 8)))
        lf = bl.smooth(bl.active()); lf.scale = (ln * 0.5, 2.4, 0.3); lf.rotation_euler = (0, math.radians(rr.uniform(-30, -5)), a)
        bl.assign(lf, lm)
    return [("circle", x, y, 9.5)]


def slipper(x, y, rot):
    a = math.radians(rot)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(x, y, 1.2)); s = bl.smooth(bl.active()); s.scale = (5, 13, 1.2); s.rotation_euler.z = a
    bl.assign(s, bl.mat("sole", (0.85, 0.82, 0.76), 0.8))
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(x - math.sin(a) * -5, y + math.cos(a) * 5, 2.8)); t = bl.smooth(bl.active()); t.scale = (5.2, 6.5, 2.6); t.rotation_euler.z = a
    m = bl.mat("fleece", (0.55, 0.62, 0.78), 0.95, Sheen_Weight=1.0); bl.noise_bump(m, scale=4, strength=0.3); bl.assign(t, m)
    return [("rect", x, y, 10.5, 26, rot)]


def stool(x, y):
    st = bl.cyl(16, 3, (x, y, 45), verts=96); bl.bevel(st, 1.0, 4); bl.assign(st, bl.wood("stool", light=(0.82, 0.62, 0.4), dark=(0.6, 0.42, 0.25), scale=0.1))
    for k in range(3):
        a = k * 2.094 + 0.3
        l_ = bl.cyl(1.6, 46, (x + math.cos(a) * 11, y + math.sin(a) * 11, 22), verts=24); bl.assign(l_, bpy.data.materials["stool"])
    # 真上から見ると座面しか見えないので、脚の 3 点だけが当たり
    return [("circle", x + math.cos(k * 2.094 + 0.3) * 11, y + math.sin(k * 2.094 + 0.3) * 11, 2.6) for k in range(3)]


def toycar(x, y, rot):
    a = math.radians(rot)
    b = bl.cube((7, 13, 3.4), (x, y, 2.8), rot=(0, 0, rot)); bl.bevel(b, 1.2, 4); bl.assign(b, bl.mat("carred", (0.85, 0.12, 0.1), 0.25))
    c = bl.cube((5.6, 6.5, 2.6), (x - math.sin(a) * -1, y + math.cos(a) * -1, 5.6), rot=(0, 0, rot)); bl.bevel(c, 1.0, 4); bl.assign(c, bl.mat("cabin", (0.85, 0.12, 0.1), 0.25))
    for sx in (-1, 1):
        for sy in (-1, 1):
            wx, wy = 3.6 * sx, 4.2 * sy
            w = bl.cyl(1.6, 1.4, (x + wx * math.cos(a) - wy * math.sin(a), y + wx * math.sin(a) + wy * math.cos(a), 1.6), verts=32)
            w.rotation_euler = (0, math.radians(90), a); bl.assign(w, bl.mat("tire", (0.06, 0.06, 0.06), 0.7))
    return [("rect", x, y, 8.5, 14, rot)]


def ball(x, y):
    b = bl.sphere(6.5, (x, y, 6.5))
    m = bl.mat("ballm", (0.95, 0.85, 0.2), 0.35)
    N, L, bs = bl.nodes(m); wv = N.new("ShaderNodeTexWave"); wv.inputs["Scale"].default_value = 0.5; wv.bands_direction = 'Z'
    tc = N.new("ShaderNodeTexCoord"); L.new(tc.outputs["Object"], wv.inputs["Vector"])
    cr = N.new("ShaderNodeValToRGB"); cr.color_ramp.interpolation = 'CONSTANT'; cr.color_ramp.elements[0].color = (0.95, 0.85, 0.2, 1); cr.color_ramp.elements[1].position = 0.5; cr.color_ramp.elements[1].color = (0.2, 0.45, 0.85, 1)
    L.new(wv.outputs["Fac"], cr.inputs["Fac"]); L.new(cr.outputs["Color"], bs.inputs["Base Color"])
    bl.assign(b, m)
    return [("circle", x, y, 6.8)]


def rug(x, y, w, h):
    r = bl.cube((w, h, 0.6), (x, y, 0.3)); bl.bevel(r, 0.25, 2)
    m = bl.mat("rug", (0.82, 0.78, 0.7), 0.95, Sheen_Weight=1.0)
    N, L, b = bl.nodes(m); tc = N.new("ShaderNodeTexCoord")
    wv = N.new("ShaderNodeTexWave"); wv.inputs["Scale"].default_value = 0.04; wv.bands_direction = 'X'; wv.wave_profile = 'SAW'
    L.new(tc.outputs["Object"], wv.inputs["Vector"])
    cr = N.new("ShaderNodeValToRGB"); cr.color_ramp.interpolation = 'CONSTANT'; cr.color_ramp.elements[0].color = (0.84, 0.8, 0.72, 1); cr.color_ramp.elements[1].position = 0.85; cr.color_ramp.elements[1].color = (0.62, 0.35, 0.3, 1)
    L.new(wv.outputs["Fac"], cr.inputs["Fac"]); L.new(cr.outputs["Color"], b.inputs["Base Color"])
    bl.noise_bump(m, scale=3, strength=0.5)
    bl.assign(r, m)


# ステージ：スタート(位置・向き°)、ゴール(呼び鈴の位置)、障害物
STAGES = [
    {"start": (-24, -46, 90), "goal": (24, 52), "make": lambda: books(2, 2, 12) + mug(-20, 34) + blocks(10, -38, 3, 20)},
    {"start": (0, -48, 90), "goal": (0, 54), "make": lambda: blocks(-12, 8, 6, 0) + plant(24, 30) + toycar(-22, -30, -25) + mug(14, -14) + ball(-26, 42)},
    {"start": (-28, 50, -90), "goal": (26, -46), "make": lambda: (rug(4, -6, 60, 44) or []) + stool(-6, 18) + books(20, -30, -20, 2) + toycar(-20, -36, 35) + blocks(-34, 0, 3, 90) + mug(28, 40)}
]


def scene_base():
    sc = bl.reset(); look(sc, 0.0); sc.view_settings.look = 'AgX - Punchy'
    bl.world((0.9, 0.92, 0.98), 0.4)
    bl.light('SUN', (0, 0, 300), 4.5, rot_deg=SUN, angle=4, color=(1.0, 0.92, 0.8))
    return sc


def top_cam(w_cm=80, h_cm=160):
    cam = bl.camera((0, 0, 300), ortho=h_cm); cam.data.sensor_fit = 'VERTICAL'; cam.data.clip_end = 1000
    return cam


GEO = {}
gp = os.path.join(OUT, "geo.json")
if os.path.exists(gp):
    GEO = json.load(open(gp))

if PART in ("all", "stages"):
    GEO["stages"] = []
    for i, st in enumerate(STAGES):
        sc = scene_base(); rr.seed(100 + i)
        floor(); shapes = st["make"]()
        top_cam()
        bl.render(os.path.join(OUT, f"stage{i}.png"), 810, 1620, samples=S)
        hit = []
        for s_ in shapes:
            if s_[0] == "circle":
                c = to_px(s_[1], s_[2]); hit.append({"t": "c", "x": c[0], "y": c[1], "r": round(s_[3] * PX, 1)})
            else:
                c = to_px(s_[1], s_[2]); hit.append({"t": "r", "x": c[0], "y": c[1], "w": round(s_[3] * PX, 1), "h": round(s_[4] * PX, 1), "a": -s_[5]})
        sx, sy, sa = st["start"]
        GEO["stages"].append({"start": to_px(sx, sy) + [-sa], "goal": to_px(*st["goal"]), "hit": hit})

if PART in ("all", "bell"):
    sc = scene_base()
    base = bl.cyl(4.2, 1.6, (0, 0, 0.8), verts=64); bl.bevel(base, 0.5, 3); bl.assign(base, bl.wood("bellbase", light=(0.4, 0.22, 0.12), dark=(0.25, 0.12, 0.06), scale=0.3, rough=0.3))
    bpy.ops.mesh.primitive_uv_sphere_add(radius=3.6, location=(0, 0, 1.6), segments=64, ring_count=32)
    dome = bl.smooth(bl.active())
    bm = bmesh.new(); bm.from_mesh(dome.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -0.01], context='VERTS'); bm.to_mesh(dome.data); bm.free()
    bl.assign(dome, bl.mat("brassb", (0.95, 0.75, 0.35), 0.12, metal=1.0))
    knob = bl.cyl(0.35, 1.4, (0, 0, 5.6), verts=24); bl.assign(knob, bpy.data.materials["brassb"])
    kb = bl.sphere(0.75, (0, 0, 6.4)); bl.assign(kb, bpy.data.materials["brassb"])
    bl.shadow_catcher(30)
    bpy.ops.object.light_add(type='AREA', location=(-20, 20, 40)); a = bl.active(); a.data.energy = 3000; a.data.size = 30; a.rotation_euler = (math.radians(-30), math.radians(-30), 0)
    cam = bl.camera((0, 0, 100), ortho=16); cam.data.clip_end = 300
    bl.render(os.path.join(OUT, "bell.png"), 216, 216, samples=S, transparent=True)
    GEO["bell"] = {"size": round(16 * PX, 1)}

DW, DT, DH = 2.4, 0.9, 4.8       # ドミノ：はば・あつみ・高さ
ANG = [0, 10, 20, 30, 40, 50, 60, 70, 80, 89]
CELL = (7.0, 3.6)                # 1 コマの範囲（cm）。よこ：-1.5〜5.5、たて：±1.8
DPC = 24                         # 1cm ＝ 24px
if PART in ("all", "dom"):
    from PIL import Image
    sc = scene_base()
    cols = [(0.95, 0.93, 0.86), (0.85, 0.2, 0.18), (0.18, 0.4, 0.78), (0.22, 0.6, 0.38)]
    rows = []
    for ci, col in enumerate(cols):
        for o in list(bpy.data.objects):
            if o.type == 'MESH': bpy.data.objects.remove(o)
        piv = bpy.data.objects.new("piv", None); bl.link(piv); piv.location = (DT / 2, 0, 0)
        d = bl.cube((DT, DW, DH), (0, 0, DH / 2)); bl.bevel(d, 0.12, 3)
        bl.assign(d, bl.mat(f"dom{ci}", col, 0.25, Coat_Weight=0.5))
        parts = [d]
        pip = bl.mat("pip", (0.05, 0.05, 0.05) if ci == 0 else (0.97, 0.97, 0.95), 0.3)
        # 目：両面に（たおれると上を向く -x の面がよく見える）
        for side in (-1, 1):
            ln = bl.cube((0.05, DW * 0.75, 0.08), (side * (DT / 2 + 0.005), 0, DH / 2)); bl.assign(ln, pip); parts.append(ln)
            for (py, pz) in ((-0.55, DH * 0.78), (0.55, DH * 0.62), (0, DH * 0.25), (-0.55, DH * 0.12), (0.55, DH * 0.38)):
                p = bl.cyl(0.22, 0.06, (side * (DT / 2 + 0.01), py, pz), verts=16); p.rotation_euler.y = math.radians(90); bl.assign(p, pip); parts.append(p)
        bpy.context.view_layer.update()
        for o in parts:
            o.parent = piv; o.matrix_parent_inverse = piv.matrix_world.inverted()
        cam = bl.camera((2.0, 0, 50), ortho=CELL[0]); cam.data.sensor_fit = 'HORIZONTAL'; cam.data.clip_end = 200
        row = []
        for a in ANG:
            piv.rotation_euler.y = math.radians(a)
            f = os.path.join(OUT, "_d.png")
            bl.render(f, int(CELL[0] * DPC), int(CELL[1] * DPC), samples=S, transparent=True, pct=100)
            row.append(Image.open(f).copy()); os.remove(f)
        rows.append(row)
    cw, ch = rows[0][0].size
    atlas = Image.new("RGBA", (cw * len(ANG), ch * len(cols)))
    for r, row in enumerate(rows):
        for k, im in enumerate(row):
            atlas.paste(im, (k * cw, r * ch))
    atlas.save(os.path.join(OUT, "dom.png"))
    # ピボット（前の下のふち）がコマのどこにあるか：カメラ中心 x=2.0、はば 7cm
    GEO["dom"] = {"cw": cw, "ch": ch, "ang": ANG, "pivx": (DT / 2 - (2.0 - CELL[0] / 2)) / CELL[0], "cellcm": list(CELL), "h": DH, "w": DW, "t": DT, "px": PX}

json.dump(GEO, open(gp, "w"))
print("done")
