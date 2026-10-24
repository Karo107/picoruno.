"""マンションの灯り：素材レンダリング。

夜の住宅街。道路から見上げた 11 階建てのマンション（7 列 × 10 階の窓＋1 階のロビー）。
out/off.png     ぜんぶの部屋が消灯
out/on.png      ぜんぶの部屋が点灯（ゲームでは、窓ごとに on の絵を切りぬいて重ねる）
out/geo.json    窓 70 個の四すみ（画面）
540x1080 を 1.5 倍（スマホのたて長に合わせて細長い）。ここは 1 = 1m（ふつうの大きさ）。
"""
import json, math, os, sys, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "common"))
import bpy, mathutils
from bpy_extras.object_utils import world_to_camera_view
import bl

OUT = os.path.join(os.path.dirname(__file__), "out")
os.makedirs(OUT, exist_ok=True)
FAST = "--fast" in sys.argv
S = 32 if FAST else 64
rr = random.Random(16)
COLS, FLOORS = 7, 10
BAY, FH = 3.2, 3.0
BW = COLS * BAY                     # 建物のはば
WW, WH, SILL = 1.9, 1.55, 0.95      # 窓のはば・高さ・床からの高さ
X0 = -BW / 2


def concrete(name, col, scale=1.5):
    m = bl.mat(name, col, 0.85)
    bl.noise_color(m, tuple(c * 0.86 for c in col), col, scale=scale, detail=6)
    bl.noise_bump(m, scale=40, strength=0.15)
    return m


def window_xy(c, f):
    """c 列・f 階（1〜10）の窓の左下"""
    return X0 + c * BAY + (BAY - WW) / 2, f * FH + SILL


def building(lit):
    fac = concrete("fac", (0.7, 0.64, 0.56))
    band = concrete("band", (0.5, 0.49, 0.47))
    # 正面の壁：窓の穴をあけた板を、帯ごとに組む
    H_ = (FLOORS + 1) * FH
    for f in range(FLOORS + 1):
        z0 = f * FH
        if f == 0:
            continue
        # 窓の下と上の帯
        b = bl.cube((BW, 0.4, SILL), (0, 0, z0 + SILL / 2)); bl.assign(b, fac)
        top = FH - SILL - WH
        b = bl.cube((BW, 0.4, top), (0, 0, z0 + SILL + WH + top / 2)); bl.assign(b, fac)
        for c in range(COLS + 1):
            x = X0 + c * BAY
            w = (BAY - WW) if 0 < c < COLS else (BAY - WW) / 2
            cx_ = x if 0 < c < COLS else (x + w / 2 if c == 0 else x - w / 2)
            p = bl.cube((w, 0.4, WH), (cx_, 0, z0 + SILL + WH / 2)); bl.assign(p, fac)
        # 階のさかいの出っぱり（影ができる）
        e = bl.cube((BW + 0.3, 0.7, 0.18), (0, -0.2, z0)); bl.assign(e, band)
        # 窓わくと、室外機・植木（ところどころ）
        for c in range(COLS):
            wx, wz = window_xy(c, f)
            fr = bl.mat("frame", (0.25, 0.25, 0.27), 0.4, metal=0.6)
            for (sx, sz, ox, oz) in ((WW + 0.1, 0.07, WW / 2, 0), (WW + 0.1, 0.07, WW / 2, WH), (0.07, WH, 0, WH / 2), (0.07, WH, WW, WH / 2), (0.05, WH, WW / 2, WH / 2)):
                o = bl.cube((sx, 0.08, sz), (wx + ox, -0.22, wz + oz)); bl.assign(o, fr)
            sill = bl.cube((WW + 0.25, 0.3, 0.06), (wx + WW / 2, -0.3, wz - 0.04)); bl.assign(sill, band)
            if rr.random() < 0.18:
                pot = bl.cyl(0.12, 0.2, (wx + rr.uniform(0.2, WW - 0.2), -0.33, wz + 0.08), verts=16); bl.assign(pot, bl.mat("pot", (0.55, 0.3, 0.2), 0.7))
                leaf = bl.sphere(0.22, (pot.location.x, -0.33, wz + 0.35)); leaf.scale = (1, 1, 1.2); bl.assign(leaf, bl.mat("leaf", (0.12, 0.25, 0.1), 0.8))
    # 1 階：ロビー（いつも明るい）
    lob = bl.cube((BW, 0.4, 0.6), (0, 0, FH - 0.3)); bl.assign(lob, band)
    for x in (-BW / 2 + 1.5, BW / 2 - 1.5):
        p = bl.cube((3.0, 0.4, FH - 0.6), (x, 0, (FH - 0.6) / 2)); bl.assign(p, fac)
    glass = bl.cube((BW - 6, 0.05, FH - 0.6), (0, 0.1, (FH - 0.6) / 2)); bl.assign(glass, bl.mat("lobbyglass", (0.9, 0.95, 1), 0.05, Transmission_Weight=1.0, IOR=1.45))
    lobby = bl.cube((BW - 6, 4, 0.05), (0, 2.2, FH - 0.65)); bl.assign(lobby, bl.emission("lobbylight", (1, 0.86, 0.66), 1.1))
    for i in range(9):
        mx_ = -(BW - 6) / 2 + (BW - 6) * i / 8
        bl.assign(bl.cube((0.12, 0.15, FH - 0.6), (mx_, 0.05, (FH - 0.6) / 2)), bl.mat(f"mull{i}", (0.15, 0.15, 0.17), 0.4, metal=1.0))
    lf = bl.cube((BW - 6, 4, 0.05), (0, 2.2, 0.02)); bl.assign(lf, bl.mat("lobbyfloor", (0.75, 0.7, 0.62), 0.3))
    lw = bl.cube((BW - 6, 0.1, FH), (0, 4.2, FH / 2)); bl.assign(lw, bl.mat("lobbywall", (0.5, 0.44, 0.37), 0.6))
    # 屋上：手すりと給水タンク
    roof = bl.cube((BW + 0.4, 0.8, 0.5), (0, -0.1, H_ + 0.25)); bl.assign(roof, band)
    tank = bl.cyl(1.4, 2.2, (BW / 2 - 4, 4, H_ + 1.6), verts=32); bl.assign(tank, bl.mat("tank", (0.7, 0.72, 0.75), 0.5))
    ant = bl.cyl(0.04, 4, (-BW / 2 + 3, 3, H_ + 2), verts=8); bl.assign(ant, bl.mat("ant", (0.3, 0.3, 0.3), 0.5))
    red = bl.sphere(0.12, (-BW / 2 + 3, 3, H_ + 4.05)); bl.assign(red, bl.emission("redlamp", (1, 0.1, 0.05), 40))
    # 側面（右がわが少し見える）
    side = bl.cube((0.4, 12, H_), (BW / 2 + 0.2, 6, H_ / 2)); bl.assign(side, concrete("side", (0.45, 0.44, 0.42)))
    side2 = bl.cube((0.4, 12, H_), (-BW / 2 - 0.2, 6, H_ / 2)); bl.assign(side2, concrete("side2", (0.45, 0.44, 0.42)))


def rooms(lit):
    """窓のうしろの部屋。lit なら天井の灯りがつく"""
    warm = [(1, 0.78, 0.5), (1, 0.82, 0.58), (1, 0.72, 0.45), (0.9, 0.93, 1.0)]
    for f in range(1, FLOORS + 1):
        for c in range(COLS):
            r = random.Random(f * 31 + c)        # 部屋の中身は on/off で同じにする
            wx, wz = window_xy(c, f)
            z0 = f * FH
            cxr = X0 + c * BAY + BAY / 2
            wallc = r.choice([(0.85, 0.8, 0.7), (0.8, 0.75, 0.68), (0.75, 0.78, 0.8), (0.86, 0.82, 0.76), (0.7, 0.62, 0.52)])
            back = bl.cube((BAY - 0.2, 0.1, FH - 0.1), (cxr, 4.0, z0 + FH / 2)); bl.assign(back, bl.mat(f"bw{f}{c}", wallc, 0.8))
            for sx in (-1, 1):
                sw = bl.cube((0.1, 4, FH - 0.1), (cxr + sx * (BAY / 2 - 0.15), 2.1, z0 + FH / 2)); bl.assign(sw, bl.mat(f"sw{f}{c}", tuple(v * 0.9 for v in wallc), 0.8))
            fl = bl.cube((BAY - 0.2, 4, 0.1), (cxr, 2.1, z0 + 0.05)); bl.assign(fl, bl.mat(f"fl{f}{c}", (0.45, 0.32, 0.2), 0.5))
            ce = bl.cube((BAY - 0.2, 4, 0.1), (cxr, 2.1, z0 + FH - 0.05)); bl.assign(ce, bl.mat(f"ce{f}{c}", (0.9, 0.9, 0.88), 0.8))
            # 家具のかげ（棚・ソファ・観葉植物）
            k = r.random()
            if k < 0.4:
                sh = bl.cube((r.uniform(0.6, 1.2), 0.4, r.uniform(1.0, 1.8)), (cxr + r.uniform(-0.8, 0.8), 3.7, z0 + 0.9)); bl.assign(sh, bl.mat(f"sh{f}{c}", (0.35, 0.25, 0.18), 0.6))
            elif k < 0.7:
                so = bl.cube((1.6, 0.8, 0.8), (cxr + r.uniform(-0.5, 0.5), 3.4, z0 + 0.4)); bl.assign(so, bl.mat(f"so{f}{c}", r.choice([(0.3, 0.4, 0.5), (0.55, 0.35, 0.3), (0.4, 0.45, 0.35)]), 0.9))
            else:
                pl = bl.sphere(0.5, (cxr + r.uniform(-0.9, 0.9), 3.2, z0 + 1.2)); pl.scale = (1, 1, 1.4); bl.assign(pl, bl.mat(f"pl{f}{c}", (0.15, 0.3, 0.12), 0.8))
            # カーテン（左右）かブラインド
            cc = r.choice([(0.9, 0.86, 0.78), (0.75, 0.82, 0.86), (0.86, 0.72, 0.62), (0.8, 0.8, 0.72), (0.65, 0.72, 0.58), (0.9, 0.76, 0.8)])
            cm = bl.mat(f"cu{f}{c}", cc, 0.9, Transmission_Weight=0.0, Subsurface_Weight=0.0)
            N, L, b = bl.nodes(cm)
            # 光をすこし通す布
            tr = N.new("ShaderNodeBsdfTranslucent"); tr.inputs[0].default_value = (*cc, 1)
            mx = N.new("ShaderNodeMixShader"); mx.inputs[0].default_value = 0.45
            out = N["Material Output"]
            L.new(b.outputs[0], mx.inputs[1]); L.new(tr.outputs[0], mx.inputs[2]); L.new(mx.outputs[0], out.inputs[0])
            if r.random() < 0.75:
                op = r.uniform(0.25, 0.7)
                for sx in (-1, 1):
                    w = WW * (1 - op) / 2 + 0.1
                    cu = bl.cube((w, 0.06, WH + 0.2), (wx + (WW / 2) + sx * (WW / 2 - w / 2 + 0.05), 0.35, wz + WH / 2)); bl.assign(cu, cm)
                    wv = cu.modifiers.new("w", 'WAVE'); wv.use_normal = False; wv.use_y = True; wv.use_x = False; wv.height = 0.05; wv.width = 0.12; wv.narrowness = 1.2
            else:
                for i in range(int(WH / 0.12 * r.uniform(0.2, 0.7))):
                    sl = bl.cube((WW, 0.06, 0.08), (wx + WW / 2, 0.35, wz + WH - 0.06 - i * 0.12), rot=(30, 0, 0)); bl.assign(sl, cm)
            # 天井の灯り
            col = r.choice(warm)
            lamp = bl.cube((0.8, 0.8, 0.04), (cxr, 2.2, z0 + FH - 0.12))
            if lit:
                bl.assign(lamp, bl.emission(f"lp{f}{c}", col, 9))
                l = bl.light('POINT', (cxr, 2.2, z0 + FH - 0.4), 55, size=0.6, color=col)
                if r.random() < 0.2:        # テレビの青い光
                    tv = bl.cube((0.9, 0.05, 0.5), (cxr + r.uniform(-0.6, 0.6), 3.9, z0 + 1.0)); bl.assign(tv, bl.emission(f"tv{f}{c}", (0.5, 0.65, 1), 6))
            else:
                bl.assign(lamp, bl.mat(f"lpoff{f}{c}", (0.85, 0.85, 0.82), 0.5))


def glass():
    gm = bl.mat("glass", (0.95, 0.97, 1), 0.04, Transmission_Weight=1.0, IOR=1.45)
    for f in range(1, FLOORS + 1):
        for c in range(COLS):
            wx, wz = window_xy(c, f)
            g = bl.cube((WW, 0.02, WH), (wx + WW / 2, -0.12, wz + WH / 2)); bl.assign(g, gm)
            g.visible_shadow = False


def street():
    # 道路・歩道・電柱と街灯・となりの建物のかげ
    road = bl.plane((200, 80), (0, -40, -0.01)); bl.assign(road, bl.mat("road", (0.12, 0.12, 0.13), 0.7))
    walk = bl.cube((200, 5, 0.15), (0, -2.8, 0.07)); bl.assign(walk, concrete("walk", (0.4, 0.39, 0.37), 3))
    for x in (-15, 14):
        pole = bl.cyl(0.08, 6, (x, -5, 3), verts=12); bl.assign(pole, bl.mat("pole", (0.25, 0.25, 0.27), 0.4, metal=0.7))
        head = bl.cube((0.7, 0.3, 0.12), (x, -5.3, 6.0)); bl.assign(head, bl.mat("lhead", (0.2, 0.2, 0.2), 0.4))
        bulb = bl.cube((0.5, 0.2, 0.03), (x, -5.3, 5.93)); bl.assign(bulb, bl.emission("bulb", (1, 0.85, 0.6), 30))
        bl.light('SPOT', (x, -5.3, 5.9), 900, rot_deg=(0, 0, 0), size=0.3, color=(1, 0.82, 0.55)).data.spot_size = math.radians(110)
    # 足もとから壁を照らす灯り（上に行くほど暗い）
    for x in (-7, 7):
        sp = bl.light('SPOT', (x, -3, 0.3), 2500, rot_deg=(163, 0, 0), size=0.2, color=(1, 0.75, 0.45)); sp.data.spot_size = math.radians(40); sp.data.spot_blend = 0.8
    # となりの低い建物と木（シルエット）
    for (x, w, h) in ((-22, 9, 14), (22, 9, 18), (-30, 8, 22), (31, 10, 10)):
        nb = bl.cube((w, 8, h), (x, 6, h / 2)); bl.assign(nb, concrete(f"nb{x}", (0.18, 0.18, 0.2)))
        for i in range(int(h / 3)):
            for j in range(int(w / 3)):
                if rr.random() < 0.35:
                    wl = bl.cube((1.0, 0.05, 0.8), (x - w / 2 + 1.5 + j * 3, 1.95, 1.8 + i * 3)); bl.assign(wl, bl.emission(f"nw{x}{i}{j}", rr.choice([(1, 0.8, 0.55), (0.9, 0.9, 1)]), 3))
    for (x, y) in ((-12.5, -6), (12, -7)):
        tr = bl.sphere(2.2, (x, y, 4.5)); tr.scale = (1, 1, 1.15)
        d = tr.modifiers.new("d", 'DISPLACE'); t = bpy.data.textures.new("tt", 'CLOUDS'); t.noise_scale = 0.8; d.texture = t; d.strength = 0.7
        bl.assign(tr, bl.mat("tree", (0.05, 0.09, 0.05), 0.9))
        tk = bl.cyl(0.18, 3, (x, y, 1.5), verts=12); bl.assign(tk, bl.mat("trunk", (0.1, 0.07, 0.05), 0.9))


def sky():
    w = bpy.data.worlds.new("w"); bpy.context.scene.world = w; w.use_nodes = True
    N, L = w.node_tree.nodes, w.node_tree.links
    bg = N["Background"]
    tc = N.new("ShaderNodeTexCoord"); sep = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Generated"], sep.inputs[0])
    cr = N.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].position = 0.5; cr.color_ramp.elements[0].color = (0.05, 0.07, 0.16, 1)
    cr.color_ramp.elements[1].position = 0.75; cr.color_ramp.elements[1].color = (0.008, 0.012, 0.04, 1)
    L.new(sep.outputs["Z"], cr.inputs["Fac"])
    # 星
    vo = N.new("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = 260; L.new(tc.outputs["Generated"], vo.inputs["Vector"])
    st = N.new("ShaderNodeMath"); st.operation = 'LESS_THAN'; st.inputs[1].default_value = 0.035; L.new(vo.outputs["Distance"], st.inputs[0])
    sm = N.new("ShaderNodeMath"); sm.operation = 'MULTIPLY'; sm.inputs[1].default_value = 1.6; L.new(st.outputs[0], sm.inputs[0])
    ad = N.new("ShaderNodeMix"); ad.data_type = 'RGBA'; ad.blend_type = 'ADD'; ad.inputs[0].default_value = 1
    L.new(cr.outputs["Color"], ad.inputs[6]); L.new(sm.outputs[0], ad.inputs[7])
    L.new(ad.outputs[2], bg.inputs["Color"]); bg.inputs["Strength"].default_value = 1.0
    # 月あかり
    bl.light('SUN', (0, 0, 50), 0.12, rot_deg=(55, 0, 30), angle=1, color=(0.7, 0.8, 1))
    moon = bl.sphere(2.2, (11, 70, 62)); bl.assign(moon, bl.emission("moon", (1, 0.96, 0.85), 4))


def proj(sc, cam, p):
    v = world_to_camera_view(sc, cam, mathutils.Vector(p))
    return [round(v.x * 540, 1), round((1 - v.y) * 1080, 1)]


def scene(lit):
    sc = bl.reset(); sc.view_settings.look = 'AgX - Medium High Contrast'; sc.view_settings.exposure = 0.6
    sky(); building(lit); rooms(lit); glass(); street()
    cam = bl.camera((0, -52, 1.6), rot_deg=(90 + 19, 0, 0), lens=26)
    cam.data.sensor_fit = 'VERTICAL'; cam.data.sensor_height = 24; cam.data.clip_end = 1000
    sc.render.resolution_x, sc.render.resolution_y = 810, 1620
    bpy.context.view_layer.update()
    return sc, cam


part = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else "all"
for lit in (False, True):
    name = "on" if lit else "off"
    if part not in ("all", name, "geo"):
        continue
    sc, cam = scene(lit)
    if not lit:
        wins = []
        for f in range(1, FLOORS + 1):
            for c in range(COLS):
                wx, wz = window_xy(c, f)
                wins.append([proj(sc, cam, (wx, -0.12, wz)), proj(sc, cam, (wx + WW, -0.12, wz)), proj(sc, cam, (wx + WW, -0.12, wz + WH)), proj(sc, cam, (wx, -0.12, wz + WH))])
        geo = {"cols": COLS, "floors": FLOORS, "win": wins}
        json.dump(geo, open(os.path.join(OUT, "geo.json"), "w")); print("geo", wins[0], wins[-1])
        if part == "geo":
            sys.exit(0)
    bl.render(os.path.join(OUT, f"{name}.png"), 810, 1620, samples=S)
print("done")
