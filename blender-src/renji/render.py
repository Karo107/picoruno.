"""レンジ何秒？：素材レンダリング。

台所のカウンターに電子レンジ。正面から少し見おろす。1 = 1cm。
out/bg.png       台所とレンジ（扉なし、庫内灯は消えている）
out/lit.png      庫内灯がついた庫内だけ（bg に重ねる。geo.lit の範囲）
out/door.png     閉じた扉だけ（窓はすけている）
out/food.png     食べもの 6 種 × 8 コマ（ターンテーブルでまわる）＋ 温めすぎ 1 コマ。よこ 9 マス × たて 6 段
out/geo.json
540x1080 を 1.5 倍。
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
PART = next((a for a in sys.argv[1:] if not a.startswith("-")), "all")
rr = random.Random(5)
RX, RY = 810, 1620

# レンジの寸法
MW, MH, MD = 50, 29, 38          # 外形
CX0, CX1, CZ0, CZ1 = -22.5, 9.5, 3.2, 25.5   # 庫内（正面から見た穴）
FY = -MD / 2                     # 正面の y
TT = (-6.5, -1.0, CZ0 + 1.0)     # ターンテーブルの中心（上面）


def look(sc, exp=0.0):
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Base Contrast'; sc.view_settings.exposure = exp


def rounded_box(size, loc, r, segs=4, name=None):
    o = bl.cube(size, loc); bl.bevel(o, r, segs); return o


def tiles_mat():
    m = bl.mat("tile", (0.92, 0.92, 0.9), 0.2)
    N, L, b = bl.nodes(m)
    tc = N.new("ShaderNodeTexCoord")
    br = N.new("ShaderNodeTexBrick"); br.inputs["Scale"].default_value = 1.0
    br.inputs["Mortar Size"].default_value = 0.012; br.inputs["Brick Width"].default_value = 0.15; br.inputs["Row Height"].default_value = 0.075
    br.offset = 0.5
    br.inputs["Color1"].default_value = (0.93, 0.93, 0.91, 1); br.inputs["Color2"].default_value = (0.88, 0.89, 0.88, 1); br.inputs["Mortar"].default_value = (0.7, 0.69, 0.66, 1)
    mp = N.new("ShaderNodeMapping"); mp.inputs["Rotation"].default_value = (math.radians(90), 0, 0); mp.inputs["Scale"].default_value = (0.01, 0.01, 0.01)
    L.new(tc.outputs["Object"], mp.inputs["Vector"]); L.new(mp.outputs["Vector"], br.inputs["Vector"])
    L.new(br.outputs["Color"], b.inputs["Base Color"])
    bp = N.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.4; bp.invert = True
    L.new(br.outputs["Fac"], bp.inputs["Height"]); L.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def kitchen():
    objs = []
    # かべ（白いタイル）
    w = bl.cube((400, 4, 260), (0, 40, 100)); bl.assign(w, tiles_mat()); objs.append(w)
    # カウンター（木）
    ct = bl.cube((400, 90, 4), (0, -5, -2)); bl.bevel(ct, 0.6, 3)
    bl.assign(ct, bl.wood("counter", light=(0.72, 0.52, 0.32), dark=(0.5, 0.33, 0.18), scale=0.06, rough=0.4)); objs.append(ct)
    # 下の戸棚
    cb = bl.cube((400, 4, 90), (0, -48, -50)); bl.assign(cb, bl.mat("cab", (0.82, 0.8, 0.74), 0.5)); objs.append(cb)
    for x in (-60, 0, 60):
        dr = bl.cube((58, 1, 80), (x, -50.5, -48)); bl.bevel(dr, 0.6, 3); bl.assign(dr, bl.mat(f"door{x}", (0.86, 0.84, 0.78), 0.45)); objs.append(dr)
        hd = bl.cube((14, 2, 1.4), (x, -52, -12)); bl.bevel(hd, 0.5, 3); bl.assign(hd, bl.mat("brass", (0.75, 0.58, 0.3), 0.25, metal=1.0)); objs.append(hd)
    # 上のたな（びん・観葉植物）
    sh = bl.cube((200, 22, 2.5), (0, 29, 66)); bl.assign(sh, bl.wood("shelf", scale=0.08)); objs.append(sh)
    jars = [(-36, (0.95, 0.6, 0.2)), (-24, (0.6, 0.35, 0.15)), (-12, (0.98, 0.95, 0.85))]
    for x, col in jars:
        j = bl.cyl(4.5, 13, (x, 29, 74), verts=48); bl.assign(j, bl.mat(f"jar{x}", (0.95, 0.97, 1), 0.05, Transmission_Weight=1.0)); objs.append(j)
        c = bl.cyl(4.0, 9, (x, 29, 72), verts=48); bl.assign(c, bl.mat(f"in{x}", col, 0.7)); objs.append(c)
        lid = bl.cyl(4.7, 2, (x, 29, 81.5), verts=48); bl.bevel(lid, 0.4, 2); bl.assign(lid, bl.wood(f"lid{x}", scale=0.2)); objs.append(lid)
    pot = bl.cyl(6, 10, (22, 29, 72), verts=48); bl.bevel(pot, 0.8, 3); bl.assign(pot, bl.mat("pot", (0.85, 0.5, 0.35), 0.7)); objs.append(pot)
    lm = bl.mat("leaf", (0.2, 0.45, 0.18), 0.5, Subsurface_Weight=0.2)
    for i in range(14):
        a = i * 2.4; ln = rr.uniform(9, 15)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(22 + math.cos(a) * ln * 0.35, 29 + math.sin(a) * ln * 0.3, 78 + ln * 0.35))
        lf = bl.smooth(bl.active()); lf.scale = (ln * 0.35, 1.6, 0.25); lf.rotation_euler = (0, math.radians(-40 + rr.uniform(-20, 20)), a)
        bl.assign(lf, lm); objs.append(lf)
    # カウンターの上：まな板とふきん（すみに少しだけ）
    bd = bl.cube((34, 24, 2), (-44, -40, 1)); bl.bevel(bd, 0.8, 3); bd.rotation_euler.z = math.radians(8); bl.assign(bd, bl.wood("board", light=(0.85, 0.7, 0.48), dark=(0.7, 0.55, 0.35), scale=0.1)); objs.append(bd)
    tw = bl.cube((22, 16, 1.2), (44, -42, 0.6)); bl.bevel(tw, 0.5, 3); tw.rotation_euler.z = math.radians(-12)
    m = bl.mat("towel", (0.9, 0.9, 0.86), 0.9, Sheen_Weight=0.6)
    N, L, b = bl.nodes(m); ck = N.new("ShaderNodeTexChecker"); ck.inputs["Scale"].default_value = 0.4
    ck.inputs["Color1"].default_value = (0.9, 0.9, 0.86, 1); ck.inputs["Color2"].default_value = (0.35, 0.5, 0.72, 1)
    tc = N.new("ShaderNodeTexCoord"); L.new(tc.outputs["Object"], ck.inputs["Vector"]); L.new(ck.outputs["Color"], b.inputs["Base Color"])
    bl.assign(tw, m); objs.append(tw)
    return objs


def microwave():
    body, inner = [], []
    wm = bl.mat("mwbody", (0.9, 0.9, 0.88), 0.35)
    # 外箱：上・下・左右・背中を板で（庫内を空けるため）
    for (sx, sy, sz, x, y, z) in ((MW, MD, 2.5, 0, 0, MH - 1.25), (MW, MD, 3, 0, 0, 1.5), (2.2, MD, MH - 5.5, -MW / 2 + 1.1, 0, MH / 2 + 0.25),
                                   (MW / 2 - CX1 - 0.5, MD, MH - 5.5, (CX1 + 0.5 + MW / 2) / 2, 0, MH / 2 + 0.25), (MW, 2, MH - 5.5, 0, MD / 2 - 1, MH / 2 + 0.25)):
        o = bl.cube((sx, sy, sz), (x, y, z)); bl.bevel(o, 0.8, 3); bl.assign(o, wm); body.append(o)
    # 足
    for x in (-MW / 2 + 4, MW / 2 - 4):
        for y in (-MD / 2 + 4, MD / 2 - 4):
            f = bl.cyl(1.4, 1.0, (x, y, -0.3), verts=24); bl.assign(f, bl.mat("foot", (0.1, 0.1, 0.1), 0.6)); body.append(f)
    # 庫内（明るいグレーのほうろう）
    em = bl.mat("enamel", (0.78, 0.78, 0.76), 0.45)
    for (sx, sy, sz, x, y, z) in ((CX1 - CX0, MD - 3, 0.4, (CX0 + CX1) / 2, 0.5, CZ0), (CX1 - CX0, MD - 3, 0.4, (CX0 + CX1) / 2, 0.5, CZ1),
                                   (0.4, MD - 3, CZ1 - CZ0, CX0, 0.5, (CZ0 + CZ1) / 2), (0.4, MD - 3, CZ1 - CZ0, CX1, 0.5, (CZ0 + CZ1) / 2),
                                   (CX1 - CX0, 0.4, CZ1 - CZ0, (CX0 + CX1) / 2, MD / 2 - 2.2, (CZ0 + CZ1) / 2)):
        o = bl.cube((sx, sy, sz), (x, y, z)); bl.assign(o, em); inner.append(o)
    # 右かべの通気あな
    hm = bl.mat("hole", (0.2, 0.2, 0.2), 0.6)
    for i in range(5):
        for j in range(6):
            h = bl.cyl(0.35, 0.3, (CX1 - 0.25, -2 + j * 1.6, 16 + i * 1.6), verts=12); h.rotation_euler.y = math.radians(90); bl.assign(h, hm); inner.append(h)
    # 庫内灯のカバー（左上）
    lc = bl.cube((5, 3.5, 0.3), (CX0 + 5, 6, CZ1 - 0.25)); bl.assign(lc, bl.mat("lampcover", (1, 0.95, 0.85), 0.3)); inner.append(lc)
    # ターンテーブル
    tt = bl.cyl(13.5, 0.6, (TT[0], TT[1], CZ0 + 0.7), verts=96); bl.bevel(tt, 0.25, 3)
    bl.assign(tt, bl.mat("ttglass", (0.9, 0.95, 0.95), 0.05, Transmission_Weight=0.9, IOR=1.5)); inner.append(tt)
    # 正面の操作パネル
    px0, px1 = CX1 + 1.2, MW / 2 - 1.2
    pn = bl.cube((px1 - px0, 0.6, MH - 4), ((px0 + px1) / 2, FY - 0.2, MH / 2)); bl.bevel(pn, 0.4, 3); bl.assign(pn, bl.mat("panel", (0.86, 0.86, 0.84), 0.4)); body.append(pn)
    lcd = bl.cube((px1 - px0 - 2.4, 0.4, 3.2), ((px0 + px1) / 2, FY - 0.55, MH - 5.5)); bl.bevel(lcd, 0.3, 3)
    bl.assign(lcd, bl.mat("lcd", (0.05, 0.08, 0.07), 0.15)); body.append(lcd)
    bm_ = bl.mat("btn", (0.8, 0.8, 0.78), 0.45)
    for i in range(4):
        for j in range(2):
            b = bl.cube(((px1 - px0 - 3.6) / 2, 0.6, 1.8), (px0 + 1.2 + (j + 0.5) * (px1 - px0 - 2.4) / 2, FY - 0.6, MH - 10 - i * 2.8)); bl.bevel(b, 0.5, 3); bl.assign(b, bm_); body.append(b)
    sb = bl.cube((px1 - px0 - 2.4, 0.8, 3.4), ((px0 + px1) / 2, FY - 0.7, 7)); bl.bevel(sb, 0.8, 4); bl.assign(sb, bl.mat("startbtn", (0.3, 0.55, 0.42), 0.4)); body.append(sb)
    # 扉（閉じた状態）。白いわく＋すける窓
    door = []
    dx0, dx1 = -MW / 2 + 0.6, CX1 + 1.0
    fr = bl.cube((dx1 - dx0, 1.6, MH - 1.6), ((dx0 + dx1) / 2, FY - 0.9, MH / 2)); bl.bevel(fr, 0.7, 4)
    # 窓の穴（ブーリアン）
    hole = bl.cube((CX1 - CX0 - 4, 4, CZ1 - CZ0 - 5), ((CX0 + CX1) / 2 - 1, FY - 0.9, (CZ0 + CZ1) / 2 + 0.3))
    bo = fr.modifiers.new("b", 'BOOLEAN'); bo.object = hole; bo.operation = 'DIFFERENCE'
    bpy.context.view_layer.objects.active = fr; bpy.ops.object.modifier_apply(modifier="b")
    bpy.data.objects.remove(hole)
    bl.assign(fr, bl.mat("doorframe", (0.92, 0.92, 0.9), 0.3)); door.append(fr)
    hd = bl.cube((1.4, 2.2, MH - 9), (dx1 - 2.4, FY - 2.4, MH / 2)); bl.bevel(hd, 0.6, 4); bl.assign(hd, bl.mat("handle", (0.75, 0.75, 0.74), 0.3, metal=0.6)); door.append(hd)
    win = bl.cube((CX1 - CX0 - 3.4, 0.3, CZ1 - CZ0 - 4.4), ((CX0 + CX1) / 2 - 1, FY - 0.6, (CZ0 + CZ1) / 2 + 0.3))
    m = bpy.data.materials.new("window"); m.use_nodes = True
    N, L = m.node_tree.nodes, m.node_tree.links
    N.remove(N["Principled BSDF"])
    tr = N.new("ShaderNodeBsdfTransparent")
    gl = N.new("ShaderNodeBsdfPrincipled"); gl.inputs["Base Color"].default_value = (0.02, 0.02, 0.025, 1); gl.inputs["Roughness"].default_value = 0.08
    # 網の点々：sin(x)·sin(z)
    tc = N.new("ShaderNodeTexCoord"); sep = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Object"], sep.inputs[0])
    def sn(axis):
        mu = N.new("ShaderNodeMath"); mu.operation = 'MULTIPLY'; mu.inputs[1].default_value = 2 * math.pi / 0.45; L.new(sep.outputs[axis], mu.inputs[0])
        s_ = N.new("ShaderNodeMath"); s_.operation = 'SINE'; L.new(mu.outputs[0], s_.inputs[0]); return s_.outputs[0]
    mul = N.new("ShaderNodeMath"); mul.operation = 'MULTIPLY'; L.new(sn("X"), mul.inputs[0]); L.new(sn("Z"), mul.inputs[1])
    cr = N.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].position = 0.15; cr.color_ramp.elements[0].color = (0.3, 0.3, 0.3, 1)
    cr.color_ramp.elements[1].position = 0.45; cr.color_ramp.elements[1].color = (0.66, 0.66, 0.66, 1)
    L.new(mul.outputs[0], cr.inputs["Fac"])
    mx = N.new("ShaderNodeMixShader"); L.new(cr.outputs["Color"], mx.inputs[0]); L.new(tr.outputs[0], mx.inputs[1]); L.new(gl.outputs[0], mx.inputs[2])
    L.new(mx.outputs[0], N["Material Output"].inputs["Surface"])
    bl.assign(win, m); door.append(win)
    return body, inner, door


def lights(lamp_on):
    bl.world((0.85, 0.88, 0.95), 0.45)
    bl.light('AREA', (-140, -60, 110), 90000, rot_deg=(60, 0, -60), size=80, color=(1.0, 0.95, 0.88))
    bl.light('AREA', (60, -120, 160), 25000, rot_deg=(40, 0, 25), size=120, color=(0.95, 0.97, 1.0))
    if lamp_on:
        bl.light('POINT', (CX0 + 5, 4, CZ1 - 1.8), 450, size=2.5, color=(1.0, 0.8, 0.5))
        bl.light('POINT', (CX0 + 18, -10, CZ1 - 3), 120, size=4, color=(1.0, 0.82, 0.55))


def camera():
    cam = bl.camera((0, -96, 50), rot_deg=(69, 0, 0), lens=52)
    cam.data.sensor_fit = 'HORIZONTAL'; cam.data.shift_y = -0.24; cam.data.clip_end = 2000
    return cam


def proj(cam, p):
    v = world_to_camera_view(bpy.context.scene, cam, mathutils.Vector(p))
    return [round(v.x * 540, 1), round((1 - v.y) * 1080, 1)]


def bbox_px(cam, objs, pad=6):
    xs, ys = [], []
    for o in objs:
        for c in o.bound_box:
            p = proj(cam, o.matrix_world @ mathutils.Vector(c)); xs.append(p[0]); ys.append(p[1])
    return [max(0, min(xs) - pad), max(0, min(ys) - pad), min(540, max(xs) + pad), min(1080, max(ys) + pad)]


def border(sc, r):
    """540x1080 の座標 r=[x0,y0,x1,y1] だけをレンダリングする"""
    sc.render.use_border = True; sc.render.use_crop_to_border = True
    sc.render.border_min_x = r[0] / 540; sc.render.border_max_x = r[2] / 540
    sc.render.border_min_y = 1 - r[3] / 1080; sc.render.border_max_y = 1 - r[1] / 1080


# ---------- 食べもの ----------
def sss(name, col, rough=0.5, w=0.3, scale=0.4):
    return bl.mat(name, col, rough, Subsurface_Weight=w, Subsurface_Scale=scale)


def grain_bump(m, scale=2.2, strength=0.5):
    N, L, b = bl.nodes(m)
    tc = N.new("ShaderNodeTexCoord")
    vr = N.new("ShaderNodeTexVoronoi"); vr.feature = 'SMOOTH_F1'; vr.inputs["Scale"].default_value = scale
    mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1, 1, 1.8); L.new(tc.outputs["Object"], mp.inputs["Vector"]); L.new(mp.outputs["Vector"], vr.inputs["Vector"])
    bp = N.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = strength; L.new(vr.outputs["Distance"], bp.inputs["Height"]); L.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def lathe(profile, loc, segs=64):
    """(r, z) の点列をまわして器をつくる"""
    bm = bmesh.new()
    rings = []
    for k in range(segs):
        a = 2 * math.pi * k / segs
        rings.append([bm.verts.new((r * math.cos(a), r * math.sin(a), z)) for r, z in profile])
    for k in range(segs):
        r0, r1 = rings[k], rings[(k + 1) % segs]
        for i in range(len(profile) - 1):
            bm.faces.new((r0[i], r1[i], r1[i + 1], r0[i + 1]))
    me = bpy.data.meshes.new("lathe"); bm.to_mesh(me); bm.free()
    o = bl.link(bpy.data.objects.new("lathe", me)); o.location = loc
    bl.smooth(o)
    return o


def lumpy(o, amt, scale, seed):
    tx = bpy.data.textures.new(f"lp{seed}", 'CLOUDS'); tx.noise_scale = scale; tx.noise_depth = 2
    d = o.modifiers.new("lp", 'DISPLACE'); d.texture = tx; d.strength = amt; d.texture_coords = 'LOCAL'
    return d


def f_rice(over):
    x, y, z = TT
    prof = [(0.0, 0.0), (2.4, 0.0), (2.6, 0.9), (3.2, 1.0), (4.6, 2.0), (5.8, 3.8), (6.3, 6.0), (6.1, 6.2), (5.5, 4.0), (4.3, 2.4), (2.6, 1.6), (0.0, 1.6)]
    bw = lathe(prof, (x, y, z))
    m = bl.mat("chawan", (0.93, 0.92, 0.88), 0.18)
    N, L, b = bl.nodes(m)
    tc = N.new("ShaderNodeTexCoord"); sep = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Object"], sep.inputs[0])
    # 藍の帯
    cr = N.new("ShaderNodeValToRGB"); cr.color_ramp.interpolation = 'CONSTANT'
    cr.color_ramp.elements[0].color = (0.93, 0.92, 0.88, 1); cr.color_ramp.elements[1].position = 0.55; cr.color_ramp.elements[1].color = (0.12, 0.2, 0.45, 1)
    e = cr.color_ramp.elements.new(0.72); e.color = (0.93, 0.92, 0.88, 1)
    mp = N.new("ShaderNodeMapRange"); mp.inputs["From Min"].default_value = 0; mp.inputs["From Max"].default_value = 6.2
    L.new(sep.outputs["Z"], mp.inputs["Value"]); L.new(mp.outputs[0], cr.inputs["Fac"]); L.new(cr.outputs["Color"], b.inputs["Base Color"])
    bl.assign(bw, m)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(x, y, z + 5.2), segments=64, ring_count=32)
    rc = bl.smooth(bl.active()); rc.scale = (5.6, 5.6, 2.9 if not over else 2.3)
    lumpy(rc, 0.35, 1.0, 3)
    rm = sss("rice", (0.95, 0.94, 0.9) if not over else (0.86, 0.78, 0.6), 0.45 if not over else 0.8, 0.5)
    grain_bump(rm, 2.4, 0.6 if not over else 0.9)
    if over:
        bl.noise_color(rm, (0.75, 0.62, 0.4), (0.9, 0.84, 0.68), scale=1.2)
    bl.assign(rc, rm)
    return [bw, rc]


def f_milk(over):
    x, y, z = TT
    prof = [(0.0, 0.0), (3.6, 0.0), (4.1, 0.3), (4.3, 9.0), (4.1, 9.3), (3.8, 9.0), (3.7, 0.8), (0.0, 0.8)]
    mg = lathe(prof, (x, y, z)); bl.assign(mg, bl.mat("mug", (0.55, 0.75, 0.68), 0.22))
    bpy.ops.mesh.primitive_torus_add(major_radius=2.4, minor_radius=0.55, location=(x + 4.6, y, z + 4.8), rotation=(math.radians(90), 0, 0))
    hd = bl.smooth(bl.active()); hd.scale = (0.8, 1, 1.2); bl.assign(hd, bpy.data.materials["mug"])
    # 取っ手の内がわを消すため、ほんの少しマグに埋める
    hd.location.x -= 0.2
    lv = 8.4 if not over else 9.1
    mk = bl.cyl(3.75, 0.2, (x, y, z + lv), verts=64)
    mm = sss("milk", (0.96, 0.95, 0.9) if not over else (0.94, 0.9, 0.8), 0.25, 0.8, 0.6)
    bl.assign(mk, mm)
    out = [mg, hd, mk]
    if over:
        # 表面の膜としわ、ふきこぼれ
        sub = mk.modifiers.new("s", 'SUBSURF'); sub.levels = sub.render_levels = 3
        lumpy(mk, 0.25, 0.6, 7)
        for i in range(5):
            a = math.radians(-120 + i * 26 + rr.uniform(-8, 8)); ln = rr.uniform(3, 8.5)
            bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(x + math.cos(a) * 4.35, y + math.sin(a) * 4.35, z + 9.2 - ln / 2))
            d = bl.smooth(bl.active()); d.scale = (0.55, 0.55, ln / 2); bl.assign(d, mm); out.append(d)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(x - 1, y - 3, z + 0.05))
        pd = bl.smooth(bl.active()); pd.scale = (7.5, 6, 0.2); lumpy(pd, 0.8, 3, 8); bl.assign(pd, mm); out.append(pd)
    return out


def f_nikuman(over):
    x, y, z = TT
    pp = bl.cube((10, 10, 0.08), (x, y, z + 0.05)); bl.assign(pp, bl.mat("paper", (0.97, 0.96, 0.92), 0.8)); pp.rotation_euler.z = 0.3
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(0, 0, 0), segments=96, ring_count=48)
    bn = bl.smooth(bl.active())
    sx, sz = (4.7, 3.6) if not over else (4.2, 3.0)
    bm = bmesh.new(); bm.from_mesh(bn.data)
    for v in bm.verts:
        X, Y, Z = v.co.x * sx, v.co.y * sx, v.co.z * sz
        Z = max(Z, -sz * 0.35)                       # 底は平ら
        a = math.atan2(Y, X)
        t = max(0.0, Z / sz - 0.45) / 0.55           # 上のほうほど、ひだ
        k = 1 + 0.07 * t * math.sin(a * 14) - 0.25 * t * t
        X, Y = X * k, Y * k
        Z += 0.35 * t * math.sin(a * 14)
        v.co.x, v.co.y, v.co.z = X, Y, Z
    bm.to_mesh(bn.data); bm.free()
    bn.location = (x, y, z + sz * 0.35 + 0.1)
    m = sss("bun", (0.97, 0.94, 0.87) if not over else (0.88, 0.83, 0.72), 0.55 if not over else 0.8, 0.5, 0.5)
    bl.noise_bump(m, scale=1.5 if not over else 4, strength=0.08 if not over else 0.4)
    if over:
        lumpy(bn, 0.3, 0.5, 9)
    bl.assign(bn, m)
    return [pp, bn]


def f_bento(over):
    x, y, z = TT
    tr = bl.cube((17, 12.5, 3.2), (x, y, z + 1.6)); bl.bevel(tr, 0.9, 4)
    inner = bl.cube((16.2, 11.7, 3.0), (x, y, z + 2.2)); bl.bevel(inner, 0.7, 4)
    bo = tr.modifiers.new("b", 'BOOLEAN'); bo.object = inner; bo.operation = 'DIFFERENCE'
    bpy.context.view_layer.objects.active = tr; bpy.ops.object.modifier_apply(modifier="b"); bpy.data.objects.remove(inner)
    bl.assign(tr, bl.mat("tray", (0.03, 0.03, 0.03), 0.35)); out = [tr]
    # しきり
    dv = bl.cube((0.25, 11.6, 2.4), (x + 0.5, y, z + 1.6)); bl.assign(dv, bpy.data.materials["tray"]); out.append(dv)
    # ごはん（左）＋梅
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x - 4.0, y, z + 2.4)); r_ = bl.active(); r_.scale = (7.6, 11.2, 2.0)
    bpy.ops.object.transform_apply(scale=True); bl.bevel(r_, 0.9, 4)
    sb = r_.modifiers.new("s", 'SUBSURF'); sb.levels = sb.render_levels = 2; lumpy(r_, 0.3, 1.0, 11)
    rm = sss("brice", (0.95, 0.94, 0.9) if not over else (0.86, 0.79, 0.62), 0.45, 0.5); grain_bump(rm, 2.4, 0.6 if not over else 0.9); bl.assign(r_, rm); out.append(r_)
    um = bl.sphere(1.0, (x - 4.0, y, z + 3.5)); um.scale.z = 0.75; bl.noise_bump(sss("ume", (0.75, 0.08, 0.1), 0.3, 0.3), scale=3, strength=0.4); bl.assign(um, bpy.data.materials["ume"]); out.append(um)
    # からあげ（右）
    km = bl.mat("karaage", (0.55, 0.3, 0.1) if not over else (0.32, 0.16, 0.06), 0.5 if not over else 0.8)
    bl.noise_color(km, (0.45, 0.22, 0.07) if not over else (0.2, 0.1, 0.04), (0.72, 0.45, 0.18) if not over else (0.4, 0.22, 0.1), scale=2)
    bl.noise_bump(km, scale=3, strength=0.5)
    for i, (dx, dy) in enumerate(((3.2, 2.6), (6.2, 2.4), (4.6, -0.6))):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4, radius=1.7 if not over else 1.45, location=(x + dx, y + dy, z + 2.7))
        k = bl.smooth(bl.active()); k.scale = (1.1, 1.0, 0.85); lumpy(k, 0.6, 0.9, 12 + i); bl.assign(k, km); out.append(k)
    # 卵焼きとたくあん
    eg = bl.cube((3.4, 2.4, 1.8), (x + 4.0, y - 3.8, z + 2.2)); bl.bevel(eg, 0.5, 3); bl.assign(eg, sss("tama", (0.98, 0.8, 0.3) if not over else (0.85, 0.65, 0.22), 0.5, 0.2)); out.append(eg)
    for i in range(2):
        tk = bl.cyl(1.0, 0.35, (x + 7.0, y - 3.4 - i * 0.5, z + 1.8 + i * 0.3), verts=24); tk.rotation_euler.x = math.radians(70)
        bl.assign(tk, sss("takuan", (0.98, 0.88, 0.2), 0.35, 0.3)); out.append(tk)
    if over:
        sm = bl.mat("splat", (0.3, 0.15, 0.06), 0.2)
        for i in range(10):
            s_ = bl.sphere(rr.uniform(0.15, 0.35), (x + rr.uniform(-8, 8), y + rr.uniform(-5.5, 5.5), z + 3.3)); s_.scale.z = 0.3; bl.assign(s_, sm); out.append(s_)
    return out


def f_pizza(over):
    x, y, z = TT
    pl = lathe([(0, 0), (9.5, 0), (10.5, 0.7), (10.6, 0.9), (9.4, 0.6), (0, 0.6)], (x, y, z)); bl.assign(pl, bl.mat("plate", (0.96, 0.96, 0.95), 0.2)); out = [pl]
    base = bl.cyl(8.3, 0.7, (x, y, z + 1.0), verts=96); bl.assign(base, bl.mat("dough", (0.88, 0.7, 0.42), 0.6)); out.append(base)
    bpy.ops.mesh.primitive_torus_add(major_radius=8.2, minor_radius=0.75, location=(x, y, z + 1.4), major_segments=96)
    cr = bl.smooth(bl.active()); lumpy(cr, 0.25, 0.8, 21)
    cm = bl.mat("crust", (0.85, 0.6, 0.3) if not over else (0.35, 0.18, 0.08), 0.6)
    bl.noise_color(cm, (0.8, 0.52, 0.22) if not over else (0.15, 0.07, 0.03), (0.92, 0.72, 0.42) if not over else (0.45, 0.25, 0.1), scale=1.5)
    bl.assign(cr, cm); out.append(cr)
    # チーズ（白〜黄色、トマトがすける）
    bpy.ops.mesh.primitive_circle_add(vertices=96, radius=7.6, fill_type='NGON', location=(x, y, z + 1.45))
    ch = bl.active(); bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.subdivide(number_cuts=24); bpy.ops.object.mode_set(mode='OBJECT')
    lumpy(ch, 0.25, 0.7, 22); bl.smooth(ch)
    m = bl.mat("cheese", (0.98, 0.9, 0.6), 0.35, Subsurface_Weight=0.3)
    if over:
        bl.noise_color(m, (0.6, 0.35, 0.12), (0.97, 0.85, 0.5), scale=1.6, lo=0.45, hi=0.6)
    else:
        bl.noise_color(m, (0.85, 0.3, 0.12), (0.99, 0.92, 0.65), scale=0.9, lo=0.25, hi=0.45)
    bl.assign(ch, m); out.append(ch)
    sal = bl.mat("salami", (0.6, 0.1, 0.08) if not over else (0.35, 0.06, 0.04), 0.4); bl.noise_color(sal, (0.55, 0.08, 0.06) if not over else (0.3, 0.05, 0.03), (0.85, 0.5, 0.45), scale=4, lo=0.6, hi=0.7)
    for i in range(7):
        a = i * 0.9 + 0.3; d = 0 if i == 0 else 4.6
        s_ = bl.cyl(1.6, 0.25, (x + math.cos(a) * d, y + math.sin(a) * d, z + 1.8), verts=32)
        if over:
            sd = s_.modifiers.new("c", 'SIMPLE_DEFORM'); sd.deform_method = 'BEND'; sd.angle = math.radians(40); sd.deform_axis = 'X'
        bl.assign(s_, sal); out.append(s_)
    gp = bl.mat("pepper", (0.15, 0.45, 0.12), 0.3)
    for i in range(5):
        a = i * 1.25 + 0.8
        bpy.ops.mesh.primitive_torus_add(major_radius=0.8, minor_radius=0.13, location=(x + math.cos(a) * 3, y + math.sin(a) * 3, z + 1.9))
        bl.assign(bl.active(), gp); out.append(bl.active())
    return out


def f_egg(over):
    x, y, z = TT
    cup = lathe([(0, 0), (2.4, 0), (2.5, 0.4), (1.2, 1.2), (1.1, 2.0), (2.0, 2.6), (2.6, 4.0), (2.4, 4.1), (1.9, 2.9), (0, 2.9)], (x, y, z))
    bl.assign(cup, bl.mat("eggcup", (0.95, 0.95, 0.93), 0.2)); out = [cup]
    shell = sss("shell", (0.95, 0.88, 0.78), 0.45, 0.2); bl.noise_bump(shell, scale=8, strength=0.08)
    if not over:
        bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(x, y, z + 5.6), segments=64, ring_count=32)
        e = bl.smooth(bl.active()); e.scale = (2.3, 2.3, 3.0)
        bm = bmesh.new(); bm.from_mesh(e.data)
        for v in bm.verts:
            if v.co.z > 0: v.co.x *= 1 - 0.12 * v.co.z; v.co.y *= 1 - 0.12 * v.co.z
        bm.to_mesh(e.data); bm.free()
        bl.assign(e, shell); out.append(e)
    else:
        # はじけた：からのかけら、白身と黄身がとびちる
        wm = sss("white", (0.97, 0.97, 0.95), 0.3, 0.6)
        ym = sss("yolk", (1.0, 0.65, 0.1), 0.35, 0.3)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(x, y, z + 3.7)); b_ = bl.smooth(bl.active()); b_.scale = (2.2, 2.2, 1.5); lumpy(b_, 0.5, 0.7, 31); bl.assign(b_, wm); out.append(b_)
        for i in range(14):
            a = rr.uniform(0, 6.28); d = rr.uniform(3, 11)
            bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=24, ring_count=12, location=(x + math.cos(a) * d, y + math.sin(a) * d * 0.8, z + 0.25))
            p_ = bl.smooth(bl.active()); s = rr.uniform(0.6, 1.6); p_.scale = (s, s * rr.uniform(0.6, 1), 0.25); p_.rotation_euler.z = a
            bl.assign(p_, wm if i % 3 else ym); out.append(p_)
        for i in range(10):
            a = rr.uniform(0, 6.28); d = rr.uniform(2.5, 9)
            bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=16, ring_count=8, location=(x + math.cos(a) * d, y + math.sin(a) * d * 0.8, z + 0.5))
            sh = bl.active(); sh.scale = (rr.uniform(0.5, 1.1), rr.uniform(0.4, 0.9), 0.4); sh.rotation_euler = (rr.uniform(0, 3), rr.uniform(0, 3), a)
            sl = sh.modifiers.new("s", 'SOLIDIFY'); sl.thickness = 0.05; bl.assign(sh, shell); out.append(sh)
    return out


FOODS = [("rice", f_rice), ("milk", f_milk), ("nikuman", f_nikuman), ("bento", f_bento), ("pizza", f_pizza), ("egg", f_egg)]
NF = 8

GEO = {}
gp = os.path.join(OUT, "geo.json")
if os.path.exists(gp):
    GEO = json.load(open(gp))

if PART in ("all", "bg"):
    sc = bl.reset(); look(sc, 0.0)
    sc.render.resolution_x, sc.render.resolution_y = RX, RY
    kitchen(); body, inner, door = microwave()
    for o in door: o.hide_render = True
    lights(False)
    cam = camera(); bpy.context.view_layer.update()
    bl.render(os.path.join(OUT, "bg.png"), RX, RY, samples=S)
    # 庫内灯をつけた庫内だけ
    lights(True)
    q = [proj(cam, p) for p in ((CX0, FY, CZ0), (CX1, FY, CZ0), (CX1, FY, CZ1), (CX0, FY, CZ1))]
    r = [min(p[0] for p in q) - 4, min(p[1] for p in q) - 4, max(p[0] for p in q) + 4, max(p[1] for p in q) + 4]
    border(sc, r)
    bl.render(os.path.join(OUT, "lit.png"), RX, RY, samples=S)
    GEO["lit"] = r
    GEO["cavity"] = q
    # パネルの表示窓と、ボタンのならび
    px0, px1 = CX1 + 1.2, MW / 2 - 1.2
    lc = (px0 + px1) / 2
    GEO["lcd"] = [proj(cam, (lc - (px1 - px0 - 2.4) / 2, FY - 0.8, MH - 5.5 + 1.6)), proj(cam, (lc + (px1 - px0 - 2.4) / 2, FY - 0.8, MH - 5.5 - 1.6))]
    GEO["start"] = proj(cam, (lc, FY - 1.1, 7))
    GEO["tt"] = proj(cam, TT)
    GEO["mw"] = [proj(cam, (-MW / 2, FY, 0)), proj(cam, (MW / 2, FY, MH))]
    # 扉
    sc.render.use_border = False
    for o in bpy.data.objects:
        if o.type == 'MESH': o.is_holdout = True
    for o in door: o.hide_render = False; o.is_holdout = False
    r = bbox_px(cam, door, 4)
    border(sc, r)
    bl.render(os.path.join(OUT, "door.png"), RX, RY, samples=S, transparent=True)
    GEO["door"] = r
    GEO["hinge"] = proj(cam, (-MW / 2 + 0.6, FY - 0.9, MH / 2))

if PART in ("all", "food"):
    from PIL import Image
    cells = []
    rect = None
    for fi, (name, fn) in enumerate(FOODS):
        for over in (False, True):
            sc = bl.reset(); look(sc, 0.35)
            sc.render.resolution_x, sc.render.resolution_y = RX, RY
            kitchen(); body, inner, door = microwave()
            for o in door: o.hide_render = True
            lights(True)
            cam = camera()
            for o in bpy.data.objects:
                if o.type == 'MESH': o.is_holdout = True
            food = fn(over)
            for o in food: o.is_holdout = False
            piv = bpy.data.objects.new("piv", None); bl.link(piv); piv.location = TT
            bpy.context.view_layer.update()
            for o in food:
                o.parent = piv; o.matrix_parent_inverse = piv.matrix_world.inverted()
            bpy.context.view_layer.update()
            if rect is None:
                # どの食べものもおさまる共通の枠（ターンテーブルの上、庫内の高さまで）
                q = [proj(cam, p) for p in ((CX0, FY, CZ0), (CX1, FY, CZ0), (CX1, FY, CZ1), (CX0, FY, CZ1))]
                rect = [round(min(p[0] for p in q)) - 4, round(min(p[1] for p in q)) - 4, round(max(p[0] for p in q)) + 4, round(max(p[1] for p in q)) + 6]
            border(sc, rect)
            frames = range(NF) if not over else [0]
            row = []
            for k in frames:
                piv.rotation_euler.z = 2 * math.pi * k / NF
                f = os.path.join(OUT, f"_f.png")
                bl.render(f, RX, RY, samples=S, transparent=True, pct=150)
                if FAST: sc.render.resolution_percentage = 100; bpy.ops.render.render(write_still=True)
                row.append(Image.open(f).copy()); os.remove(f)
            cells.append((fi, over, row))
    # どのコマも入る範囲だけ切りぬく
    box = None
    for _, _, row in cells:
        for im in row:
            b = im.getchannel("A").point(lambda v: 255 if v > 2 else 0).getbbox()
            if b: box = b if box is None else (min(box[0], b[0]), min(box[1], b[1]), max(box[2], b[2]), max(box[3], b[3]))
    box = (max(0, box[0] - 4), max(0, box[1] - 4), box[2] + 4, box[3] + 4)
    cells = [(fi, ov, [im.crop(box) for im in row]) for fi, ov, row in cells]
    cw, ch = cells[0][2][0].size
    atlas = Image.new("RGBA", (cw * (NF + 1), ch * len(FOODS)))
    for fi, over, row in cells:
        for k, im in enumerate(row):
            atlas.paste(im, ((NF if over else k) * cw, fi * ch))
    atlas.save(os.path.join(OUT, "food.png"))
    GEO["food"] = {"rect": rect, "off": [box[0], box[1]], "cw": cw, "ch": ch, "n": NF, "names": [n for n, _ in FOODS]}
    GEO["foodScale"] = (1.5 if FAST else 2.25)

json.dump(GEO, open(gp, "w"))
print("done")
