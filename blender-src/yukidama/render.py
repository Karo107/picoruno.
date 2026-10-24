"""雪玉ころがし：素材レンダリング。

1 = 1cm。坂は真上から（上が山側、下へころがる）。日ざしは左上から。
out/slope.png    坂の雪。たて方向にくり返せる（360x720cm を 810x1620）
out/ball.png     ころがる雪玉 12 コマ（真上から、X 軸まわりに 30° ずつ）
out/obj.png      障害物とごほうび 6 種（影つき、240cm 角のマス 3x2）
out/yard.png     ゴールの庭（夕暮れ）。雪だるまを立てる場所
out/ballf.png    正面から見た雪玉（庭の光）
out/parts.png    雪だるまの小物（バケツ・にんじん・炭・枝）
out/geo.json
"""
import json, math, os, sys, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "common"))
import bpy, bmesh, mathutils
from bpy_extras.object_utils import world_to_camera_view
import bl

OUT = os.path.join(os.path.dirname(__file__), "out")
os.makedirs(OUT, exist_ok=True)
FAST = "--fast" in sys.argv
S = 24 if FAST else 160
PART = next((a for a in sys.argv[1:] if not a.startswith("-")), "all")
rr = random.Random(7)
GEO = {}
gp = os.path.join(OUT, "geo.json")
if os.path.exists(gp):
    GEO = json.load(open(gp))

SUN_ROT = (35, 0, -135)       # 左上から右下へ（高さ 55°）
SNOW = (0.93, 0.95, 0.99)


def look(sc, exp=0.0):
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Base Contrast'; sc.view_settings.exposure = exp


def snow_mat(name, col=SNOW, fine=0.9, coarse=None, period=None, ao=True, rough=0.6, bump=0.25, dist=0.5):
    """雪。こまかい粒の凹凸＋ゆるい吹きだまり。period を与えると y 方向にくり返す座標でノイズを引く。"""
    m = bl.mat(name, col, rough, Subsurface_Weight=0.35, Subsurface_Scale=1.5)
    N, L, b = bl.nodes(m)
    b.inputs["Subsurface Radius"].default_value = (0.5, 0.75, 1.0)
    tc = N.new("ShaderNodeTexCoord")
    vec = tc.outputs["Object"]
    if period:
        # (x, R cos θ, R sin θ)：y が period でひとまわり
        sep = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Object"], sep.inputs[0])
        th = N.new("ShaderNodeMath"); th.operation = 'MULTIPLY'; th.inputs[1].default_value = 2 * math.pi / period; L.new(sep.outputs["Y"], th.inputs[0])
        R = period / (2 * math.pi)
        cs = N.new("ShaderNodeMath"); cs.operation = 'COSINE'; L.new(th.outputs[0], cs.inputs[0])
        sn = N.new("ShaderNodeMath"); sn.operation = 'SINE'; L.new(th.outputs[0], sn.inputs[0])
        c2 = N.new("ShaderNodeMath"); c2.operation = 'MULTIPLY'; c2.inputs[1].default_value = R; L.new(cs.outputs[0], c2.inputs[0])
        s2 = N.new("ShaderNodeMath"); s2.operation = 'MULTIPLY'; s2.inputs[1].default_value = R; L.new(sn.outputs[0], s2.inputs[0])
        cb = N.new("ShaderNodeCombineXYZ"); L.new(sep.outputs["X"], cb.inputs[0]); L.new(c2.outputs[0], cb.inputs[1]); L.new(s2.outputs[0], cb.inputs[2])
        vec = cb.outputs[0]
    nf = N.new("ShaderNodeTexNoise"); nf.inputs["Scale"].default_value = fine; nf.inputs["Detail"].default_value = 10; nf.inputs["Roughness"].default_value = 0.7
    L.new(vec, nf.inputs["Vector"])
    h = nf.outputs["Fac"]
    if coarse:
        nc = N.new("ShaderNodeTexNoise"); nc.inputs["Scale"].default_value = coarse; nc.inputs["Detail"].default_value = 3
        L.new(vec, nc.inputs["Vector"])
        mc = N.new("ShaderNodeMath"); mc.operation = 'MULTIPLY_ADD'; mc.inputs[1].default_value = 6.0; L.new(nc.outputs["Fac"], mc.inputs[0]); L.new(nf.outputs["Fac"], mc.inputs[2])
        h = mc.outputs[0]
    bp = N.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = bump; bp.inputs["Distance"].default_value = dist
    L.new(h, bp.inputs["Height"]); L.new(bp.outputs["Normal"], b.inputs["Normal"])
    # ほんのり青いくぼみ（AO）
    if ao:
        a = N.new("ShaderNodeAmbientOcclusion"); a.inputs["Distance"].default_value = 6
        mx = N.new("ShaderNodeMix"); mx.data_type = 'RGBA'
        mx.inputs[6].default_value = (0.62, 0.72, 0.9, 1); mx.inputs[7].default_value = (*col, 1)
        L.new(a.outputs["AO"], mx.inputs[0]); L.new(mx.outputs[2], b.inputs["Base Color"])
    return m


def mix_by_up(name, under, rough_u, thresh=0.55, noise=0.25, nscale=0.08):
    """上を向いた面に雪がのる素材（岩・しげみ・木）。"""
    m = bl.mat(name, under, rough_u)
    N, L, b = bl.nodes(m)
    out = N["Material Output"]
    s = N.new("ShaderNodeBsdfPrincipled"); s.inputs["Base Color"].default_value = (*SNOW, 1); s.inputs["Roughness"].default_value = 0.6
    s.inputs["Subsurface Weight"].default_value = 0.35; s.inputs["Subsurface Scale"].default_value = 1.5
    nb = N.new("ShaderNodeTexNoise"); nb.inputs["Scale"].default_value = 0.9; nb.inputs["Detail"].default_value = 8
    bps = N.new("ShaderNodeBump"); bps.inputs["Strength"].default_value = 0.3; L.new(nb.outputs["Fac"], bps.inputs["Height"]); L.new(bps.outputs["Normal"], s.inputs["Normal"])
    # 雪かどうか：法線の z ＋ノイズ
    gm = N.new("ShaderNodeNewGeometry")
    sep = N.new("ShaderNodeSeparateXYZ"); L.new(gm.outputs["Normal"], sep.inputs[0])
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = nscale; nz.inputs["Detail"].default_value = 4
    ad = N.new("ShaderNodeMath"); ad.operation = 'MULTIPLY_ADD'; ad.inputs[1].default_value = noise * 2
    sub = N.new("ShaderNodeMath"); sub.operation = 'SUBTRACT'; sub.inputs[1].default_value = 0.5; L.new(nz.outputs["Fac"], sub.inputs[0])
    L.new(sub.outputs[0], ad.inputs[0]); L.new(sep.outputs["Z"], ad.inputs[2])
    cr = N.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].position = thresh - 0.04; cr.color_ramp.elements[1].position = thresh + 0.04
    L.new(ad.outputs[0], cr.inputs["Fac"])
    ms = N.new("ShaderNodeMixShader"); L.new(cr.outputs["Color"], ms.inputs[0]); L.new(b.outputs[0], ms.inputs[1]); L.new(s.outputs[0], ms.inputs[2])
    L.new(ms.outputs[0], out.inputs["Surface"])
    return m


def sky_world(top, horizon, strength=1.0, mid=None):
    w = bl.world((0, 0, 0), strength)
    N, L = w.node_tree.nodes, w.node_tree.links
    tc = N.new("ShaderNodeTexCoord"); sep = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Generated"], sep.inputs[0])
    cr = N.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].position = 0.0; cr.color_ramp.elements[0].color = (*horizon, 1)
    cr.color_ramp.elements[1].position = 0.35; cr.color_ramp.elements[1].color = (*top, 1)
    if mid:
        e = cr.color_ramp.elements.new(0.09); e.color = (*mid, 1)
    L.new(sep.outputs["Z"], cr.inputs["Fac"]); L.new(cr.outputs["Color"], N["Background"].inputs[0])
    return w


def sun(energy=4.5, rot=SUN_ROT, color=(1.0, 0.95, 0.86), angle=2.5):
    return bl.light('SUN', (0, 0, 500), energy, rot_deg=rot, angle=angle, color=color)


def lumpy(o, amt, scale, seed):
    tx = bpy.data.textures.new(f"lp{seed}", 'CLOUDS'); tx.noise_scale = scale; tx.noise_depth = 2
    d = o.modifiers.new("lp", 'DISPLACE'); d.texture = tx; d.strength = amt; d.mid_level = 0.5
    d.texture_coords = 'LOCAL'
    return d


def slope_mat(period=720):
    """坂の雪：ゆるい吹きだまり＋風のさざ波（どちらも y 方向に period でくり返す）を本当に盛り上げる。"""
    m = snow_mat("slope", fine=0.35, period=period, bump=0.6, dist=1.0)
    m.displacement_method = 'BOTH'
    N, L, b = bl.nodes(m)
    tc = next(n for n in N if n.type == 'TEX_COORD')
    cb = next(n for n in N if n.type == 'COMBXYZ')
    sep = next(n for n in N if n.type == 'SEPXYZ')
    def nz(scale, det=3):
        n = N.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = scale; n.inputs["Detail"].default_value = det
        L.new(cb.outputs[0], n.inputs["Vector"]); return n.outputs["Fac"]
    def op(o, a, b_=None, v=None):
        n = N.new("ShaderNodeMath"); n.operation = o
        for i, x in enumerate((a, b_)):
            if x is None: continue
            if isinstance(x, (int, float)): n.inputs[i].default_value = x
            else: L.new(x, n.inputs[i])
        if v is not None: n.inputs[1].default_value = v
        return n.outputs[0]
    # さざ波：sin(2π·k·y/period ＋ ゆらぎ)
    ph = op('MULTIPLY', sep.outputs["Y"], 2 * math.pi * 26 / period)
    ph = op('ADD', ph, op('MULTIPLY', nz(0.01, 2), 7.0))
    rip = op('SINE', ph)
    msk = op('POWER', nz(0.008, 2), 3.0)
    rip = op('MULTIPLY', op('MULTIPLY', rip, msk), 4.0)
    big = op("MULTIPLY", nz(0.006, 4), 30.0)
    h = op('ADD', big, rip)
    d = N.new("ShaderNodeDisplacement"); d.inputs["Scale"].default_value = 1.0; d.inputs["Midlevel"].default_value = 15.0
    L.new(h, d.inputs["Height"]); L.new(d.outputs[0], N["Material Output"].inputs["Displacement"])
    return m


# ---------- 1) 坂 ----------
if PART in ("all", "slope"):
    sc = bl.reset(); look(sc, 0.6)
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=480, y_subdivisions=900, size=1)
    p = bl.active(); p.scale = (480, 900, 1); bpy.ops.object.transform_apply(scale=True); bl.smooth(p)
    bl.assign(p, slope_mat())
    sky_world((0.42, 0.6, 0.95), (0.75, 0.85, 1.0), 0.9)
    sun()
    cam = bl.camera((0, 0, 500), ortho=720); cam.data.sensor_fit = 'VERTICAL'; cam.data.clip_end = 2000
    bl.render(os.path.join(OUT, "slope.png"), 810, 1620, samples=S)

# ---------- 2) 雪玉（真上） ----------
BALL_R = 10
BCELL = 320
if PART in ("all", "ball"):
    from PIL import Image
    sc = bl.reset(); look(sc, 0.6)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=6, radius=BALL_R, location=(0, 0, BALL_R))
    b = bl.smooth(bl.active())
    lumpy(b, 1.1, 3.2, 1); lumpy(b, 0.35, 0.9, 2)
    bl.assign(b, snow_mat("ball", col=(0.9, 0.93, 0.98), fine=0.9, coarse=0.25, rough=0.7))
    sky_world((0.42, 0.6, 0.95), (0.75, 0.85, 1.0), 0.9)
    sun()
    cam = bl.camera((0, 0, 200), ortho=BALL_R * 2.3); cam.data.clip_end = 500
    cell = BCELL // 2 if FAST else BCELL
    strip = Image.new("RGBA", (cell * 12, cell))
    for k in range(12):
        b.rotation_euler = (math.radians(30 * k), 0, 0)
        f = os.path.join(OUT, f"_b{k}.png")
        bl.render(f, BCELL, BCELL, samples=S, transparent=True)
        strip.paste(Image.open(f), (k * cell, 0)); os.remove(f)
    strip.save(os.path.join(OUT, "ball.png"))

# ---------- 3) 障害物 ----------
OCELL = 240


def pine(x, y, sc=1.0, name="pine"):
    """真上から見たモミの木：ギザギザの段を重ねる。上を向いた面に雪。"""
    tm = mix_by_up(name, (0.03, 0.12, 0.04), 0.85, thresh=0.6, noise=0.55, nscale=0.1)
    N, L, b = bl.nodes(tm); b.inputs["Specular IOR Level"].default_value = 0.15
    bl.noise_color(tm, (0.012, 0.045, 0.02), (0.035, 0.1, 0.035), scale=0.3)
    tiers = [(96, 60, 64), (82, 52, 100), (66, 46, 132), (50, 40, 160), (34, 34, 184), (18, 28, 204)]
    for i, (r, h, z) in enumerate(tiers):
        bpy.ops.mesh.primitive_cone_add(vertices=28, radius1=r * sc, radius2=1, depth=h * sc, location=(x, y, z * sc))
        c = bl.active()
        bm = bmesh.new(); bm.from_mesh(c.data)
        for v in bm.verts:
            if v.co.z < 0:
                k = 0.66 if (round(math.atan2(v.co.y, v.co.x) / (2 * math.pi / 28)) % 2) else 1.0
                j = rr.uniform(0.9, 1.06)
                v.co.x *= k * j; v.co.y *= k * j; v.co.z += (rr.uniform(-6, 4) + (6 if k < 1 else 0)) * sc
        bm.to_mesh(c.data); bm.free()
        c.rotation_euler.z = rr.uniform(0, 6.28)
        sb = c.modifiers.new("s", 'SUBSURF'); sb.levels = sb.render_levels = 2
        lumpy(c, 4 * sc, 7 * sc, 10 + i); lumpy(c, 1.2 * sc, 1.5 * sc, 20 + i)
        bl.assign(c, tm)
    t = bl.cyl(7 * sc, 60 * sc, (x, y, 30 * sc), verts=16); bl.assign(t, bl.mat("bark", (0.2, 0.12, 0.07), 0.9))


def rock(x, y):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=5, radius=1, location=(x, y, 6))
    o = bl.smooth(bl.active()); o.scale = (40, 32, 24); o.rotation_euler.z = 0.5
    bpy.ops.object.transform_apply(scale=True)
    lumpy(o, 9, 18, 21); lumpy(o, 2.5, 4, 22)
    m = mix_by_up("rock", (0.3, 0.3, 0.32), 0.85, thresh=0.93, noise=0.3, nscale=0.06)
    bl.noise_color(m, (0.22, 0.22, 0.24), (0.4, 0.39, 0.38), scale=0.15)
    bl.assign(o, m)


def bush(x, y):
    m = mix_by_up("bush", (0.12, 0.13, 0.08), 0.85, thresh=0.5, noise=0.3, nscale=0.2)
    for i in range(9):
        a = i * 2.4; d = 0 if i == 0 else rr.uniform(14, 26)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4, radius=rr.uniform(16, 24), location=(x + math.cos(a) * d, y + math.sin(a) * d, 18 + rr.uniform(-4, 6)))
        o = bl.smooth(bl.active()); o.scale.z = 0.75; lumpy(o, 4, 5, 30 + i); bl.assign(o, m)
    # 赤い実（南天）を少し
    bm_ = bl.mat("berry", (0.75, 0.05, 0.04), 0.3)
    for i in range(10):
        a = rr.uniform(0, 6.28); d = rr.uniform(8, 30)
        bl.assign(bl.sphere(1.8, (x + math.cos(a) * d, y + math.sin(a) * d, 36 + rr.uniform(-4, 4))), bm_)


def patch_mask(N, L, tc, radius, edge=0.25, nscale=0.02, wob=0.35):
    """中心からの距離＋ノイズで、ふちのギザギザした丸いマスク（1＝中）"""
    sep = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Object"], sep.inputs[0])
    ln = N.new("ShaderNodeVectorMath"); ln.operation = 'LENGTH'; L.new(tc.outputs["Object"], ln.inputs[0])
    dv = N.new("ShaderNodeMath"); dv.operation = 'DIVIDE'; dv.inputs[1].default_value = radius; L.new(ln.outputs["Value"], dv.inputs[0])
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = nscale; nz.inputs["Detail"].default_value = 6; L.new(tc.outputs["Object"], nz.inputs["Vector"])
    ad = N.new("ShaderNodeMath"); ad.operation = 'MULTIPLY_ADD'; ad.inputs[1].default_value = wob; L.new(nz.outputs["Fac"], ad.inputs[0]); L.new(dv.outputs[0], ad.inputs[2])
    cr = N.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].position = 1.0 - edge; cr.color_ramp.elements[0].color = (1, 1, 1, 1)
    cr.color_ramp.elements[1].position = 1.0 + 0.02; cr.color_ramp.elements[1].color = (0, 0, 0, 1)
    L.new(ad.outputs[0], cr.inputs["Fac"])
    return cr.outputs["Color"]


def dirt(x, y):
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=120, y_subdivisions=120, size=200, location=(x, y, 0.3))
    o = bl.active(); lumpy(o, 3, 14, 40)
    m = bl.mat("dirt", (0.25, 0.17, 0.1), 0.95)
    bl.noise_color(m, (0.2, 0.14, 0.08), (0.4, 0.36, 0.18), scale=0.06, lo=0.4, hi=0.7)
    N, L, b = bl.nodes(m)
    tc = N.new("ShaderNodeTexCoord")
    mk = patch_mask(N, L, tc, 78, edge=0.35)
    L.new(mk, b.inputs["Alpha"])
    vor = N.new("ShaderNodeTexVoronoi"); vor.inputs["Scale"].default_value = 0.35; L.new(tc.outputs["Object"], vor.inputs["Vector"])
    bp = N.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.6; L.new(vor.outputs["Distance"], bp.inputs["Height"]); L.new(bp.outputs["Normal"], b.inputs["Normal"])
    bl.assign(o, m)
    # 枯れ草の小さなたば
    gm = bl.mat("grass", (0.3, 0.24, 0.12), 0.8)
    for i in range(26):
        a = rr.uniform(0, 6.28); d = rr.uniform(0, 60)
        for j in range(5):
            bl.assign(bl.cube((0.8, 0.8, rr.uniform(8, 16)), (x + math.cos(a) * d + rr.uniform(-2, 2), y + math.sin(a) * d + rr.uniform(-2, 2), 4), rot=(rr.uniform(-40, 40), rr.uniform(-40, 40), 0)), gm)


def powder(x, y):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=6, radius=1, location=(x, y, -2))
    o = bl.smooth(bl.active()); o.scale = (86, 74, 9); bpy.ops.object.transform_apply(scale=True)
    lumpy(o, 6, 26, 50); lumpy(o, 2.6, 2.5, 51)
    bl.assign(o, snow_mat("powder", col=(0.97, 0.98, 1.0), fine=1.6, coarse=0.06, rough=0.75))
    # きらきら
    sp = bl.emission("spark", (1, 1, 1), 6)
    for i in range(70):
        a = rr.uniform(0, 6.28); d = rr.uniform(0, 70)
        bl.assign(bl.sphere(0.5, (x + math.cos(a) * d, y + math.sin(a) * d * 0.85, 7 - d * 0.08)), sp)


def ice(x, y):
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=60, y_subdivisions=60, size=220, location=(x, y, 0.4))
    o = bl.active()
    m = bl.mat("ice", (0.55, 0.75, 0.92), 0.04, Coat_Weight=1.0)
    N, L, b = bl.nodes(m)
    tc = N.new("ShaderNodeTexCoord")
    mk = patch_mask(N, L, tc, 92, edge=0.12, nscale=0.012, wob=0.4)
    L.new(mk, b.inputs["Alpha"])
    vor = N.new("ShaderNodeTexVoronoi"); vor.feature = 'DISTANCE_TO_EDGE'; vor.inputs["Scale"].default_value = 0.04; L.new(tc.outputs["Object"], vor.inputs["Vector"])
    cr = N.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].position = 0.0; cr.color_ramp.elements[0].color = (0.95, 0.98, 1, 1)
    cr.color_ramp.elements[1].position = 0.03; cr.color_ramp.elements[1].color = (0.45, 0.66, 0.86, 1)
    L.new(vor.outputs["Distance"], cr.inputs["Fac"]); L.new(cr.outputs["Color"], b.inputs["Base Color"])
    bl.assign(o, m)


if PART in ("all", "obj"):
    sc = bl.reset(); look(sc, 0.6)
    makers = [pine, rock, bush, dirt, powder, ice]
    for i, f in enumerate(makers):
        cx, cy = (i % 3 - 1) * OCELL, (0.5 - i // 3) * OCELL
        f(cx - 25, cy + 25)
    sc_ = bl.shadow_catcher(OCELL * 3 + 40)
    sky_world((0.42, 0.6, 0.95), (0.75, 0.85, 1.0), 0.9)
    sun()
    cam = bl.camera((0, 0, 900), ortho=OCELL * 3); cam.data.sensor_fit = 'HORIZONTAL'; cam.data.clip_end = 2000
    bl.render(os.path.join(OUT, "obj.png"), OCELL * 3 * 2, OCELL * 2 * 2, samples=S, transparent=True)

# ---------- 4) 庭（ゴール） ----------
CAM_Y = -600


def yard_scene():
    sc = bl.reset(); look(sc, 0.0)
    # 地面の雪
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=360, y_subdivisions=360, size=1, location=(0, 1200, 0))
    g = bl.active(); g.scale = (5000, 4400, 1); bpy.ops.object.transform_apply(scale=True)
    lumpy(g, 14, 200, 60); lumpy(g, 2, 20, 61); bl.smooth(g)
    bl.assign(g, snow_mat("ground", fine=0.5, coarse=0.004))
    # 家の壁（板ばり）と窓
    wall = bl.mat("siding", (0.62, 0.5, 0.38), 0.7)
    N, L, b = bl.nodes(wall)
    tc = N.new("ShaderNodeTexCoord"); wv = N.new("ShaderNodeTexWave"); wv.wave_type = 'BANDS'; wv.bands_direction = 'Z'
    wv.inputs["Scale"].default_value = 0.025; wv.inputs["Distortion"].default_value = 0; L.new(tc.outputs["Object"], wv.inputs["Vector"])
    bp = N.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 1.0; bp.inputs["Distance"].default_value = 3.0; L.new(wv.outputs["Fac"], bp.inputs["Height"]); L.new(bp.outputs["Normal"], b.inputs["Normal"])
    w = bl.cube((920, 30, 520), (-540, 1100, 260)); bl.assign(w, wall)
    fr = bl.mat("frame", (0.92, 0.9, 0.85), 0.5)
    for (x, z, ww, hh) in ((-215, 190, 120, 110),):
        Y0 = 1083; f = bl.cube((ww + 16, 10, hh + 16), (x, Y0, z)); bl.assign(f, fr)
        gl = bl.cube((ww, 6, hh), (x, Y0 - 5, z)); bl.assign(gl, bl.emission("win", (1.0, 0.66, 0.32), 4))
        bl.assign(bl.cube((6, 8, hh), (x, Y0 - 7, z)), fr); bl.assign(bl.cube((ww, 8, 6), (x, Y0 - 7, z)), fr)
        sl = bl.cube((ww + 30, 30, 8), (x, Y0 - 13, z - hh / 2 - 12)); bl.assign(sl, fr)
        sn = bl.cube((ww + 24, 26, 6), (x, Y0 - 15, z - hh / 2 - 5)); bl.bevel(sn, 3, 3); bl.assign(sn, snow_mat("sill"))
        lt = bl.light('AREA', (x, Y0 - 30, z), 2500, rot_deg=(-90, 0, 0), size=ww, color=(1.0, 0.7, 0.4))
    # 雨どいの下の雪の帯
    sb = bl.cube((920, 60, 20), (-540, 1060, 2)); bl.bevel(sb, 8, 4); lumpy(sb, 5, 30, 62); bl.assign(sb, snow_mat("drift"))
    # 木のさく（右）
    fw = bl.wood("fence", light=(0.5, 0.36, 0.24), dark=(0.3, 0.2, 0.12), scale=0.08)
    for i in range(9):
        x = 60 + i * 34
        p = bl.cube((22, 6, 130 + (i % 2) * 6), (x, 820, 65)); bl.bevel(p, 1.5, 2); bl.assign(p, fw)
        cap = bl.cube((24, 10, 7), (x, 820, 133 + (i % 2) * 6)); bl.bevel(cap, 3.5, 3); lumpy(cap, 1.2, 4, 70 + i); bl.assign(cap, snow_mat(f"cap{i}"))
    for z in (40, 100):
        r = bl.cube((300, 5, 10), (196, 826, z)); bl.assign(r, fw)
    # 奥の木
    for i, (x, y, k) in enumerate(((300, 1500, 1.5), (-40, 2700, 2.3), (480, 3100, 2.6), (150, 3600, 2.8))):
        pine(x, y, k, f"far{i}")
    # 外灯
    pole = bl.cyl(3, 220, (-60, 880, 110), verts=16); bl.assign(pole, bl.mat("iron", (0.1, 0.1, 0.11), 0.4, metal=1.0))
    gl = bl.sphere(14, (-60, 880, 228)); bl.assign(gl, bl.emission("lamp", (1.0, 0.8, 0.5), 12))
    bl.light('POINT', (-60, 860, 228), 80000, size=14, color=(1.0, 0.78, 0.5))
    # 夕暮れの空と光
    sky_world((0.07, 0.1, 0.3), (1.0, 0.5, 0.25), 1.0, mid=(0.5, 0.33, 0.55))
    bl.light('SUN', (0, 0, 500), 1.6, rot_deg=(80, 0, -60), angle=4, color=(1.0, 0.62, 0.42))
    # 正面からのやわらかい光（カメラ側の家の窓あかり）
    bl.light('AREA', (-180, CAM_Y + 50, 180), 90000, rot_deg=(75, 0, -30), size=200, color=(1.0, 0.82, 0.62))
    cam = bl.camera((0, CAM_Y, 110), rot_deg=(88, 0, 0), lens=32); cam.data.sensor_fit = 'VERTICAL'; cam.data.clip_end = 5000
    return sc, cam


def proj(cam, p, W=540, H=1080):
    v = world_to_camera_view(bpy.context.scene, cam, mathutils.Vector(p))
    return [v.x * W, (1 - v.y) * H]


if PART in ("all", "yard"):
    from PIL import Image
    sc, cam = yard_scene()
    sc.render.resolution_x, sc.render.resolution_y = 810, 1620
    bpy.context.view_layer.update()
    g0 = proj(cam, (0, 0, 0)); g1 = proj(cam, (0, 0, 100))
    GEO["yard"] = {"ground": g0, "pxcm": (g0[1] - g1[1]) / 100}
    bl.render(os.path.join(OUT, "yard.png"), 810, 1620, samples=S)
    # 雪玉（正面）と小物は、庭と同じ光で、ほかを消してから透明で
    keep = {o.name for o in bpy.data.objects if o.type in ('LIGHT', 'CAMERA')}
    for o in bpy.data.objects:
        if o.name not in keep:
            o.hide_render = True
    sc.render.resolution_percentage = 50 if FAST else 100
    R = 50
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=6, radius=R, location=(0, 0, R))
    b = bl.smooth(bl.active()); lumpy(b, 5.5, 16, 91); lumpy(b, 1.7, 4.5, 92)
    bl.assign(b, snow_mat("ballf", col=(0.9, 0.93, 0.98), fine=0.18, coarse=0.05, rough=0.7))
    parts = {}

    def shoot(name, objs, anchor):
        for o in objs:
            o.hide_render = False
        f = os.path.join(OUT, f"_{name}.png")
        bl.render(f, 810, 1620, samples=S, transparent=True)
        for o in objs:
            o.hide_render = True
        im = Image.open(f); os.remove(f)
        bb = im.getchannel("A").point(lambda v: 255 if v > 3 else 0).getbbox()
        sc_ = im.width / 540
        parts[name] = {"im": im.crop(bb), "bb": [c / sc_ for c in bb], "anchor": proj(cam, anchor)}
    shoot("ball", [b], (0, 0, R))
    # 小物：頭（半径 30）が (0,0,130) にあるつもりで置く
    HZ, HR = 130, 30
    bk = bl.cyl(20, 26, (0, 0, HZ + HR + 6), verts=48); bk.rotation_euler = (0, math.radians(-12), 0)
    bm = bmesh.new(); bm.from_mesh(bk.data)
    for v in bm.verts:
        if v.co.z > 0:
            v.co.x *= 0.78; v.co.y *= 0.78
    bm.to_mesh(bk.data); bm.free(); bl.bevel(bk, 1.2, 3)
    bl.assign(bk, bl.mat("bucket", (0.75, 0.12, 0.1), 0.35))
    shoot("bucket", [bk], (0, 0, HZ + HR - 6))
    bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=4.2, radius2=0.4, depth=24, location=(0, 0, 0))
    cr = bl.smooth(bl.active())
    cr.rotation_euler = (math.radians(100), 0, math.radians(-50)); cr.location = (8, -HR - 8, HZ - 3)
    m = bl.mat("carrot", (0.95, 0.38, 0.06), 0.55)
    N, L, b2 = bl.nodes(m); wv = N.new("ShaderNodeTexWave"); wv.inputs["Scale"].default_value = 0.6; wv.bands_direction = 'Z'
    tc = N.new("ShaderNodeTexCoord"); L.new(tc.outputs["Object"], wv.inputs["Vector"])
    bp = N.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.3; L.new(wv.outputs["Fac"], bp.inputs["Height"]); L.new(bp.outputs["Normal"], b2.inputs["Normal"])
    bl.assign(cr, m)
    shoot("nose", [cr], (0, -HR, HZ - 3))
    coal = bl.mat("coal", (0.03, 0.03, 0.035), 0.45)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4, radius=3.2, location=(0, -HR - 1, HZ + 8))
    e = bl.smooth(bl.active()); lumpy(e, 0.6, 1.2, 93); bl.assign(e, coal)
    shoot("coal", [e], (0, -HR - 1, HZ + 8))
    # 枝の腕（右）。左は左右反転で使う
    tw = bl.mat("twig", (0.25, 0.15, 0.08), 0.85)
    segs = []

    def branch(p0, ang, ln, r, depth):
        dx, dz = math.cos(ang), math.sin(ang)
        p1 = (p0[0] + dx * ln, p0[1], p0[2] + dz * ln)
        c = bl.cyl(r, ln, ((p0[0] + p1[0]) / 2, p0[1], (p0[2] + p1[2]) / 2), verts=10)
        c.rotation_euler = (0, math.pi / 2 - ang, 0); bl.assign(c, tw); segs.append(c)
        if depth:
            branch(p1, ang + 0.5, ln * 0.45, r * 0.6, depth - 1)
            branch(((p0[0] + p1[0] * 2) / 3, p0[1], (p0[2] + p1[2] * 2) / 3), ang - 0.55, ln * 0.35, r * 0.55, 0)
            branch(p1, ang - 0.15, ln * 0.4, r * 0.6, 0)
    branch((44, 0, 62), 0.42, 50, 1.6, 1)
    shoot("arm", segs, (44, 0, 62))
    # まとめて 1 枚に（よこ並び）
    x = 0; H = max(p["im"].height for p in parts.values())
    atlas = Image.new("RGBA", (sum(p["im"].width + 4 for p in parts.values()), H))
    meta = {}
    sc_ = atlas.width and parts["ball"]["im"].width / (parts["ball"]["bb"][2] - parts["ball"]["bb"][0])
    for k, p in parts.items():
        atlas.paste(p["im"], (x, 0))
        bb = p["bb"]
        meta[k] = {"sx": x / sc_, "sw": p["im"].width / sc_, "sh": p["im"].height / sc_, "x": bb[0], "y": bb[1], "ax": p["anchor"][0], "ay": p["anchor"][1]}
        x += p["im"].width + 4
    ball_im = parts["ball"]["im"]
    atlas.save(os.path.join(OUT, "parts.png"))
    GEO["parts"] = meta
    GEO["partsScale"] = sc_
    GEO["ref"] = {"bodyR": R, "headR": HR, "headZ": HZ}

if PART in ("all", "yard", "obj", "ball", "slope"):
    GEO.update({"ballR": BALL_R, "ballCell": BCELL // 2 if FAST else BCELL, "ballCm": BALL_R * 2.3, "ocell": OCELL, "oPxPerCm": 1 if FAST else 2})
    json.dump(GEO, open(gp, "w"))
print("done")
