"""Bake delle lightmap con Cycles (diretta + indiretta), denoise OIDN, salvataggio WebP codificato."""
import math
import os

import bpy
import numpy as np


def denoise_pixels(img, cache):
    sc = bpy.data.scenes.new('__denoise')
    cam = bpy.data.objects.new('__cam', bpy.data.cameras.new('__cam'))
    sc.collection.objects.link(cam)
    sc.camera = cam
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = 1
    sc.render.resolution_x, sc.render.resolution_y = img.size
    sc.render.resolution_percentage = 100
    sc.view_settings.view_transform = 'Standard'
    ng = bpy.data.node_groups.new('__dn', 'CompositorNodeTree')
    ng.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
    n_img = ng.nodes.new('CompositorNodeImage')
    n_img.image = img
    n_dn = ng.nodes.new('CompositorNodeDenoise')
    out = ng.nodes.new('NodeGroupOutput')
    ng.links.new(n_img.outputs['Image'], n_dn.inputs['Image'])
    ng.links.new(n_dn.outputs['Image'], out.inputs[0])
    sc.compositing_node_group = ng
    sc.render.use_compositing = True
    if hasattr(sc.render, 'compositor_device'):
        sc.render.compositor_device = 'CPU'
    sc.render.image_settings.file_format = 'OPEN_EXR'
    sc.render.image_settings.color_depth = '32'
    path = os.path.join(cache, '__denoise.exr')
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True, scene=sc.name)
    res = bpy.data.images.load(path, check_existing=False)
    px = np.empty(res.size[0] * res.size[1] * 4, np.float32)
    res.pixels.foreach_get(px)
    bpy.data.images.remove(res)
    bpy.data.scenes.remove(sc)
    return px


def bake_lightmap(scene, obj, size, samples, cache):
    me = obj.data
    if 'UVMap' not in me.uv_layers:
        me.uv_layers.new(name='UVMap')
    lm = me.uv_layers.new(name='Lightmap')
    me.uv_layers['UVMap'].active_render = True
    me.uv_layers.active = lm
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.0015, area_weight=1.0, scale_to_bounds=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    img = bpy.data.images.new(f'LM_{obj.name}', size, size, float_buffer=True)
    added = []
    for mat in me.materials:
        nt = mat.node_tree
        n = nt.nodes.new('ShaderNodeTexImage')
        n.image = img
        uvn = nt.nodes.new('ShaderNodeUVMap')
        uvn.uv_map = 'Lightmap'
        nt.links.new(uvn.outputs['UV'], n.inputs['Vector'])
        for x in nt.nodes:
            x.select = False
        n.select = True
        nt.nodes.active = n
        added.append((nt, n, uvn))
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = samples
    scene.cycles.max_bounces = 4
    bpy.ops.object.bake(type='DIFFUSE', pass_filter={'DIRECT', 'INDIRECT'}, margin=8, use_clear=True)
    for nt, n, uvn in added:
        nt.nodes.remove(n)
        nt.nodes.remove(uvn)
    px = denoise_pixels(img, cache)
    return px.reshape(size, size, 4)[::-1, :, :3]


def save_lightmap(rgb, path, scale):
    from PIL import Image
    enc = np.clip(rgb / scale, 0, 1) ** (1 / 2.2)
    Image.fromarray((enc * 255 + 0.5).astype(np.uint8)).save(path, quality=90, method=6)
    print('lightmap', path, 'max', float(rgb.max()), 'p99', float(np.percentile(rgb, 99)))
