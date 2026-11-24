"""Appartamento dimostrativo al piano 3, costruito dentro il palazzo (stesso file, stessa luce, stesse finestre).

Legge la pianta da palazzo_spec.py (stanze, tramezzi, porte, finestre, arredi) e produce:
- LM_Appartamento      parte bassa (pavimenti, muri fino a 2,40 m, porte, arredi)   -> lightmap
- LM_AppartamentoAlto  parte alta (muri sopra il taglio, soffitti, cornici, luci, tende) -> lightmap
- LM_PiantaMuri        muri perimetrali spessi fino a 2,40 m, visibili solo nella planimetria 3D
Le lightmap si calcolano due volte: luce normale (soffitto chiuso) e "planimetria" (sezione a 2,40 m).

Uso: <venv-blender>/bin/python pipeline/blender/build_appartamento.py [--render salone|planimetria|balcone]
"""
import argparse
import glob
import math
import os
import sys

import bpy  # noqa: I001
import bmesh
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
import palazzo_spec as P  # noqa: E402
from lib import box, lathe  # noqa: E402
from materials import pbr, kelvin  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CACHE = os.path.join(ROOT, 'pipeline', 'cache')
TEX = lambda a, f: os.path.join(CACHE, 'textures', a, f)  # noqa: E731
DER = lambda f: os.path.join(CACHE, 'derived', f)  # noqa: E731

ap = argparse.ArgumentParser()
ap.add_argument('--render', default=None)
ap.add_argument('--samples', type=int, default=64)
ap.add_argument('--res', type=float, default=0.5)
ap.add_argument('--no-export', action='store_true')
ap.add_argument('--no-bake', action='store_true')
ap.add_argument('--lm-size', type=int, default=2048)
ap.add_argument('--lm-samples', type=int, default=96)
args = ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:])

bpy.ops.wm.open_mainfile(filepath=os.path.join(CACHE, 'palazzo.blend'))
scene = bpy.context.scene

FZ = P.APT_FLOOR          # pavimento finito
CZ = P.APT_CEIL           # intradosso del solaio
CUT = FZ + 2.40           # quota del taglio per la planimetria
X0, X1, Y0, Y1 = P.APT_X0, P.APT_X1, P.APT_Y0, P.APT_Y1

LOW = lib.collection('Appartamento')
HIGH = lib.collection('AppartamentoAlto')
PIANTA = lib.collection('PiantaMuri')

M = {
    'parquet': pbr('Parquet', diff=DER('parquet_rovere_diff.jpg'),
                   nor=TEX('herringbone_parquet', 'herringbone_parquet_nor_gl_1k.jpg'),
                   rough=0.42, nor_strength=0.6),
    'marmo': pbr('MarmoBagni', diff=DER('marmo_chiaro_diff.jpg'), nor=TEX('marble_01', 'marble_01_nor_gl_2k.jpg'), rough=0.18, nor_strength=0.25),
    'intonaco': pbr('Intonaco', diff=DER('intonaco_interno_diff.jpg'), rough=0.9),
    'soffitto': pbr('Soffitto', color=(0.92, 0.9, 0.86), rough=0.92),
    'laccato': pbr('LaccatoBianco', color=(0.86, 0.85, 0.82), rough=0.32),
    'noce': pbr('PortaNoce', color=(0.24, 0.15, 0.09), rough=0.4),
    'rovere': pbr('Rovere', diff=DER('rovere_diff.jpg'), nor=TEX('oak_veneer_01', 'oak_veneer_01_nor_gl_1k.jpg'), rough=0.5, nor_strength=0.4),
    'marmo_top': pbr('MarmoPiani', diff=DER('marmo_camino_diff.jpg'), rough=0.12),
    'camino': pbr('MarmoCamino', diff=DER('marmo_camino_diff.jpg'), nor=TEX('marble_01', 'marble_01_nor_gl_2k.jpg'), rough=0.2, nor_strength=0.2),
    'velluto': pbr('Velluto', diff=DER('velluto_tortora_diff.jpg'), nor=TEX('velour_velvet', 'velour_velvet_nor_gl_1k.jpg'), rough=0.85),
    'lino': pbr('Lino', diff=DER('lino_diff.jpg'), nor=TEX('rough_linen', 'rough_linen_nor_gl_1k.jpg'), rough=0.95, nor_strength=0.6),
    'tappeto': pbr('Tappeto', diff=DER('tappeto_diff.jpg'), nor=TEX('rough_linen', 'rough_linen_nor_gl_1k.jpg'), rough=1.0, nor_strength=1.2),
    'ottone': pbr('OttoneInterni', color=(0.82, 0.62, 0.3), rough=0.25, metal=1.0),
    'acciaio': pbr('AcciaioSatinato', color=(0.75, 0.75, 0.76), rough=0.25, metal=1.0),
    'nero': pbr('NeroOpaco', color=(0.03, 0.03, 0.03), rough=0.45),
    'ceramica': pbr('Ceramica', color=(0.93, 0.93, 0.92), rough=0.08),
    'vetro': pbr('VetroDoccia', color=(1, 1, 1), rough=0.02, transmission=1.0, ior=1.5),
    'specchio': pbr('Specchio', color=(0.95, 0.95, 0.95), rough=0.02, metal=1.0),
    'tenda': pbr('TendaLino', diff=DER('lino_diff.jpg'), rough=0.95, alpha=0.82),
    'paralume': pbr('Paralume', color=(0.95, 0.9, 0.8), rough=0.9, emission=(1.0, 0.78, 0.5), emission_strength=3.0),
    'braci': pbr('Braci', color=(0.1, 0.05, 0.02), rough=0.9, emission=(1.0, 0.42, 0.12), emission_strength=6.0),
    'scala': pbr('PietraScala', diff=DER('marmo_chiaro_diff.jpg'), rough=0.5),
    'muro_pianta': pbr('MuroSezione', diff=DER('stone_cream_diff.jpg'), rough=0.9),
}
ROOM_FLOOR = {'parquet': M['parquet'], 'marmo': M['marmo']}


def two_part(name, x0, x1, y0, y1, z0, z1, mat, bev=0.0, uv=1.5):
    """Volume diviso al taglio della planimetria (parte bassa in LOW, alta in HIGH)."""
    if z0 < CUT:
        box(f'{name}_b', x0, x1, y0, y1, z0, min(z1, CUT), mat, LOW, bev=bev, uv_scale=uv)
    if z1 > CUT:
        box(f'{name}_a', x0, x1, y0, y1, max(z0, CUT), z1, mat, HIGH, bev=bev, uv_scale=uv)


# ============================================================================ pavimenti, soffitti
for name, x0, x1, y0, y1, fl in P.APT_ROOMS:
    box(f'Pavimento_{name}', x0, x1, y0, y1, FZ - 0.06, FZ, ROOM_FLOOR[fl], LOW, uv_scale=1.4)
# soglia della portafinestra del balcone
box('SogliaBalcone', -P.CENTRAL['c3_win']['w'] / 2, P.CENTRAL['c3_win']['w'] / 2, P.GLASS_Y, Y0, FZ - 0.25, FZ, M['marmo_top'], LOW)
box('Soffitto', X0, X1, Y0, Y1, CZ, CZ + 0.08, M['soffitto'], HIGH, uv_scale=3.0)

# ============================================================================ muri perimetrali (pelle interna) con aperture


def wall_with_openings(name, axis, fixed0, fixed1, span0, span1, openings, mat, reveal_to=None, side=1):
    """Muro lungo X (axis='x', fixed = y) o lungo Y (axis='y', fixed = x) con aperture [(a0, a1, z0, z1)].
    reveal_to: coordinata dei vetri verso cui rivestire gli sguinci (spallette) delle aperture."""
    ops = sorted(openings)
    cuts = [span0]
    for a0, a1, _, _ in ops:
        cuts += [a0, a1]
    cuts.append(span1)

    def piece(nm, s0, s1, z0, z1):
        if s1 - s0 < 1e-3 or z1 - z0 < 1e-3:
            return
        if axis == 'x':
            two_part(nm, s0, s1, fixed0, fixed1, z0, z1, mat)
        else:
            two_part(nm, fixed0, fixed1, s0, s1, z0, z1, mat)
    for i in range(0, len(cuts), 2):
        piece(f'{name}_p{i}', cuts[i], cuts[i + 1], FZ, CZ)
    for k, (a0, a1, z0, z1) in enumerate(ops):
        piece(f'{name}_sopra{k}', a0, a1, z1, CZ)
        piece(f'{name}_sotto{k}', a0, a1, FZ, z0)
        if reveal_to is not None:
            f_in = fixed0 if side > 0 else fixed1
            r0, r1 = sorted((reveal_to, f_in))
            t = 0.02
            if axis == 'x':
                two_part(f'{name}_sgSx{k}', a0, a0 + t, r0, r1, z0, z1, M['intonaco'])
                two_part(f'{name}_sgDx{k}', a1 - t, a1, r0, r1, z0, z1, M['intonaco'])
                two_part(f'{name}_sgSu{k}', a0, a1, r0, r1, z1 - t, z1, M['intonaco'])
                if z0 > FZ + 0.05:
                    box(f'{name}_davanzale{k}', a0 - 0.03, a1 + 0.03, r0, r1 + 0.04, z0 - 0.03, z0, M['marmo_top'], LOW)


facade_ops = [(w['x'] - w['w'] / 2 + 0.02, w['x'] + w['w'] / 2 - 0.02, max(FZ, w['z0']), w['z1'] - 0.02)
              for w in P.APT_WINDOWS if w['wall'] == 'facciata']
back_ops = [(w['x'] - w['w'] / 2 + 0.02, w['x'] + w['w'] / 2 - 0.02, w['z0'], w['z1'] - 0.02)
            for w in P.APT_WINDOWS if w['wall'] == 'retro']
wall_with_openings('PelleFacciata', 'x', Y0, Y0 + 0.02, X0, X1, facade_ops, M['intonaco'], reveal_to=P.GLASS_Y + 0.05, side=1)
wall_with_openings('PelleRetro', 'x', Y1 - 0.02, Y1, X0, X1, back_ops, M['intonaco'], reveal_to=P.DEPTH - 0.3, side=-1)
two_part('PelleOvest', X0, X0 + 0.02, Y0, Y1, FZ, CZ, M['intonaco'])
two_part('PelleEst', X1 - 0.02, X1, Y0, Y1, FZ, CZ, M['intonaco'])

# ============================================================================ tramezzi e porte
DOOR_H = P.APT_DOOR_H


def door_leaf(name, hinge, width, thickness, angle, along_x, mat, glazed=False, fixed_y=None):
    """Anta a pannelli (o vetrata) con cerniera in 'hinge', ruotata di 'angle' gradi."""
    leaf_parts = [box(f'{name}_anta', 0, width, -thickness / 2, thickness / 2, FZ + 0.01, FZ + DOOR_H - 0.01, mat, LOW, bev=0.004)]
    if glazed:
        for k in range(4):
            z0 = FZ + 0.45 + k * 0.56
            leaf_parts.append(box(f'{name}_vetro{k}', 0.1, width - 0.1, -thickness / 2 - 0.002, thickness / 2 + 0.002, z0, z0 + 0.46,
                                  M['vetro'], LOW))
    else:
        for (z0, z1) in ((FZ + 0.18, FZ + 1.05), (FZ + 1.25, FZ + DOOR_H - 0.18)):
            for s in (-1, 1):
                leaf_parts.append(box(f'{name}_pan', 0.12, width - 0.12, s * thickness / 2 - 0.004, s * thickness / 2 + 0.004, z0, z1,
                                      mat, LOW, bev=0.006))
    for s in (-1, 1):
        h = lathe(f'{name}_maniglia', [(0.012, 0), (0.012, 0.06), (0.018, 0.075), (0.0, 0.08)], M['ottone'], LOW, segs=10)
        h.rotation_euler = (math.radians(90 * s), 0, 0)
        h.location = (width - 0.08, 0, FZ + 1.02)
        leaf_parts.append(h)
    o = lib.join(leaf_parts, name)
    a = math.radians(angle) + (0 if along_x else math.pi / 2)
    o.rotation_euler = (0, 0, a)
    o.location = hinge
    return o


DOOR_SWING = {(-0.90, 0.90): 'doppia', (-0.50, 0.50): 'blindata'}
for wi, wl in enumerate(P.APT_WALLS):
    x0, x1, y0, y1 = wl['r']
    along_x = (x1 - x0) > (y1 - y0)
    ops = [(a0, a1, FZ, FZ + DOOR_H) for a0, a1 in wl['doors']]
    if along_x:
        wall_with_openings(f'Tramezzo{wi}', 'x', y0, y1, x0, x1, ops, M['intonaco'])
    else:
        wall_with_openings(f'Tramezzo{wi}', 'y', x0, x1, y0, y1, ops, M['intonaco'])
    for di, (a0, a1) in enumerate(wl['doors']):
        wdt = a1 - a0
        kind = DOOR_SWING.get((a0, a1), 'singola')
        mid = (y0 + y1) / 2 if along_x else (x0 + x1) / 2
        # mostre (cornici) su entrambi i lati
        for s in (-1, 1):
            f0 = (y0 if s < 0 else y1) + s * 0.012
            if along_x:
                for (p0, p1) in ((a0 - 0.08, a0), (a1, a1 + 0.08)):
                    box(f'Mostra{wi}{di}', p0, p1, min(f0, f0 + s * 0.02), max(f0, f0 + s * 0.02), FZ, FZ + DOOR_H + 0.08, M['laccato'], LOW)
                two_part(f'MostraSu{wi}{di}{s}', a0 - 0.08, a1 + 0.08, min(f0, f0 + s * 0.02), max(f0, f0 + s * 0.02), FZ + DOOR_H,
                         FZ + DOOR_H + 0.08, M['laccato'])
            else:
                for (p0, p1) in ((a0 - 0.08, a0), (a1, a1 + 0.08)):
                    box(f'Mostra{wi}{di}', min(f0, f0 + s * 0.02), max(f0, f0 + s * 0.02), p0, p1, FZ, FZ + DOOR_H + 0.08, M['laccato'], LOW)
                two_part(f'MostraSu{wi}{di}{s}', min(f0, f0 + s * 0.02), max(f0, f0 + s * 0.02), a0 - 0.08, a1 + 0.08, FZ + DOOR_H,
                         FZ + DOOR_H + 0.08, M['laccato'])
        if kind == 'doppia':
            # porta vetrata a due ante, spalancata verso il salone (enfilade ingresso -> balcone)
            door_leaf('PortaSaloneSx', (a0, y0, 0), wdt / 2, 0.045, -95, True, M['laccato'], glazed=True)  # ruotata sul lato opposto
            door_leaf('PortaSaloneDx', (a1, y0, 0), wdt / 2, 0.045, -85, True, M['laccato'], glazed=True)
        elif kind == 'blindata':
            o = door_leaf('PortaIngresso', (a0, mid, 0), wdt, 0.07, 0, True, M['noce'])
        else:
            hinge = (a0, mid, 0) if along_x else (mid, a0, 0)
            door_leaf(f'Porta{wi}{di}', hinge, wdt, 0.045, -75 if along_x else 75, along_x, M['laccato'])

# ============================================================================ cornici dei soffitti e boiserie


def ceiling_cornice(name, x0, x1, y0, y1):
    """Cornice a gola sul perimetro della stanza (percorso orario visto dall'alto: la sporgenza va verso l'interno)."""
    prof = [(0.0, -0.20), (0.02, -0.19), (0.03, -0.16), (0.06, -0.14), (0.09, -0.10), (0.12, -0.07), (0.15, -0.05),
            (0.16, -0.03), (0.18, -0.02), (0.18, 0.0), (0.0, 0.0)]
    pts = [Vector(p) for p in ((x0, y0), (x0, y1), (x1, y1), (x1, y0))]
    n = len(pts)
    segs = [(pts[(i + 1) % n] - pts[i]).normalized() for i in range(n)]
    normals = [Vector((s.y, -s.x)) for s in segs]
    v, f = [], []
    np_ = len(prof)
    for i in range(n):
        n1, n2 = normals[i - 1], normals[i]
        m = (n1 + n2) / (1 + n1.dot(n2))
        for d, h in prof:
            q = pts[i] + m * d
            v.append((q.x, q.y, CZ + h))
    for i in range(n):
        i2 = (i + 1) % n
        for j in range(np_):
            j2 = (j + 1) % np_
            f.append((i * np_ + j, i2 * np_ + j, i2 * np_ + j2, i * np_ + j2))
    lib.mesh_obj(name, v, f, M['soffitto'], HIGH, smooth=True, sharp_deg=35, uv_scale=None)


for name, x0, x1, y0, y1, _ in P.APT_ROOMS:
    if not name.startswith('Disimpegno'):
        ceiling_cornice(f'Cornice_{name}', x0, x1, y0, y1)
rosone = lathe('Rosone', [(0.0, 0.0), (0.55, 0.0), (0.5, -0.03), (0.38, -0.04), (0.3, -0.07), (0.12, -0.08), (0.0, -0.09)],
               M['soffitto'], HIGH, segs=48)
rosone.location = (-3.9, 2.9, CZ)


def boiserie_wall(name, axis, fixed, s0, s1, inward, panels, z0=0.32, z1=2.25):
    """Riquadri a modanatura su una parete parallela a Y (x = fixed), tra y = s0 e y = s1.
    inward = +1 se la stanza è verso +X, -1 se verso -X."""
    step = (s1 - s0) / panels
    prof = [(0, 0), (0, 0.012), (0.012, 0.018), (0.03, 0.018), (0.035, 0.0)]
    for k in range(panels):
        a, b = s0 + k * step + 0.12, s0 + (k + 1) * step - 0.12
        if inward > 0:   # rotazione +90: x locale -> y, sporgenza (-y locale) -> +x
            o = lib.frame_rect(f'{name}{k}', a, b, FZ + z0, FZ + z1, prof, M['intonaco'], LOW, y0=0.0)
            o.rotation_euler = (0, 0, math.radians(90))
        else:            # rotazione -90: x locale -> -y, sporgenza -> -x
            o = lib.frame_rect(f'{name}{k}', -b, -a, FZ + z0, FZ + z1, prof, M['intonaco'], LOW, y0=0.0)
            o.rotation_euler = (0, 0, math.radians(-90))
        o.location = (fixed, 0, 0)


boiserie_wall('BoiserieOvest', 'y', X0 + 0.02, Y0 + 0.3, 1.85, 1, 1)
boiserie_wall('BoiserieOvest2', 'y', X0 + 0.02, 3.95, 7.3, 1, 2)
boiserie_wall('BoiserieEst', 'y', 1.85 - 0.0, 0.9, 6.9, -1, 3)
box('Zoccolino_Salone', X0, 1.85, Y0, Y0 + 0.015, FZ, FZ + 0.1, M['intonaco'], LOW)

# ============================================================================ arredi


def import_model(asset, name, loc, rot_deg, scale=1.0, coll=LOW, max_faces=9000):
    files = glob.glob(os.path.join(CACHE, 'models', asset, '*.gltf'))
    if not files:
        print('modello mancante', asset)
        return None
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=files[0])
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        for c in o.users_collection:
            c.objects.unlink(o)
        coll.objects.link(o)
        if o.type == 'MESH' and len(o.data.polygons) > max_faces:
            mdec = o.modifiers.new('dec', 'DECIMATE')
            mdec.ratio = max(0.05, max_faces / len(o.data.polygons))
            lib.apply_modifiers(o)
    roots = [o for o in new if o.parent is None]
    for r in roots:
        r.name = name
        r.location = loc
        r.scale = (r.scale[0] * scale, r.scale[1] * scale, r.scale[2] * scale)
        r.rotation_euler.z += math.radians(rot_deg)
    return roots


def local_box(name, cx, cy, rot, x0, x1, y0, y1, z0, z1, mat, coll=LOW, bev=0.0):
    o = box(name, x0, x1, y0, y1, z0, z1, mat, coll, bev=bev, uv_scale=1.0)
    o.location = (cx, cy, FZ)
    o.rotation_euler = (0, 0, math.radians(rot))
    return o


def fireplace(cx, cy, rot):
    parts = [
        box('CaminoBase', -1.0, 1.0, -0.3, 0.26, 0.0, 0.06, M['camino'], LOW, bev=0.01),
        box('CaminoSx', -0.9, -0.62, -0.22, 0.24, 0.06, 1.12, M['camino'], LOW, bev=0.01),
        box('CaminoDx', 0.62, 0.9, -0.22, 0.24, 0.06, 1.12, M['camino'], LOW, bev=0.01),
        box('CaminoArchitrave', -0.9, 0.9, -0.22, 0.24, 0.9, 1.14, M['camino'], LOW, bev=0.01),
        box('CaminoMensola', -1.02, 1.02, -0.3, 0.24, 1.14, 1.2, M['camino'], LOW, bev=0.012),
        box('CaminoFocolare', -0.62, 0.62, 0.0, 0.24, 0.06, 0.9, M['nero'], LOW),
        box('CaminoBraci', -0.4, 0.4, 0.02, 0.18, 0.06, 0.12, M['braci'], LOW, bev=0.02),
    ]
    o = lib.join(parts, 'Camino')
    o.location = (cx, cy, FZ)
    o.rotation_euler = (0, 0, math.radians(rot))


def bed(name, cx, cy, w, d, rot):
    hw, hd = w / 2, d / 2
    parts = [
        box(f'{name}Telaio', -hw, hw, -hd, hd - 0.06, 0.08, 0.36, M['velluto'], LOW, bev=0.03, bev_seg=2),
        box(f'{name}Materasso', -hw + 0.04, hw - 0.04, -hd + 0.04, hd - 0.1, 0.36, 0.58, M['lino'], LOW, bev=0.05, bev_seg=3),
        box(f'{name}Piumone', -hw - 0.02, hw + 0.02, -hd - 0.02, hd - 0.65, 0.5, 0.64, M['lino'], LOW, bev=0.06, bev_seg=3),
        box(f'{name}Testiera', -hw - 0.08, hw + 0.08, hd - 0.1, hd, 0.08, 1.25, M['velluto'], LOW, bev=0.04, bev_seg=3),
        box(f'{name}Plaid', -hw - 0.03, hw + 0.03, -hd + 0.15, -hd + 0.6, 0.62, 0.67, M['velluto'], LOW, bev=0.02, bev_seg=2),
    ]
    for s in (-1, 1):
        parts.append(box(f'{name}Cuscino', s * hw * 0.5 - 0.34, s * hw * 0.5 + 0.34, hd - 0.62, hd - 0.18, 0.56, 0.78, M['lino'], LOW,
                         bev=0.07, bev_seg=3))
    o = lib.join(parts, name)
    o.location = (cx, cy, FZ)
    o.rotation_euler = (0, 0, math.radians(rot))


def cabinet(name, cx, cy, w, d, h, rot, front, top=None, doors=2, plinth=0.08):
    hw, hd = w / 2, d / 2
    parts = [box(f'{name}Corpo', -hw, hw, -hd + 0.02, hd, plinth, h, front, LOW, bev=0.004),
             box(f'{name}Zoccolo', -hw + 0.02, hw - 0.02, -hd + 0.06, hd, 0.0, plinth, M['nero'], LOW)]
    for k in range(1, doors):
        x = -hw + w * k / doors
        parts.append(box(f'{name}Fuga', x - 0.003, x + 0.003, -hd + 0.015, -hd + 0.025, plinth + 0.01, h - 0.01, M['nero'], LOW))
    if top:
        parts.append(box(f'{name}Top', -hw - 0.01, hw + 0.01, -hd - 0.01, hd, h, h + 0.04, top, LOW, bev=0.004))
    o = lib.join(parts, name)
    o.location = (cx, cy, FZ)
    o.rotation_euler = (0, 0, math.radians(rot))
    return o


def table_lamp(name, x, y, z):
    base = lathe(f'{name}Base', [(0.07, 0), (0.08, 0.02), (0.05, 0.05), (0.03, 0.3), (0.01, 0.36)], M['ottone'], LOW, segs=16)
    shade = lathe(f'{name}Paralume', [(0.17, 0.3), (0.12, 0.52), (0.0, 0.52)], M['paralume'], LOW, segs=24)
    o = lib.join([base, shade], name)
    o.location = (x, y, z)
    return o


def floor_lamp(name, x, y):
    stem = lathe(f'{name}Stelo', [(0.16, 0), (0.16, 0.03), (0.015, 0.05), (0.015, 1.45), (0.0, 1.46)], M['ottone'], LOW, segs=16)
    shade = lathe(f'{name}Paralume', [(0.24, 1.35), (0.2, 1.65), (0.0, 1.65)], M['paralume'], LOW, segs=24)
    o = lib.join([stem, shade], name)
    o.location = (x, y, FZ)
    return o


def curtains(name, x0, x1, y):
    """Tende in lino a tutta altezza, raccolte ai lati della finestra."""
    w = x1 - x0
    for s, (a, b) in (('sx', (x0 - 0.35, x0 + w * 0.12)), ('dx', (x1 - w * 0.12, x1 + 0.35))):
        nx, nz = 22, 2
        verts, faces = [], []
        for j in range(nz + 1):
            z = FZ + 0.01 + (CZ - 0.12 - FZ) * j / nz
            for i in range(nx + 1):
                t = i / nx
                verts.append((a + (b - a) * t, y + 0.06 * math.sin(t * math.pi * 9), z))
        for j in range(nz):
            for i in range(nx):
                k = j * (nx + 1) + i
                faces.append((k, k + 1, k + nx + 2, k + nx + 1))
        n = len(verts)
        verts += [(vx, vy + 0.01, vz) for vx, vy, vz in verts]
        faces += [tuple(i + n for i in reversed(f)) for f in faces]
        lib.mesh_obj(f'{name}_{s}', verts, faces, M['tenda'], HIGH, smooth=True, uv_scale=None)
    box(f'{name}_bastone', x0 - 0.45, x1 + 0.45, y - 0.02, y + 0.02, CZ - 0.14, CZ - 0.1, M['ottone'], HIGH)


for t, x, y, w, d, rot in P.APT_FURNITURE:
    if t == 'camino':
        fireplace(x, y, rot)
    elif t == 'divano':
        import_model('sofa_03', 'Divano', (x, y, FZ), rot)
        import_model('throw_pillows_01', 'CuscinidDivano', (x, y, FZ + 0.42), rot, 0.95)
    elif t == 'poltrona':
        import_model('modern_arm_chair_01', 'Poltrona', (x, y, FZ), rot)
    elif t == 'poltrona_lettura':
        import_model('mid_century_lounge_chair', 'PoltronaLettura', (x, y, FZ), rot)
        floor_lamp('LampadaTerra', x + 0.55, y + 0.45)
    elif t == 'tavolino':
        import_model('modern_coffee_table_01', 'Tavolino', (x, y, FZ), rot + 90)
        import_model('ceramic_vase_02', 'VasoTavolino', (x + 0.1, y + 0.3, FZ + 0.39), 0)
    elif t == 'tappeto':
        o = local_box('Tappeto', x, y, rot, -w / 2, w / 2, -d / 2, d / 2, 0.0, 0.012, M['tappeto'], bev=0.005)
    elif t == 'tavolo':
        import_model('dining_table', 'TavoloPranzo', (x, y, FZ), rot)
        for k, dx in enumerate((-0.7, 0.0, 0.7)):
            for s in (-1, 1):
                a = math.radians(rot)
                px_ = x + dx * math.cos(a) - s * 0.62 * math.sin(a)
                py_ = y + dx * math.sin(a) + s * 0.62 * math.cos(a)
                import_model('dining_chair_02', f'Sedia{k}{s}', (px_, py_, FZ), rot + (0 if s > 0 else 180), max_faces=4000)
    elif t == 'madia':
        import_model('modern_wooden_cabinet', 'Madia', (x, y, FZ), rot, 0.82)
        import_model('brass_vase_01', 'VasoMadia', (x - 0.0, y + 0.5, FZ + 0.56), 0)
        import_model('hanging_picture_frame_02', 'Quadro', (1.85 - 0.03, y, FZ + 1.75), -90, 2.2)
    elif t == 'pianta':
        import_model('potted_plant_01', 'Pianta', (x, y, FZ), rot * 37 % 360, 1.15, max_faces=12000)
    elif t == 'letto':
        bed(f'Letto{x:.0f}', x, y, w, d, rot)
    elif t == 'comodino':
        cabinet(f'Comodino{x:.1f}{y:.1f}', x, y, w, d, 0.52, rot, M['rovere'], doors=1, plinth=0.12)
        table_lamp(f'LampadaComodino{x:.1f}{y:.1f}', x, y, FZ + 0.52)
    elif t == 'armadio':
        cabinet(f'Armadio{x:.1f}', x, y, w, d, 2.6, rot, M['laccato'], doors=max(2, round(w / 0.6)), plinth=0.06)
    elif t == 'panca':
        local_box('Panca', x, y, rot, -w / 2, w / 2, -d / 2, d / 2, 0.0, 0.46, M['velluto'], bev=0.03)
    elif t == 'vasca':
        tub = lathe('Vasca', [(0.0, 0.0), (0.8, 0.0), (0.98, 0.25), (1.0, 0.58), (0.92, 0.6), (0.82, 0.25), (0.0, 0.18)],
                    M['ceramica'], LOW, segs=48)
        tub.scale = (w / 2, d / 2, 1)
        tub.location = (x, y, FZ)
    elif t == 'lavabo_doppio':
        o = cabinet('MobileLavabo', x, y, w, d, 0.55, rot, M['rovere'], top=M['marmo_top'], doors=2, plinth=0.35)
        for k in (-0.4, 0.4):
            a = math.radians(rot)
            bx_, by_ = x + k * math.cos(a), y + k * math.sin(a)
            bowl = lathe('Bacinella', [(0.0, 0.0), (0.12, 0.0), (0.2, 0.1), (0.21, 0.15), (0.18, 0.15), (0.0, 0.05)], M['ceramica'], LOW, segs=32)
            bowl.location = (bx_, by_, FZ + 0.59)
        mir = local_box('SpecchioBagno', x, y, rot, -w / 2, w / 2, d / 2 - 0.02, d / 2, 0.95, 1.95, M['specchio'])
    elif t == 'doccia':
        local_box('PiattoDoccia', x, y, rot, -w / 2, w / 2, -d / 2, d / 2, 0.0, 0.03, M['marmo_top'])
        local_box('VetroDoccia', x, y, rot, -w / 2, w / 2 - 0.3, -d / 2 - 0.005, -d / 2 + 0.005, 0.03, 2.1, M['vetro'])
        head = lathe('Soffione', [(0.15, 0), (0.15, 0.01), (0.0, 0.015)], M['acciaio'], LOW, segs=24)
        head.location = (x, y, FZ + 2.25)
    elif t in ('wc', 'bidet'):
        bowl = lathe(t.upper(), [(0.0, 0.0), (0.17, 0.0), (0.21, 0.2), (0.2, 0.4), (0.16, 0.42), (0.0, 0.3)], M['ceramica'], LOW, segs=24)
        bowl.scale = (1.0, 1.4, 1.0)
        bowl.location = (x, y, FZ + 0.0)
        bowl.rotation_euler = (0, 0, math.radians(rot))
    elif t == 'lavabo':
        o = cabinet('MobileLavaboOspiti', x, y, w, d, 0.5, rot, M['rovere'], top=M['marmo_top'], doors=1, plinth=0.35)
        bowl = lathe('BacinellaOspiti', [(0.0, 0.0), (0.12, 0.0), (0.2, 0.1), (0.21, 0.15), (0.18, 0.15), (0.0, 0.05)], M['ceramica'], LOW, segs=32)
        bowl.location = (x, y, FZ + 0.54)
        local_box('SpecchioOspiti', x, y, rot, -0.35, 0.35, d / 2 - 0.02, d / 2, 1.0, 1.9, M['specchio'])
    elif t == 'cucina_base':
        cabinet(f'CucinaBase{x:.1f}', x, y, w, d, 0.9, rot, M['rovere'], top=M['marmo_top'], doors=max(2, round(w / 0.6)), plinth=0.1)
    elif t == 'cucina_colonne':
        o = cabinet('Colonne', x, y, w, d, 2.45, rot, M['laccato'], doors=max(2, round(w / 0.6)), plinth=0.1)
        # forni incassati
        a = math.radians(rot)
        for k, zc in ((0.0, 0.95), (0.0, 1.55)):
            local_box('Forno', x, y, rot, -0.3, 0.3, -d / 2 - 0.01, -d / 2 + 0.005, zc, zc + 0.5, M['nero'])
    elif t == 'isola':
        cabinet('Isola', x, y, w, d, 0.92, rot, M['rovere'], top=M['marmo_top'], doors=4, plinth=0.1)
        for k in (-0.55, 0.55):
            a = math.radians(rot)
            import_model('modern_ceiling_lamp_01', 'Sospensione', (x + k * math.cos(a), y + k * math.sin(a), CZ - 0.95), 0, coll=HIGH)
    elif t == 'sgabello':
        import_model('bar_chair_round_01', 'Sgabello', (x, y, FZ), rot, max_faces=4000)
    elif t == 'consolle':
        o = cabinet('Consolle', x, y, w, d, 0.82, rot, M['rovere'], top=M['marmo_top'], doors=2, plinth=0.25)
        import_model('ornate_mirror_01', 'Specchiera', (x - 0.17, y, FZ + 1.65), rot, 1.6)
        import_model('ceramic_vase_02', 'VasoConsolle', (x, y - 0.35, FZ + 0.86), 0)
    elif t == 'busto':
        col = lathe('Piedistallo', [(0.2, 0), (0.2, 0.06), (0.15, 0.1), (0.15, 1.0), (0.2, 1.04), (0.2, 1.1)], M['camino'], LOW, segs=24)
        col.location = (x, y, FZ)
        import_model('marble_bust_01', 'Busto', (x, y, FZ + 1.1), -90, 1.3)
    elif t == 'tavolino_balcone':
        import_model('outdoor_table_chair_set_01', 'SetBalcone', (x - 0.2, y, P.CENTRAL['c3_balcony']['floor']), 90, 0.9)
    elif t == 'vaso_balcone':
        import_model('potted_plant_02', 'PiantaBalcone', (x, y, P.CENTRAL['c3_balcony']['floor']), 30, 0.9, max_faces=12000)

# lampadari: sospensioni contemporanee sopra salotto e pranzo
for nm, (x, y) in (('LampadarioSalotto', (-3.9, 2.9)), ('LampadarioPranzo', (-3.6, 6.15))):
    import_model('modern_ceiling_lamp_01', nm, (x, y, CZ - 0.95), 0, 1.15, coll=HIGH)

# tende sulle finestre di facciata e del retro
for k, wdw in enumerate(P.APT_WINDOWS):
    if wdw['stanza'].startswith('Vano'):
        continue
    x0, x1 = wdw['x'] - wdw['w'] / 2, wdw['x'] + wdw['w'] / 2
    yy = Y0 + 0.12 if wdw['wall'] == 'facciata' else Y1 - 0.14
    curtains(f'Tenda{k}', x0, x1, yy)

# vano scala (parti comuni): rampe in pietra e ascensore, visibili nella planimetria
_, cx0, cx1, cy0, cy1 = P.APT_CORE
box('ScalaPavimento', cx0, cx1, cy0, cy1, FZ - 0.06, FZ, M['scala'], LOW, uv_scale=1.0)
for k in range(9):
    box(f'Gradino{k}', cx0 + 0.15, cx0 + 1.35, cy0 + 1.0 + k * 0.3, cy0 + 1.3 + k * 0.3, FZ, FZ + 0.17 * (k + 1), M['scala'], LOW)
box('Ascensore', cx1 - 1.55, cx1 - 0.1, cy1 - 1.7, cy1 - 0.1, FZ, CUT, M['acciaio'], LOW)

# ============================================================================ muri spessi per la planimetria (solo sezione)
HW = P.HALF_W


def pianta_wall(name, x0, x1, y0, y1, ops, axis):
    ops = sorted(ops)
    span0, span1 = (x0, x1) if axis == 'x' else (y0, y1)
    cuts = [span0] + [c for a0, a1, _, _ in ops for c in (a0, a1)] + [span1]
    for i in range(0, len(cuts), 2):
        a, b = cuts[i], cuts[i + 1]
        if b - a > 1e-3:
            if axis == 'x':
                box(f'{name}{i}', a, b, y0, y1, FZ - 0.35, CUT, M['muro_pianta'], PIANTA, uv_scale=2.0)
            else:
                box(f'{name}{i}', x0, x1, a, b, FZ - 0.35, CUT, M['muro_pianta'], PIANTA, uv_scale=2.0)
    for k, (a0, a1, z0, z1) in enumerate(ops):
        if z0 > FZ:
            if axis == 'x':
                box(f'{name}Davanz{k}', a0, a1, y0, y1, FZ - 0.35, z0, M['muro_pianta'], PIANTA, uv_scale=2.0)


pianta_wall('PiantaFacciata', -HW, HW, 0.0, Y0 - 0.02, facade_ops, 'x')
pianta_wall('PiantaRetro', -HW, HW, Y1 + 0.02, P.DEPTH, back_ops, 'x')
pianta_wall('PiantaOvest', -HW, X0, Y0 - 0.02, Y1 + 0.02, [], 'y')
pianta_wall('PiantaEst', X1, HW, Y0 - 0.02, Y1 + 0.02, [], 'y')
box('PiantaSolaio', -HW, HW, 0.0, P.DEPTH, FZ - 0.4, FZ - 0.06, M['muro_pianta'], PIANTA, uv_scale=2.0)

# ============================================================================ luci interne (ora d'oro: lampade accese)
LCOL = bpy.data.collections.get('Luci') or lib.collection('Luci')


def add_light(name, kind, loc, energy, temp, size=0.1, direction=None, size_y=None):
    ld = bpy.data.lights.new(name, kind)
    ld.energy = energy
    ld.color = kelvin(temp)
    if kind == 'AREA':
        ld.shape = 'RECTANGLE'
        ld.size, ld.size_y = size, size_y or size
    else:
        ld.shadow_soft_size = size
    o = bpy.data.objects.new(name, ld)
    o.visible_camera = False
    o.location = loc
    if direction is not None:
        o.rotation_euler = Vector(direction).to_track_quat('-Z', 'Y').to_euler()
    LCOL.objects.link(o)
    return o


for x, y in ((-3.9, 2.9), (-3.6, 6.15)):
    add_light('LuceLampadario', 'POINT', (x, y, CZ - 0.9), 60, 2700, size=0.12)
for x, y in ((-4.3, 12.4), (-3.2, 12.4)):
    add_light('LuceIsola', 'POINT', (x, y, CZ - 0.9), 35, 2700, size=0.1)
add_light('LuceLettura', 'POINT', (1.8, 6.0, FZ + 1.5), 25, 2600, size=0.1)
for t, x, y, w, d, rot in P.APT_FURNITURE:
    if t == 'comodino':
        add_light('LuceComodino', 'POINT', (x, y, FZ + 0.75), 12, 2600, size=0.08)
add_light('LuceCamino', 'AREA', (X0 + 0.3, 2.9, FZ + 0.2), 40, 1900, size=0.7, direction=(1, 0, 0.3), size_y=0.2)
# riempimento morbido (luce diffusa delle stanze al crepuscolo)
for name, x0, x1, y0, y1, _ in P.APT_ROOMS:
    area = (x1 - x0) * (y1 - y0)
    add_light(f'Ambiente_{name}', 'AREA', ((x0 + x1) / 2, (y0 + y1) / 2, CZ - 0.05), 9 * area, 3000, size=(x1 - x0) * 0.8,
              size_y=(y1 - y0) * 0.8, direction=(0, 0, -1))

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(CACHE, 'appartamento.blend'))
print('appartamento: oggetti', sum(1 for o in LOW.all_objects) + sum(1 for o in HIGH.all_objects),
      'facce', sum(len(o.data.polygons) for c in (LOW, HIGH) for o in c.all_objects if o.type == 'MESH'))

# ============================================================================ render di controllo


def camera(name, loc, look, lens=24):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.clip_start = 0.05
    o = bpy.data.objects.new(name, cd)
    o.location = loc
    o.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    scene.collection.objects.link(o)
    return o


if args.render:
    views = {
        'salone': ((0.9, 7.2, FZ + 1.55), (-4.6, 1.6, FZ + 1.0), 20),
        'ingresso': ((0.1, 10.9, FZ + 1.6), (0.0, -2.0, FZ + 1.2), 22),
        'cucina': ((-1.95, 10.4, FZ + 1.6), (-4.6, 14.6, FZ + 0.9), 20),
        'camera': ((2.2, 10.0, FZ + 1.6), (5.2, 13.6, FZ + 0.8), 20),
        'planimetria': ((6.0, -9.0, FZ + 22.0), (0.0, 7.5, FZ), 30),
        'balcone': ((0.6, -0.4, FZ + 1.5), (-260.0, -470.0, 10.0), 26),
    }
    loc, look, lens = views[args.render]
    cam = camera('CameraInterni', loc, look, lens)
    scene.camera = cam
    if args.render == 'planimetria':
        for o in HIGH.all_objects:
            o.hide_render = True
        # sezione: palazzo nascosto sopra il taglio (si vedono solo l'appartamento e i muri spessi)
        for c in ('Palazzo', 'Infissi', 'Interni', 'Contesto', 'Retro', 'RetroInfissi'):
            if c in bpy.data.collections:
                for o in bpy.data.collections[c].all_objects:
                    o.hide_render = True
    else:
        for o in PIANTA.all_objects:
            o.hide_render = True
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = args.samples
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 6
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    scene.render.resolution_percentage = int(args.res * 100)
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.exposure = 0.6
    scene.render.filepath = os.path.join(CACHE, 'renders', f'appartamento-{args.render}.png')
    bpy.ops.render.render(write_still=True)
    print('render', scene.render.filepath)
