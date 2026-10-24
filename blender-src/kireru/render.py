"""どこからでも切れます：素材レンダリング。

out/bg.png          居酒屋のカウンター（ゲーム座標 720x1080 を 1.5 倍）
out/pack_<id>.png   小袋の正面（透明フィルム・印刷つき、透過）。中身の液体はゲーム側で描く
袋は 4.5cm x 6.5cm。上 1.1cm がシール（ギザギザつき）。
"""
import math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "common"))
sys.path.insert(0, os.path.dirname(__file__))
import bpy
import bl
import labels

HERE = os.path.dirname(__file__)
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)
FAST = "--fast" in sys.argv
S = 24 if FAST else 96

PW, PH = 4.5, 6.5
TOP, SIDE, BOT = 1.1, 0.35, 0.45


def packet_mesh(sign, nx=90, nz=130):
    verts, faces = [], []
    for j in range(nz + 1):
        for i in range(nx + 1):
            x = -PW / 2 + PW * i / nx
            z = -PH / 2 + PH * j / nz
            if j == nz:
                z += 0.07 * (i % 2)          # 上のふちのギザギザ
            u = (x - (-PW / 2 + SIDE)) / (PW - 2 * SIDE) * 2 - 1
            v = (z - (-PH / 2 + BOT)) / (PH - TOP - BOT) * 2 - 1
            b = 0.012
            if abs(u) < 1 and abs(v) < 1:
                b = 0.012 + 0.32 * math.sqrt(max(0, 1 - u ** 4)) * math.sqrt(max(0, 1 - v ** 4))
            verts.append((x, sign * b, z))
    for j in range(nz):
        for i in range(nx):
            a = j * (nx + 1) + i
            f = (a, a + 1, a + nx + 2, a + nx + 1)
            faces.append(f if sign < 0 else f[::-1])
    me = bpy.data.meshes.new("pk")
    me.from_pydata(verts, [], faces)
    uv = me.uv_layers.new()
    for poly in me.polygons:
        for li in poly.loop_indices:
            vx, _, vz = me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv = ((vx + PW / 2) / PW, (vz + PH / 2) / PH)
    o = bpy.data.objects.new("pk", me)
    bl.link(o)
    bl.smooth(o)
    return o


def packet_mat(label_png, bump_png):
    """フィルム（不透明でレンダリングし、透け具合はあとで PIL で決める）＋印刷。"""
    m = bl.mat("film", (0.86, 0.87, 0.9), 0.14, Specular_IOR_Level=0.8)
    N, L, film = bl.nodes(m)
    out = N["Material Output"]
    pr = N.new("ShaderNodeBsdfPrincipled")
    pr.inputs["Roughness"].default_value = 0.3
    tx = N.new("ShaderNodeTexImage")
    tx.image = bpy.data.images.load(label_png)
    bm = N.new("ShaderNodeTexImage")
    bm.image = bpy.data.images.load(bump_png)
    bm.image.colorspace_settings.name = 'Non-Color'
    bp = N.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.3
    L.new(bm.outputs["Color"], bp.inputs["Height"])
    L.new(bp.outputs["Normal"], film.inputs["Normal"])
    L.new(bp.outputs["Normal"], pr.inputs["Normal"])
    L.new(tx.outputs["Color"], pr.inputs["Base Color"])
    mix = N.new("ShaderNodeMixShader")
    L.new(tx.outputs["Alpha"], mix.inputs["Fac"])
    L.new(film.outputs[0], mix.inputs[1])
    L.new(pr.outputs[0], mix.inputs[2])
    L.new(mix.outputs[0], out.inputs["Surface"])
    return m


def film_alpha(render_png, label_png, bump_png, out_png, iw=620, ih=900, ortho=7.2):
    """フィルムの部分はうすく、印刷とシールは濃く、つやの光は残す。"""
    from PIL import Image, ImageChops
    im = Image.open(render_png).convert("RGBA")
    px_cm = ih / ortho
    w, h = round(PW * px_cm), round(PH * px_cm)
    x0, y0 = round(iw / 2 - w / 2), round(ih / 2 - h / 2)
    from PIL import ImageDraw
    lab = Image.open(label_png).getchannel("A").resize((w, h)).point(lambda v: min(255, v * 2))
    base = Image.new("L", (w, h), 110)                 # シール部分
    ImageDraw.Draw(base).rectangle((round(SIDE * px_cm), round(TOP * px_cm), w - round(SIDE * px_cm), h - round(BOT * px_cm)), fill=34)
    a = ImageChops.lighter(base, lab)
    full = Image.new("L", (iw, ih), 0)
    full.paste(a, (x0, y0))
    # ギザギザの部分（袋の上端より上）は元のアルファ×シールの濃さ
    obj = im.getchannel("A")
    top = obj.crop((0, 0, iw, y0 + 2)).point(lambda v: v * 110 // 255)
    full.paste(top, (0, 0))
    lum = im.convert("L").point(lambda v: max(0, (v - 200) * 4))
    alpha = ImageChops.multiply(ImageChops.lighter(full, lum), obj)
    from PIL import ImageEnhance
    im = ImageEnhance.Color(im.convert("RGB")).enhance(1.35)
    im.putalpha(alpha)
    im.save(out_png)


# ---------- 1) 背景 ----------
sc = bl.reset()
sc.view_settings.exposure = 0.1
bl.world((0.25, 0.18, 0.12), 0.25)
counter = bl.cube((200, 90, 4), (0, 25, -2))
bl.assign(counter, bl.wood("counter", light=(0.66, 0.46, 0.28), dark=(0.42, 0.26, 0.14), scale=0.12, rough=0.25, bump=0.03))
# 小皿
dish = bl.cyl(5.5, 1.0, (0, -4, 0.5), verts=128)
bl.bevel(dish, 0.45, 6)
bl.smooth(dish)
inner = bl.cyl(4.6, 1.0, (0, -4, 1.15), verts=128)
bo = dish.modifiers.new("b", 'BOOLEAN'); bo.object = inner; bo.operation = 'DIFFERENCE'
bpy.context.view_layer.objects.active = dish
bpy.ops.object.modifier_apply(modifier="bevel")
bpy.ops.object.modifier_apply(modifier="b")
bpy.data.objects.remove(inner)
bl.bevel(dish, 0.15, 4)
dm = bl.mat("dish", (0.92, 0.92, 0.9), 0.12)
bl.noise_bump(dm, 30, 0.02)
N, L, b = bl.nodes(dm)
tc = N.new("ShaderNodeTexCoord"); gr = N.new("ShaderNodeTexGradient"); gr.gradient_type = 'SPHERICAL'
mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1 / 5.6, 1 / 5.6, 0)
L.new(tc.outputs["Object"], mp.inputs["Vector"]); L.new(mp.outputs["Vector"], gr.inputs["Vector"])
cr = N.new("ShaderNodeValToRGB"); el = cr.color_ramp.elements
el[0].color = (0.1, 0.17, 0.42, 1); el[0].position = 0.0; el[1].color = (0.93, 0.93, 0.9, 1); el[1].position = 0.035
e2 = el.new(0.17); e2.color = (0.1, 0.17, 0.42, 1); e3 = el.new(0.185); e3.color = (0.93, 0.93, 0.9, 1)
cr.color_ramp.interpolation = 'CONSTANT'
L.new(gr.outputs["Fac"], cr.inputs["Fac"]); L.new(cr.outputs["Color"], b.inputs["Base Color"])
bl.assign(dish, dm)
# 奥の箸と箸置き
for dx in (-0.5, 0.5):
    c = bl.cyl(0.32, 22, (12 + dx, 2, 0.6), rotation=(math.radians(90), 0, math.radians(-12)))
    bl.assign(c, bl.mat("hashi", (0.25, 0.08, 0.05), 0.3))
# 奥の灯り（ボケ）
import random
rnd = random.Random(4)
for i in range(40):
    s = bl.sphere(0.8 + rnd.random() * 1.2, (rnd.uniform(-70, 70), rnd.uniform(90, 130), rnd.uniform(10, 60)))
    col = rnd.choice([(1, 0.62, 0.25), (1, 0.75, 0.4), (1, 0.45, 0.2), (0.9, 0.85, 0.7)])
    bl.assign(s, bl.emission(f"bk{i}", col, 25 + rnd.random() * 40))
# 奥の壁（のれんっぽい布）
wall = bl.plane((400, 160), (0, 170, 50), rot=(90, 0, 0))
wm = bl.mat("wall", (0.08, 0.05, 0.035), 0.9)
bl.assign(wall, wm)
bl.light('AREA', (-20, -30, 50), 30000, rot_deg=(35, -20, 0), size=30, color=(1, 0.88, 0.7))
bl.light('AREA', (25, 10, 40), 9000, rot_deg=(-20, 30, 0), size=20, color=(1, 0.8, 0.6))
cam = bl.camera((0, -42, 20), rot_deg=(72, 0, 0), lens=34)
cam.data.sensor_fit = 'VERTICAL'
cam.data.sensor_height = 24
cam.data.dof.use_dof = True
cam.data.dof.focus_distance = 43
cam.data.dof.aperture_fstop = 0.9
bl.render(os.path.join(OUT, "bg.png"), 1080, 1620, samples=S)

# ---------- 2) 小袋 ----------
labels.make_bump(os.path.join(OUT, "bump.png"))
for pid, name, sub, col in labels.PACKS:
    sc = bl.reset()
    sc.view_settings.exposure = 0.2
    bl.world((0.9, 0.85, 0.8), 0.5)
    bl.light('AREA', (-6, -10, 8), 1500, rot_deg=(50, 0, -30), size=6, color=(1, 0.92, 0.82))
    bl.light('AREA', (8, -6, -2), 600, rot_deg=(95, 0, 50), size=4, color=(0.85, 0.9, 1))
    lp = os.path.join(OUT, f"label_{pid}.png")
    labels.make(lp, name, sub, col)
    m = packet_mat(lp, os.path.join(OUT, "bump.png"))
    for sgn in (-1, 1):
        o = packet_mesh(sgn)
        bl.assign(o, m)
    bl.camera((0, -20, 0), rot_deg=(90, 0, 0), ortho=7.2)
    raw = os.path.join(OUT, f"raw_{pid}.png")
    bl.render(raw, 620, 900, samples=S, transparent=True)
    film_alpha(raw, lp, os.path.join(OUT, "bump.png"), os.path.join(OUT, f"pack_{pid}.png"), *( (310, 450) if FAST else (620, 900)))
print("done")
