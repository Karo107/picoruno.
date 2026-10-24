"""ぴったりエレベーター：素材レンダリング。

夜のビルの断面ミニチュア（12階）。まん中がエレベーターの縦穴、左右に部屋（人はいない）。
out/bldg.jpg   ビルの断面（縦長、正投影。1階 = FLOOR_PX px）
out/car.png    エレベーターのかご（透明背景）
out/geo.json   各階の床の y（画像の px）、縦穴の x、かごの大きさ
1 = 1cm。
"""
import json, math, os, sys, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "common"))
import bpy
import bl

OUT = os.path.join(os.path.dirname(__file__), "out")
os.makedirs(OUT, exist_ok=True)
FAST = "--fast" in sys.argv
S = 24 if FAST else 96
NF = 12                 # 階の数（1F〜12F）
FH = 300                # 1階の高さ cm
SW = 220                # 縦穴の幅
RW = 420                # 部屋の幅（片側）
DEPTH = 360
WIDTH = SW + 2 * RW + 2 * 30     # 外壁込み
TOTAL_H = NF * FH + 120          # 屋上まで
IMG_W = 1080
SCALE = IMG_W / (WIDTH + 80)     # px/cm
rr = random.Random(7)


def concrete(name, c=(0.62, 0.6, 0.57)):
    m = bl.mat(name, c, 0.8); bl.noise_bump(m, scale=0.08, strength=0.15); return m


def wall_paper(name, c):
    m = bl.mat(name, c, 0.85); bl.noise_bump(m, scale=0.5, strength=0.05); return m


def room(x0, f, kind):
    """x0: 部屋の左端。f: 階（0 から）。家具はかんたんな形で、あかりは暖色。"""
    z = f * FH
    cxr = x0 + RW / 2
    wallc = [(0.85, 0.8, 0.7), (0.72, 0.8, 0.78), (0.86, 0.74, 0.68), (0.78, 0.76, 0.84), (0.9, 0.86, 0.76)][rr.randrange(5)]
    back = bl.cube((RW, 4, FH - 30), (cxr, DEPTH / 2, z + 30 + (FH - 30) / 2)); bl.assign(back, wall_paper(f"wp{f}{x0}", wallc))
    floor = bl.cube((RW, DEPTH, 4), (cxr, 0, z + 32))
    bl.assign(floor, bl.wood(f"fl{f}{x0}", light=(0.6, 0.42, 0.27), dark=(0.42, 0.28, 0.17), scale=0.03, stretch=10) if rr.random() < 0.7 else bl.mat(f"tile{f}{x0}", (0.8, 0.78, 0.74), 0.4))
    # 奥の窓（夜景）
    if rr.random() < 0.7:
        wx = cxr + rr.uniform(-80, 80)
        win = bl.cube((120, 2, 110), (wx, DEPTH / 2 - 3, z + 170)); bl.assign(win, bl.emission(f"win{f}{x0}", (0.12, 0.16, 0.32), 1.2))
        for dx in (-60, 0, 60):
            fr = bl.cube((5, 4, 114), (wx + dx, DEPTH / 2 - 5, z + 170)); bl.assign(fr, bl.mat("wf", (0.9, 0.9, 0.88), 0.5))
        cur = bl.cube((30, 5, 120), (wx - 70, DEPTH / 2 - 10, z + 168)); bl.assign(cur, bl.mat(f"cur{f}{x0}", rr.choice([(0.8, 0.5, 0.4), (0.5, 0.6, 0.75), (0.85, 0.8, 0.6)]), 0.9))
    # あかり：天井のペンダント
    lx = cxr + rr.uniform(-60, 60)
    cord = bl.cyl(0.8, 40, (lx, 40, z + FH - 20), verts=8); bl.assign(cord, bl.mat("cord", (0.1, 0.1, 0.1), 0.5))
    shade = bl.sphere(14, (lx, 40, z + FH - 48)); shade.scale = (1, 1, 0.6); bl.assign(shade, bl.emission(f"lamp{f}{x0}", (1, 0.72, 0.4), 6))
    p = bl.light('POINT', (lx, 0, z + FH - 70), 4e5, size=20, color=(1, 0.75, 0.48))
    # 家具
    if kind == "living":
        sofa = bl.cube((170, 70, 40), (cxr - 40, DEPTH / 2 - 60, z + 55)); bl.bevel(sofa, 8, 3)
        sm = bl.mat(f"sofa{f}{x0}", rr.choice([(0.25, 0.42, 0.55), (0.62, 0.3, 0.25), (0.4, 0.5, 0.32)]), 0.9); bl.assign(sofa, sm)
        backr = bl.cube((170, 20, 45), (cxr - 40, DEPTH / 2 - 25, z + 92)); bl.bevel(backr, 8, 3); bl.assign(backr, sm)
        tbl = bl.cyl(35, 4, (cxr + 20, 0, z + 72)); bl.assign(tbl, bl.wood(f"tb{f}{x0}", scale=0.1))
        leg = bl.cyl(3, 36, (cxr + 20, 0, z + 52)); bl.assign(leg, bl.mat("leg", (0.15, 0.12, 0.1), 0.5))
        rug = bl.cube((200, 160, 1), (cxr, 0, z + 34.5)); bl.assign(rug, bl.mat(f"rug{f}{x0}", rr.choice([(0.85, 0.75, 0.6), (0.7, 0.45, 0.4)]), 1.0))
    elif kind == "books":
        for i in range(3):
            sh = bl.cube((70, 34, 200), (x0 + 60 + i * 74, DEPTH / 2 - 22, z + 134)); bl.assign(sh, bl.wood(f"bs{f}{i}{x0}", scale=0.08))
            for k in range(4):
                for b in range(7):
                    bk = bl.cube((7, 26, 32 + rr.uniform(-6, 4)), (x0 + 32 + i * 74 + b * 8.5, DEPTH / 2 - 42, z + 54 + k * 46))
                    bl.assign(bk, bl.mat(f"bk{f}{i}{k}{b}{x0}", (rr.uniform(0.2, 0.85), rr.uniform(0.2, 0.7), rr.uniform(0.2, 0.6)), 0.7))
        chair = bl.cube((60, 60, 50), (cxr + 120, 0, z + 60)); bl.bevel(chair, 10, 3); bl.assign(chair, bl.mat(f"ch{f}{x0}", (0.75, 0.55, 0.3), 0.8))
    elif kind == "bed":
        bed = bl.cube((200, 140, 40), (cxr, 20, z + 55)); bl.bevel(bed, 6, 3); bl.assign(bed, bl.mat(f"bed{f}{x0}", (0.92, 0.9, 0.86), 0.9))
        blk = bl.cube((140, 144, 14), (cxr + 30, 20, z + 80)); bl.bevel(blk, 6, 3); bl.assign(blk, bl.mat(f"blk{f}{x0}", rr.choice([(0.35, 0.45, 0.7), (0.8, 0.55, 0.5), (0.5, 0.65, 0.5)]), 0.95))
        pil = bl.cube((40, 60, 16), (cxr - 75, 20, z + 84)); bl.bevel(pil, 6, 3); bl.assign(pil, bl.mat("pil", (0.98, 0.97, 0.95), 0.9))
        lamp = bl.sphere(12, (cxr - 150, DEPTH / 2 - 50, z + 100)); bl.assign(lamp, bl.emission(f"bl{f}{x0}", (1, 0.6, 0.3), 4))
    elif kind == "kitchen":
        ctr = bl.cube((300, 60, 90), (cxr, DEPTH / 2 - 40, z + 79)); bl.assign(ctr, bl.mat(f"kt{f}{x0}", (0.9, 0.9, 0.88), 0.3))
        top = bl.cube((304, 64, 4), (cxr, DEPTH / 2 - 40, z + 126)); bl.assign(top, bl.wood(f"ktt{f}{x0}", light=(0.7, 0.55, 0.38), scale=0.1))
        fr = bl.cube((70, 66, 180), (x0 + RW - 50, DEPTH / 2 - 42, z + 124)); bl.bevel(fr, 4, 3); bl.assign(fr, bl.mat(f"fr{f}{x0}", (0.85, 0.87, 0.9), 0.25))
        for i in range(3):
            pot = bl.cyl(12, 14, (cxr - 100 + i * 50, DEPTH / 2 - 40, z + 135)); bl.assign(pot, bl.mat(f"pt{f}{i}{x0}", rr.choice([(0.8, 0.3, 0.2), (0.3, 0.3, 0.32), (0.9, 0.8, 0.5)]), 0.3, metal=0.3))
        tbl = bl.cube((120, 80, 5), (cxr - 40, -40, z + 105)); bl.assign(tbl, bl.wood(f"dt{f}{x0}", scale=0.1))
    elif kind == "office":
        for i in range(2):
            desk = bl.cube((140, 70, 5), (x0 + 110 + i * 200, 10, z + 105)); bl.assign(desk, bl.mat(f"dk{f}{i}{x0}", (0.85, 0.83, 0.8), 0.4))
            mon = bl.cube((60, 4, 38), (x0 + 110 + i * 200, 30, z + 135)); bl.assign(mon, bl.emission(f"mon{f}{i}{x0}", (0.5, 0.75, 1.0), 2.5))
            ch = bl.cube((50, 50, 60), (x0 + 110 + i * 200, -40, z + 64)); bl.bevel(ch, 10, 2); bl.assign(ch, bl.mat(f"oc{f}{i}{x0}", (0.15, 0.17, 0.2), 0.6))
        pl = bl.cyl(18, 40, (x0 + RW - 30, DEPTH / 2 - 40, z + 54)); bl.assign(pl, bl.mat("pp", (0.9, 0.88, 0.84), 0.6))
        for k in range(5):
            lf = bl.sphere(22, (x0 + RW - 30 + rr.uniform(-16, 16), DEPTH / 2 - 40, z + 100 + rr.uniform(0, 40))); bl.assign(lf, bl.mat(f"lf{f}{k}{x0}", (0.2, 0.45, 0.2), 0.6))
    elif kind == "plants":
        for i in range(5):
            x = x0 + 50 + i * 80; h = rr.uniform(40, 120)
            pot = bl.cyl(20, 36, (x, DEPTH / 2 - 60, z + 52)); bl.assign(pot, bl.mat(f"pp{f}{i}{x0}", rr.choice([(0.75, 0.42, 0.28), (0.9, 0.88, 0.84), (0.3, 0.32, 0.35)]), 0.7))
            for k in range(4):
                lf = bl.sphere(rr.uniform(16, 28), (x + rr.uniform(-14, 14), DEPTH / 2 - 60 + rr.uniform(-10, 10), z + 80 + h * rr.random()))
                bl.assign(lf, bl.mat(f"pl{f}{i}{k}{x0}", (0.15 + rr.random() * 0.15, 0.38 + rr.random() * 0.2, 0.15), 0.6))
        bench = bl.cube((160, 50, 45), (cxr, -40, z + 56)); bl.bevel(bench, 5, 3); bl.assign(bench, bl.wood(f"bn{f}{x0}", scale=0.1))


def building():
    xl = -(SW / 2 + RW)          # 左の部屋の左端
    kinds = ["living", "books", "bed", "kitchen", "office", "plants"]
    for f in range(NF):
        ks = rr.sample(kinds, 2)
        room(xl, f, ks[0]); room(SW / 2, f, ks[1])
        # 床スラブ（断面）
        slab = bl.cube((WIDTH, DEPTH + 40, 30), (0, 0, f * FH + 15)); bl.assign(slab, concrete(f"slab{f}"))
    roof = bl.cube((WIDTH, DEPTH + 40, 40), (0, 0, NF * FH + 20)); bl.assign(roof, concrete("roof"))
    # 外壁（断面）と縦穴の壁
    for x in (-(WIDTH / 2 - 15), WIDTH / 2 - 15):
        w = bl.cube((30, DEPTH + 40, NF * FH + 40), (x, 0, (NF * FH + 40) / 2)); bl.assign(w, concrete("ext", (0.7, 0.68, 0.64)))
    for x in (-SW / 2 - 8, SW / 2 + 8):
        w = bl.cube((16, DEPTH + 40, NF * FH), (x, 0, NF * FH / 2)); bl.assign(w, concrete("shaftw", (0.55, 0.54, 0.52)))
    # 縦穴の奥：コンクリートとレール、ケーブル
    sb = bl.cube((SW, 4, NF * FH), (0, DEPTH / 2, NF * FH / 2)); bl.assign(sb, concrete("shaftb", (0.38, 0.38, 0.4)))
    rail = bl.mat("rail", (0.5, 0.52, 0.55), 0.3, metal=1.0)
    for x in (-SW / 2 + 14, SW / 2 - 14):
        r = bl.cube((8, 10, NF * FH), (x, DEPTH / 2 - 30, NF * FH / 2)); bl.assign(r, rail)
    for x in (-12, 0, 12):
        c = bl.cyl(1.4, NF * FH, (x, 40, NF * FH / 2), verts=8); bl.assign(c, bl.mat("cable", (0.12, 0.12, 0.13), 0.4, metal=0.8))
    # 各階の乗り場の扉（縦穴の奥の壁に、階ごとの数字板）
    for f in range(NF):
        lp = bl.cube((30, 3, 14), (0, DEPTH / 2 - 4, f * FH + 260)); bl.assign(lp, bl.emission(f"lp{f}", (1, 0.6, 0.25), 1.5))
    # 屋上の給水塔と、看板
    tank = bl.cyl(50, 80, (-250, 40, NF * FH + 80)); bl.assign(tank, concrete("tank", (0.75, 0.73, 0.7)))
    # 夜空（背景）
    sky = bl.plane((6000, 8000), (0, 1500, NF * FH / 2), rot=(90, 0, 0)); bl.assign(sky, bl.emission("sky", (0.05, 0.07, 0.16), 1.0))
    # 遠くのビルの灯り
    for i in range(160):
        x = rr.uniform(-1600, 1600); z = rr.uniform(0, NF * FH * 0.9)
        b = bl.cube((rr.uniform(14, 30), 2, rr.uniform(10, 18)), (x, 1400, z)); bl.assign(b, bl.emission(f"far{i}", rr.choice([(1, 0.8, 0.5), (0.8, 0.9, 1), (1, 0.6, 0.3)]), rr.uniform(0.4, 1.5)))


def lights():
    bl.world((0.06, 0.07, 0.12), 0.6)
    bl.light('AREA', (0, -1200, NF * FH / 2), 1.6e7, rot_deg=(90, 0, 0), size=3000, color=(0.55, 0.65, 1.0))   # 正面から弱い月あかり


if "--car" not in sys.argv:
    sc = bl.reset(); sc.view_settings.exposure = 0.0
    building(); lights()
    H = TOTAL_H + 200
    cam = bl.camera((0, -3000, H / 2 - 60), rot_deg=(90, 0, 0), ortho=None)
    cam.data.type = 'ORTHO'; cam.data.sensor_fit = 'HORIZONTAL'; cam.data.ortho_scale = WIDTH + 80; cam.data.clip_end = 20000
    px_h = int(round(H * SCALE / 2) * 2)
    geo = {"scale": SCALE, "w": IMG_W, "h": px_h, "nf": NF, "fh": FH,
           "floors": [round(px_h / 2 - ((f * FH + 34) - (H / 2 - 60)) * SCALE, 1) for f in range(NF)],
           "shaft": [round(IMG_W / 2 - SW / 2 * SCALE, 1), round(IMG_W / 2 + SW / 2 * SCALE, 1)], "carW": SW - 40 + 60, "carH": 240 + 60}
    json.dump(geo, open(os.path.join(OUT, "geo.json"), "w")); print(geo["h"], geo["floors"][:3], geo["shaft"])
    if "--geo" in sys.argv: sys.exit(0)
    bl.render(os.path.join(OUT, "bldg.png"), IMG_W, px_h, samples=S)

# かご（正面が開いた箱。中は明るい）
if "--bldg" not in sys.argv:
    sc = bl.reset(); sc.view_settings.exposure = 0.0
    CW, CH = SW - 40, 240
    st = bl.mat("steel", (0.75, 0.76, 0.78), 0.25, metal=1.0)
    for x in (-CW / 2, CW / 2):
        s = bl.cube((6, 160, CH), (x, 0, CH / 2)); bl.assign(s, st)
    bk = bl.cube((CW, 6, CH), (0, 80, CH / 2)); bl.assign(bk, bl.mat("cwall", (0.82, 0.74, 0.62), 0.5))
    fl = bl.cube((CW + 6, 166, 10), (0, 0, 5)); bl.assign(fl, bl.mat("cfloor", (0.35, 0.3, 0.28), 0.6))
    ce = bl.cube((CW + 6, 166, 14), (0, 0, CH + 7)); bl.assign(ce, st)
    lt = bl.cube((CW - 40, 120, 2), (0, 0, CH - 1)); bl.assign(lt, bl.emission("clt", (1, 0.95, 0.85), 6))
    hr = bl.cube((CW - 30, 4, 4), (0, 74, 95)); bl.assign(hr, bl.mat("hr", (0.8, 0.65, 0.4), 0.3, metal=1.0))
    pn = bl.cube((24, 4, 60), (CW / 2 - 24, 76, 120)); bl.assign(pn, bl.mat("pn", (0.2, 0.2, 0.22), 0.4))
    for i in range(6):
        b = bl.cyl(3, 2, (CW / 2 - 24, 73, 100 + i * 8), verts=16); b.rotation_euler = (math.radians(90), 0, 0); bl.assign(b, bl.emission(f"btn{i}", (1, 0.7, 0.3), 2))
    top = bl.cube((40, 40, 30), (0, 0, CH + 30)); bl.assign(top, bl.mat("motor", (0.25, 0.25, 0.27), 0.5, metal=0.5))
    bl.world((0.1, 0.1, 0.12), 0.8)
    bl.light('POINT', (0, -10, CH - 30), 3e5, size=40, color=(1, 0.95, 0.85))
    bl.light('AREA', (0, -400, 150), 6e5, rot_deg=(90, 0, 0), size=400)
    cam = bl.camera((0, -3000, CH / 2 + 15), rot_deg=(90, 0, 0))
    cam.data.type = 'ORTHO'; cam.data.sensor_fit = 'HORIZONTAL'; cam.data.ortho_scale = CW + 60; cam.data.clip_end = 20000
    w = int(round((CW + 60) * SCALE * 2)); h = int(round((CH + 60) * SCALE * 2 / 2) * 2)   # 2倍の解像度
    bl.render(os.path.join(OUT, "car.png"), w, h, samples=S, transparent=True)
    print("car", w, h)
print("done")
