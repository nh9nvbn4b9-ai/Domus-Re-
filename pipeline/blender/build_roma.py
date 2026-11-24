"""Roma attorno al palazzo: Colosseo, Arco di Costantino, Colle Oppio, Palatino, Circo Massimo,
via dei Fori Imperiali, isolati a corte con intonaci romani e tetti in coppi, cupole e campanili,
pini domestici e, all'orizzonte, i Colli Albani (Castelli Romani).

Stesso sistema di coordinate del palazzo (origine al centro della facciata, strada verso -Y).
Il Colosseo ha la luce calcolata con Cycles (lightmap); la città usa il sole in tempo reale nel sito.

Uso: <venv-blender>/bin/python pipeline/blender/build_roma.py [--render aerea] [--no-export] [--no-bake]
"""
import argparse
import json
import math
import os
import random
import sys

import bpy  # noqa: I001 (bpy prima di bmesh)
import bmesh
from mathutils import Vector, Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
import colosseo  # noqa: E402
from materials import pbr, kelvin  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CACHE = os.path.join(ROOT, 'pipeline', 'cache')
TEX = lambda a, f: os.path.join(CACHE, 'textures', a, f)  # noqa: E731
DER = lambda f: os.path.join(CACHE, 'derived', f)  # noqa: E731

ap = argparse.ArgumentParser()
ap.add_argument('--render', default=None)
ap.add_argument('--samples', type=int, default=48)
ap.add_argument('--res', type=float, default=0.5)
ap.add_argument('--no-export', action='store_true')
ap.add_argument('--no-bake', action='store_true')
ap.add_argument('--lm-size', type=int, default=2048)
ap.add_argument('--lm-samples', type=int, default=48)
ap.add_argument('--skip-colosseo', action='store_true', help='non riesporta il Colosseo (lightmap invariata)')
args = ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:])

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
rnd = random.Random(1957)

# ---------------------------------------------------------------------------- materiali
M = {
    'travertino': pbr('Travertino', diff=DER('travertino_diff.jpg'), nor=TEX('worn_rock_natural_01', 'worn_rock_natural_01_nor_gl_2k.jpg'),
                      rough=0.85, nor_strength=1.2),
    'laterizio': pbr('Laterizio', diff=DER('laterizio_diff.jpg'), nor=TEX('medieval_red_brick', 'medieval_red_brick_nor_gl_1k.jpg'),
                     rough=0.9, nor_strength=0.8),
    'legno': pbr('LegnoArena', color=(0.33, 0.24, 0.16), rough=0.8),
    'terra': pbr('TerraIpogei', diff=DER('piazza_diff.jpg'), rough=0.95),
    'marmo': pbr('MarmoArco', diff=DER('travertino_diff.jpg'), rough=0.7, color=(0.9, 0.88, 0.84)),
    'piazza': pbr('Piazza', diff=DER('piazza_diff.jpg'), nor=TEX('park_dirt', 'park_dirt_nor_gl_1k.jpg'), rough=0.9),
    'asfalto': pbr('Asfalto', diff=DER('asfalto_diff.jpg'), nor=TEX('aerial_asphalt_01', 'aerial_asphalt_01_nor_gl_1k.jpg'), rough=0.8),
    'prato': pbr('Prato', diff=DER('prato_diff.jpg'), nor=TEX('leafy_grass', 'leafy_grass_nor_gl_1k.jpg'), rough=0.95),
    'prato_secco': pbr('PratoSecco', diff=DER('prato_secco_diff.jpg'), rough=0.95),
    'coppi': pbr('Coppi', diff=DER('coppi_diff.jpg'), nor=TEX('clay_roof_tiles_02', 'clay_roof_tiles_02_nor_gl_1k.jpg'), rough=0.75),
    'coppi_vecchi': pbr('CoppiVecchi', diff=DER('coppi_vecchi_diff.jpg'), nor=TEX('clay_roof_tiles_02', 'clay_roof_tiles_02_nor_gl_1k.jpg'),
                        rough=0.8),
    'piombo': pbr('CupolaPiombo', color=(0.36, 0.38, 0.40), rough=0.55, metal=0.6),
    'chioma': pbr('ChiomaPino', color=(0.07, 0.11, 0.05), rough=0.85),
    'tronco': pbr('TroncoPino', color=(0.24, 0.18, 0.14), rough=0.9),
    'colli': pbr('ColliAlbani', color=(0.21, 0.25, 0.17), rough=1.0),
    'cornicione': pbr('CornicioneCitta', color=(0.82, 0.78, 0.7), rough=0.85),
}
FACCIATE = [pbr(f'Facciata_{n}', diff=DER(f'facciata_{n}_diff.jpg'), emission_map=DER(f'facciata_{n}_emit.jpg'),
                emission_strength=0.5, rough=0.85) for n in ('ocra', 'terracotta', 'giallo', 'avorio', 'rosa')]
FACADE_TILE = (12.8, 13.6)

CITY = lib.collection('Citta')
VERDE = lib.collection('Verde')
STRADE = lib.collection('Strade')
LM = lib.collection('Monumenti')
FAR = lib.collection('Lontano')

# ---------------------------------------------------------------------------- monumenti
C = Vector((-260.0, -470.0, 0.0))     # Colosseo, a sud-ovest del palazzo (Colle Oppio in mezzo)
ROT_C = math.radians(14.0)
col = colosseo.build(LM, M, location=tuple(C), rot_z=ROT_C)
arco = colosseo.arco_costantino(LM, M, location=(C.x - 75.0, C.y - 118.0, 0.0), rot_z=math.radians(78))


def ellipse_poly(cx, cy, a, b, rot, n=96):
    cr, sr = math.cos(rot), math.sin(rot)
    return [(cx + a * math.cos(t) * cr - b * math.sin(t) * sr, cy + a * math.cos(t) * sr + b * math.sin(t) * cr)
            for t in [2 * math.pi * k / n for k in range(n)]]


def flat_poly(name, pts, z0, z1, mat, coll, uv=4.0):
    n = len(pts)
    v = [(x, y, z0) for x, y in pts] + [(x, y, z1) for x, y in pts]
    f = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))] + [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    return lib.mesh_obj(name, v, f, mat, coll, uv_scale=uv)


def point_in_poly(x, y, poly):
    inside = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi:
            inside = not inside
        j = i
    return inside


# piazza attorno al Colosseo
piazza = ellipse_poly(C.x, C.y, colosseo.A_OUT + 40, colosseo.B_OUT + 34, ROT_C)
_inner = ellipse_poly(C.x, C.y, colosseo.A_OUT - 1.0, colosseo.B_OUT - 1.0, ROT_C)
_n = len(piazza)
_v = [(x, y, 0.02) for x, y in piazza] + [(x, y, 0.02) for x, y in _inner]
_f = [(i, (i + 1) % _n, _n + (i + 1) % _n, _n + i) for i in range(_n)]
lib.mesh_obj('PiazzaColosseo', _v, _f, M['piazza'], LM, uv_scale=6.0)  # anello: l'arena resta scoperta

# ---------------------------------------------------------------------------- terreno e verde
box_ground = lib.box('Suolo', -4200, 4200, -4400, 3600, -0.6, -0.15, M['asfalto'], STRADE, uv_scale=24.0)
# foro nel suolo sopra l'arena: gli ipogei restano visibili
_arena = ellipse_poly(C.x, C.y, colosseo.A_OUT - 20.0, colosseo.B_OUT - 20.0, ROT_C, 64)
_cut = lib.mesh_obj('cut', [(x, y, -2.0) for x, y in _arena] + [(x, y, 2.0) for x, y in _arena],
                    [tuple(range(63, -1, -1)), tuple(range(64, 128))] + [(i, (i + 1) % 64, 64 + (i + 1) % 64, 64 + i) for i in range(64)],
                    None, STRADE, uv_scale=None)
lib.boolean_cut(box_ground, [_cut])
lib.cube_uv(box_ground.data, 24.0)

COLLE_OPPIO = [(-190, -24), (215, -24), (238, -150), (170, -300), (-40, -345), (-120, -330), (-175, -250), (-215, -150)]
CELIO = ellipse_poly(140, -700, 190, 150, 0.3, 40)
FORI_DIR = Vector((-0.82, 0.57, 0)).normalized()
FORI_START = C + Vector((-120, 70, 0))
FORI = [tuple(FORI_START + FORI_DIR * 0 + Vector((-FORI_DIR.y, FORI_DIR.x, 0)) * 70)[:2],
        tuple(FORI_START + FORI_DIR * 900 + Vector((-FORI_DIR.y, FORI_DIR.x, 0)) * 70)[:2],
        tuple(FORI_START + FORI_DIR * 900 - Vector((-FORI_DIR.y, FORI_DIR.x, 0)) * 90)[:2],
        tuple(FORI_START + FORI_DIR * 0 - Vector((-FORI_DIR.y, FORI_DIR.x, 0)) * 90)[:2]]
PALATINO_C = Vector((-610.0, -780.0, 0.0))
PALATINO = ellipse_poly(PALATINO_C.x, PALATINO_C.y, 270, 210, 0.5, 48)
CIRCO_C = Vector((-930.0, -1060.0, 0.0))
CIRCO = ellipse_poly(CIRCO_C.x, CIRCO_C.y, 310, 70, math.radians(-38), 40)
PALAZZO_ZONE = [(-62, -42), (62, -42), (62, 18), (-62, 18)]   # palazzo, vicini e strada (già in palazzo.glb)

flat_poly('ColleOppio', COLLE_OPPIO, -0.15, 0.05, M['prato'], VERDE, uv=8.0)
flat_poly('Celio', CELIO, -0.15, 0.05, M['prato'], VERDE, uv=8.0)
flat_poly('ForiImperiali', FORI, -4.0, -0.1, M['prato_secco'], VERDE, uv=8.0)
flat_poly('CircoMassimo', CIRCO, -3.0, 0.0, M['prato_secco'], VERDE, uv=10.0)

# viale dei Fori Imperiali (asfalto chiaro rialzato sopra gli scavi)
w = Vector((-FORI_DIR.y, FORI_DIR.x, 0))
viale = [tuple(FORI_START + w * 16)[:2], tuple(FORI_START + FORI_DIR * 900 + w * 16)[:2],
         tuple(FORI_START + FORI_DIR * 900 - w * 16)[:2], tuple(FORI_START - w * 16)[:2]]
flat_poly('ViaForiImperiali', viale, -0.15, 0.15, M['asfalto'], STRADE, uv=20.0)
# rovine dei Fori: tratti di muro e rocchi di colonne
for k in range(70):
    t = rnd.uniform(0.05, 0.95)
    side = rnd.choice((-1, 1))
    off = rnd.uniform(22, 80) * side
    p = FORI_START + FORI_DIR * (900 * t) + w * off
    if rnd.random() < 0.55:
        c = lib.lathe('ForoColonna', [(0.75, 0), (0.7, rnd.uniform(3, 14))], M['travertino'], VERDE, segs=10)
        c.location = (p.x, p.y, -4.0)
    else:
        a = rnd.uniform(0, math.pi)
        L = rnd.uniform(6, 22)
        dx, dy = math.cos(a) * L / 2, math.sin(a) * L / 2
        nx, ny = -math.sin(a) * 0.8, math.cos(a) * 0.8
        flat_poly('ForoMuro', [(p.x - dx - nx, p.y - dy - ny), (p.x + dx - nx, p.y + dy - ny), (p.x + dx + nx, p.y + dy + ny),
                                (p.x - dx + nx, p.y - dy + ny)], -4.0, rnd.uniform(-1.0, 6.0), M['laterizio'], VERDE)


def mound(name, center, rx, ry, height, rot, mat, coll, n=40):
    """Collina dolce (Palatino) come griglia deformata."""
    verts, faces = [], []
    cr, sr = math.cos(rot), math.sin(rot)
    for j in range(n + 1):
        for i in range(n + 1):
            u, v = (i / n) * 2 - 1, (j / n) * 2 - 1
            r = math.sqrt(u * u + v * v)
            h = height * max(0.0, 1 - r) ** 0.6 * (1 if r < 1 else 0)
            h += (math.sin(u * 7.1) * math.cos(v * 5.3)) * 1.2 * (1 - min(1, r))
            x, y = u * rx, v * ry
            verts.append((center.x + x * cr - y * sr, center.y + x * sr + y * cr, h - 0.1))
    for j in range(n):
        for i in range(n):
            k = j * (n + 1) + i
            faces.append((k, k + 1, k + n + 2, k + n + 1))
    return lib.mesh_obj(name, verts, faces, mat, coll, smooth=True, uv_scale=10.0)


mound('Palatino', PALATINO_C, 300, 240, 28.0, 0.5, M['prato_secco'], VERDE)
# rovine dei palazzi imperiali sul Palatino
for k in range(55):
    a = rnd.uniform(0, 2 * math.pi)
    r = math.sqrt(rnd.random()) * 0.8
    x = PALATINO_C.x + math.cos(a) * 270 * r
    y = PALATINO_C.y + math.sin(a) * 210 * r
    base = 28.0 * max(0.0, 1 - r) ** 0.6 - 1
    sx, sy = rnd.uniform(6, 30), rnd.uniform(1.2, 2.2) if rnd.random() < 0.6 else rnd.uniform(6, 18)
    b = lib.box('PalatinoRovina', -sx / 2, sx / 2, -sy / 2, sy / 2, 0, rnd.uniform(3, 16), M['laterizio'], VERDE, uv_scale=4.0)
    b.location = (x, y, base)
    b.rotation_euler = (0, 0, rnd.uniform(0, math.pi))
# Terme di Traiano sul Colle Oppio: esedra in laterizio
esedra = []
for k in range(25):
    t = math.pi * k / 24
    esedra.append((80 + 32 * math.cos(t), -210 + 32 * math.sin(t)))
for k in range(24, -1, -1):
    t = math.pi * k / 24
    esedra.append((80 + 29 * math.cos(t), -210 + 29 * math.sin(t)))
flat_poly('EsedraTraiano', esedra, -0.1, 13.0, M['laterizio'], VERDE)

# ---------------------------------------------------------------------------- isolati
EXCLUDE = [COLLE_OPPIO, CELIO, FORI, PALATINO, CIRCO, piazza, PALAZZO_ZONE]


def blocked(x, y, margin=0.0):
    for poly in EXCLUDE:
        if point_in_poly(x, y, poly):
            return True
    return False


def gable_roof(x0, x1, y0, y1, z, along_x, mat, coll, h=2.6):
    if along_x:
        ym = (y0 + y1) / 2
        v = [(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z), (x0, ym, z + h), (x1, ym, z + h)]
        f = [(0, 1, 5, 4), (2, 3, 4, 5), (0, 4, 3), (1, 2, 5)]
    else:
        xm = (x0 + x1) / 2
        v = [(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z), (xm, y0, z + h), (xm, y1, z + h)]
        f = [(3, 0, 4, 5), (1, 2, 5, 4), (0, 1, 4), (2, 3, 5)]
    return v, f


class Batch:
    """Accumula muri/tetti per materiale e crea pochi oggetti grandi (poche chiamate di disegno)."""

    def __init__(self):
        self.parts = {}

    def add(self, mat, verts, faces):
        vv, ff = self.parts.setdefault(mat.name, (mat, [], []))[1:]
        b = len(vv)
        vv += verts
        ff += [tuple(b + i for i in fc) for fc in faces]

    def box(self, mat, x0, x1, y0, y1, z0, z1, rot=None, origin=None, top_only=False):
        v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
        if rot is not None:
            v = [rot_pt(p, rot, origin) for p in v]
        if top_only:
            self.add(mat, v[4:], [(0, 1, 2, 3)])
            return
        # senza faccia inferiore (mai visibile)
        self.add(mat, v, [(4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])

    def build(self, coll, prefix, uv=None):
        out = []
        for name, (mat, v, f) in self.parts.items():
            me = bpy.data.meshes.new(f'{prefix}_{name}')
            me.from_pydata(v, [], f)
            me.validate()
            me.shade_flat()
            me.materials.append(mat)
            uv_tile = uv.get(name) if uv else None
            facade_uv(me, uv_tile)
            o = bpy.data.objects.new(f'{prefix}_{name}', me)
            coll.objects.link(o)
            out.append(o)
        return out


def rot_pt(p, a, o):
    x, y, z = p[0] - o[0], p[1] - o[1], p[2]
    return (o[0] + x * math.cos(a) - y * math.sin(a), o[1] + x * math.sin(a) + y * math.cos(a), z)


def facade_uv(me, tile):
    """UV in metri: sulle pareti u = lunghezza lungo il muro / larghezza modulo, v = quota / altezza modulo."""
    uvl = me.uv_layers.get('UVMap') or me.uv_layers.new(name='UVMap')
    tw, th = tile or (4.0, 4.0)
    for poly in me.polygons:
        n = poly.normal
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            if abs(n.z) < 0.5:
                t = Vector((-n.y, n.x, 0)).normalized()
                u = co.dot(t) / tw
                v = co.z / th
            else:
                u, v = co.x / tw, co.y / tw
            uvl.data[li].uv = (u, v)


batch = Batch()
churches = []
pines = []
CELL = 96.0
STREET = 8.0
for gi in range(-34, 35):
    for gj in range(-36, 28):
        cx, cy = gi * CELL, gj * CELL
        dist = math.hypot(cx - C.x, cy - C.y)
        if dist > 2800:
            continue
        near = min(dist, math.hypot(cx, cy)) < 800
        # distretti con orientamento proprio (la trama irregolare di Roma)
        district = (gi // 6, gj // 6)
        drot = math.radians(((hash(district) % 23) - 11) * 1.1)
        jx, jy = rnd.uniform(-10, 10), rnd.uniform(-10, 10)
        ox, oy = cx + jx, cy + jy
        if blocked(ox, oy) or any(blocked(ox + dx, oy + dy) for dx, dy in ((30, 30), (-30, -30), (30, -30), (-30, 30))):
            continue
        if rnd.random() < 0.035 and dist < 1500:
            # piazza alberata
            sq = CELL - 2 * STREET
            batch.box(M['piazza'], ox - sq / 2, ox + sq / 2, oy - sq / 2, oy + sq / 2, -0.2, 0.06, rot=drot, origin=(ox, oy), top_only=True)
            for _ in range(6):
                pines.append((ox + rnd.uniform(-30, 30), oy + rnd.uniform(-30, 30), 0.0, rnd.uniform(0, 6.3), rnd.uniform(0.7, 1.0)))
            continue
        drot = drot + math.radians(rnd.uniform(-4, 4))
        bw = CELL - 2 * STREET - rnd.uniform(0, 14)
        bh = CELL - 2 * STREET - rnd.uniform(0, 14)
        x0, x1, y0, y1 = ox - bw / 2, ox + bw / 2, oy - bh / 2, oy + bh / 2
        far = dist > 1500
        if rnd.random() < 0.012 and not far:
            churches.append((ox, oy, drot))
        depth = 13.0
        # quattro ali attorno alla corte, divise in edifici di altezze e colori diversi
        sides = [('S', x0, x1, y0, y0 + depth), ('N', x0, x1, y1 - depth, y1),
                 ('W', x0, x0 + depth, y0 + depth, y1 - depth), ('E', x1 - depth, x1, y0 + depth, y1 - depth)]
        for sd, a0, a1, b0, b1 in sides:
            along_x = sd in 'SN'
            L = (a1 - a0) if along_x else (b1 - b0)
            pos = 0.0
            while pos < L - 1:
                seg = min(L - pos, rnd.uniform(14, 32) if not far else L)
                h = rnd.choice((15.4, 18.8, 18.8, 22.2, 22.2, 25.6)) if not far else rnd.uniform(15, 24)
                fac = FACCIATE[rnd.randrange(len(FACCIATE))]
                if along_x:
                    sx0, sx1, sy0, sy1 = a0 + pos, a0 + pos + seg, b0, b1
                else:
                    sx0, sx1, sy0, sy1 = a0, a1, b0 + pos, b0 + pos + seg
                batch.box(fac, sx0, sx1, sy0, sy1, -0.2, h, rot=drot, origin=(ox, oy))
                if near:
                    batch.box(M['cornicione'], sx0 - 0.35, sx1 + 0.35, sy0 - 0.35, sy1 + 0.35, h - 0.4, h, rot=drot, origin=(ox, oy))
                roof = M['coppi'] if rnd.random() < 0.6 else M['coppi_vecchi']
                v, f = gable_roof(sx0 - 0.3, sx1 + 0.3, sy0 - 0.3, sy1 + 0.3, h, along_x, roof, CITY, h=2.4 + rnd.uniform(0, 0.8))
                batch.add(roof, [rot_pt(p, drot, (ox, oy)) for p in v], f)
                pos += seg
        # cortile pavimentato
        batch.box(M['piazza'], x0 + depth, x1 - depth, y0 + depth, y1 - depth, -0.2, 0.05, rot=drot, origin=(ox, oy), top_only=True)

city_objs = batch.build(CITY, 'Isolati', uv={f.name: FACADE_TILE for f in FACCIATE} | {
    'Coppi': (4.0, 4.0), 'CoppiVecchi': (4.0, 4.0), 'Piazza': (8.0, 8.0), 'CornicioneCitta': (4.0, 4.0)})

# chiese con cupola e campanili romanici
for k, (x, y, r) in enumerate(churches):
    nave = lib.box(f'Chiesa{k}', -9, 9, -26, 18, 0, 19, FACCIATE[3], CITY, uv_scale=None)
    facade_uv(nave.data, FACADE_TILE)
    drum = lib.lathe(f'Tamburo{k}', [(8.5, 0), (8.5, 7.5)], FACCIATE[3], CITY, segs=24, smooth=False, uv_scale=None)
    facade_uv(drum.data, FACADE_TILE)
    drum.location = (0, 6, 19)
    dome = lib.lathe(f'Cupola{k}', [(9.0, 0)] + [(9.0 * math.cos(a), 9.0 * 1.15 * math.sin(a)) for a in
                                                  [math.pi / 2 * i / 10 for i in range(1, 11)]], M['piombo'], CITY, segs=24)
    dome.location = (0, 6, 26.5)
    lantern = lib.lathe(f'Lanterna{k}', [(1.6, 0), (1.6, 3.5), (0.3, 6.0)], FACCIATE[3], CITY, segs=10)
    lantern.location = (0, 6, 36.8)
    roof_v, roof_f = gable_roof(-9.4, 9.4, -26.4, 18.4, 19, False, M['coppi'], CITY, h=4.0)
    rr = lib.mesh_obj(f'TettoChiesa{k}', roof_v, roof_f, M['coppi'], CITY, uv_scale=4.0)
    parts = [nave, drum, dome, lantern, rr]
    if k % 2 == 0:
        tw = lib.box(f'Campanile{k}', 10, 17, 10, 17, 0, 46, M['laterizio'], CITY, uv_scale=4.0)
        tv, tf = [(10, 10, 46), (17, 10, 46), (17, 17, 46), (10, 17, 46), (13.5, 13.5, 52)], [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4), (0, 3, 2, 1)]
        parts += [tw, lib.mesh_obj(f'CuspideCampanile{k}', tv, tf, M['coppi_vecchi'], CITY, uv_scale=4.0)]
    o = lib.join(parts, f'Chiesa{k}')
    o.location = (x, y, 0)
    o.rotation_euler = (0, 0, r + rnd.choice((0, math.pi / 2)))

# ---------------------------------------------------------------------------- pini domestici


def pine_prototype():
    """Pino domestico (Pinus pinea): fusto alto e inclinato, chioma piatta "a ombrello"."""
    bm = bmesh.new()
    r = random.Random(3)
    # fusto rastremato e leggermente curvo
    rings, segs, H = 8, 7, 11.5
    prev = None
    for i in range(rings + 1):
        t = i / rings
        cx = 0.9 * math.sin(t * 1.4)
        rad = 0.42 * (1 - 0.55 * t)
        ring = [bm.verts.new((cx + rad * math.cos(2 * math.pi * k / segs), rad * math.sin(2 * math.pi * k / segs), H * t))
                for k in range(segs)]
        if prev:
            for k in range(segs):
                bm.faces.new((prev[k], prev[(k + 1) % segs], ring[(k + 1) % segs], ring[k]))
        prev = ring
    n_trunk = len(bm.faces)
    # chioma: cuscini schiacciati con rilievo irregolare
    for k in range(7):
        a = 2 * math.pi * k / 7 + r.uniform(-0.3, 0.3)
        d = 0 if k == 0 else r.uniform(2.6, 4.2)
        res = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0)
        sx = r.uniform(3.2, 4.4)
        sz = r.uniform(1.1, 1.6)
        off = Vector((0.9 * math.sin(1.4) + math.cos(a) * d, math.sin(a) * d, H + r.uniform(-0.4, 0.9)))
        for v in res['verts']:
            nrm = v.co.normalized()
            bump = 1 + 0.16 * math.sin(nrm.x * 9.1 + k) * math.cos(nrm.y * 8.3 - k) + 0.08 * math.sin(nrm.z * 13.0)
            v.co = Vector((v.co.x * sx * bump, v.co.y * sx * bump, v.co.z * sz * bump)) + off
    me = bpy.data.meshes.new('PinoPrototipo')
    bm.to_mesh(me)
    bm.free()
    me.materials.append(M['tronco'])
    me.materials.append(M['chioma'])
    for p in me.polygons:
        p.material_index = 0 if p.index < n_trunk else 1
    me.shade_smooth()
    o = bpy.data.objects.new('PinoPrototipo', me)
    VERDE.objects.link(o)
    return o


pino = pine_prototype()


def scatter(poly, count, min_d=14.0, base_h=None):
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    tries = 0
    while count > 0 and tries < count * 40:
        tries += 1
        x, y = rnd.uniform(min(xs), max(xs)), rnd.uniform(min(ys), max(ys))
        if not point_in_poly(x, y, poly):
            continue
        if any((x - px) ** 2 + (y - py) ** 2 < min_d ** 2 for px, py, *_ in pines[-400:]):
            continue
        z = base_h(x, y) if base_h else 0.0
        pines.append((x, y, z, rnd.uniform(0, 2 * math.pi), rnd.uniform(0.8, 1.25)))
        count -= 1


scatter(COLLE_OPPIO, 150, 12.0)
scatter(CELIO, 70, 15.0)


def palatino_h(x, y):
    u = ((x - PALATINO_C.x) * math.cos(-0.5) - (y - PALATINO_C.y) * math.sin(-0.5)) / 300
    v = ((x - PALATINO_C.x) * math.sin(-0.5) + (y - PALATINO_C.y) * math.cos(-0.5)) / 240
    r = math.hypot(u, v)
    return 28.0 * max(0.0, 1 - r) ** 0.6 - 0.5


scatter(PALATINO, 140, 16.0, palatino_h)
# filari lungo via di San Gregorio (tra Palatino e Celio) e attorno al Circo Massimo
for k in range(26):
    t = k / 25
    x, y = C.x - 60 + (-230) * t, C.y - 170 + (-330) * t
    pines.append((x + 12, y + 8, 0.0, rnd.uniform(0, 6.3), rnd.uniform(0.9, 1.2)))

for i, (x, y, z, rz, s) in enumerate(pines):
    lib.instance(pino, f'Pino{i}', VERDE, location=(x, y, z), rotation=(0, 0, rz), scale=(s, s, s))

# ---------------------------------------------------------------------------- Colli Albani all'orizzonte (sud-est)


def ridge(name, center, length, width, height, rot, n=60, seed=0):
    r = random.Random(seed)
    peaks = [(r.uniform(-0.8, 0.8), r.uniform(-0.3, 0.3), r.uniform(0.4, 1.0)) for _ in range(9)]
    verts, faces = [], []
    cr, sr = math.cos(rot), math.sin(rot)
    m = n // 3
    for j in range(m + 1):
        for i in range(n + 1):
            u, v = i / n * 2 - 1, j / m * 2 - 1
            h = 0.0
            for px, py, ph in peaks:
                h = max(h, ph * math.exp(-((u - px) ** 2 / 0.08 + (v - py) ** 2 / 0.25)))
            h *= height * max(0.0, 1 - abs(v) ** 2) * max(0.0, 1 - abs(u) ** 6)
            x, y = u * length / 2, v * width / 2
            verts.append((center[0] + x * cr - y * sr, center[1] + x * sr + y * cr, h - 30))
    for j in range(m):
        for i in range(n):
            k = j * (n + 1) + i
            faces.append((k, k + 1, k + n + 2, k + n + 1))
    return lib.mesh_obj(name, verts, faces, M['colli'], FAR, smooth=True, uv_scale=200.0)


ridge('ColliAlbani', (11000, -17000), 22000, 9000, 900, math.radians(-40), seed=4)
ridge('MontiTiburtini', (21000, 6000), 26000, 8000, 1100, math.radians(70), seed=9)
lib.box('Campagna', -40000, 40000, -40000, 40000, -60.0, -9.0, M['colli'], FAR, uv_scale=None)

# ---------------------------------------------------------------------------- luce (stessa del palazzo)
LCOL = lib.collection('Luci')
SUN_DIR = Vector((-0.88, -0.38, 0.22)).normalized()
ld = bpy.data.lights.new('Sole', 'SUN')
ld.energy = 2.4
ld.color = kelvin(2800)
ld.angle = math.radians(1.2)
sun = bpy.data.objects.new('Sole', ld)
sun.rotation_euler = (-SUN_DIR).to_track_quat('-Z', 'Y').to_euler()
LCOL.objects.link(sun)
world = bpy.data.worlds.new('Cielo')
scene.world = world
world.use_nodes = True
wn = world.node_tree
env = wn.nodes.new('ShaderNodeTexEnvironment')
env.image = bpy.data.images.load(os.path.join(CACHE, 'hdri', 'kloppenheim_06_puresky_4k.hdr'))
mapping = wn.nodes.new('ShaderNodeMapping')
coord = wn.nodes.new('ShaderNodeTexCoord')
mapping.inputs['Rotation'].default_value[2] = math.atan2(SUN_DIR.y, -SUN_DIR.x) - (0.612 - 0.5) * 2 * math.pi
wn.links.new(coord.outputs['Generated'], mapping.inputs['Vector'])
wn.links.new(mapping.outputs['Vector'], env.inputs['Vector'])
wn.nodes['Background'].inputs['Strength'].default_value = 0.2
wn.links.new(env.outputs['Color'], wn.nodes['Background'].inputs['Color'])

print('oggetti', sum(1 for o in bpy.data.objects if o.type == 'MESH'),
      'facce (senza istanze)', sum(len(o.data.polygons) for o in bpy.data.objects if o.type == 'MESH' and not o.name.startswith('Pino')),
      'pini', len(pines), 'chiese', len(churches))

# ---------------------------------------------------------------------------- render di controllo
if args.render:
    cd = bpy.data.cameras.new('Aerea')
    cd.lens = 28
    cd.clip_end = 60000
    cam = bpy.data.objects.new('Aerea', cd)
    scene.collection.objects.link(cam)
    views = {'aerea': (Vector((150.0, 260.0, 230.0)), C + Vector((-40, -60, 0)), 28),
             'colosseo': (C + Vector((150.0, 210.0, 120.0)), C + Vector((0, 0, 8)), 35)}
    eye, look, lens = views[args.render]
    cd.lens = lens
    cam.location = eye
    cam.rotation_euler = (look - eye).to_track_quat('-Z', 'Y').to_euler()
    scene.camera = cam
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = args.samples
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    scene.render.resolution_percentage = int(args.res * 100)
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.exposure = 0.3
    os.makedirs(os.path.join(CACHE, 'renders'), exist_ok=True)
    scene.render.filepath = os.path.join(CACHE, 'renders', f'roma-{args.render}.png')
    bpy.ops.render.render(write_still=True)
    print('render', scene.render.filepath)

# ---------------------------------------------------------------------------- export
if not args.no_export:
    out_dir = os.path.join(ROOT, 'public', 'models')
    os.makedirs(out_dir, exist_ok=True)
    # istanze dei pini: esportate come elenco (InstancedMesh nel sito), il prototipo nel GLB
    inst = [{'p': [round(x, 2), round(z, 2), round(-y, 2)], 'r': round(rz, 3), 's': round(s, 3)} for x, y, z, rz, s in pines]
    with open(os.path.join(ROOT, 'src', 'data', 'pini.json'), 'w') as fh:
        json.dump(inst, fh, separators=(',', ':'))
    for o in list(bpy.data.objects):
        if o.name.startswith('Pino') and o.name != 'PinoPrototipo':
            bpy.data.objects.remove(o, do_unlink=True)
    # monumenti: un solo oggetto con lightmap Cycles
    mon = lib.join([o for o in LM.all_objects if o.type == 'MESH'], 'LM_Colosseo')
    verde = lib.join([o for o in VERDE.all_objects if o.type == 'MESH' and o.name != 'PinoPrototipo'], 'Verde')
    if not args.no_bake and not args.skip_colosseo:
        sys.argv = [sys.argv[0]]
        import importlib.util
        spec = importlib.util.spec_from_file_location('bakeutil', os.path.join(os.path.dirname(__file__), 'bakeutil.py'))
        bu = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bu)
        rgb = bu.bake_lightmap(scene, mon, args.lm_size, args.lm_samples, CACHE)
        bu.save_lightmap(rgb, os.path.join(out_dir, 'lm_colosseo.webp'), 6.0)
    for o in list(bpy.data.objects):
        if o.type in ('LIGHT', 'CAMERA'):
            bpy.data.objects.remove(o, do_unlink=True)
    kw = dict(export_format='GLB', export_apply=True, export_yup=True, export_lights=False, export_cameras=False,
              export_image_format='AUTO', use_selection=True)
    # Colosseo (con lightmap) e città in due file: la città si può rigenerare senza rifare il bake
    bpy.ops.object.select_all(action='DESELECT')
    mon.select_set(True)
    if not args.skip_colosseo:
        out_c = os.path.join(CACHE, 'colosseo_raw.glb')
        bpy.ops.export_scene.gltf(filepath=out_c, **kw)
        print('GLB', out_c, f'{os.path.getsize(out_c) / 1e6:.1f} MB')
    bpy.ops.object.select_all(action='SELECT')
    mon.select_set(False)
    out = os.path.join(CACHE, 'roma_raw.glb')
    bpy.ops.export_scene.gltf(filepath=out, **kw)
    print('GLB', out, f'{os.path.getsize(out) / 1e6:.1f} MB', 'pini', len(inst))
