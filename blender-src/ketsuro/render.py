"""結露のまど：素材レンダリング。

冬の夜、あたたかい部屋の窓。外は街の灯り（大きくぼける）。
out/clear.png   ふいたあとの窓（すきとおったガラス）
out/fog.png     くもった窓（すりガラス＋細かい水滴）
out/geo.json    ガラスの範囲（画面）
720x1080 を 1.5 倍。1 = 1cm。
"""
import json, math, os, sys, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "common"))
import bpy, mathutils
from bpy_extras.object_utils import world_to_camera_view
import bl

OUT = os.path.join(os.path.dirname(__file__), "out")
os.makedirs(OUT, exist_ok=True)
FAST = "--fast" in sys.argv
S = 24 if FAST else 160
rr = random.Random(5)
GX, GZ0, GZ1 = 33, 10, 106          # ガラスの半はば・下・上


def city():
    # 遠くのビルの窓・街灯・車のライト（ぼけて丸い光になる）
    cols = [(1, 0.78, 0.45), (1, 0.62, 0.3), (0.75, 0.85, 1), (1, 0.9, 0.7), (1, 0.4, 0.25)]
    for i in range(420):
        x = rr.uniform(-1700, 1700); z = rr.uniform(-500, 900) * (0.5 + 0.5 * rr.random()); y = rr.uniform(2600, 4200)
        s = bl.cube((rr.uniform(14, 30), 2, rr.uniform(10, 22)), (x, y, z)); bl.assign(s, bl.emission(f"c{i}", rr.choice(cols), rr.uniform(2, 9)))
    for i in range(40):   # 道路の車のライト（低いところに並ぶ）
        x = rr.uniform(-1600, 1600); s = bl.sphere(6, (x, 2400, -420 + rr.uniform(-20, 20)))
        bl.assign(s, bl.emission(f"car{i}", (1, 0.25, 0.15) if i % 2 else (1, 0.95, 0.8), 25))
    sky = bl.plane((12000, 8000), (0, 5000, 0), rot=(90, 0, 0)); bl.assign(sky, bl.emission("sky", (0.03, 0.04, 0.1), 1.0))


def window(fog):
    wood = bl.wood("frame", light=(0.62, 0.45, 0.3), dark=(0.45, 0.3, 0.18), scale=0.15)
    # わく（ガラスのまわり）
    for (sx, sz, x, z) in ((8, 120, -GX - 4, 58), (8, 120, GX + 4, 58), (82, 8, 0, GZ1 + 4), (82, 6, 0, GZ0 - 3)):
        b = bl.cube((sx, 10, sz), (x, 0, z)); bl.bevel(b, 0.8, 3); bl.assign(b, wood)
    # 窓台と、まわりの白い壁
    sill = bl.cube((120, 26, 4), (0, -10, GZ0 - 7)); bl.bevel(sill, 1, 3); bl.assign(sill, wood)
    wm = bl.mat("wall", (0.86, 0.82, 0.76), 0.85)
    for (sx, sz, x, z) in ((60, 220, -GX - 38, 50), (60, 220, GX + 38, 50), (200, 60, 0, GZ1 + 38), (200, 60, 0, GZ0 - 39)):
        b = bl.cube((sx, 4, sz), (x, 6, z)); bl.assign(b, wm)
    # ガラス
    if fog:
        gm = bl.mat("glass", (0.95, 0.97, 1.0), 0.16, Transmission_Weight=1.0, IOR=1.45)
    else:
        gm = bl.mat("glass", (0.97, 0.98, 1.0), 0.0, Transmission_Weight=1.0, IOR=1.45)
    g = bl.cube((GX * 2, 0.4, GZ1 - GZ0), (0, 0, (GZ0 + GZ1) / 2)); bl.assign(g, gm)
    if fog:
        # 細かい水滴（ガラスの手前の面）
        dm = bl.mat("drop", (1, 1, 1), 0.0, Transmission_Weight=1.0, IOR=1.33)
        src = bl.sphere(1, (0, -500, -500)); bl.assign(src, dm)
        bpy.ops.mesh.primitive_plane_add(size=1, location=(0, -0.25, (GZ0 + GZ1) / 2), rotation=(math.radians(90), 0, 0))
        em = bl.active(); em.scale = (GX * 2, GZ1 - GZ0, 1)
        ps = em.modifiers.new("p", 'PARTICLE_SYSTEM').particle_system.settings
        ps.count = 16000 if FAST else 30000; ps.frame_start = ps.frame_end = 1; ps.lifetime = 1000; ps.emit_from = 'FACE'
        ps.physics_type = 'NO'; ps.render_type = 'OBJECT'; ps.instance_object = src
        ps.particle_size = 0.2; ps.size_random = 0.85; ps.use_rotations = True; ps.rotation_mode = 'NOR'
        em.show_instancer_for_render = False
        src.scale = (1, 1, 1)


def props():
    # 窓台：小さなサボテン、湯気の出そうなマグカップ、毛糸の雪だるま（顔なし）
    pot = bl.cyl(4.5, 7, (-22, -12, GZ0 - 1.5)); bl.bevel(pot, 0.5, 3); bl.assign(pot, bl.mat("pot", (0.8, 0.45, 0.32), 0.7))
    cac = bl.sphere(4, (-22, -12, GZ0 + 6)); cac.scale = (0.8, 0.8, 1.4); bl.assign(cac, bl.mat("cactus", (0.25, 0.5, 0.3), 0.6))
    mug = bl.cyl(4, 9, (20, -14, GZ0 - 0.5)); bl.bevel(mug, 0.4, 3); bl.assign(mug, bl.mat("mug", (0.95, 0.93, 0.88), 0.25))
    bpy.ops.mesh.primitive_torus_add(major_radius=2.5, minor_radius=0.6, location=(24.5, -14, GZ0), rotation=(math.radians(90), 0, 0)); bl.assign(bl.active(), bl.mat("mug2", (0.95, 0.93, 0.88), 0.25))
    tea = bl.cyl(3.6, 0.3, (20, -14, GZ0 + 3.6)); bl.assign(tea, bl.mat("tea", (0.35, 0.18, 0.08), 0.05))
    sm = bl.mat("knit", (0.97, 0.96, 0.94), 0.95); bl.noise_bump(sm, scale=3, strength=0.6)
    b1 = bl.sphere(3.6, (6, -16, GZ0 - 1.5)); bl.assign(b1, sm)
    b2 = bl.sphere(2.6, (6, -16, GZ0 + 3.7)); bl.assign(b2, sm)
    sc_ = bl.cyl(2.7, 0.9, (6, -16, GZ0 + 1.7)); bl.assign(sc_, bl.mat("scarf", (0.8, 0.2, 0.2), 0.9))


def lights():
    bl.world((0.02, 0.025, 0.05), 0.3)
    for l in (bl.light('POINT', (-95, -45, 30), 9e5, size=20, color=(1, 0.72, 0.45)),        # 部屋のあかり
              bl.light('AREA', (0, -70, 200), 1.2e6, rot_deg=(25, 0, 0), size=100, color=(1, 0.8, 0.6))):
        l.visible_glossy = False


def proj(sc, cam, p):
    v = world_to_camera_view(sc, cam, mathutils.Vector(p))
    return [round(v.x * 720, 1), round((1 - v.y) * 1080, 1)]


for fog in ([False] if "--clear" in sys.argv else [True] if "--fog" in sys.argv else [False, True]):
    sc = bl.reset(); sc.view_settings.exposure = 0.0
    sc.cycles.transmission_bounces = 8; sc.cycles.max_bounces = 10
    city(); window(fog); props(); lights()
    cam = bl.camera((0, -112, 56), rot_deg=(90, 0, 0), lens=24.5)
    cam.data.sensor_fit = 'VERTICAL'; cam.data.sensor_height = 24; cam.data.clip_end = 20000
    cam.data.dof.use_dof = True; cam.data.dof.focus_distance = 112; cam.data.dof.aperture_fstop = 0.006
    sc.render.resolution_x, sc.render.resolution_y = 1080, 1620
    bpy.context.view_layer.update()
    geo = {"glass": [proj(sc, cam, (-GX, 0, GZ1)), proj(sc, cam, (GX, 0, GZ0))], "ppc": round(proj(sc, cam, (1, 0, 56))[0] - proj(sc, cam, (0, 0, 56))[0], 2)}
    json.dump(geo, open(os.path.join(OUT, "geo.json"), "w")); print(geo)
    if "--geo" in sys.argv: sys.exit(0)
    bl.render(os.path.join(OUT, "fog.png" if fog else "clear.png"), 1080, 1620, samples=S)
print("done")
