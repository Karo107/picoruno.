"""Blender (bpy) の共通ヘルパー。各ゲームの render.py から import して使う。

python3 render.py で実行（pip install bpy 済みの環境）。
"""
import math
import bpy


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = 96
    sc.cycles.use_denoising = True
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'AgX - Punchy'
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.02
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA'
    return sc


def world(color=(0.9, 0.9, 0.92), strength=1.0):
    sc = bpy.context.scene
    w = bpy.data.worlds.new("world")
    sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (*color, 1)
    bg.inputs[1].default_value = strength
    return w


def link(obj):
    bpy.context.scene.collection.objects.link(obj)
    return obj


def camera(loc, rot_deg=(0, 0, 0), ortho=None, lens=50):
    cam = bpy.data.cameras.new("cam")
    if ortho:
        cam.type = 'ORTHO'
        cam.ortho_scale = ortho
    else:
        cam.lens = lens
    o = link(bpy.data.objects.new("cam", cam))
    o.location = loc
    o.rotation_euler = [math.radians(a) for a in rot_deg]
    bpy.context.scene.camera = o
    return o


def light(kind, loc, energy, rot_deg=(0, 0, 0), size=1.0, color=(1, 1, 1), angle=None):
    l = bpy.data.lights.new("l", kind)
    l.energy = energy
    l.color = color
    if kind == 'AREA':
        l.size = size
    elif kind in ('POINT', 'SPOT'):
        l.shadow_soft_size = size
    if kind == 'SUN' and angle is not None:
        l.angle = math.radians(angle)
    o = link(bpy.data.objects.new("l", l))
    o.location = loc
    o.rotation_euler = [math.radians(a) for a in rot_deg]
    return o


def mat(name, color=(0.8, 0.8, 0.8), rough=0.5, metal=0.0, **kw):
    """Principled BSDF のマテリアル。kw は入力名=値（例 Transmission Weight=1）。"""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    for k, v in kw.items():
        b.inputs[k.replace("_", " ")].default_value = v
    return m


def nodes(m):
    return m.node_tree.nodes, m.node_tree.links, m.node_tree.nodes["Principled BSDF"]


def assign(obj, m):
    obj.data.materials.clear()
    obj.data.materials.append(m)
    return obj


def smooth(obj):
    for p in obj.data.polygons:
        p.use_smooth = True
    return obj


def bevel(obj, width=0.02, segments=3):
    md = obj.modifiers.new("bevel", 'BEVEL')
    md.width = width
    md.segments = segments
    md.limit_method = 'ANGLE'
    return md


def subsurf(obj, levels=2):
    md = obj.modifiers.new("sub", 'SUBSURF')
    md.levels = levels
    md.render_levels = levels
    return md


def active():
    return bpy.context.view_layer.objects.active


def cyl(r, h, loc=(0, 0, 0), verts=96, **kw):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, location=loc, vertices=verts, **kw)
    return active()


def sphere(r, loc=(0, 0, 0), **kw):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=64, ring_count=32, **kw)
    return smooth(active())


def cube(size=(1, 1, 1), loc=(0, 0, 0), rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=[math.radians(a) for a in rot])
    o = active()
    o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    return o


def plane(size=(1, 1), loc=(0, 0, 0), rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_plane_add(size=1, location=loc, rotation=[math.radians(a) for a in rot])
    o = active()
    o.scale = (size[0], size[1], 1)
    bpy.ops.object.transform_apply(scale=True)
    return o


def shadow_catcher(size=10, z=0):
    p = plane((size, size), (0, 0, z))
    p.is_shadow_catcher = True
    return p


def hide(objs, flag=True):
    for o in objs:
        o.hide_render = flag


def render(path, w, h, samples=None, transparent=False, pct=100):
    sc = bpy.context.scene
    sc.render.resolution_x = w
    sc.render.resolution_y = h
    sc.render.resolution_percentage = 50 if "--fast" in __import__("sys").argv else pct
    sc.render.film_transparent = transparent
    if samples:
        sc.cycles.samples = samples
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def wood(name, light=(0.62, 0.42, 0.26), dark=(0.38, 0.22, 0.12), scale=1.0, rough=0.45, bump=0.15, stretch=14, rings=0.35):
    """木目。ノイズを一方向に引きのばした繊維＋ゆるい年輪。scale は 1cm あたりの細かさ。"""
    m = mat(name, light, rough)
    N, L, b = nodes(m)
    tc = N.new("ShaderNodeTexCoord")
    mp = N.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (scale, scale / stretch, scale)
    L.new(tc.outputs["Object"], mp.inputs["Vector"])
    fib = N.new("ShaderNodeTexNoise")
    fib.inputs["Scale"].default_value = 6
    fib.inputs["Detail"].default_value = 12
    fib.inputs["Roughness"].default_value = 0.62
    L.new(mp.outputs["Vector"], fib.inputs["Vector"])
    wv = N.new("ShaderNodeTexWave")
    wv.wave_type = 'BANDS'
    wv.bands_direction = 'X'
    wv.inputs["Scale"].default_value = 0.6
    wv.inputs["Distortion"].default_value = 4
    wv.inputs["Detail"].default_value = 3
    L.new(mp.outputs["Vector"], wv.inputs["Vector"])
    mx = N.new("ShaderNodeMix")
    mx.data_type = 'FLOAT'
    mx.inputs[0].default_value = rings
    L.new(fib.outputs["Fac"], mx.inputs[2])
    L.new(wv.outputs["Fac"], mx.inputs[3])
    cr = N.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].color = (*dark, 1)
    cr.color_ramp.elements[1].color = (*light, 1)
    cr.color_ramp.elements[0].position = 0.3
    cr.color_ramp.elements[1].position = 0.72
    L.new(mx.outputs[0], cr.inputs["Fac"])
    L.new(cr.outputs["Color"], b.inputs["Base Color"])
    bp = N.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = bump
    L.new(mx.outputs[0], bp.inputs["Height"])
    L.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def noise_bump(m, scale=200, strength=0.1, detail=6):
    """紙や布のこまかい凹凸。"""
    N, L, b = nodes(m)
    nz = N.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = scale
    nz.inputs["Detail"].default_value = detail
    bp = N.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = strength
    L.new(nz.outputs["Fac"], bp.inputs["Height"])
    L.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def noise_color(m, c1, c2, scale=8, detail=4, lo=0.35, hi=0.65):
    """2色をノイズでまだらに混ぜる。"""
    N, L, b = nodes(m)
    nz = N.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = scale
    nz.inputs["Detail"].default_value = detail
    cr = N.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].color = (*c1, 1)
    cr.color_ramp.elements[1].color = (*c2, 1)
    cr.color_ramp.elements[0].position = lo
    cr.color_ramp.elements[1].position = hi
    L.new(nz.outputs["Fac"], cr.inputs["Fac"])
    L.new(cr.outputs["Color"], b.inputs["Base Color"])
    return m


def emission(name, color, strength=5):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    N, L = m.node_tree.nodes, m.node_tree.links
    N.remove(N["Principled BSDF"])
    e = N.new("ShaderNodeEmission")
    e.inputs[0].default_value = (*color, 1)
    e.inputs[1].default_value = strength
    L.new(e.outputs[0], N["Material Output"].inputs[0])
    return m
