"""ひびき硝子：素材レンダリング。

out/bg.png     夜の聖堂の大きな尖頭アーチ窓。ブロックがはまる位置がちょうど窓になる。
               窓の外は月夜、窓の下は燭台の灯りに照らされた石の壁。
               720x1200（ゲーム 360x600 の2倍）。1m = ゲームの100。
out/tiles.png  ステンドグラスの板（5色 x 厚み3段 x 2枚 + 透明2枚）とバーの一覧画像。
               1マス 32x20（板 26x14 のまわりに鉛の枠ぶん 3 ずつ）を 4px/1 で。
"""
import math, os, sys, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "common"))
import bpy, bmesh
import bl

OUT = os.path.join(os.path.dirname(__file__), "out")
os.makedirs(OUT, exist_ok=True)
FAST = "--fast" in sys.argv
ONLY = [a for a in sys.argv[1:] if not a.startswith("--")]


def srgb(c):
    return tuple(((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in c)


def gx(x):  # ゲーム座標 → m
    return (x - 180) / 100


def gz(y):
    return (600 - y) / 100


def node(N, kind, **inputs):
    n = N.new(kind)
    for k, v in inputs.items():
        n.inputs[k].default_value = v
    return n


# ---------------------------------------------------------------- 背景
SPRING, APEX, SILL, HALF = gz(118), gz(10), gz(244), 1.745


def arch_outline(off=0.0, segs=64):
    """尖頭アーチの窓の輪郭（左下から反時計回り）。off だけ外へふくらませる。
    楕円にすこし「とがり」を混ぜて、ゆるいゴシックの尖頭にする。"""
    a, h, pt = HALF + off, APEX - SPRING + off, 0.22
    pts = [(-a, SILL - off)]
    for i in range(segs + 1):
        u = -1 + 2 * i / segs
        z = SPRING + h * (math.sqrt(max(0, 1 - u * u)) * (1 - pt) + pt * (1 - abs(u)))
        pts.append((u * a, z))
    pts.append((a, SILL - off))
    return pts


def prism(name, outline, y0, y1):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    f = [bm.verts.new((x, y0, z)) for x, z in outline]
    b = [bm.verts.new((x, y1, z)) for x, z in outline]
    bm.faces.new(f)
    bm.faces.new(list(reversed(b)))
    n = len(outline)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((f[i], f[j], b[j], b[i]))
    bm.normal_update()
    bm.to_mesh(me)
    o = bpy.data.objects.new(name, me)
    bl.link(o)
    return o


def cut(target, cutter):
    md = target.modifiers.new("cut", 'BOOLEAN')
    md.operation = 'DIFFERENCE'
    md.object = cutter
    md.solver = 'EXACT'
    cutter.hide_render = True
    return md


def stone_mat(name, base=(0.36, 0.33, 0.30), scale=2.2):
    m = bl.mat(name, base, 0.82)
    N, L, b = bl.nodes(m)
    tc = N.new("ShaderNodeTexCoord")
    sep = N.new("ShaderNodeSeparateXYZ")
    L.new(tc.outputs["Object"], sep.inputs[0])
    comb = N.new("ShaderNodeCombineXYZ")
    L.new(sep.outputs["X"], comb.inputs["X"])
    L.new(sep.outputs["Z"], comb.inputs["Y"])
    L.new(sep.outputs["Y"], comb.inputs["Z"])
    br = node(N, "ShaderNodeTexBrick", Scale=scale, **{"Mortar Size": 0.018, "Mortar Smooth": 0.3, "Bias": 0.0,
                                                       "Brick Width": 0.9, "Row Height": 0.42})
    br.inputs["Color1"].default_value = (*srgb((0.50, 0.46, 0.41)), 1)
    br.inputs["Color2"].default_value = (*srgb((0.40, 0.37, 0.34)), 1)
    br.inputs["Mortar"].default_value = (*srgb((0.16, 0.14, 0.13)), 1)
    br.offset = 0.5
    L.new(comb.outputs[0], br.inputs["Vector"])
    nz = node(N, "ShaderNodeTexNoise", Scale=9.0, Detail=10.0, Roughness=0.62)
    L.new(comb.outputs[0], nz.inputs["Vector"])
    mx = N.new("ShaderNodeMix")
    mx.data_type = 'RGBA'
    mx.blend_type = 'MULTIPLY'
    mx.inputs[0].default_value = 0.8
    L.new(br.outputs["Color"], mx.inputs[6])
    L.new(nz.outputs["Color"], mx.inputs[7])
    L.new(mx.outputs[2], b.inputs["Base Color"])
    hgt = N.new("ShaderNodeMath")
    hgt.operation = 'ADD'
    fac = N.new("ShaderNodeMath")
    fac.operation = 'MULTIPLY'
    fac.inputs[1].default_value = 0.25
    L.new(nz.outputs["Fac"], fac.inputs[0])
    inv = N.new("ShaderNodeMath")
    inv.operation = 'SUBTRACT'
    inv.inputs[0].default_value = 1.0
    L.new(br.outputs["Fac"], inv.inputs[1])
    L.new(inv.outputs[0], hgt.inputs[0])
    L.new(fac.outputs[0], hgt.inputs[1])
    bp = node(N, "ShaderNodeBump", Strength=0.55, Distance=0.02)
    L.new(hgt.outputs[0], bp.inputs["Height"])
    L.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def sky_mat():
    m = bpy.data.materials.new("sky")
    m.use_nodes = True
    N, L = m.node_tree.nodes, m.node_tree.links
    N.remove(N["Principled BSDF"])
    tc = N.new("ShaderNodeTexCoord")
    sep = N.new("ShaderNodeSeparateXYZ")
    L.new(tc.outputs["Object"], sep.inputs[0])
    # 地平に向かって少し明るい、深い紺
    grad = N.new("ShaderNodeMapRange")
    grad.inputs["From Min"].default_value = 3 + 0.4 * 4.11
    grad.inputs["From Max"].default_value = 3 + 3.2 * 4.11
    gpos = N.new("ShaderNodeNewGeometry")
    gsep = N.new("ShaderNodeSeparateXYZ")
    L.new(gpos.outputs["Position"], gsep.inputs[0])
    L.new(gsep.outputs["Z"], grad.inputs["Value"])
    cr = N.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].color = (*srgb((0.10, 0.15, 0.30)), 1)
    cr.color_ramp.elements[1].color = (*srgb((0.025, 0.035, 0.09)), 1)
    L.new(grad.outputs[0], cr.inputs["Fac"])
    # 星
    vo = node(N, "ShaderNodeTexVoronoi", Scale=1.7, Randomness=1.0)
    L.new(tc.outputs["Object"], vo.inputs["Vector"])
    st = N.new("ShaderNodeMapRange")
    st.inputs["From Min"].default_value = 0.07
    st.inputs["From Max"].default_value = 0.0
    st.inputs["To Max"].default_value = 3.0
    L.new(vo.outputs["Distance"], st.inputs["Value"])
    pick = node(N, "ShaderNodeTexWhiteNoise")
    L.new(vo.outputs["Position"], pick.inputs["Vector"])
    keep = N.new("ShaderNodeMath")
    keep.operation = 'GREATER_THAN'
    keep.inputs[1].default_value = 0.8
    L.new(pick.outputs["Value"], keep.inputs[0])
    sm = N.new("ShaderNodeMath")
    sm.operation = 'MULTIPLY'
    L.new(st.outputs[0], sm.inputs[0])
    L.new(keep.outputs[0], sm.inputs[1])
    add = N.new("ShaderNodeMix")
    add.data_type = 'RGBA'
    add.blend_type = 'ADD'
    add.inputs[0].default_value = 1.0
    L.new(cr.outputs["Color"], add.inputs[6])
    sc = N.new("ShaderNodeCombineColor")
    for i in range(3):
        L.new(sm.outputs[0], sc.inputs[i])
    L.new(sc.outputs[0], add.inputs[7])
    em = N.new("ShaderNodeEmission")
    L.new(add.outputs[2], em.inputs[0])
    em.inputs[1].default_value = 1.0
    L.new(em.outputs[0], N["Material Output"].inputs[0])
    return m


def render_bg():
    sc = bl.reset()
    sc.cycles.samples = 24 if FAST else 160
    sc.view_settings.look = 'AgX - Medium High Contrast'
    bl.world((0.004, 0.006, 0.012), 1.0)
    cam = bl.camera((0, -14, 3.0), (90, 0, 0), lens=140)
    cam.data.sensor_fit = 'HORIZONTAL'
    cam.data.sensor_width = 36
    cam.data.dof.use_dof = True
    cam.data.dof.focus_distance = 14
    cam.data.dof.aperture_fstop = 0.9

    stone = stone_mat("stone", scale=1.7)
    # 壁（窓の穴あき）
    wall = prism("wall", [(-3, -1), (3, -1), (3, 8), (-3, 8)], 0.0, 0.55)
    hole = prism("hole", arch_outline(0.0), -0.5, 1.0)
    cut(wall, hole)
    bl.assign(wall, stone)
    # 窓のまわりの、一段手前に出た縁石（面取り）
    frame = prism("frame", arch_outline(0.16), -0.1, 0.02)
    hole2 = prism("hole2", arch_outline(0.0), -0.5, 1.0)
    cut(frame, hole2)
    bl.bevel(frame, 0.035, 3)
    bl.assign(frame, stone_mat("stone2", base=(0.5, 0.47, 0.43), scale=3.0))
    # 窓の上の横桟と、アーチの頭の細い縦桟（ブロックより上だけ）
    tr = bl.cube((2 * HALF + 0.1, 0.12, 0.035), (0, 0.2, gz(62)))
    bl.bevel(tr, 0.01, 2)
    bl.assign(tr, stone)
    for x in (-0.6, 0.0, 0.6):
        mu = bl.cube((0.03, 0.1, 0.6), (x, 0.22, gz(62) + 0.3))
        bl.bevel(mu, 0.008, 2)
        bl.assign(mu, stone)
    # 窓台
    sill = bl.cube((2 * HALF + 0.5, 0.75, 0.09), (0, -0.05, SILL - 0.045))
    bl.bevel(sill, 0.02, 3)
    bl.assign(sill, stone_mat("stone3", scale=3.0))
    # 床と、壁の根元の幅木
    base = bl.cube((6, 0.12, 0.28), (0, -0.06, 0.14))
    bl.bevel(base, 0.02, 3)
    bl.assign(base, stone_mat("stone4", base=(0.25, 0.23, 0.22), scale=4))
    floor = bl.plane((8, 6), (0, -3, 0.0))
    fm = bl.mat("floor", srgb((0.05, 0.05, 0.06)), 0.18)
    bl.noise_bump(fm, scale=6, strength=0.05)
    bl.assign(floor, fm)
    # 窓の外：月夜
    sky = bl.plane((60, 40), (0, 60.0, 12), (90, 0, 0))
    bl.assign(sky, sky_mat())
    K = 72 / 17.9
    moon = bl.sphere(0.13 * K, (0.78 * K, 58, 3 + (gz(36) - 3) * K))
    bl.assign(moon, bl.emission("moon", srgb((1.0, 0.95, 0.82)), 6))
    halo = bl.plane((1.4 * K, 1.4 * K), (0.78 * K, 57.5, 3 + (gz(36) - 3) * K), (90, 0, 0))
    hm = bpy.data.materials.new("halo")
    hm.use_nodes = True
    N, L = hm.node_tree.nodes, hm.node_tree.links
    N.remove(N["Principled BSDF"])
    tc = N.new("ShaderNodeTexCoord")
    grd = N.new("ShaderNodeTexGradient")
    grd.gradient_type = 'SPHERICAL'
    mp = N.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1.5 / K, 1.5 / K, 1.5 / K)
    L.new(tc.outputs["Object"], mp.inputs["Vector"])
    L.new(mp.outputs[0], grd.inputs["Vector"])
    pw = N.new("ShaderNodeMath")
    pw.operation = 'POWER'
    pw.inputs[1].default_value = 3.0
    L.new(grd.outputs["Fac"], pw.inputs[0])
    em = N.new("ShaderNodeEmission")
    em.inputs[0].default_value = (*srgb((0.55, 0.65, 0.95)), 1)
    L.new(pw.outputs[0], em.inputs[1])
    tp = N.new("ShaderNodeBsdfTransparent")
    ad = N.new("ShaderNodeAddShader")
    L.new(em.outputs[0], ad.inputs[0])
    L.new(tp.outputs[0], ad.inputs[1])
    L.new(ad.outputs[0], N["Material Output"].inputs[0])
    bl.assign(halo, hm)
    # 窓の外、遠くの街明かり（大きくぼけて、ガラス越しに透けて見える）
    rnd = random.Random(11)
    lamp = [bl.emission(f"lamp{i}", srgb(c), 7) for i, c in enumerate(
        [(1.0, 0.72, 0.38), (1.0, 0.84, 0.6), (0.6, 0.85, 1.0), (1.0, 0.55, 0.3), (0.8, 1.0, 0.85)])]
    for i in range(230):
        x = rnd.uniform(-7.5, 7.5)
        z = 5.0 + rnd.random() ** 1.35 * 8.0
        s_ = bl.sphere(rnd.uniform(0.03, 0.09), (x, 40, z))
        bl.assign(s_, rnd.choice(lamp))
    # 月の光が窓から差しこみ、縁や窓台をかすめる
    bl.light('AREA', (0.6, 2.2, 6.0), 900, (-35, 0, 0), size=3, color=(0.62, 0.72, 1.0))
    # 窓の縁石を上からなでる、月明かりの返し（アーチの形が見えるように）
    bl.light('AREA', (0, -2.5, 7.2), 260, (-60, 0, 0), size=4, color=(0.6, 0.7, 1.0))
    # 部屋の青い暗がり（正面からのごく弱い光）
    bl.light('AREA', (0, -10, 4), 40, (90, 0, 0), size=8, color=(0.55, 0.62, 0.9))

    # 燭台（左右）：鉄の台に3本のろうそく
    iron = bl.mat("iron", srgb((0.08, 0.06, 0.05)), 0.35, metal=1.0)
    wax = bl.mat("wax", srgb((0.93, 0.88, 0.78)), 0.5, Subsurface_Weight=0.4)
    flame = bl.emission("flame", srgb((1.0, 0.72, 0.36)), 22)
    for sx in (-1, 1):
        x0, y0 = sx * 1.52, -0.75
        pole = bl.cyl(0.022, 1.32, (x0, y0, 0.66), verts=24)
        bl.assign(pole, iron)
        foot = bl.cyl(0.16, 0.05, (x0, y0, 0.025), verts=48)
        bl.bevel(foot, 0.015, 2)
        bl.assign(foot, iron)
        arm = bl.cube((0.62, 0.035, 0.035), (x0, y0, 1.30))
        bl.assign(arm, iron)
        for k, dx in enumerate((-0.28, 0.0, 0.28)):
            hgt = (0.30, 0.42, 0.24)[k] if sx < 0 else (0.26, 0.38, 0.32)[k]
            cup = bl.cyl(0.055, 0.04, (x0 + dx, y0, 1.33), verts=32)
            bl.assign(cup, iron)
            c = bl.cyl(0.032, hgt, (x0 + dx, y0, 1.35 + hgt / 2), verts=32)
            bl.assign(c, wax)
            fz = 1.35 + hgt + 0.045
            f = bl.sphere(0.017, (x0 + dx, y0, fz))
            f.scale = (1, 1, 2.4)
            bl.assign(f, flame)
            bl.light('POINT', (x0 + dx, y0 - 0.03, fz + 0.02), 15, size=0.03, color=(1.0, 0.6, 0.3))
    bl.render(os.path.join(OUT, "bg_raw.png"), 720, 1200)
    glow(os.path.join(OUT, "bg_raw.png"), os.path.join(OUT, "bg.png"))


def glow(src, dst):
    """明るいところ（月・ろうそく・窓の縁）からにじむ光と、四隅の暗がり。"""
    from PIL import Image, ImageChops, ImageFilter
    import numpy as np
    im = np.asarray(Image.open(src).convert("RGB")).astype(np.float32) / 255
    lum = im.max(axis=2, keepdims=True)
    hi = np.clip((lum - 0.55) / 0.45, 0, 1) * im
    hiI = Image.fromarray((hi * 255).astype(np.uint8))
    b1 = np.asarray(hiI.filter(ImageFilter.GaussianBlur(6))).astype(np.float32) / 255
    b2 = np.asarray(hiI.filter(ImageFilter.GaussianBlur(28))).astype(np.float32) / 255
    out = im + b1 * 0.8 + b2 * 1.3
    h, w = out.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.sqrt(((xx - w / 2) / (w * 0.75)) ** 2 + ((yy - h * 0.45) / (h * 0.62)) ** 2)
    out *= np.clip(1.15 - d * 0.55, 0.45, 1)[..., None]
    Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8)).save(dst)


# ---------------------------------------------------------------- ステンドグラスの板
COLORS = [  # NOTES の順：琥珀・薔薇・菫・青磁・空
    (1.00, 0.58, 0.12),
    (0.96, 0.22, 0.36),
    (0.55, 0.36, 1.00),
    (0.16, 0.82, 0.64),
    (0.22, 0.60, 1.00),
]
CW, CH, TW, TH = 32, 20, 26, 14
COLS = 8


def cell_center(c, r, atlas_w, atlas_h):
    return (c * CW + CW / 2 - atlas_w / 2, atlas_h / 2 - (r * CH + CH / 2))


def glass_mat(name, color, th, seed, clear=False):
    """裏から月明かりを受けて光る、手吹きのステンドグラス。
    色の濃淡のむら（筋）・表面の槌目・泡、表面のつや。"""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    N, L = m.node_tree.nodes, m.node_tree.links
    N.remove(N["Principled BSDF"])
    out = N["Material Output"]
    tc = N.new("ShaderNodeTexCoord")
    mp = N.new("ShaderNodeMapping")
    mp.inputs["Location"].default_value = (seed * 37.1, seed * 11.3, seed * 5.7)
    L.new(tc.outputs["Object"], mp.inputs["Vector"])
    # 吹きガラスの筋（横に引きのばしたノイズ）
    sm = N.new("ShaderNodeMapping")
    sm.inputs["Scale"].default_value = (0.05, 0.16, 0.1)
    L.new(mp.outputs[0], sm.inputs["Vector"])
    streak = node(N, "ShaderNodeTexNoise", Scale=2.2, Detail=6.0, Roughness=0.55)
    L.new(sm.outputs[0], streak.inputs["Vector"])
    # 槌目（ボロノイのくぼみ）
    hammer = node(N, "ShaderNodeTexVoronoi", Scale=0.42, Randomness=0.9)
    hammer.feature = 'SMOOTH_F1'
    L.new(mp.outputs[0], hammer.inputs["Vector"])
    # 色：筋で明るさ・彩度がゆらぐ
    deep = (0.78, 0.66, 0.55)[th - 1]
    lo = tuple(v * (deep if not clear else 1) for v in color)
    hi = tuple(min(1, v * (1.0, 0.92, 0.85)[th - 1] + (0.2, 0.06, 0.0)[th - 1]) for v in color)
    cr = N.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].position = 0.2
    cr.color_ramp.elements[1].position = 0.85
    cr.color_ramp.elements[0].color = (*srgb(lo), 1)
    cr.color_ramp.elements[1].color = (*srgb(hi), 1)
    L.new(streak.outputs["Fac"], cr.inputs["Fac"])
    # 面の向きで明るさを変える：左上を向いた面は明るく、右下を向いた面は暗く（面取りが立体に見える）
    geo = N.new("ShaderNodeNewGeometry")
    dot = N.new("ShaderNodeVectorMath")
    dot.operation = 'DOT_PRODUCT'
    dot.inputs[1].default_value = (-0.45, 0.45, 0.77)
    L.new(geo.outputs["Normal"], dot.inputs[0])
    fc = N.new("ShaderNodeMath")
    fc.operation = 'MULTIPLY_ADD'
    fc.inputs[1].default_value = 0.85
    fc.inputs[2].default_value = 0.35
    L.new(dot.outputs["Value"], fc.inputs[0])
    # 槌目のくぼみの中心ほど少し明るい（レンズのように光を集める）
    hm = N.new("ShaderNodeMapRange")
    hm.inputs["From Min"].default_value = 0.0
    hm.inputs["From Max"].default_value = 1.2
    hm.inputs["To Min"].default_value = 1.18
    hm.inputs["To Max"].default_value = 0.86
    L.new(hammer.outputs["Distance"], hm.inputs["Value"])
    k = N.new("ShaderNodeMath")
    k.operation = 'MULTIPLY'
    L.new(fc.outputs[0], k.inputs[0])
    L.new(hm.outputs[0], k.inputs[1])
    strength = N.new("ShaderNodeMath")
    strength.operation = 'MULTIPLY'
    strength.inputs[1].default_value = (1.0, 0.8, 0.68)[th - 1] if not clear else 0.10
    L.new(k.outputs[0], strength.inputs[0])
    em = N.new("ShaderNodeEmission")
    L.new(cr.outputs["Color"], em.inputs["Color"])
    L.new(strength.outputs[0], em.inputs["Strength"])
    # 表面のつや
    gl = N.new("ShaderNodeBsdfPrincipled")
    gl.inputs["Base Color"].default_value = (0, 0, 0, 1)
    gl.inputs["Roughness"].default_value = 0.08 if th < 3 else 0.12
    gl.inputs["Specular IOR Level"].default_value = 0.9
    bump = node(N, "ShaderNodeBump", Strength=(0.18, 0.2, 0.16)[th - 1], Distance=0.6)
    L.new(hammer.outputs["Distance"], bump.inputs["Height"])
    L.new(bump.outputs["Normal"], gl.inputs["Normal"])
    add = N.new("ShaderNodeAddShader")
    L.new(em.outputs[0], add.inputs[0])
    L.new(gl.outputs[0], add.inputs[1])
    # 透けるガラス：平らな面はほとんど透明（向こうの景色はゲーム側で屈折させて映す）。
    # 面取りの斜めの面と縁ほど不透明になり、色が濃く、つやが乗る。
    nz = N.new("ShaderNodeSeparateXYZ")
    L.new(geo.outputs["Normal"], nz.inputs[0])
    slant = N.new("ShaderNodeMath")
    slant.operation = 'MULTIPLY_ADD'
    slant.inputs[1].default_value = -3.2
    slant.inputs[2].default_value = 3.2 + ((0.18, 0.26, 0.34)[th - 1] if not clear else 0.22)
    L.new(nz.outputs["Z"], slant.inputs[0])
    slant.use_clamp = True
    tp = N.new("ShaderNodeBsdfTransparent")
    mix = N.new("ShaderNodeMixShader")
    L.new(slant.outputs[0], mix.inputs[0])
    L.new(tp.outputs[0], mix.inputs[1])
    L.new(add.outputs[0], mix.inputs[2])
    L.new(mix.outputs[0], out.inputs[0])
    return m


def came_mat():
    # 鉛の枠：黒に近い焦げ茶の金属（ほそい茶色のふち）
    m = bl.mat("came", srgb((0.30, 0.20, 0.13)), 0.45, metal=0.8)
    bl.noise_bump(m, scale=1.6, strength=0.2)
    return m


def slab(cx, cy, th):
    """板のかたち。1=平らな薄板 2=ふちを大きく面取りした厚板 3=まんなかが盛り上がった宝石カット。"""
    w, h = TW - 0.6, TH - 0.6
    z, ins = [(0.6, 0.5), (1.6, 3.0), (2.8, 5.4)][th - 1]
    me = bpy.data.meshes.new("slab")
    bm = bmesh.new()
    lo = [bm.verts.new((cx + x * w / 2, cy + y * h / 2, 0)) for x, y in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    tw, tht = max(1.0, w - 2 * ins), max(1.0, h - 2 * ins)
    hi = [bm.verts.new((cx + x * tw / 2, cy + y * tht / 2, z)) for x, y in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    bm.faces.new(list(reversed(lo)))
    bm.faces.new(hi)
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
    bm.to_mesh(me)
    o = bpy.data.objects.new("slab", me)
    bl.link(o)
    md = bl.bevel(o, 0.25, 2)
    md.limit_method = 'NONE'
    return o


def came(cx, cy, m):
    out = bl.cube((TW + 3.0, TH + 3.0, 1.2), (cx, cy, 0.0))
    inner = bl.cube((TW - 1.4, TH - 1.4, 6), (cx, cy, 0))
    md = out.modifiers.new("cut", 'BOOLEAN')
    md.operation = 'DIFFERENCE'
    md.object = inner
    md.solver = 'EXACT'
    inner.hide_render = True
    bl.bevel(out, 0.5, 4).limit_method = 'NONE'
    out.location.z = 0.35
    bl.assign(out, m)
    bl.smooth(out)
    return out


def render_tiles():
    sc = bl.reset()
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    sc.cycles.samples = 24 if FAST else 96
    sc.render.film_transparent = True
    bl.world((0.02, 0.025, 0.04), 1.0)
    rows = 4
    atlas_w, atlas_h = COLS * CW, rows * CH + 24
    bl.camera((0, 0, 60), (0, 0, 0), ortho=atlas_w)
    # 左上からの大きな面光源（面取りの面がきらっと光る）＋右下からの弱い返し
    bl.light('AREA', (-60, 70, 70), 60000, (-40, -35, 0), size=40, color=(1.0, 0.97, 0.92))
    bl.light('AREA', (80, -60, 40), 9000, (50, 40, 0), size=60, color=(0.7, 0.78, 1.0))
    cm = came_mat()
    rng = random.Random(3)
    i = 0
    for note in range(5):
        for th in (1, 2, 3):
            for v in range(2):
                c, r = i % COLS, i // COLS
                cx, cy = cell_center(c, r, atlas_w, atlas_h)
                bl.assign(slab(cx, cy, th), glass_mat(f"g{note}{th}{v}", COLORS[note], th, rng.random() * 10))
                came(cx, cy, cm)
                i += 1
    for v in range(2):
        c, r = i % COLS, i // COLS
        cx, cy = cell_center(c, r, atlas_w, atlas_h)
        bl.assign(slab(cx, cy, 1), glass_mat(f"clear{v}", (0.62, 0.72, 0.88), 1, rng.random() * 10, clear=True))
        came(cx, cy, cm)
        i += 1
    # バー：澄んだ水色の厚いガラス棒に、真鍮の留め金
    py = atlas_h / 2 - (rows * CH + 12)
    px = -atlas_w / 2 + 40
    bar = bl.cube((60, 10, 6), (px, py, 3))
    bl.bevel(bar, 2.6, 5).limit_method = 'NONE'
    bl.smooth(bar)
    bl.assign(bar, glass_mat("bar", (0.55, 0.92, 0.86), 1, 1.7))
    brass = bl.mat("brass", srgb((0.86, 0.64, 0.32)), 0.25, metal=1.0)
    for sx in (-1, 1):
        cap = bl.cube((5, 11.6, 7), (px + sx * 31.5, py, 3.5))
        bl.bevel(cap, 1.6, 4).limit_method = 'NONE'
        bl.smooth(cap)
        bl.assign(cap, brass)
    bl.render(os.path.join(OUT, "tiles.png"), atlas_w * 4, atlas_h * 4, transparent=True)


if __name__ == "__main__":
    if not ONLY or "bg" in ONLY:
        render_bg()
    if not ONLY or "tiles" in ONLY:
        render_tiles()
