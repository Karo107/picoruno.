# Renders the sprites and the board for gyakuso-button.html.
# python3 render.py <outdir>   (needs `pip install bpy`)
import bpy, math, sys, os
from mathutils import Vector, Euler

OUT = sys.argv[-1] if len(sys.argv) > 1 else 'out'
os.makedirs(OUT, exist_ok=True)

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = 48
    sc.cycles.use_denoising = True
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA'
    w = bpy.data.worlds.new('w'); sc.world = w
    w.use_nodes = True
    w.node_tree.nodes['Background'].inputs[0].default_value = (0.55, 0.58, 0.66, 1)
    w.node_tree.nodes['Background'].inputs[1].default_value = 0.55
    return sc

def mat(name, color, rough=0.5, metal=0.0, coat=0.0, emit=None, sss=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    b.inputs['Coat Weight'].default_value = coat
    if sss:
        b.inputs['Subsurface Weight'].default_value = sss
        b.inputs['Subsurface Radius'].default_value = (0.3, 0.2, 0.1)
        b.inputs['Subsurface Scale'].default_value = 0.05
    if emit:
        b.inputs['Emission Color'].default_value = (*emit[0], 1)
        b.inputs['Emission Strength'].default_value = emit[1]
    return m

def srgb(h):
    h = h.lstrip('#'); c = [int(h[i:i+2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)

def smooth(o, levels=2):
    for p in o.data.polygons: p.use_smooth = True
    if levels:
        mod = o.modifiers.new('s', 'SUBSURF'); mod.levels = levels; mod.render_levels = levels

def sphere(loc, scale, m, parent=None, seg=32):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=seg // 2, location=loc)
    o = bpy.context.object; o.scale = scale
    for p in o.data.polygons: p.use_smooth = True
    o.data.materials.append(m)
    if parent: o.parent = parent
    return o

def lights(sc, key=5.0):
    bpy.ops.object.light_add(type='SUN', location=(0, 0, 10))
    s = bpy.context.object; s.data.energy = key; s.data.angle = math.radians(18)
    s.rotation_euler = Euler((math.radians(38), 0, math.radians(-35)))
    bpy.ops.object.light_add(type='AREA', location=(-3, -4, 5))
    a = bpy.context.object; a.data.energy = 600; a.data.size = 5
    a.rotation_euler = (Vector((0, 0, 0)) - a.location).to_track_quat('-Z', 'Y').to_euler()

def camera(sc, elev_deg, scale, target=(0, 0, 0), res=(256, 256)):
    el = math.radians(elev_deg)
    d = 20
    loc = Vector(target) + Vector((0, -math.cos(el) * d, math.sin(el) * d))
    bpy.ops.object.camera_add(location=loc)
    c = bpy.context.object
    c.rotation_euler = (Vector(target) - loc).to_track_quat('-Z', 'Y').to_euler()
    c.data.type = 'ORTHO'; c.data.ortho_scale = scale
    sc.camera = c
    sc.render.resolution_x, sc.render.resolution_y = res
    return c

def render(sc, path):
    sc.render.filepath = os.path.join(OUT, path)
    bpy.ops.render.render(write_still=True)
    print('wrote', path)

SPRITE_ELEV = 38

# ---------- chick ----------
def build_chick():
    root = bpy.data.objects.new('chick', None); bpy.context.collection.objects.link(root)
    yel = mat('yel', srgb('#ffd23a'), 0.55, sss=0.15)
    yel2 = mat('yel2', srgb('#f2b622'), 0.6)
    red = mat('red', srgb('#e8382f'), 0.4, coat=0.3)
    ora = mat('ora', srgb('#ff8a1e'), 0.35, coat=0.4)
    blk = mat('blk', (0.01, 0.01, 0.012), 0.15, coat=1.0)
    wht = mat('wht', (1, 1, 1), 0.3, emit=((1, 1, 1), 2.0))
    pnk = mat('pnk', srgb('#ff8fa0'), 0.6)
    R = 0.37; CZ = 0.38
    sphere((0, 0, CZ), (R, R * 0.96, R * 0.97), yel, root, 64)
    def front(x, z, inset=0.0):  # a point on the body's front surface
        return -(max(R * R - x * x - (z - CZ) ** 2, 0) ** 0.5) * 0.96 + inset
    for i, (x, z, r) in enumerate([(-0.09, 0.72, .07), (0, 0.76, .09), (0.09, 0.72, .07)]):
        sphere((x, -0.02, z), (r * 0.8, r, r), red, root)                 # comb
    bz = 0.40
    bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=0.075, depth=0.14, location=(0, front(0, bz) - 0.05, bz))
    bk = bpy.context.object; bk.rotation_euler = (math.radians(90), 0, 0); bk.scale = (1.15, 0.75, 1)
    for p in bk.data.polygons: p.use_smooth = True
    bk.data.materials.append(ora); bk.parent = root
    for s in (-1, 1):
        ex, ez = s * 0.13, 0.50
        sphere((ex, front(ex, ez) + 0.012, ez), (0.05, 0.025, 0.065), blk, root)   # eyes
        sphere((ex - 0.016, front(ex, ez) - 0.008, ez + 0.025), (0.017, 0.01, 0.017), wht, root)
        cx, cz = s * 0.22, 0.38
        sphere((cx, front(cx, cz) + 0.01, cz), (0.055, 0.02, 0.035), pnk, root)    # cheeks
        w = sphere((s * 0.355, 0.04, 0.33), (0.06, 0.13, 0.1), yel2, root)          # wings
        w.rotation_euler = (math.radians(-20), math.radians(s * 25), 0)
        for t in (-1, 0, 1):                                                       # feet
            bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.022, depth=0.11, location=(s * 0.13 + t * 0.03, -0.1, 0.02))
            f = bpy.context.object; f.rotation_euler = (math.radians(90), 0, math.radians(t * 30)); f.data.materials.append(ora); f.parent = root
    tail = sphere((0, 0.34, 0.5), (0.08, 0.07, 0.09), yel2, root)
    tail.rotation_euler = (math.radians(-35), 0, 0)
    return root

def chick_sprites():
    sc = reset(); lights(sc)
    root = build_chick()
    camera(sc, SPRITE_ELEV, 1.1, target=(0, 0, 0.36), res=(256, 256))
    # dir 0 up(away from camera), 1 right, 2 down(towards camera), 3 left
    for d, rz in [(0, 180), (1, 90), (2, 0), (3, -90)]:
        root.rotation_euler = (0, 0, math.radians(rz))
        render(sc, f'chick{d}.png')
    # dizzy: eyes closed look (squash a bit) facing camera
    root.rotation_euler = (0, 0, math.radians(0))
    for o in bpy.data.objects:
        if o.data and hasattr(o.data, 'materials') and o.data.materials and o.data.materials[0].name in ('blk', 'wht'):
            o.scale = (o.scale.x * 1.2, o.scale.y, o.scale.z * 0.25)
    root.scale = (1.08, 1.08, 0.9)
    render(sc, 'chick_hurt.png')

# ---------- coin ----------
def coin_sprites(n=12):
    sc = reset(); lights(sc, 4.5)
    gold = mat('gold', srgb('#ffd447'), 0.2, metal=1.0)
    gold2 = mat('gold2', srgb('#f0aa1c'), 0.28, metal=1.0)
    root = bpy.data.objects.new('coin', None); bpy.context.collection.objects.link(root)
    root.location = (0, 0, 0.3)
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=0.26, depth=0.07)
    c = bpy.context.object; c.rotation_euler = (math.radians(90), 0, 0); c.parent = root
    bv = c.modifiers.new('b', 'BEVEL'); bv.width = 0.02; bv.segments = 4
    for p in c.data.polygons: p.use_smooth = True
    c.data.materials.append(gold2)
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=0.21, depth=0.08)
    f = bpy.context.object; f.rotation_euler = (math.radians(90), 0, 0); f.parent = root; f.data.materials.append(gold)
    for side in (-1, 1):
        bpy.ops.object.text_add(location=(0, side * 0.04, 0))
        t = bpy.context.object; t.data.body = 'P'; t.data.align_x = 'CENTER'; t.data.align_y = 'CENTER'
        t.data.size = 0.3; t.data.extrude = 0.012; t.data.bevel_depth = 0.006
        t.rotation_euler = (math.radians(90), 0, 0 if side < 0 else math.pi)
        t.data.materials.append(gold2); t.parent = root
    camera(sc, SPRITE_ELEV, 0.8, target=(0, 0, 0.3), res=(160, 160))
    for i in range(n):
        root.rotation_euler = (0, 0, math.radians(i * 360 / n))
        render(sc, f'coin{i}.png')

# ---------- golden egg ----------
def egg_sprite():
    sc = reset(); lights(sc, 4.5)
    gold = mat('egg', srgb('#ffd23f'), 0.25, metal=0.55, coat=1.0, emit=(srgb('#ffcf3a'), 0.25))
    e = sphere((0, 0, 0.3), (0.2, 0.2, 0.27), gold, None, 64)
    bm = e.data
    for v in bm.vertices:  # egg shape: narrower top
        if v.co.z > 0: v.co.x *= 1 - 0.18 * v.co.z; v.co.y *= 1 - 0.18 * v.co.z
    camera(sc, SPRITE_ELEV, 0.8, target=(0, 0, 0.3), res=(160, 160))
    render(sc, 'egg.png')

# ---------- spike block ----------
def spike_sprite():
    sc = reset(); lights(sc, 5)
    plate = mat('plate', srgb('#8f1d18'), 0.5, coat=0.4)
    steel = mat('steel', (0.85, 0.86, 0.9), 0.18, metal=1.0)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.05))
    p = bpy.context.object; p.scale = (0.86, 0.86, 0.1)
    bv = p.modifiers.new('b', 'BEVEL'); bv.width = 0.05; bv.segments = 4
    p.data.materials.append(plate)
    for x in (-0.2, 0.2):
        for y in (-0.2, 0.2):
            bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=0.15, depth=0.38, location=(x, y, 0.29))
            c = bpy.context.object; c.data.materials.append(steel)
            for q in c.data.polygons: q.use_smooth = True
    bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=0.13, depth=0.32, location=(0, 0, 0.26))
    bpy.context.object.data.materials.append(steel)
    camera(sc, SPRITE_ELEV, 1.2, target=(0, 0, 0.2), res=(220, 220))
    render(sc, 'spike.png')

# ---------- board (top down) ----------
def board(N=7, px=128):
    sc = reset(); sc.render.film_transparent = False
    sc.cycles.samples = 64
    lights(sc, 2.4)
    # asphalt: noise-tinted dark grey with bumpy grain
    a = bpy.data.materials.new('asphalt'); a.use_nodes = True
    nt = a.node_tree; b = nt.nodes['Principled BSDF']
    tc = nt.nodes.new('ShaderNodeTexCoord')
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 14; nz.inputs['Detail'].default_value = 12; nz.inputs['Roughness'].default_value = 0.75
    nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.35; ramp.color_ramp.elements[1].position = 0.7
    ramp.color_ramp.elements[0].color = (*srgb('#1f2127'), 1); ramp.color_ramp.elements[1].color = (*srgb('#3d404a'), 1)
    nt.links.new(nz.outputs['Fac'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], b.inputs['Base Color'])
    bump = nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.8
    nt.links.new(nz.outputs['Fac'], bump.inputs['Height']); nt.links.new(bump.outputs['Normal'], b.inputs['Normal'])
    b.inputs['Roughness'].default_value = 0.85
    gap = mat('gap', srgb('#15161b'), 0.9)
    white = mat('paint', srgb('#e9e6dc'), 0.6)
    yellow = mat('ypaint', srgb('#f1c232'), 0.6)
    bpy.ops.mesh.primitive_plane_add(size=N + 0.4, location=(0, 0, -0.02))
    bpy.context.object.data.materials.append(gap)
    for y in range(N):
        for x in range(N):
            bpy.ops.mesh.primitive_cube_add(size=1, location=(x - (N - 1) / 2, (N - 1) / 2 - y, 0))
            t = bpy.context.object; t.scale = (0.94, 0.94, 0.06)
            bv = t.modifiers.new('b', 'BEVEL'); bv.width = 0.035; bv.segments = 3
            t.data.materials.append(a)
    # road paint: yellow dashed center line (vertical) and white edge lines
    for i in range(N):
        bpy.ops.mesh.primitive_plane_add(size=1, location=(0, (N - 1) / 2 - i, 0.032))
        d = bpy.context.object; d.scale = (0.07, 0.42, 1); d.data.materials.append(yellow)
    faded = mat('faded', srgb('#4d4f57'), 0.85)
    for (cx, cy) in ((-2, -1), (2, 2)):   # worn road arrows pointing up
        bpy.ops.mesh.primitive_plane_add(size=1, location=(cx, cy - 0.12, 0.032))
        sh = bpy.context.object; sh.scale = (0.09, 0.26, 1); sh.data.materials.append(faded)
        bpy.ops.mesh.primitive_circle_add(vertices=3, radius=0.22, fill_type='NGON', location=(cx, cy + 0.2, 0.032))
        hd = bpy.context.object; hd.scale = (1.2, 1, 1); hd.data.materials.append(faded)
    bpy.ops.object.camera_add(location=(0, 0, 20)); c = bpy.context.object
    c.data.type = 'ORTHO'; c.data.ortho_scale = N; sc.camera = c
    sc.render.resolution_x = sc.render.resolution_y = N * px
    sc.render.image_settings.color_mode = 'RGB'
    render(sc, 'board.png')

which = sys.argv[-2] if len(sys.argv) > 2 else 'all'
if which in ('all', 'chick'): chick_sprites()
if which in ('all', 'coin'): coin_sprites()
if which in ('all', 'egg'): egg_sprite()
if which in ('all', 'spike'): spike_sprite()
if which in ('all', 'board'): board()
