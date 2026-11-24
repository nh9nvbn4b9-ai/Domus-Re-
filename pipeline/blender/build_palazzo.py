"""Costruisce il palazzo ricostruito dalla foto, la strada e le luci; esporta il GLB per il sito
e, a richiesta, un render Cycles di controllo.

Uso (dalla radice del repo):
  <venv-blender>/bin/python pipeline/blender/build_palazzo.py [--render foto|hero] [--samples 64]
      [--res 0.5] [--no-export] [--no-trees]
"""
import argparse
import math
import os
import sys
import glob

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
from lib import box, sweep_h, sweep_arc, frame_rect, prism_xz, arch_poly, lathe  # noqa: E402
import palazzo_spec as P  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CACHE = os.path.join(ROOT, 'pipeline', 'cache')
TEX = lambda a, f: os.path.join(CACHE, 'textures', a, f)  # noqa: E731
DER = lambda f: os.path.join(CACHE, 'derived', f)  # noqa: E731

ap = argparse.ArgumentParser()
ap.add_argument('--render', default=None)
ap.add_argument('--samples', type=int, default=64)
ap.add_argument('--res', type=float, default=0.5)
ap.add_argument('--no-export', action='store_true')
ap.add_argument('--no-trees', action='store_true')
ap.add_argument('--out', default=os.path.join(CACHE, 'renders'))
ap.add_argument('--world', type=float, default=0.2)
ap.add_argument('--sun', type=float, default=2.4)
ap.add_argument('--exposure', type=float, default=0.45)
ap.add_argument('--no-bake', action='store_true')
ap.add_argument('--lm-size', type=int, default=2048)
ap.add_argument('--lm-samples', type=int, default=64)
args = ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:])

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'

HW = P.HALF_W
G, U, C, M = P.GROUND, P.UPPER, P.CENTRAL, P.MANSARD

# ===========================================================================
# Materiali (Principled BSDF con texture collegate direttamente: esportabili in glTF)
# ===========================================================================

def image_node(nt, path, non_color=False):
    img = bpy.data.images.load(path, check_existing=True)
    if non_color:
        img.colorspace_settings.name = 'Non-Color'
    n = nt.nodes.new('ShaderNodeTexImage')
    n.image = img
    return n


def pbr(name, color=(0.8, 0.8, 0.8), rough=0.5, metal=0.0, diff=None, nor=None, rough_map=None,
        nor_strength=1.0, emission=None, emission_strength=0.0, alpha=1.0, transmission=0.0, ior=1.45,
        spec=0.5):
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
    if emission:
        b.inputs['Emission Color'].default_value = (*emission, 1)
        b.inputs['Emission Strength'].default_value = emission_strength
    if transmission:
        b.inputs['Transmission Weight'].default_value = transmission
    if alpha < 1.0:
        b.inputs['Alpha'].default_value = alpha
        if hasattr(m, 'surface_render_method'):
            m.surface_render_method = 'BLENDED'
    return m


MAT = {
    'stone': pbr('Pietra', diff=DER('stone_cream_diff.jpg'), nor=TEX('plaster_grey_04', 'plaster_grey_04_nor_gl_2k.jpg'),
                 rough_map=TEX('plaster_grey_04', 'plaster_grey_04_rough_2k.jpg'), nor_strength=0.6),
    'slab': pbr('PietraLastre', diff=DER('slab_cream_diff.jpg'), nor=TEX('marble_01', 'marble_01_nor_gl_2k.jpg'),
                rough_map=TEX('marble_01', 'marble_01_rough_2k.jpg'), nor_strength=0.5),
    'slate': pbr('Ardesia', diff=DER('slate_dark_diff.jpg'),
                 nor=TEX('roof_slates_03', 'roof_slates_03_nor_gl_2k.jpg'),
                 rough_map=TEX('roof_slates_03', 'roof_slates_03_rough_2k.jpg'), nor_strength=1.0),
    'pavement': pbr('Marciapiede', diff=DER('pavement_diff.jpg'), nor=TEX('marble_01', 'marble_01_nor_gl_2k.jpg'),
                    rough=0.35, nor_strength=0.4),
    'road': pbr('Sampietrini', diff=TEX('square_cobblestone', 'square_cobblestone_diff_2k.jpg'),
                nor=TEX('square_cobblestone', 'square_cobblestone_nor_gl_2k.jpg'),
                rough_map=TEX('square_cobblestone', 'square_cobblestone_rough_2k.jpg'), nor_strength=1.0),
    'neighbor': pbr('PietraVicino', diff=DER('stone_neighbor_diff.jpg'), nor=TEX('plaster_grey_04', 'plaster_grey_04_nor_gl_2k.jpg'),
                    rough=0.8, nor_strength=0.5),
    'mortar': pbr('Fuga', color=(0.42, 0.38, 0.32), rough=0.95),
    'iron': pbr('FerroVerniciato', color=(0.018, 0.018, 0.018), rough=0.38, metal=0.7),
    'bronze': pbr('Bronzo', color=(0.11, 0.08, 0.05), rough=0.42, metal=1.0),
    'brass': pbr('Ottone', color=(0.86, 0.66, 0.32), rough=0.22, metal=1.0),
    'glass': pbr('Vetro', color=(1, 1, 1), rough=0.02, transmission=1.0, ior=1.5),
    'curtain': pbr('TendaSottile', color=(0.9, 0.82, 0.7), rough=0.9, emission=(1.0, 0.72, 0.45), emission_strength=0.35),
    'int_wall': pbr('ParetiInterne', color=(0.62, 0.5, 0.38), rough=0.85),
    'int_ceiling': pbr('SoffittiInterni', color=(0.85, 0.8, 0.72), rough=0.9, emission=(1.0, 0.74, 0.5), emission_strength=0.12),
    'int_floor': pbr('ParquetProvvisorio', color=(0.32, 0.2, 0.11), rough=0.35),
    'lobby_floor': pbr('MarmoAtrio', diff=DER('slab_cream_diff.jpg'), rough=0.12, nor=TEX('marble_01', 'marble_01_nor_gl_2k.jpg'), nor_strength=0.2),
    'lamp_glow': pbr('LuceCalda', color=(1, 0.85, 0.6), emission=(1.0, 0.78, 0.5), emission_strength=25.0),
    'zinc': pbr('Zinco', color=(0.25, 0.26, 0.27), rough=0.5, metal=0.8),
    'hedge': pbr('Siepe', color=(0.05, 0.09, 0.04), rough=0.9),
}

COLL = {k: lib.collection(k) for k in ('Palazzo', 'Infissi', 'Interni', 'Contesto', 'Strada')}
PAL, INF, INT, CTX, STR = COLL['Palazzo'], COLL['Infissi'], COLL['Interni'], COLL['Contesto'], COLL['Strada']

# ===========================================================================
# Profili di modanature (d = sporgenza, h = quota) — chiusi automaticamente sul muro
# ===========================================================================

def cornice_profile(H, Pj):
    pts = [(0.0, 0.0), (0.10 * Pj, 0.0), (0.10 * Pj, 0.08 * H)]
    for i in range(1, 7):  # ovolo
        a = math.pi / 2 * i / 6
        pts.append((0.10 * Pj + 0.18 * Pj * math.sin(a), 0.08 * H + 0.22 * H * (1 - math.cos(a))))
    pts += [(0.30 * Pj, 0.34 * H), (0.82 * Pj, 0.40 * H), (0.86 * Pj, 0.40 * H), (0.86 * Pj, 0.62 * H),
            (0.90 * Pj, 0.62 * H), (0.90 * Pj, 0.66 * H)]
    for i in range(1, 9):  # gola dritta
        t = i / 8
        pts.append((0.90 * Pj + 0.10 * Pj * (0.5 - 0.5 * math.cos(math.pi * t)), 0.66 * H + 0.30 * H * t))
    pts += [(1.0 * Pj, 1.0 * H), (0.0, 1.0 * H)]
    return pts


def band_profile(H, Pj):
    return [(0, 0), (0.6 * Pj, 0.0), (0.6 * Pj, 0.15 * H), (Pj, 0.35 * H), (Pj, 0.75 * H), (0.8 * Pj, H), (0, H)]


def base_profile(H, Pj):
    """Zoccolo/base: sporgenza maggiore in basso."""
    return [(0, 0), (Pj, 0), (Pj, 0.45 * H), (0.75 * Pj, 0.55 * H), (0.45 * Pj, 0.8 * H), (0.2 * Pj, H), (0, H)]


def archivolt_profile(W, Pj):
    return [(0, 0), (0, 0.55 * Pj), (0.08 * W, 0.6 * Pj), (0.35 * W, 0.6 * Pj), (0.38 * W, 0.8 * Pj),
            (0.7 * W, 0.8 * Pj), (0.74 * W, Pj), (W, Pj), (W, 0)]


def chambranle_profile(W, Pj):
    return [(0, 0), (0, 0.6 * Pj), (0.15 * W, 0.75 * Pj), (0.55 * W, 0.75 * Pj), (0.62 * W, Pj), (W, Pj), (W, 0)]


def around(x0, x1, y_front, y_back=0.02):
    """Percorso attorno a un elemento sporgente (lato sx, fronte, lato dx)."""
    return [(x0, y_back), (x0, y_front), (x1, y_front), (x1, y_back)]


def mirror_x(fn):
    for s in (-1, 1):
        fn(s)


# ===========================================================================
# Muro di facciata con aperture
# ===========================================================================
EAVE = U['cornice_top']
wall = box('MuroFacciata', -HW, HW, 0.0, P.WALL_T, 0.0, EAVE, MAT['stone'], PAL, uv_scale=2.5)
cutters = []
CUT_Y0, CUT_Y1 = -0.5, P.WALL_T + 0.5


def cut_rect(x0, x1, z0, z1, y0=CUT_Y0, y1=CUT_Y1):
    cutters.append(box('cut', x0, x1, y0, y1, z0, z1, None, PAL, uv_scale=None))


def cut_poly(poly, y0=CUT_Y0, y1=CUT_Y1):
    cutters.append(prism_xz('cut', poly, y0, y1, None, PAL, uv_scale=None))


# --- aperture: archi del piano terra
for a in G['arches']:
    r = a['w'] / 2
    cut_poly(arch_poly(a['x'], -0.01, a['w'], a['top'] - r))

# --- aperture: finestre laterali per piano
for f in P.FLOORS:
    for s in (-1, 1):
        cx = s * U['side_bay_x']
        z0 = f['level'] if f['n'] > 1 else G['cornice_top'] - 0.05
        cut_rect(cx - U['side_win_w'] / 2, cx + U['side_win_w'] / 2, z0, f['win_top'])
        if 'balustrade' in f:  # nicchia della balaustra decorativa sotto la finestra
            b0, b1 = f['balustrade']
            cut_rect(cx - U['side_win_w'] / 2, cx + U['side_win_w'] / 2, b0, b1, -0.5, 0.14)
# --- aperture centrali
w2, w3, w4 = C['c2_win'], C['c3_win'], C['c4_win']
cut_rect(-w2['w'] / 2, w2['w'] / 2, w2['bottom'], w2['top'])
cut_rect(-w3['w'] / 2, w3['w'] / 2, w3['bottom'], w3['top'])
cut_poly(arch_poly(0, w4['bottom'], w4['w'], w4['top'] - w4['w'] / 2))
# nicchia della balaustra dell'attico
for s in (-1, 1):
    cx = s * U['side_bay_x']
    cut_rect(cx - U['side_win_w'] / 2, cx + U['side_win_w'] / 2, P.ATTIC_BALUSTRADE[0], P.ATTIC_BALUSTRADE[1], -0.5, 0.14)
lib.boolean_cut(wall, cutters)
lib.cube_uv(wall.data, 2.5)

# Finestre sul retro (cortile, non visibile in foto): stessi assi su tutti i piani; al piano 3 servono
# cucina, camera padronale e scala dell'appartamento (vedi palazzo_spec.APT_WINDOWS)
BACK_WINDOWS = [(w_['x'], w_['w']) for w_ in P.APT_WINDOWS if w_['wall'] == 'retro']
# Pareti laterali/posteriore (non visibili in foto: lisce, senza aperture inventate)
box('MuroLatoSx', -HW, -HW + 0.5, P.WALL_T, P.DEPTH, 0, EAVE, MAT['stone'], PAL, uv_scale=2.5)
retro_wall = box('MuroRetro', -HW, HW, P.DEPTH - 0.5, P.DEPTH, 0, EAVE, MAT['stone'], PAL, uv_scale=2.5)
_rc = []
for f in P.FLOORS[1:]:
    for bx, bw in BACK_WINDOWS:
        _rc.append(box('cut', bx - bw / 2, bx + bw / 2, P.DEPTH - 1.0, P.DEPTH + 1.0, f['level'] + 0.9, f['win_top'], None, PAL, uv_scale=None))
lib.boolean_cut(retro_wall, _rc)
lib.cube_uv(retro_wall.data, 2.5)
box('MuroLatoDx', HW - 0.5, HW, P.WALL_T, P.DEPTH, 0, EAVE, MAT['stone'], PAL, uv_scale=2.5)

# ===========================================================================
# Bugnato: corsi orizzontali di blocchi in rilievo nelle fasce di muro
# ===========================================================================

def rusticate(x0, x1, z0, z1, course, name, proj=0.05, gap=0.014, stagger=True):
    n = max(1, round((z1 - z0) / course))
    h = (z1 - z0) / n
    for i in range(n):
        zb = z0 + i * h + gap / 2
        zt = z0 + (i + 1) * h - gap / 2
        width = x1 - x0
        if width > 1.4 and stagger:
            # giunti verticali sfalsati per i tratti larghi
            k = 2 if width < 2.6 else 3
            off = (width / k) * (0.5 if i % 2 else 0.0)
            cuts = sorted({x0, x1} | {x0 + off + j * width / k for j in range(1, k + 1) if x0 < x0 + off + j * width / k < x1})
            for a, b in zip(cuts[:-1], cuts[1:]):
                box(f'{name}_{i}', a + gap / 2, b - gap / 2, -proj, 0.0, zb, zt, MAT['stone'], PAL, bev=0.012, uv_scale=2.5)
        else:
            box(f'{name}_{i}', x0, x1, -proj, 0.0, zb, zt, MAT['stone'], PAL, bev=0.012, uv_scale=2.5)


Z_CORN = G['cornice_top']
Z_FRIEZE = U['frieze_bottom']
oc, ic = U['outer_col_x'], U['inner_col_x']
sb, sw = U['side_bay_x'], U['side_win_w']
FRAME_W = 0.20
side_frame_in = sb - sw / 2 - 0.10 - FRAME_W
side_frame_out = sb + sw / 2 + 0.10 + FRAME_W
for s in (-1, 1):
    regions = [
        (oc + U['outer_col_r'], HW),
        (side_frame_out, oc - U['outer_col_r']),
        (ic + U['inner_col_r'], side_frame_in),
    ]
    for k, (a, b) in enumerate(regions):
        xa, xb = sorted((s * a, s * b))
        rusticate(xa, xb, Z_CORN, Z_FRIEZE, U['course_h'], f'Bugnato{s}_{k}')
    xa, xb = sorted((s * (w3['w'] / 2 + 0.15), s * (ic - U['inner_col_r'])))
    rusticate(xa, xb, Z_CORN, C['arch_frame']['cz'], U['course_h'], f'BugnatoC{s}')
    # piano terra: fasce tra lesene e archi
    px = G['pilaster_x']
    g_regions = [
        (abs(px[0]) + G['shaft_w'] / 2, HW),
        (abs(G['arches'][0]['x']) + G['arches'][0]['w'] / 2 + 0.28, abs(px[0]) - G['shaft_w'] / 2),
        (abs(px[1]) + G['shaft_w'] / 2, abs(G['arches'][0]['x']) - G['arches'][0]['w'] / 2 - 0.28),
        (G['arches'][1]['w'] / 2 + 0.28, abs(px[1]) - G['shaft_w'] / 2),
    ]
    for k, (a, b) in enumerate(g_regions):
        if b - a < 0.05:
            continue
        xa, xb = sorted((s * a, s * b))
        rusticate(xa, xb, 0.0, G['capital_top'], 0.56, f'BugnatoPT{s}_{k}', proj=0.04)

# ===========================================================================
# Piano terra: lesene scanalate, archi, trabeazione
# ===========================================================================
PED_PROJ, SHAFT_PROJ = 0.55, 0.42
for i, x in enumerate(G['pilaster_x']):
    pw = G['pedestal_w']
    box(f'PiedistalloPT{i}', x - pw / 2, x + pw / 2, -PED_PROJ, 0.02, 0.0, G['pedestal_top'] - 0.18, MAT['stone'], PAL, bev=0.01)
    sweep_h(f'PiedistalloPTcap{i}', around(x - pw / 2, x + pw / 2, -PED_PROJ), G['pedestal_top'] - 0.18,
            band_profile(0.18, 0.06), MAT['stone'], PAL)
    sweep_h(f'PiedistalloPTbase{i}', around(x - pw / 2, x + pw / 2, -PED_PROJ), 0.0, base_profile(0.22, 0.05), MAT['stone'], PAL)
    frame_rect(f'PiedistalloPTpan{i}', x - pw / 2 + 0.16, x + pw / 2 - 0.16, 0.32, G['pedestal_top'] - 0.36,
               chambranle_profile(0.05, 0.025), MAT['stone'], PAL, y0=-PED_PROJ)
    sh = lib.fluted_pilaster(f'LesenaPT{i}', G['shaft_w'], G['shaft_top'] - G['pedestal_top'], SHAFT_PROJ, MAT['stone'], PAL)
    sh.location = (x, 0, G['pedestal_top'])
    # base attica della lesena
    sweep_h(f'LesenaPTbase{i}', around(x - G['shaft_w'] / 2, x + G['shaft_w'] / 2, -SHAFT_PROJ), G['pedestal_top'],
            base_profile(0.16, 0.05), MAT['stone'], PAL)
    # capitello: collarino + echino + abaco
    cap_h = G['capital_top'] - G['shaft_top']
    ov = (G['capital_w'] - G['shaft_w']) / 2
    sweep_h(f'LesenaPTcap{i}', around(x - G['shaft_w'] / 2, x + G['shaft_w'] / 2, -SHAFT_PROJ), G['shaft_top'],
            [(0, 0), (0.03, 0), (0.03, 0.05 * cap_h), (0.01, 0.1 * cap_h), (0.01, 0.42 * cap_h), (0.03, 0.46 * cap_h),
             (0.03, 0.5 * cap_h), (0.6 * ov, 0.6 * cap_h), (0.85 * ov, 0.7 * cap_h), (ov, 0.74 * cap_h), (ov, cap_h), (0, cap_h)],
            MAT['stone'], PAL)

for i, a in enumerate(G['arches']):
    r = a['w'] / 2
    spring = a['top'] - r
    sweep_arc(f'ArchivoltoPT{i}', a['x'], spring, r, archivolt_profile(0.26, 0.09), MAT['stone'], PAL, extend=spring, segs=40)
    # chiave in bronzo a mensola (come in foto)
    kz = a['top'] + 0.26
    key = prism_xz(f'ChiaveBronzo{i}', [(a['x'] - 0.12, a['top'] - 0.05), (a['x'] + 0.12, a['top'] - 0.05),
                                        (a['x'] + 0.2, G['capital_top'] - 0.02), (a['x'] - 0.2, G['capital_top'] - 0.02)],
                   -0.24, 0.0, MAT['bronze'], PAL)
    lib.bevel(key, 0.02, 2)
    for s in (-1, 1):
        sc = lib.spiral_band(f'ChiaveVoluta{i}{s}', 0.09, 0.16, 1.6, 0.32, 0.05, MAT['bronze'], PAL)
        sc.location = (a['x'] + s * 0.13, -0.24, kz + 0.25)
        sc.scale = (s, 1, 1)

# trabeazione del piano terra
CHW = G['cornice_half_w']
ARCH_FRONT = -0.62
left_path = lambda yf: [(-CHW, P.DEPTH), (-CHW, yf), (CHW, yf), (CHW, 0.4)]  # noqa: E731
box('ArchitravePT', -CHW, CHW, ARCH_FRONT, 0.3, G['capital_top'], G['frieze_top'], MAT['stone'], PAL, uv_scale=2.5)
box('ArchitravePTlato', -CHW, -HW, 0.3, P.DEPTH, G['capital_top'], G['frieze_top'], MAT['stone'], PAL, uv_scale=2.5)
sweep_h('CornicionePT', left_path(ARCH_FRONT), G['frieze_top'], cornice_profile(G['cornice_top'] - G['frieze_top'], 0.5),
        MAT['stone'], PAL, uv_scale=2.5)
sweep_h('CornicionePTlist', left_path(ARCH_FRONT), G['capital_top'] - 0.06, band_profile(0.08, 0.03), MAT['stone'], PAL)
# zoccolo del palazzo
sweep_h('Zoccolo', [(-HW, P.DEPTH), (-HW, 0.0), (HW, 0.0), (HW, 0.3)], 0.0, base_profile(0.3, 0.06), MAT['stone'], PAL)

# ===========================================================================
# Ordine gigante: colonne ioniche su piedistalli
# ===========================================================================

def ionic_capital(name, x, yc, R, z0):
    parts = []
    parts.append(lathe(f'{name}_echino', [(R * 1.02, 0), (R * 1.08, R * 0.12), (R * 1.14, R * 0.28), (R * 1.0, R * 0.36)],
                       MAT['stone'], PAL, segs=40))
    parts[-1].location = (x, yc, z0)
    w = R * 2.9
    ab = box(f'{name}_abaco', x - w / 2, x + w / 2, yc - R * 1.45, yc + R * 0.4, z0 + R * 0.62, z0 + R * 0.78, MAT['stone'], PAL, bev=0.015)
    parts.append(ab)
    # canale tra le volute
    parts.append(box(f'{name}_canale', x - R * 1.25, x + R * 1.25, yc - R * 1.3, yc + R * 0.2, z0 + R * 0.36, z0 + R * 0.62,
                     MAT['stone'], PAL, bev=0.03, bev_seg=2))
    for s in (-1, 1):
        v = lib.spiral_band(f'{name}_voluta{s}', R * 0.5, 0.11, 2.3, 0.34, R * 1.4, MAT['stone'], PAL)
        v.location = (x + s * R * 1.12, yc - R * 0.6, z0 + R * 0.12)
        v.scale = (s, 1, 1)
        parts.append(v)
    return parts


def column(name, x, yc, R, ped_proj, z_ped0, z_ped1, z_base1, z_cap0, z_cap1):
    pw = R * 3.3
    box(f'{name}_piedistallo', x - pw / 2, x + pw / 2, -ped_proj, 0.02, z_ped0, z_ped1 - 0.2, MAT['stone'], PAL, bev=0.01)
    sweep_h(f'{name}_pied_cap', around(x - pw / 2, x + pw / 2, -ped_proj), z_ped1 - 0.2, band_profile(0.2, 0.06), MAT['stone'], PAL)
    sweep_h(f'{name}_pied_base', around(x - pw / 2, x + pw / 2, -ped_proj), z_ped0, base_profile(0.25, 0.05), MAT['stone'], PAL)
    frame_rect(f'{name}_pied_pan', x - pw / 2 + 0.14, x + pw / 2 - 0.14, z_ped0 + 0.32, z_ped1 - 0.36,
               chambranle_profile(0.05, 0.025), MAT['stone'], PAL, y0=-ped_proj)
    hb = z_base1 - z_ped1
    b = lathe(f'{name}_base', [(R * 1.35, 0), (R * 1.35, hb * 0.25), (R * 1.25, hb * 0.45), (R * 1.15, hb * 0.5),
                               (R * 1.1, hb * 0.7), (R * 1.18, hb * 0.82), (R * 1.05, hb), (R * 1.0, hb)], MAT['stone'], PAL, segs=48)
    b.location = (x, yc, z_ped1)
    sh = lib.fluted_shaft(f'{name}_fusto', R, z_cap0 - z_base1, MAT['stone'], PAL, flutes=24)
    sh.location = (x, yc, z_base1)
    ionic_capital(f'{name}_capitello', x, yc, R, z_cap0)


for s in (-1, 1):
    column(f'ColonnaEst{s}', s * oc, -0.20, U['outer_col_r'], 0.75, Z_CORN, U['col_pedestal_top'], U['col_base_top'],
           U['outer_capital_bottom'], U['outer_capital_top'])
    column(f'ColonnaInt{s}', s * ic, -0.17, U['inner_col_r'], 0.62, Z_CORN, U['col_pedestal_top'], U['col_base_top'],
           U['inner_capital_bottom'], U['inner_capital_top'])
    # imposta dell'arco centrale sopra i capitelli interni
    box(f'ImpostaArco{s}', s * ic - 0.42, s * ic + 0.42, -0.42, 0.0, U['inner_capital_top'], C['arch_frame']['cz'], MAT['stone'], PAL, bev=0.01)

# ===========================================================================
# Campate laterali: cornici verticali, finestre, ringhiere, balaustre
# ===========================================================================
_baluster_cache = {}


def baluster_mesh(h):
    key = round(h, 3)
    if key not in _baluster_cache:
        o = lathe(f'Balaustro_{key}', lib.baluster_profile(h), MAT['stone'], PAL, segs=20)
        PAL.objects.unlink(o)
        _baluster_cache[key] = o
    return _baluster_cache[key]


def balustrade(name, x0, x1, z0, z1, y_center, depth=0.22, coll=PAL, spacing=0.2, returns=0.0):
    """Balaustra in pietra: zoccolo, balaustri a vaso torniti, corrimano."""
    plinth_h, rail_h = 0.09, 0.09
    yf, yb = y_center - depth / 2, y_center + depth / 2
    box(f'{name}_zoccolo', x0, x1, yf, yb, z0, z0 + plinth_h, MAT['stone'], coll, bev=0.008)
    box(f'{name}_corrimano', x0 - 0.02, x1 + 0.02, yf - 0.025, yb, z1 - rail_h, z1, MAT['stone'], coll, bev=0.012)
    bh = (z1 - rail_h) - (z0 + plinth_h)
    src = baluster_mesh(bh)
    n = max(2, int((x1 - x0 - 0.1) / spacing))
    step = (x1 - x0 - 0.1) / n
    for i in range(n + 1):
        lib.instance(src, f'{name}_b{i}', coll, location=(x0 + 0.05 + i * step, y_center, z0 + plinth_h))


def iron_railing(name, x0, x1, z0, z1, y, coll=INF, unit=0.24):
    """Parapetto in ferro battuto: telaio, piantoni e volute a C contrapposte."""
    r = 0.011
    lib.tube_path(f'{name}_top', [(x0, y, z1), (x1, y, z1)], r * 1.5, MAT['iron'], coll)
    lib.tube_path(f'{name}_mid', [(x0, y, z0 + 0.06), (x1, y, z0 + 0.06)], r, MAT['iron'], coll)
    lib.tube_path(f'{name}_bot', [(x0, y, z0 + 0.01), (x1, y, z0 + 0.01)], r, MAT['iron'], coll)
    n = max(1, round((x1 - x0) / unit))
    u = (x1 - x0) / n
    h = z1 - z0 - 0.08
    for i in range(n + 1):
        xi = x0 + i * u
        lib.tube_path(f'{name}_v{i}', [(xi, y, z0), (xi, y, z1)], r, MAT['iron'], coll)
        if i < n:
            cx = xi + u / 2
            for k, (zc, flip) in enumerate(((z0 + 0.06 + h * 0.3, 1), (z0 + 0.06 + h * 0.72, -1))):
                rr = min(u * 0.36, h * 0.2)
                pts = lib.scroll_pts(cx, zc, rr, turns=1.3, steps=22, flip=flip, y=y, start=math.pi / 2)
                lib.tube_path(f'{name}_s{i}{k}', pts, r * 0.8, MAT['iron'], coll)
            # anello centrale
            ring = [(cx + 0.035 * math.cos(t), y, z0 + 0.06 + h * 0.51 + 0.035 * math.sin(t)) for t in [2 * math.pi * j / 16 for j in range(16)]]
            lib.tube_path(f'{name}_o{i}', ring, r * 0.7, MAT['iron'], coll, closed=True)


def window_frame(name, x0, x1, z0, z1, transom=None, mullions=1, coll=INF, arch=False, fw=0.06):
    """Serramento in acciaio nero con vetro, traverso e montanti."""
    fy0, fy1 = P.GLASS_Y - 0.04, P.GLASS_Y + 0.04
    w = x1 - x0
    if arch:
        r = w / 2
        spring = z1 - r
        poly = arch_poly((x0 + x1) / 2, z0, w, spring)
        prism_xz(f'{name}_vetro', poly, P.GLASS_Y - 0.004, P.GLASS_Y + 0.004, MAT['glass'], coll, uv_scale=None)
        sweep_arc(f'{name}_arco', (x0 + x1) / 2, spring, r, [(-fw, -0.04), (0, -0.04), (0, 0.04), (-fw, 0.04)], MAT['iron'], coll,
                  y0=P.GLASS_Y, segs=32)
        box(f'{name}_sx', x0, x0 + fw, fy0, fy1, z0, spring, MAT['iron'], coll)
        box(f'{name}_dx', x1 - fw, x1, fy0, fy1, z0, spring, MAT['iron'], coll)
        box(f'{name}_spring', x0, x1, fy0, fy1, spring - 0.03, spring + 0.03, MAT['iron'], coll)
        # raggiera della lunetta
        cx = (x0 + x1) / 2
        sweep_arc(f'{name}_arcoint', cx, spring, r * 0.55, [(-0.035, -0.03), (0, -0.03), (0, 0.03), (-0.035, 0.03)], MAT['iron'], coll,
                  y0=P.GLASS_Y, segs=24)
        for k in (1, 2, 3):
            a = math.pi * k / 4
            box_pts = [(cx + r * 0.55 * math.cos(a), spring + r * 0.55 * math.sin(a)), (cx + (r - fw) * math.cos(a), spring + (r - fw) * math.sin(a))]
            lib.tube_path(f'{name}_rag{k}', [(box_pts[0][0], P.GLASS_Y, box_pts[0][1]), (box_pts[1][0], P.GLASS_Y, box_pts[1][1])], 0.016, MAT['iron'], coll)
        top_rect = spring
    else:
        box(f'{name}_vetro', x0, x1, P.GLASS_Y - 0.004, P.GLASS_Y + 0.004, z0, z1, MAT['glass'], coll, uv_scale=None)
        box(f'{name}_sx', x0, x0 + fw, fy0, fy1, z0, z1, MAT['iron'], coll)
        box(f'{name}_dx', x1 - fw, x1, fy0, fy1, z0, z1, MAT['iron'], coll)
        box(f'{name}_sopra', x0, x1, fy0, fy1, z1 - fw, z1, MAT['iron'], coll)
        top_rect = z1
    box(f'{name}_sotto', x0, x1, fy0, fy1, z0, z0 + fw, MAT['iron'], coll)
    if transom:
        box(f'{name}_trav', x0, x1, fy0, fy1, transom - 0.025, transom + 0.025, MAT['iron'], coll)
    for k in range(1, mullions + 1):
        xm = x0 + w * k / (mullions + 1)
        box(f'{name}_mont{k}', xm - fw * 0.42, xm + fw * 0.42, fy0, fy1, z0, top_rect if arch else z1, MAT['iron'], coll)


def curtains(name, x0, x1, z0, z1, y=P.GLASS_Y + 0.35):
    """Tende sottili raccolte ai lati, retroilluminate (come nella foto)."""
    w = x1 - x0
    for s, (a, b) in (('sx', (x0, x0 + w * 0.3)), ('dx', (x1 - w * 0.3, x1))):
        nx, nz = 18, 2
        verts, faces = [], []
        for j in range(nz + 1):
            z = z0 + (z1 - z0) * j / nz
            for i in range(nx + 1):
                t = i / nx
                xx = a + (b - a) * t
                yy = y + 0.04 * math.sin(t * math.pi * 7)
                verts.append((xx, yy, z))
        for j in range(nz):
            for i in range(nx):
                k = j * (nx + 1) + i
                faces.append((k, k + 1, k + nx + 2, k + nx + 1))
        # spessore minimo per avere un solido
        n = len(verts)
        verts += [(vx, vy + 0.01, vz) for vx, vy, vz in verts]
        faces += [tuple(i + n for i in reversed(f)) for f in faces]
        lib.mesh_obj(f'{name}_{s}', verts, faces, MAT['curtain'], INT, smooth=True, uv_scale=None)


for s in (-1, 1):
    cx = s * sb
    x0, x1 = cx - sw / 2, cx + sw / 2
    # lesene sottili che inquadrano la campata
    for xa in (x0 - 0.10 - FRAME_W, x1 + 0.10):
        box(f'CampataLesena{s}{xa:.2f}', xa, xa + FRAME_W, -0.10, 0.0, Z_CORN, Z_FRIEZE, MAT['stone'], PAL, bev=0.008)
    for f in P.FLOORS:
        n = f['n']
        z0 = f['level'] if n > 1 else Z_CORN - 0.05
        frame_rect(f'Cornice{n}{s}', x0, x1, z0, f['win_top'], chambranle_profile(0.10, 0.07), MAT['stone'], PAL)
        window_frame(f'Finestra{n}{s}', x0, x1, z0, f['win_top'], transom=f['win_top'] - 0.42, mullions=1)
        if n != P.APARTMENT_FLOOR:  # il piano 3 è l'appartamento (build_appartamento.py)
            curtains(f'Tende{n}{s}', x0, x1, z0, f['win_top'] - 0.1)
        if n == 1:
            continue
        iron_railing(f'Ringhiera{n}{s}', x0 + 0.02, x1 - 0.02, f['level'], f['railing_top'], -0.03)
        b0, b1 = f['balustrade']
        box(f'NicchiaFondo{n}{s}', x0, x1, 0.12, 0.16, b0, b1, MAT['stone'], PAL)
        balustrade(f'BalaustraDeco{n}{s}', x0 + 0.03, x1 - 0.03, b0, b1, 0.02, depth=0.18, spacing=0.17)
        p0, p1 = f['panel']
        frame_rect(f'Specchiatura{n}{s}', x0 + 0.05, x1 - 0.05, p0, p1, chambranle_profile(0.05, 0.03), MAT['stone'], PAL)
        ros = lathe(f'Rosone{n}{s}', [(0.07, 0), (0.07, 0.02), (0.05, 0.05), (0.02, 0.065), (0, 0.07)], MAT['stone'], PAL, segs=24)
        ros.location = (cx, 0.0, (p0 + p1) / 2)
        ros.rotation_euler = (math.pi / 2, 0, 0)
    # fregio e balaustra dell'attico sopra le finestre del piano 4
    f4 = P.FLOORS[-1]
    box(f'FregioAttico{s}', x0 - 0.1, x1 + 0.1, -0.08, 0.0, f4['win_top'], P.ATTIC_BALUSTRADE[0], MAT['stone'], PAL, bev=0.01)
    sweep_h(f'FregioAtticoCorn{s}', around(x0 - 0.1, x1 + 0.1, -0.08), P.ATTIC_BALUSTRADE[0] - 0.12, band_profile(0.12, 0.05), MAT['stone'], PAL)
    box(f'NicchiaAttico{s}', x0, x1, 0.12, 0.16, *P.ATTIC_BALUSTRADE, MAT['stone'], PAL)
    balustrade(f'BalaustraAttico{s}', x0 + 0.03, x1 - 0.03, *P.ATTIC_BALUSTRADE, 0.02, depth=0.18, spacing=0.17)

# vetrate in acciaio nero degli archi, con traversi e anelli in ottone (come in foto)
for i, a in enumerate(G['arches']):
    r = a['w'] / 2
    spring = a['top'] - r
    x0, x1 = a['x'] - r, a['x'] + r
    window_frame(f'VetrataPT{i}', x0, x1, 0.0, a['top'], arch=True, mullions=1, fw=0.11)
    for zt in (G['transom_low'], G['transom_high']):
        box(f'VetrataPTtrav{i}_{zt:.2f}', x0, x1, P.GLASS_Y - 0.045, P.GLASS_Y + 0.045, zt - 0.05, zt + 0.05, MAT['iron'], INF)
    zc = (G['transom_low'] + G['transom_high']) / 2
    ring = [(a['x'] + 0.15 * math.cos(t), P.GLASS_Y - 0.06, zc + 0.15 * math.sin(t)) for t in [2 * math.pi * j / 32 for j in range(32)]]
    lib.tube_path(f'AnelloOttone{i}', ring, 0.022, MAT['brass'], INF, closed=True)
    disc = lathe(f'AnelloOttoneC{i}', [(0.05, 0), (0.05, 0.02), (0.03, 0.035), (0, 0.04)], MAT['brass'], INF, segs=20)
    disc.location = (a['x'], P.GLASS_Y - 0.05, zc)
    disc.rotation_euler = (math.pi / 2, 0, 0)
    if i == 1:  # portone centrale a quattro ante con maniglioni ad anello
        for xm in (a['x'] - r / 2, a['x'] + r / 2):
            box(f'PortoneMontante{xm:.2f}', xm - 0.03, xm + 0.03, P.GLASS_Y - 0.045, P.GLASS_Y + 0.045, 0.0, G['transom_low'], MAT['iron'], INF)
        for s in (-1, 1):
            h = [(a['x'] + s * 0.09 + 0.07 * math.cos(t), P.GLASS_Y - 0.1, 1.05 + 0.12 * math.sin(t)) for t in [2 * math.pi * j / 24 for j in range(24)]]
            lib.tube_path(f'Maniglione{s}', h, 0.014, MAT['brass'], INF, closed=True)

RETRO = lib.collection('RetroInfissi')
_gy = P.GLASS_Y
P.GLASS_Y = P.DEPTH - 0.28
for f in P.FLOORS[1:]:
    for bx, bw in BACK_WINDOWS:
        window_frame(f'RetroFinestra{f["n"]}_{bx:.1f}', bx - bw / 2, bx + bw / 2, f['level'] + 0.9, f['win_top'],
                     transom=f['win_top'] - 0.4, mullions=1, coll=RETRO)
        box(f'RetroDavanzale{f["n"]}_{bx:.1f}', bx - bw / 2 - 0.06, bx + bw / 2 + 0.06, P.DEPTH - 0.02, P.DEPTH + 0.06,
            f['level'] + 0.84, f['level'] + 0.9, MAT['stone'], RETRO)
P.GLASS_Y = _gy

# ===========================================================================
# Campata centrale
# ===========================================================================
af = C['arch_frame']
sweep_arc('ArcoCentrale', 0.0, af['cz'], af['r_in'], archivolt_profile(af['r_out'] - af['r_in'], 0.16), MAT['stone'], PAL, segs=56)
# piano 4: finestra ad arco + balconcino in ferro su mensola
b4 = C['c4_balcony']
box('MensolaP4', -b4['base_half_w'], b4['base_half_w'], -b4['depth'], 0.0, b4['base_bottom'] + 0.12, b4['floor'] - 0.1, MAT['stone'], PAL, bev=0.01)
sweep_h('MensolaP4top', around(-b4['base_half_w'], b4['base_half_w'], -b4['depth']), b4['floor'] - 0.12,
        band_profile(0.12, 0.05), MAT['stone'], PAL)
sweep_h('MensolaP4bot', around(-b4['base_half_w'], b4['base_half_w'], -b4['depth']), b4['base_bottom'],
        [(0, 0), (0.0, 0.0), (0.04, 0.04), (0.06, 0.12), (0, 0.12)], MAT['stone'], PAL)
yb = -b4['depth'] + 0.05
iron_railing('BalconcinoP4', -b4['half_w'], b4['half_w'], b4['floor'], b4['rail_top'], yb)
for s in (-1, 1):
    lib.tube_path(f'BalconcinoP4lato{s}', [(s * b4['half_w'], yb, b4['rail_top']), (s * b4['half_w'], 0.0, b4['rail_top'])], 0.016, MAT['iron'], INF)
window_frame('FinestraP4C', -w4['w'] / 2, w4['w'] / 2, w4['bottom'], w4['top'], arch=True, mullions=1)
frame_rect('CorniceP4C', -w4['w'] / 2, w4['w'] / 2, w4['bottom'], w4['top'] - w4['w'] / 2, chambranle_profile(0.08, 0.05), MAT['stone'], PAL)
curtains('TendeP4C', -w4['w'] / 2, w4['w'] / 2, w4['bottom'], w4['top'] - 0.5)

# piano 3: portafinestra + grande balcone con balaustra (piano dell'appartamento)
b3 = C['c3_balcony']
SLAB_T = 0.28
box('BalconeP3soletta', -b3['half_w'] - 0.05, b3['half_w'] + 0.05, -b3['depth'] - 0.06, 0.0, b3['floor'] - SLAB_T, b3['floor'], MAT['stone'], PAL, bev=0.01)
box('BalconeP3fascia', -b3['slab_half_w'], b3['slab_half_w'], -b3['depth'] + 0.08, 0.0, b3['slab_bottom'] + 0.1, b3['floor'] - SLAB_T,
    MAT['stone'], PAL, bev=0.01)
sweep_h('BalconeP3fasciaCorn', around(-b3['slab_half_w'], b3['slab_half_w'], -b3['depth'] + 0.08), b3['slab_bottom'],
        [(0, 0), (0.05, 0.0), (0.05, 0.05), (0.02, 0.1), (0, 0.1)], MAT['stone'], PAL)
frame_rect('BalconeP3pan', -b3['slab_half_w'] + 0.2, b3['slab_half_w'] - 0.2, b3['slab_bottom'] + 0.22, b3['floor'] - SLAB_T - 0.12,
           chambranle_profile(0.05, 0.03), MAT['stone'], PAL, y0=-b3['depth'] + 0.08)
sweep_h('BalconeP3sotto', around(-b3['half_w'] - 0.05, b3['half_w'] + 0.05, -b3['depth'] - 0.06), b3['floor'] - SLAB_T,
        [(0, 0), (0.0, 0.0), (0.05, 0.08), (0.05, 0.14), (0, 0.14)], MAT['stone'], PAL)
yb3 = -b3['depth'] + 0.08
balustrade('BalaustraP3', -b3['half_w'] + 0.12, b3['half_w'] - 0.12, b3['floor'], b3['rail_top'], yb3, depth=0.24)
for s in (-1, 1):
    # pilastrini d'angolo e balaustre di ritorno
    box(f'BalconeP3dado{s}', s * b3['half_w'] - 0.14, s * b3['half_w'] + 0.14, yb3 - 0.14, yb3 + 0.14, b3['floor'], b3['rail_top'] + 0.03,
        MAT['stone'], PAL, bev=0.01)
    for i in range(3):
        lib.instance(baluster_mesh(b3['rail_top'] - b3['floor'] - 0.18), f'BalconeP3rit{s}{i}', PAL,
                     location=(s * (b3['half_w'] - 0.02), yb3 + 0.3 + i * 0.22, b3['floor'] + 0.09))
    box(f'BalconeP3ritCorr{s}', s * b3['half_w'] - 0.11, s * b3['half_w'] + 0.11, yb3 + 0.14, 0.0, b3['rail_top'] - 0.09, b3['rail_top'],
        MAT['stone'], PAL, bev=0.01)
    box(f'BalconeP3ritZoc{s}', s * b3['half_w'] - 0.11, s * b3['half_w'] + 0.11, yb3 + 0.14, 0.0, b3['floor'], b3['floor'] + 0.09,
        MAT['stone'], PAL, bev=0.008)
window_frame('PortafinestraP3', -w3['w'] / 2, w3['w'] / 2, w3['bottom'], w3['top'], transom=w3['transom'], mullions=3)
frame_rect('CorniceP3C', -w3['w'] / 2, w3['w'] / 2, w3['bottom'], w3['top'], chambranle_profile(0.10, 0.07), MAT['stone'], PAL)
box('ArchitraveP3C', -w3['w'] / 2 - 0.25, w3['w'] / 2 + 0.25, -0.16, 0.0, w3['top'] + 0.12, w3['top'] + 0.42, MAT['stone'], PAL, bev=0.01)
# piano 3: tende e interni dell'appartamento in build_appartamento.py

# piano 2: finestra sopra la lunetta
window_frame('FinestraP2C', -w2['w'] / 2, w2['w'] / 2, w2['bottom'], w2['top'], transom=w2['transom'], mullions=3)
frame_rect('CorniceP2C', -w2['w'] / 2, w2['w'] / 2, w2['bottom'], w2['top'], chambranle_profile(0.10, 0.07), MAT['stone'], PAL)
curtains('TendeP2C', -w2['w'] / 2, w2['w'] / 2, w2['bottom'], w2['transom'])

# lunetta sopra il cornicione del piano terra
lu = C['lunette']
semi = [(lu['r_in'] * math.cos(math.pi * i / 48), lu['cz'] + lu['r_in'] * math.sin(math.pi * i / 48)) for i in range(49)]
prism_xz('LunettaFondo', semi, -0.07, 0.0, MAT['slab'], PAL, uv_scale=2.0)
sweep_arc('LunettaArco', 0.0, lu['cz'], lu['r_in'], archivolt_profile(lu['r_out'] - lu['r_in'], 0.24), MAT['stone'], PAL, segs=64)

# ===========================================================================
# Trabeazione principale e mansarda
# ===========================================================================
FR_FRONT = -0.12
box('Fregio', -HW, HW, FR_FRONT, 0.3, U['frieze_bottom'], U['cornice_bottom'], MAT['stone'], PAL, uv_scale=2.5)
sweep_h('FregioListello', [(-HW, P.DEPTH), (-HW, FR_FRONT), (HW, FR_FRONT), (HW, 0.3)], U['frieze_bottom'] - 0.08,
        band_profile(0.1, 0.04), MAT['stone'], PAL)
sweep_h('Cornicione', [(-HW, P.DEPTH), (-HW, FR_FRONT), (HW, FR_FRONT), (HW, 0.4)], U['cornice_bottom'],
        cornice_profile(U['cornice_top'] - U['cornice_bottom'], 0.62), MAT['stone'], PAL, uv_scale=2.5)

# mansarda: tronco di piramide in ardesia
mb0 = M['eave']
mb1 = M['curb_bottom']
sb_ = M['setback']
xb, yb0, yb1 = HW - 0.08, 0.15, P.DEPTH - 0.15
xt, yt0, yt1 = xb - 0.55, yb0 + sb_, yb1 - sb_
mv = [(-xb, yb0, mb0), (xb, yb0, mb0), (xb, yb1, mb0), (-xb, yb1, mb0),
      (-xt, yt0, mb1), (xt, yt0, mb1), (xt, yt1, mb1), (-xt, yt1, mb1)]
mf = [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (4, 5, 6, 7), (0, 3, 2, 1)]
mans = lib.mesh_obj('Mansarda', mv, mf, MAT['slate'], PAL, uv_scale=2.0)
# fasce in pietra sugli spigoli di displuvio
for s in (-1, 1):
    a = Vector((s * xb, yb0, mb0))
    b = Vector((s * xt, yt0, mb1))
    d = (b - a)
    n = Vector((-0.0, -1.0, 0.0))
    side = Vector((s, 0, 0)) * -0.38
    quad = [a, a + side, b + side * 0.9, b]
    th = Vector((0, -0.05, 0.0))
    v = [tuple(p) for p in quad] + [tuple(p + th) for p in quad]
    lib.mesh_obj(f'SpigoloMansarda{s}', v, [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)],
                 MAT['stone'], PAL, uv_scale=2.0)
sweep_h('CordoloMansarda', [(-xt, P.DEPTH - 1.0), (-xt, yt0), (xt, yt0), (xt, P.DEPTH - 1.0)], mb1,
        cornice_profile(M['curb_top'] - mb1, 0.32), MAT['stone'], PAL)
box('TettoPiano', -xt, xt, yt0, yt1, M['curb_top'] - 0.05, M['curb_top'] + 0.12, MAT['zinc'], PAL, uv_scale=None)

# abbaini laterali ad arco
for s in (-1, 1):
    cx = s * M['side_dormer_x']
    W_ = M['dormer_surround_w']
    sp = M['dormer_surround_top'] - W_ / 2
    body = prism_xz(f'Abbaino{s}', arch_poly(cx, mb0 - 0.05, W_, sp), 0.10, 1.6, MAT['stone'], PAL, uv_scale=2.0)
    ww = M['dormer_w']
    wsp = M['dormer_top'] - ww / 2
    lib.boolean_cut(body, [prism_xz('cut', arch_poly(cx, mb0 + 0.02, ww, wsp), -0.2, 1.0, None, PAL, uv_scale=None)])
    lib.cube_uv(body.data, 2.0)
    sweep_arc(f'AbbainoCornice{s}', cx, sp, W_ / 2 - 0.14, archivolt_profile(0.16, 0.08), MAT['stone'], PAL, y0=0.10, extend=sp - mb0 - 0.2)
    sweep_arc(f'AbbainoFinestraCornice{s}', cx, wsp, ww / 2, chambranle_profile(0.07, 0.05), MAT['stone'], PAL, y0=0.10, extend=wsp - mb0)
    for k in (-1, 1):
        v = lib.spiral_band(f'AbbainoOrecchio{s}{k}', 0.11, 0.14, 1.7, 0.35, 0.1, MAT['stone'], PAL)
        v.location = (cx + k * (W_ / 2 + 0.05), 0.05, mb0 + 0.62)
        v.scale = (-k, 1, 1)
    gy = P.GLASS_Y
    P.GLASS_Y = 0.32
    window_frame(f'AbbainoFinestra{s}', cx - ww / 2, cx + ww / 2, mb0 + 0.02, M['dormer_top'], arch=True, mullions=1)
    P.GLASS_Y = gy

# padiglione centrale in pietra
ph = M['pavilion_half_w']
pav_top = M['pavilion_top'] - 0.32
pav = prism_xz('Padiglione', [(-ph, mb0 - 0.05), (ph, mb0 - 0.05), (ph - 0.12, pav_top), (-ph + 0.12, pav_top)], 0.0, 3.2, MAT['stone'], PAL, uv_scale=2.5)
pw_ = M['pav_win_w']
psp = M['pav_win_top'] - pw_ / 2
lib.boolean_cut(pav, [prism_xz('cut', arch_poly(0, M['pav_win_bottom'], pw_, psp), -0.3, 1.0, None, PAL, uv_scale=None)])
lib.cube_uv(pav.data, 2.5)
sweep_h('PadiglioneCorn', [(-ph + 0.12, 3.0), (-ph + 0.12, 0.0), (ph - 0.12, 0.0), (ph - 0.12, 3.0)], pav_top,
        cornice_profile(M['pavilion_top'] - pav_top, 0.3), MAT['stone'], PAL)
sweep_arc('PadiglioneArco', 0.0, psp, pw_ / 2 + 0.02, archivolt_profile(0.42, 0.14), MAT['stone'], PAL, segs=48)
for s in (-1, 1):
    x_in = s * (pw_ / 2 + 0.1)
    xa, xbb = sorted((x_in, x_in + s * 0.62))
    box(f'PadiglionePilastro{s}', xa, xbb, -0.10, 0.0, mb0, M['pav_impost'], MAT['stone'], PAL, bev=0.01)
    sweep_h(f'PadiglioneImposta{s}', around(xa, xbb, -0.10), M['pav_impost'], band_profile(0.2, 0.06), MAT['stone'], PAL)
balustrade('BalaustraPadiglione', -pw_ / 2 - 0.05, pw_ / 2 + 0.05, M['pav_win_bottom'], M['pav_balustrade_top'], -0.12, depth=0.2)
window_frame('FinestraPadiglione', -pw_ / 2, pw_ / 2, M['pav_win_bottom'], M['pav_win_top'], arch=True, mullions=1)
curtains('TendePadiglione', -pw_ / 2, pw_ / 2, M['pav_win_bottom'], psp)

# ===========================================================================
# Interni visibili dalle finestre (provvisori: l'appartamento del piano 3 arriva in fase 4)
# ===========================================================================

def room(name, x0, x1, y0, y1, z0, z1, floor_mat):
    o = box(name, x0, x1, y0, y1, z0, z1, MAT['int_wall'], INT, uv_scale=2.0)
    me = o.data
    me.flip_normals()
    # rimuove la parete verso la facciata: le stanze si vedono attraverso le finestre
    import bmesh as _bm
    bm = _bm.new()
    bm.from_mesh(me)
    _bm.ops.delete(bm, geom=[f for f in bm.faces if f.normal.y > 0.5 and f.calc_center_median().y < y0 + 1e-3], context='FACES')
    bm.to_mesh(me)
    bm.free()
    me.materials.append(floor_mat)
    me.materials.append(MAT['int_ceiling'])
    for p in me.polygons:
        if p.normal.z > 0.5:
            p.material_index = 1
        elif p.normal.z < -0.5:
            p.material_index = 2
    return o


levels = [f['level'] for f in P.FLOORS] + [U['cornice_top'] - 0.4]
for i, f in enumerate(P.FLOORS):
    if f['n'] != P.APARTMENT_FLOOR:
        room(f'Interno{f["n"]}', -HW + 0.55, HW - 0.55, P.WALL_T, P.WALL_T + 5.5, f['level'] - 0.02, levels[i + 1] - 0.35, MAT['int_floor'])
room('InternoMansarda', -HW + 1.0, HW - 1.0, 0.5, 4.0, mb0 - 0.1, mb1, MAT['int_floor'])
lobby = room('Atrio', -HW + 0.55, HW - 0.55, P.WALL_T, 9.0, 0.0, G['capital_top'] - 0.2, MAT['lobby_floor'])


def import_gltf(asset, name, coll, loc, scale=1.0, rot_z=0.0):
    files = glob.glob(os.path.join(CACHE, 'models', asset, '*.gltf'))
    if not files:
        return []
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=files[0])
    new = [o for o in bpy.data.objects if o not in before]
    roots = [o for o in new if o.parent is None]
    for o in new:
        for c in o.users_collection:
            c.objects.unlink(o)
        coll.objects.link(o)
    for o in new:
        o['asset'] = asset
    for r in roots:
        r.name = name
        r.location = loc
        r.scale = (r.scale[0] * scale, r.scale[1] * scale, r.scale[2] * scale)
        r.rotation_euler.z += rot_z
    return new


import_gltf('Chandelier_03', 'LampadarioAtrio', INT, (0, 3.2, G['capital_top'] - 0.2 - 2.4), 2.2)
for s in (-1, 1):
    import_gltf('potted_plant_01', f'PiantaAtrio{s}', INT, (s * 3.66, 2.2, 0), 1.5, rot_z=s)
    import_gltf('potted_plant_02', f'PiantaAtrioB{s}', INT, (s * 1.6, 6.5, 0), 1.2)
for nlev, z in ((2, P.FLOORS[1]['level']),):
    import_gltf('Chandelier_03', f'LampadarioP{nlev}', INT, (0, 2.6, levels[nlev] - 0.35 - 1.05), 1.0)
import_gltf('Chandelier_01', 'LampadarioP4', INT, (0, 2.4, levels[4] - 0.35 - 0.85), 0.9)

# ===========================================================================
# Strada, marciapiedi, lampioni, contesto
# ===========================================================================
SW, RW = P.STREET['sidewalk_w'], P.STREET['road_w']
box('Marciapiede', -60, 60, -SW, 0.6, -0.15, 0.0, MAT['pavement'], STR, uv_scale=2.4)
box('Cordolo', -60, 60, -SW - 0.3, -SW, -0.17, 0.0, MAT['slab'], STR, bev=0.02, uv_scale=1.5)
box('Strada', -60, 60, -SW - 0.3 - RW, -SW - 0.3, -0.35, -0.15, MAT['road'], STR, uv_scale=1.6)
box('MarciapiedeOpposto', -60, 60, -SW - 0.3 - RW - 5, -SW - 0.3 - RW, -0.35, -0.15, MAT['pavement'], STR, uv_scale=2.4)
for i, x in enumerate(P.STREET['lamp_x']):
    import_gltf('street_lamp_01', f'Lampione{i}', STR, (x, P.STREET['lamp_y'], 0.0), 1.0, rot_z=math.pi / 2)
    glow = lathe(f'LampioneLuce{i}', [(0.05, 0), (0.07, 0.08), (0.05, 0.16)], MAT['lamp_glow'], STR, segs=12)
    glow.location = (x, P.STREET['lamp_y'], 3.42)

# edificio adiacente (a destra, visibile in foto: stesso linguaggio, un piano in meno)
NX0, NX1 = HW, HW + 15.0
N_EAVE = 19.2
box('VicinoMuro', NX0, NX1, 0.0, 0.6, 0.0, N_EAVE, MAT['neighbor'], CTX, uv_scale=2.5)
box('VicinoCorpo', NX0, NX1, 4.2, 14.0, 0.0, N_EAVE, MAT['neighbor'], CTX, uv_scale=2.5)
box('VicinoLato', NX1 - 0.5, NX1, 0.6, 4.2, 0.0, N_EAVE, MAT['neighbor'], CTX, uv_scale=2.5)
nc = []
for k in range(5):
    cx = NX0 + 1.6 + k * 2.9
    for lev, top in ((0.0, 4.6), (7.0, 9.4), (10.6, 13.0), (14.2, 16.6)):
        nc.append(box('cut', cx - 0.65, cx + 0.65, -0.5, 1.0, lev + (0.0 if lev == 0 else 0.0), top, None, CTX, uv_scale=None))
vic = bpy.data.objects['VicinoMuro']
lib.boolean_cut(vic, nc)
lib.cube_uv(vic.data, 2.5)
for k in range(5):
    cx = NX0 + 1.6 + k * 2.9
    for lev, top in ((0.0, 4.6), (7.0, 9.4), (10.6, 13.0), (14.2, 16.6)):
        frame_rect(f'VicinoCornice{k}_{lev}', cx - 0.65, cx + 0.65, lev, top, chambranle_profile(0.1, 0.06), MAT['neighbor'], CTX)
        window_frame(f'VicinoFinestra{k}_{lev}', cx - 0.65, cx + 0.65, lev, top, transom=top - 0.45, mullions=1, coll=CTX)
        if lev > 0:
            iron_railing(f'VicinoRinghiera{k}_{lev}', cx - 0.62, cx + 0.62, lev, lev + 0.45, -0.03, coll=CTX, unit=0.3)
            room(f'VicinoInterno{k}_{lev}', cx - 1.2, cx + 1.2, 0.7, 4.0, lev, top + 0.5, MAT['int_floor'])
sweep_h('VicinoMarcapiano', [(NX0, 0.0), (NX0, -0.1), (NX1, -0.1), (NX1, 0.3)], 6.2, cornice_profile(0.6, 0.35), MAT['neighbor'], CTX)
sweep_h('VicinoCornicione', [(NX0, 0.0), (NX0, -0.1), (NX1, -0.1), (NX1, 0.3)], N_EAVE - 0.5, cornice_profile(0.5, 0.6), MAT['neighbor'], CTX)
nv = [(NX0 + 0.1, 0.1, N_EAVE), (NX1, 0.1, N_EAVE), (NX1, 13.9, N_EAVE), (NX0 + 0.1, 13.9, N_EAVE),
      (NX0 + 0.1, 0.9, N_EAVE + 2.6), (NX1, 0.9, N_EAVE + 2.6), (NX1, 13.1, N_EAVE + 2.6), (NX0 + 0.1, 13.1, N_EAVE + 2.6)]
lib.mesh_obj('VicinoMansarda', nv, mf, MAT['slate'], CTX, uv_scale=2.0)

# edifici di contesto: intonaci romani (ocra, terracotta) con finestre e persiane
MAT['ochre'] = pbr('IntonacoOcra', diff=DER('plaster_ochre_diff.jpg'), nor=TEX('plaster_grey_04', 'plaster_grey_04_nor_gl_2k.jpg'), rough=0.85, nor_strength=0.6)
MAT['terracotta'] = pbr('IntonacoTerracotta', diff=DER('plaster_terracotta_diff.jpg'), nor=TEX('plaster_grey_04', 'plaster_grey_04_nor_gl_2k.jpg'), rough=0.85, nor_strength=0.6)
MAT['shutter'] = pbr('Persiane', color=(0.10, 0.16, 0.11), rough=0.6)


def context_building(name, x0, x1, height, mat, floors=5, ground_h=4.8, bays=None):
    box(f'{name}Muro', x0, x1, 0.0, 0.5, 0.0, height, mat, CTX, uv_scale=2.5)
    box(f'{name}Corpo', x0, x1, 3.6, 14.0, 0.0, height, mat, CTX, uv_scale=2.5)
    for xs in (x0, x1 - 0.4):
        box(f'{name}Lato{xs:.0f}', xs, xs + 0.4, 0.5, 3.6, 0.0, height, mat, CTX, uv_scale=2.5)
    bays = bays or max(2, int((x1 - x0) / 3.0))
    step = (x1 - x0) / bays
    fl_h = (height - ground_h - 0.8) / floors
    cuts, wins = [], []
    for k in range(bays):
        cx = x0 + step * (k + 0.5)
        wins.append((cx, 0.0, ground_h - 0.9, 1.6))
        for f in range(floors):
            z0 = ground_h + f * fl_h + 0.35
            wins.append((cx, z0, z0 + fl_h * 0.62, 1.1))
    for cx, z0, z1, w in wins:
        cuts.append(box('cut', cx - w / 2, cx + w / 2, -0.5, 1.0, z0, z1, None, CTX, uv_scale=None))
    lib.boolean_cut(bpy.data.objects[f'{name}Muro'], cuts)
    lib.cube_uv(bpy.data.objects[f'{name}Muro'].data, 2.5)
    for i, (cx, z0, z1, w) in enumerate(wins):
        window_frame(f'{name}Fin{i}', cx - w / 2, cx + w / 2, z0, z1, transom=z1 - 0.4 if z0 > 0 else None, mullions=1, coll=CTX)
        box(f'{name}Davanzale{i}', cx - w / 2 - 0.08, cx + w / 2 + 0.08, -0.08, 0.05, z0 - 0.07, z0, MAT['slab'], CTX, bev=0.01)
        if z0 > 0:
            for s in (-1, 1):  # persiane aperte ai lati della finestra
                xa = cx + s * (w / 2 + 0.02)
                box(f'{name}Pers{i}{s}', min(xa, xa + s * w / 2), max(xa, xa + s * w / 2), -0.06, -0.02, z0, z1, MAT['shutter'], CTX)
            room(f'{name}Int{i}', cx - w, cx + w, 0.5, 3.4, z0, z1 + 0.4, MAT['int_floor'])
    sweep_h(f'{name}Gronda', [(x0, 0.4), (x0, -0.02), (x1, -0.02), (x1, 0.4)], height - 0.5, cornice_profile(0.5, 0.55), mat, CTX)
    sweep_h(f'{name}Marcapiano', [(x0, 0.4), (x0, -0.02), (x1, -0.02), (x1, 0.4)], ground_h - 0.1, band_profile(0.25, 0.08), mat, CTX)
    rv = [(x0, -0.5, height), (x1, -0.5, height), (x1, 14.0, height), (x0, 14.0, height),
          ((x0 + x1) / 2 - 0.01, 6.5, height + 2.6), ((x0 + x1) / 2 + 0.01, 6.5, height + 2.6)]
    lib.mesh_obj(f'{name}Tetto', rv, [(0, 1, 5, 4), (1, 2, 5), (2, 3, 4, 5), (3, 0, 4), (0, 3, 2, 1)],
                 pbr(f'{name}Coppi', diff=TEX('roof_slates_03', 'roof_slates_03_diff_2k.jpg'), color=(0.6, 0.3, 0.2), rough=0.8), CTX, uv_scale=2.0)


context_building('EdificioSx', -40.0, -19.5, 20.5, MAT['ochre'], floors=5)
context_building('EdificioDx', NX1, NX1 + 17.0, 21.5, MAT['terracotta'], floors=5)


def billboard_tree(asset, name, loc, height, rot=0.0):
    """Albero su piani incrociati con l'immagine renderizzata da render_billboards.py."""
    path_a = os.path.join(CACHE, 'billboards', f'{asset}_a.png')
    if not os.path.exists(path_a):
        return
    size, zmin, _ = (float(v) for v in open(path_a.replace('.png', '.txt')).read().split())
    m = bpy.data.materials.get(f'AlberoBillboard_{asset}')
    if m is None:
        m = pbr(f'AlberoBillboard_{asset}', rough=0.9, spec=0.2)
        nt = m.node_tree
        t = image_node(nt, path_a)
        nt.links.new(t.outputs['Color'], nt.nodes['Principled BSDF'].inputs['Base Color'])
        nt.links.new(t.outputs['Alpha'], nt.nodes['Principled BSDF'].inputs['Alpha'])
        if hasattr(m, 'surface_render_method'):
            m.surface_render_method = 'DITHERED'
    k = height / size
    h = size * k
    for j, ang in enumerate((rot, rot + math.pi / 2)):
        ca, sa = math.cos(ang) * h / 2, math.sin(ang) * h / 2
        v = [(-ca, -sa, 0), (ca, sa, 0), (ca, sa, h), (-ca, -sa, h)]
        me = bpy.data.meshes.new(f'{name}{j}')
        me.from_pydata(v, [], [(0, 1, 2, 3)])
        uv = me.uv_layers.new(name='UVMap')
        for li, (uu, vv) in enumerate(((0, 0), (1, 0), (1, 1), (0, 1))):
            uv.data[li].uv = (uu, vv)
        me.materials.append(m)
        o = bpy.data.objects.new(f'{name}{j}', me)
        o.location = (loc[0], loc[1], loc[2] - zmin * k)
        CTX.objects.link(o)


# giardino a sinistra (in foto: alberi e siepi scure oltre il palazzo)
box('Siepe', -19.5, -HW - 0.4, -0.4, 0.6, 0.0, 1.6, MAT['hedge'], CTX, bev=0.2, bev_seg=3)
box('Prato', -19.5, -HW, -0.4, P.DEPTH, -0.05, 0.02, MAT['hedge'], CTX)
if args.no_trees:
    # web: alberi come billboard renderizzati dagli stessi modelli scansionati
    for i, (asset, x, y, h, r) in enumerate([('tree_small_02', -HW - 2.8, 1.6, 11.0, 0.3), ('island_tree_02', -HW - 7.5, 2.0, 7.5, 1.1),
                                              ('tree_small_02', -HW - 11.5, 3.5, 12.5, 0.9), ('island_tree_02', -HW - 15.0, 1.2, 6.8, 0.4)]):
        billboard_tree(asset, f'Albero{i}', (x, y, 0.0), h, r)
else:
    import_gltf('tree_small_02', 'AlberoSx', CTX, (-HW - 2.8, 1.6, 0.0), 2.4, rot_z=0.6)
    import_gltf('island_tree_02', 'AlberoSx2', CTX, (-HW - 7.5, 2.0, 0.0), 2.2, rot_z=2.0)
    import_gltf('tree_small_02', 'AlberoSx3', CTX, (-HW - 11.5, 3.5, 0.0), 2.7, rot_z=1.5)

# ===========================================================================
# Luci (Cycles) — le stesse posizioni sono esportate in src/data/palazzo.json per il web
# ===========================================================================
LCOL = lib.collection('Luci')


def kelvin(t):
    t = t / 100.0
    r = 255 if t <= 66 else 329.698727446 * ((t - 60) ** -0.1332047592)
    g = 99.4708025861 * math.log(t) - 161.1195681661 if t <= 66 else 288.1221695283 * ((t - 60) ** -0.0755148492)
    b = 255 if t >= 66 else (0 if t <= 19 else 138.5177312231 * math.log(t - 10) - 305.0447927307)
    return tuple(max(0, min(255, c)) / 255 for c in (r, g, b))


def add_light(name, kind, loc, energy, color, size=None, spot=None, blend=0.5, direction=None):
    ld = bpy.data.lights.new(name, kind)
    ld.energy = energy
    ld.color = color
    if kind == 'SPOT':
        ld.spot_size = math.radians(spot)
        ld.spot_blend = blend
        ld.shadow_soft_size = size or 0.04
    elif kind in ('POINT',):
        ld.shadow_soft_size = size or 0.05
    elif kind == 'AREA':
        ld.shape = 'RECTANGLE'
        ld.size, ld.size_y = size
    o = bpy.data.objects.new(name, ld)
    o.visible_camera = False
    o.location = loc
    if direction is not None:
        o.rotation_euler = Vector(direction).to_track_quat('-Z', 'Y').to_euler()
    LCOL.objects.link(o)
    return o


WARM = kelvin(2700)
for i, l in enumerate(P.light_rig()):
    if l['tipo'] == 'uplight':
        add_light(f'Uplight{i}', 'SPOT', l['pos'], 2600 if l['pos'][2] < 3 else 7000, kelvin(2500), spot=16, blend=0.5, direction=l['dir'])
    elif l['tipo'] == 'downlight':
        add_light(f'Downlight{i}', 'SPOT', l['pos'], 90, WARM, spot=70, blend=0.9, direction=l['dir'])
    else:
        add_light(f'Lanterna{i}', 'POINT', l['pos'], 45, kelvin(2400), size=0.06)
for i, f in enumerate(P.FLOORS):
    if f['n'] == P.APARTMENT_FLOOR:
        continue
    add_light(f'LuceInterno{f["n"]}', 'AREA', (0, P.WALL_T + 2.5, levels[i + 1] - 0.45), 160, kelvin(2900), size=(10.0, 4.0), direction=(0, 0, -1))
add_light('LuceAtrio', 'AREA', (0, 4.0, G['capital_top'] - 0.3), 420, kelvin(2800), size=(10.0, 7.0), direction=(0, 0, -1))
add_light('LuceLampadarioAtrio', 'POINT', (0, 3.2, G['capital_top'] - 0.2 - 2.0), 120, kelvin(2600), size=0.3)
add_light('LuceMansarda', 'AREA', (0, 2.0, mb1 - 0.2), 90, kelvin(2900), size=(9.0, 2.5), direction=(0, 0, -1))

# Sole basso dell'ora d'oro, coerente con il cielo HDRI (sole a ~5° sull'orizzonte)
SUN_DIR = Vector((-0.74, -0.64, 0.2)).normalized()  # sole basso da sud-ovest: rilievo in facciata e lame di luce negli interni
sun = add_light('Sole', 'SUN', (0, 0, 30), args.sun, kelvin(2800), direction=-SUN_DIR)
sun.data.angle = math.radians(1.2)

world = bpy.data.worlds.new('Cielo')
scene.world = world
world.use_nodes = True
wn = world.node_tree
env = wn.nodes.new('ShaderNodeTexEnvironment')
env.image = bpy.data.images.load(os.path.join(CACHE, 'hdri', 'kloppenheim_06_puresky_4k.hdr'))
mapping = wn.nodes.new('ShaderNodeMapping')
coord = wn.nodes.new('ShaderNodeTexCoord')
# il sole dell'HDRI (u≈0,612) viene ruotato nella direzione di SUN_DIR
u_sun = 0.612
az_hdri = (u_sun - 0.5) * 2 * math.pi           # atan2(y, -x) della direzione del sole nell'HDRI
az_target = math.atan2(SUN_DIR.y, -SUN_DIR.x)
mapping.inputs['Rotation'].default_value[2] = az_target - az_hdri
wn.links.new(coord.outputs['Generated'], mapping.inputs['Vector'])
wn.links.new(mapping.outputs['Vector'], env.inputs['Vector'])
bg = wn.nodes['Background']
bg.inputs['Strength'].default_value = args.world
wn.links.new(env.outputs['Color'], bg.inputs['Color'])

# ===========================================================================
# Camere
# ===========================================================================

def add_camera(name, loc, center_z, fov_v_deg, res):
    """Camera orizzontale con decentramento ottico (verticali parallele): center_z = quota del centro quadro sul piano di facciata."""
    cd = bpy.data.cameras.new(name)
    cd.sensor_fit = 'VERTICAL'
    cd.sensor_height = 24.0
    cd.lens = 12.0 / math.tan(math.radians(fov_v_deg) / 2)
    dist = -loc[1]
    frame_h = 2 * dist * math.tan(math.radians(fov_v_deg) / 2)
    # con sensor_fit VERTICAL lo spostamento è espresso in frazioni dell'altezza del fotogramma
    cd.shift_y = (center_z - loc[2]) / frame_h
    cd.clip_end = 3000
    o = bpy.data.objects.new(name, cd)
    o.location = loc
    o.rotation_euler = (math.radians(90), 0, 0)  # orizzontale, verso +Y (verticali parallele, come la foto)
    scene.collection.objects.link(o)
    o['res'] = res
    return o


cams = {
    # stessa inquadratura della foto (per il confronto) e inquadratura iniziale del sito (più ampia)
    'foto': add_camera('CameraFoto', (0, -40.0, 1.6), 13.4, 37.7, (836, 1672)),
    'hero': add_camera('CameraHero', (0, -36.0, 1.7), 15.0, 47.0, (1920, 1080)),
}

os.makedirs(os.path.join(ROOT, 'src', 'data'), exist_ok=True)
P.write_json(os.path.join(ROOT, 'src', 'data', 'palazzo.json'))

blend_path = os.path.join(CACHE, 'palazzo.blend')
bpy.ops.wm.save_as_mainfile(filepath=blend_path)
print('salvato', blend_path)
print('oggetti mesh:', sum(1 for o in bpy.data.objects if o.type == 'MESH'),
      'facce:', sum(len(o.data.polygons) for o in bpy.data.objects if o.type == 'MESH'))

# ===========================================================================
# Render di controllo
# ===========================================================================
if args.render:
    cam = cams[args.render]
    scene.camera = cam
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = args.samples
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 6
    scene.render.resolution_x, scene.render.resolution_y = cam['res']
    scene.render.resolution_percentage = int(args.res * 100)
    scene.view_settings.view_transform = 'AgX'
    try:
        scene.view_settings.look = 'AgX - Medium High Contrast'
    except TypeError:
        pass
    scene.view_settings.exposure = args.exposure
    os.makedirs(args.out, exist_ok=True)
    scene.render.filepath = os.path.join(args.out, f'palazzo-{args.render}.png')
    bpy.ops.render.render(write_still=True)
    print('render', scene.render.filepath)


# ===========================================================================
# Esportazione per il web: unione per materiale, semplificazione, Draco, WebP
# ===========================================================================

def decimate_heavy(limit=40000, asset_limit=9000):
    for o in list(bpy.data.objects):
        if o.type != 'MESH':
            continue
        lim = asset_limit if 'asset' in o else limit
        n = len(o.data.polygons)
        if n > lim:
            if o.data.users > 1:
                o.data = o.data.copy()
            m = o.modifiers.new('dec', 'DECIMATE')
            m.ratio = max(0.03, lim / n)
            lib.apply_modifiers(o)


def merge_collection(coll, keep_prefixes=()):
    groups = {}
    for o in list(coll.all_objects):
        if o.type != 'MESH' or any(o.name.startswith(k) for k in keep_prefixes):
            continue
        groups.setdefault('all', []).append(o)
    for k, objs in groups.items():
        if len(objs) > 1:
            # i figli importati da glTF vanno staccati dai genitori prima dell'unione
            lib.join(objs, f'{coll.name}')


def limit_textures():
    for img in bpy.data.images:
        if img.size[0] == 0 or 'opacity' in img.name.lower() or img.packed_file:
            continue
        big = 2048 if any(k in img.name for k in ('stone_cream', 'slab_cream')) else (512 if any(
            k in img.name for k in ('Chandelier', 'potted', 'street_lamp')) else 1024)
        if max(img.size) > big:
            img.scale(big, big * img.size[1] // img.size[0])


def bake_lightmap(obj, size, samples):
    """Luce calcolata con Cycles (diretta + indiretta, senza colore) in una seconda UV: la stessa
    illuminazione del render, applicata nel sito come lightMap (vale anche su telefono)."""
    import numpy as np
    me = obj.data
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
    px = denoise_pixels(img)
    rgb = px.reshape(size, size, 4)[::-1, :, :3]  # Blender: origine in basso
    return rgb


def denoise_pixels(img):
    """Denoise OIDN dell'immagine di bake tramite il compositor (scena vuota, device CPU)."""
    import numpy as np
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
    path = os.path.join(CACHE, '__denoise.exr')
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True, scene=sc.name)
    res = bpy.data.images.load(path, check_existing=False)
    px = np.empty(res.size[0] * res.size[1] * 4, np.float32)
    res.pixels.foreach_get(px)
    bpy.data.images.remove(res)
    bpy.data.scenes.remove(sc)
    return px


def cull_hidden(obj, backs=False):
    """Elimina facce mai visibili prima del bake (concentra la risoluzione sulle parti in vista)."""
    import bmesh as _bm
    bm = _bm.new()
    bm.from_mesh(obj.data)
    dead = []
    for f in bm.faces:
        c, n = f.calc_center_median(), f.normal
        if n.z < -0.9 and c.z < 0.05:
            dead.append(f)                       # appoggiate a terra
        elif n.y > 0.9 and abs(c.y) < 0.025:
            dead.append(f)                       # retro di elementi a filo facciata
        elif n.y > 0.9 and abs(c.y - P.WALL_T) < 0.02:
            dead.append(f)                       # faccia interna del muro di facciata
        elif backs and n.y > 0.5:
            dead.append(f)
    _bm.ops.delete(bm, geom=dead, context='FACES')
    bm.to_mesh(obj.data)
    bm.free()
    print('cull', obj.name, len(dead), 'facce rimosse')


def save_lightmap(rgb, path, scale):
    import numpy as np
    from PIL import Image, ImageFilter
    enc = np.clip(rgb / scale, 0, 1) ** (1 / 2.2)
    im = Image.fromarray((enc * 255 + 0.5).astype(np.uint8))
    im.save(path, quality=90, method=6)
    print('lightmap', path, 'valore max', float(rgb.max()), 'p99', float(np.percentile(rgb, 99)))


if not args.no_export:
    for o in list(bpy.data.objects):
        if o.name.startswith('PiantaAtrioB') or (o.parent and o.parent.name.startswith('PiantaAtrioB')):
            bpy.data.objects.remove(o, do_unlink=True)
    # retro e lato coperto dal vicino: fuori dalla lightmap (non visibili dalla strada)
    retro = lib.collection('Retro')
    for o in list(bpy.data.collections['RetroInfissi'].objects):
        for c in o.users_collection:
            c.objects.unlink(o)
        retro.objects.link(o)
    for nm in ('MuroRetro', 'MuroLatoDx'):
        o = bpy.data.objects[nm]
        for c in o.users_collection:
            c.objects.unlink(o)
        retro.objects.link(o)
    decimate_heavy()
    for name in ('Palazzo', 'Infissi', 'Strada'):
        merge_collection(COLL[name])
    merge_collection(COLL['Contesto'], keep_prefixes=('Albero',))
    merge_collection(COLL['Interni'], keep_prefixes=('Interno3',))
    merge_collection(lib.collection('Retro'))
    for o in list(bpy.data.objects):
        if o.type == 'EMPTY' and not o.children:
            bpy.data.objects.remove(o, do_unlink=True)
    # palazzo + infissi in un unico atlante di luce
    pal = lib.join([bpy.data.objects['Palazzo'], bpy.data.objects['Infissi']], 'LM_Palazzo')
    bpy.data.objects['Contesto'].name = 'LM_Contesto'
    bpy.data.objects['Strada'].name = 'LM_Strada'
    bpy.data.objects['Interni'].name = 'LM_Interni'
    cull_hidden(pal)
    cull_hidden(bpy.data.objects['LM_Contesto'], backs=True)
    cull_hidden(bpy.data.objects['LM_Strada'])
    LM_SCALE = 6.0
    lm_dir = os.path.join(ROOT, 'public', 'models')
    os.makedirs(lm_dir, exist_ok=True)
    if not args.no_bake:
        for oname, size, spp in (('LM_Palazzo', args.lm_size, args.lm_samples), ('LM_Contesto', args.lm_size // 2, args.lm_samples // 2),
                                 ('LM_Strada', args.lm_size // 2, args.lm_samples // 2), ('LM_Interni', args.lm_size // 2, args.lm_samples // 2)):
            rgb = bake_lightmap(bpy.data.objects[oname], size, spp)
            save_lightmap(rgb, os.path.join(lm_dir, f'{oname.lower()}.webp'), LM_SCALE)
    for o in list(bpy.data.objects):
        if o.type in ('LIGHT', 'CAMERA'):
            bpy.data.objects.remove(o, do_unlink=True)
    limit_textures()
    out = os.path.join(CACHE, 'palazzo_raw.glb')  # ottimizzato poi da scripts/optimize-glb.mjs
    os.makedirs(os.path.dirname(out), exist_ok=True)
    kw = dict(filepath=out, export_format='GLB', export_apply=True, export_yup=True, export_lights=False,
              export_cameras=False, export_image_format='AUTO')
    bpy.ops.export_scene.gltf(**kw)
    print('GLB', out, f'{os.path.getsize(out) / 1e6:.1f} MB',
          'mesh:', sum(1 for o in bpy.data.objects if o.type == 'MESH'),
          'facce:', sum(len(o.data.polygons) for o in bpy.data.objects if o.type == 'MESH'))
