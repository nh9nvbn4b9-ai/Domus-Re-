"""Aereo acrobatico a elica (generico, monomotore ad ala bassa) per la scrittura nel cielo.

Lunghezza 7,1 m, apertura alare 7,5 m. Livrea bianca con fasce oro e nere (colori Domus Re).
L'elica è un oggetto separato ("Elica") per farla ruotare nel sito; l'ugello del fumo è in coda.
Asse longitudinale lungo +X (muso), Z in alto.

Uso: <venv-blender>/bin/python pipeline/blender/build_aereo.py [--render]
"""
import math
import os
import sys

import bpy  # noqa: I001
import bmesh

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
from materials import pbr  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
COLL = lib.collection('Aereo')

M = {
    'vernice': pbr('VerniceBianca', color=(0.92, 0.92, 0.9), rough=0.22, spec=0.6),
    'oro': pbr('FasciaOro', color=(0.83, 0.62, 0.24), rough=0.3, metal=0.9),
    'nero': pbr('FasciaNera', color=(0.02, 0.02, 0.02), rough=0.3),
    'vetro': pbr('Tettuccio', color=(0.05, 0.07, 0.09), rough=0.05, metal=0.3),
    'gomma': pbr('Gomma', color=(0.03, 0.03, 0.03), rough=0.7),
    'elica': pbr('Elica', color=(0.04, 0.04, 0.04), rough=0.4),
}

# --------------------------------------------------------------------------- fusoliera (loft di sezioni ellittiche)
# (x, semilarghezza, semialtezza, quota del centro)
STATIONS = [
    (3.55, 0.05, 0.05, 0.05), (3.45, 0.28, 0.30, 0.05), (3.2, 0.42, 0.44, 0.05), (2.6, 0.50, 0.52, 0.08),
    (1.6, 0.52, 0.58, 0.12), (0.6, 0.50, 0.62, 0.15), (-0.4, 0.44, 0.52, 0.18), (-1.6, 0.32, 0.38, 0.22),
    (-2.6, 0.20, 0.28, 0.28), (-3.35, 0.10, 0.20, 0.34), (-3.55, 0.03, 0.05, 0.36),
]
SEG = 24
bm = bmesh.new()
rings = []
for x, hw, hh, zc in STATIONS:
    ring = []
    for k in range(SEG):
        a = 2 * math.pi * k / SEG
        # sezione a "uovo": più piatta sul fondo
        z = zc + hh * math.sin(a) * (0.82 if math.sin(a) < 0 else 1.0)
        ring.append(bm.verts.new((x, hw * math.cos(a), z)))
    rings.append(ring)
for r0, r1 in zip(rings[:-1], rings[1:]):
    for k in range(SEG):
        bm.faces.new((r0[k], r1[k], r1[(k + 1) % SEG], r0[(k + 1) % SEG]))
bm.faces.new(rings[0][::-1])
bm.faces.new(rings[-1])
me = bpy.data.meshes.new('Fusoliera')
bm.to_mesh(me)
bm.free()
me.materials.append(M['vernice'])
me.shade_smooth()
fus = bpy.data.objects.new('Fusoliera', me)
COLL.objects.link(fus)

# fasce decorative: anelli leggermente più larghi della fusoliera
for x0, x1, mat in ((1.0, 1.25, 'oro'), (1.3, 1.38, 'nero'), (-2.2, -2.0, 'oro')):
    st = [s for s in STATIONS]

    def interp(x):
        for (xa, wa, ha, za), (xb, wb, hb, zb) in zip(st[:-1], st[1:]):
            if xb <= x <= xa:
                t = (xa - x) / (xa - xb)
                return wa + (wb - wa) * t, ha + (hb - ha) * t, za + (zb - za) * t
        return st[-1][1:]
    v, f = [], []
    for x in (x0, x1):
        hw, hh, zc = interp(x)
        for k in range(SEG):
            a = 2 * math.pi * k / SEG
            v.append((x, (hw + 0.006) * math.cos(a), zc + (hh + 0.006) * math.sin(a) * (0.82 if math.sin(a) < 0 else 1.0)))
    for k in range(SEG):
        f.append((k, SEG + k, SEG + (k + 1) % SEG, (k + 1) % SEG))
    o = lib.mesh_obj(f'Fascia{mat}{x0}', v, f, M[mat], COLL, smooth=True, uv_scale=None)

# --------------------------------------------------------------------------- superfici alari (profilo lenticolare)


def wing(name, root_x, root_c, tip_c, span, sweep, z0, dihedral, thick, mat, vertical=False, mirror=True):
    """Ala/impennaggio rastremato: root_x = bordo d'attacco alla radice, corde in metri."""
    sides = (1, -1) if mirror else (1,)
    for s in sides:
        n = 12
        v, f = [], []
        for j, (c, yy) in enumerate(((root_c, 0.0), (tip_c, span))):
            xl = root_x - sweep * (yy / span) if span else root_x
            for i in range(n):
                t = i / (n - 1)
                x = xl - c * t
                th = thick * c * 4 * t * (1 - t) ** 1.2
                if vertical:
                    v.append((x, th / 2, z0 + yy))
                else:
                    v.append((x, s * (0.3 + yy), z0 + yy * math.tan(dihedral) + th / 2))
            for i in range(n - 1, -1, -1):
                t = i / (n - 1)
                x = xl - c * t
                th = thick * c * 4 * t * (1 - t) ** 1.2
                if vertical:
                    v.append((x, -th / 2, z0 + yy))
                else:
                    v.append((x, s * (0.3 + yy), z0 + yy * math.tan(dihedral) - th / 2 * 0.6))
        m = 2 * n
        for i in range(m):
            f.append((i, (i + 1) % m, m + (i + 1) % m, m + i))
        f.append(tuple(range(m - 1, -1, -1)))
        f.append(tuple(range(m, 2 * m)))
        lib.mesh_obj(f'{name}{s}', v, f, mat, COLL, smooth=True, sharp_deg=50, uv_scale=None)
        if vertical:
            break


wing('Ala', 1.35, 1.75, 1.05, 3.45, 0.25, -0.28, math.radians(3), 0.13, M['vernice'])
wing('Stabilizzatore', -2.75, 0.85, 0.55, 1.35, 0.15, 0.36, 0.0, 0.09, M['vernice'])
wing('Deriva', -2.55, 1.05, 0.55, 1.25, 0.55, 0.45, 0.0, 0.1, M['vernice'], vertical=True, mirror=False)
# estremità alari e timone in oro
for s in (1, -1):
    lib.box(f'Estremita{s}', -0.2, 0.75, s * 3.72 - 0.03, s * 3.72 + 0.03, -0.12, 0.02, M['oro'], COLL, bev=0.02)
lib.box('TimoneFascia', -3.6, -3.05, -0.03, 0.03, 1.0, 1.7, M['oro'], COLL)

# tettuccio a goccia
bmc = bmesh.new()
res = bmesh.ops.create_uvsphere(bmc, u_segments=24, v_segments=12, radius=1.0)
for v in res['verts']:
    v.co.x *= 1.05
    v.co.y *= 0.36
    v.co.z *= 0.42
    if v.co.z < 0:
        v.co.z = 0
    v.co.x += 0.35
    v.co.z += 0.62
me = bpy.data.meshes.new('Tettuccio')
bmc.to_mesh(me)
bmc.free()
me.materials.append(M['vetro'])
me.shade_smooth()
COLL.objects.link(bpy.data.objects.new('Tettuccio', me))

# carrello fisso con carenature
for s in (1, -1):
    leg = lib.tube_path(f'Gamba{s}', [(1.65, s * 0.35, -0.3), (1.55, s * 1.05, -1.05)], 0.05, M['vernice'], COLL)
    spat = lib.lathe(f'Carenatura{s}', [(0.0, -0.45), (0.14, -0.3), (0.2, 0.0), (0.16, 0.25), (0.0, 0.42)], M['vernice'], COLL, segs=14)
    spat.rotation_euler = (0, math.pi / 2, 0)
    spat.location = (1.5, s * 1.05, -1.12)
    wheel = lib.lathe(f'Ruota{s}', [(0.0, -0.06), (0.2, -0.06), (0.22, 0.0), (0.2, 0.06), (0.0, 0.06)], M['gomma'], COLL, segs=16)
    wheel.rotation_euler = (math.pi / 2, 0, 0)
    wheel.location = (1.5, s * 1.05, -1.2)
lib.box('RuotinoCoda', -3.3, -3.2, -0.03, 0.03, 0.05, 0.25, M['nero'], COLL)

# ogiva ed elica (oggetto separato per la rotazione)
ogiva = lib.lathe('Ogiva', [(0.26, 0.0), (0.24, 0.12), (0.17, 0.26), (0.06, 0.38), (0.0, 0.42)], M['oro'], COLL, segs=20)
ogiva.rotation_euler = (0, math.pi / 2, 0)
ogiva.location = (3.5, 0, 0.05)
blades = []
for k in range(3):
    a = 2 * math.pi * k / 3
    v, f = [], []
    for j, (r, c, tw) in enumerate(((0.15, 0.16, 0.6), (0.6, 0.18, 0.35), (1.0, 0.1, 0.15))):
        for (u, w) in ((-c / 2, -0.015), (c / 2, -0.015), (c / 2, 0.015), (-c / 2, 0.015)):
            y = r * math.cos(a) - (u * math.cos(tw)) * math.sin(a)
            z = r * math.sin(a) + (u * math.cos(tw)) * math.cos(a)
            x = u * math.sin(tw) + w
            v.append((x, y, z))
    for j in range(2):
        for i in range(4):
            a0, a1 = j * 4 + i, j * 4 + (i + 1) % 4
            f.append((a0, a1, a1 + 4, a0 + 4))
    f += [(3, 2, 1, 0), (8, 9, 10, 11)]
    blades.append(lib.mesh_obj(f'Pala{k}', v, f, M['elica'], COLL, smooth=False, uv_scale=None))
elica = lib.join(blades, 'Elica')
elica.location = (3.62, 0, 0.05)

# ugello del fumo in coda
lib.tube_path('UgelloFumo', [(-3.4, 0, 0.2), (-3.75, 0, 0.2)], 0.03, M['nero'], COLL)

# unione delle parti fisse (l'elica resta separata)
fixed = [o for o in COLL.objects if o.type == 'MESH' and o.name != 'Elica']
body = lib.join(fixed, 'Aereo')
elica.parent = body

out = os.path.join(ROOT, 'public', 'models', 'aereo.glb')
bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', export_apply=True, export_yup=True, export_lights=False,
                          export_cameras=False)
print('aereo', out, f'{os.path.getsize(out) / 1e3:.0f} KB', 'facce', sum(len(o.data.polygons) for o in COLL.objects if o.type == 'MESH'))

if '--render' in sys.argv:
    from materials import kelvin
    from mathutils import Vector
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
    cam.location = (5.5, -7.5, 2.8)
    cam.rotation_euler = (Vector((0, 0, 0)) - Vector(cam.location)).to_track_quat('-Z', 'Y').to_euler()
    scene.collection.objects.link(cam)
    scene.camera = cam
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
    sun.data.energy = 3
    sun.data.color = kelvin(3200)
    sun.rotation_euler = (0.9, 0.2, 0.8)
    scene.collection.objects.link(sun)
    w = bpy.data.worlds.new('w')
    scene.world = w
    w.use_nodes = True
    w.node_tree.nodes['Background'].inputs[0].default_value = (0.45, 0.58, 0.8, 1)
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 32
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = 900, 600
    scene.render.filepath = os.path.join(ROOT, 'pipeline', 'cache', 'renders', 'aereo.png')
    bpy.ops.render.render(write_still=True)
    print('render', scene.render.filepath)
