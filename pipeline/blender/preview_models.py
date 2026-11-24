"""Render di anteprima (Cycles CPU) dei modelli Poly Haven scaricati, uno per immagine."""
import bpy, sys, os, glob, math, time
from mathutils import Vector

OUT = sys.argv[sys.argv.index('--out') + 1]
ids = sys.argv[sys.argv.index('--ids') + 1].split(',')
ROOT = os.path.join(os.path.dirname(__file__), '..', 'cache', 'models')

for asset in ids:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 24; sc.cycles.use_denoising = True
    sc.render.resolution_x = sc.render.resolution_y = 320
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
    w.node_tree.nodes['Background'].inputs[0].default_value = (0.8, 0.8, 0.82, 1); w.node_tree.nodes['Background'].inputs[1].default_value = 1.0
    f = glob.glob(os.path.join(ROOT, asset, '*.gltf'))[0]
    t = time.time(); bpy.ops.import_scene.gltf(filepath=f)
    objs = [o for o in sc.objects if o.type == 'MESH']
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    c = (mn + mx) / 2; size = max(mx - mn)
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
    cam.location = c + Vector((size * 1.2, -size * 1.6, size * 0.6))
    cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler()
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); sun.data.energy = 3; sun.rotation_euler = (0.8, 0.2, 0.6); sc.collection.objects.link(sun)
    sc.render.filepath = os.path.join(OUT, f'model-{asset}.png')
    bpy.ops.render.render(write_still=True)
    tris = sum(len(o.data.polygons) for o in objs)
    print(f'{asset}: dims {tuple(round(v,2) for v in (mx-mn))} m, faces {tris}, {time.time()-t:.1f}s')
