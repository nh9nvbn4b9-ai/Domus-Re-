"""Billboard degli alberi: render Cycles (sfondo trasparente) degli alberi scansionati Poly Haven,
illuminati dallo stesso cielo e dallo stesso sole della scena. Gli alberi veri hanno 1-2 milioni
di poligoni: per il web si usano queste immagini su piani incrociati.

Uso: <venv-blender>/bin/python pipeline/blender/render_billboards.py
"""
import glob
import math
import os

import bpy
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CACHE = os.path.join(ROOT, 'pipeline', 'cache')
OUT = os.path.join(CACHE, 'billboards')
os.makedirs(OUT, exist_ok=True)
TREES = {'tree_small_02': 0.0, 'island_tree_02': 0.0}

for asset, rot in TREES.items():
    for view, yaw in (('a', 0.0), ('b', math.pi / 2)):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        sc = bpy.context.scene
        sc.render.engine = 'CYCLES'
        sc.cycles.device = 'CPU'
        sc.cycles.samples = 48
        sc.cycles.use_denoising = True
        sc.render.film_transparent = True
        sc.render.resolution_x = sc.render.resolution_y = 1024
        sc.view_settings.view_transform = 'Standard'
        w = bpy.data.worlds.new('w')
        sc.world = w
        w.use_nodes = True
        env = w.node_tree.nodes.new('ShaderNodeTexEnvironment')
        env.image = bpy.data.images.load(os.path.join(CACHE, 'hdri', 'kloppenheim_06_puresky_4k.hdr'))
        w.node_tree.links.new(env.outputs['Color'], w.node_tree.nodes['Background'].inputs['Color'])
        w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.5
        f = glob.glob(os.path.join(CACHE, 'models', asset, '*.gltf'))[0]
        bpy.ops.import_scene.gltf(filepath=f)
        objs = [o for o in sc.objects if o.type == 'MESH']
        for o in sc.objects:
            if o.parent is None:
                o.rotation_euler.z += rot + yaw
        bpy.context.view_layer.update()
        pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
        mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
        mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
        size = max(mx.x - mn.x, mx.z - mn.z) * 1.02
        cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
        cam.data.type = 'ORTHO'
        cam.data.ortho_scale = size
        cam.location = ((mn.x + mx.x) / 2, mn.y - 30, mn.z + size / 2)
        cam.rotation_euler = (math.radians(90), 0, 0)
        sc.collection.objects.link(cam)
        sc.camera = cam
        sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
        sun.data.energy = 2.2
        sun.data.color = (1.0, 0.72, 0.48)
        sun.rotation_euler = Vector((0.74, 0.64, -0.2)).to_track_quat('-Z', 'Y').to_euler()
        sc.collection.objects.link(sun)
        sc.render.filepath = os.path.join(OUT, f'{asset}_{view}.png')
        bpy.ops.render.render(write_still=True)
        with open(os.path.join(OUT, f'{asset}_{view}.txt'), 'w') as fh:
            fh.write(f'{size} {mn.z} {(mn.x + mx.x) / 2}')
        print('billboard', asset, view, 'lato', round(size, 2), 'm')
