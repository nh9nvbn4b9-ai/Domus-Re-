"""Materiali PBR esportabili in glTF (texture collegate direttamente al Principled BSDF) e utilità di luce."""
import math

import bpy


def image_node(nt, path, non_color=False):
    img = bpy.data.images.load(path, check_existing=True)
    if non_color:
        img.colorspace_settings.name = 'Non-Color'
    n = nt.nodes.new('ShaderNodeTexImage')
    n.image = img
    return n


def pbr(name, color=(0.8, 0.8, 0.8), rough=0.5, metal=0.0, diff=None, nor=None, rough_map=None, nor_strength=1.0,
        emission=None, emission_strength=0.0, emission_map=None, alpha=1.0, transmission=0.0, ior=1.45, spec=0.5):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    b.inputs['IOR'].default_value = ior
    b.inputs['Specular IOR Level'].default_value = spec
    if diff:
        t = image_node(nt, diff)
        nt.links.new(t.outputs['Color'], b.inputs['Base Color'])
    if rough_map:
        t = image_node(nt, rough_map, True)
        nt.links.new(t.outputs['Color'], b.inputs['Roughness'])
    if nor:
        t = image_node(nt, nor, True)
        nm = nt.nodes.new('ShaderNodeNormalMap')
        nm.inputs['Strength'].default_value = nor_strength
        nt.links.new(t.outputs['Color'], nm.inputs['Color'])
        nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])
    if emission_map:
        t = image_node(nt, emission_map)
        nt.links.new(t.outputs['Color'], b.inputs['Emission Color'])
        b.inputs['Emission Strength'].default_value = emission_strength or 1.0
    elif emission:
        b.inputs['Emission Color'].default_value = (*emission, 1)
        b.inputs['Emission Strength'].default_value = emission_strength
    if transmission:
        b.inputs['Transmission Weight'].default_value = transmission
    if alpha < 1.0:
        b.inputs['Alpha'].default_value = alpha
        if hasattr(m, 'surface_render_method'):
            m.surface_render_method = 'BLENDED'
    return m


def kelvin(t):
    t = t / 100.0
    r = 255 if t <= 66 else 329.698727446 * ((t - 60) ** -0.1332047592)
    g = 99.4708025861 * math.log(t) - 161.1195681661 if t <= 66 else 288.1221695283 * ((t - 60) ** -0.0755148492)
    b = 255 if t >= 66 else (0 if t <= 19 else 138.5177312231 * math.log(t - 10) - 305.0447927307)
    return tuple(max(0, min(255, c)) / 255 for c in (r, g, b))
