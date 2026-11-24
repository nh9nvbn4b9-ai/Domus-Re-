"""Primitive di modellazione architettonica per Blender (bpy), senza operatori UI.

Convenzioni: Z in alto, facciata sul piano y = 0 rivolta verso -Y (la strada).
Le profondità "d" sono misurate verso la strada (y = -d). Unità: metri.
Tutte le mesh generate sono solidi chiusi con normali ricalcolate.
"""
import math
import bpy
import bmesh
from mathutils import Vector

# ---------------------------------------------------------------------------
# Scena / collezioni
# ---------------------------------------------------------------------------

def collection(name, parent=None):
    coll = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    parent = parent or bpy.context.scene.collection
    if coll.name not in parent.children:
        parent.children.link(coll)
    return coll


def _finish(me, smooth=False, sharp_deg=None, uv_scale=None):
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    if smooth:
        me.shade_smooth()
        if sharp_deg is not None:
            me.set_sharp_from_angle(angle=math.radians(sharp_deg))
    else:
        me.shade_flat()
    if uv_scale:
        cube_uv(me, uv_scale)
    me.update()
    return me


def mesh_obj(name, verts, faces, mat, coll, smooth=False, sharp_deg=None, uv_scale=1.0, location=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.validate()
    _finish(me, smooth, sharp_deg, uv_scale)
    if mat:
        me.materials.append(mat)
    obj = bpy.data.objects.new(name, me)
    if location:
        obj.location = location
    coll.objects.link(obj)
    return obj


def instance(src, name, coll, location=(0, 0, 0), rotation=(0, 0, 0), scale=(1, 1, 1)):
    """Duplicato collegato (stessa mesh): esportato in glTF come geometria condivisa."""
    obj = bpy.data.objects.new(name, src.data)
    obj.location, obj.rotation_euler, obj.scale = location, rotation, scale
    coll.objects.link(obj)
    return obj


def cube_uv(me, scale=1.0):
    """Proiezione UV a cubo in coordinate oggetto (metri / scale): tessiture continue sulla pietra."""
    uv = me.uv_layers.get('UVMap') or me.uv_layers.new(name='UVMap')
    for poly in me.polygons:
        n = poly.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            if ax == 0:
                u, v = co.y * (1 if n.x > 0 else -1), co.z
            elif ax == 1:
                u, v = co.x * (-1 if n.y > 0 else 1), co.z
            else:
                u, v = co.x, co.y * (1 if n.z > 0 else -1)
            uv.data[li].uv = (u / scale, v / scale)


def apply_modifiers(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    new = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
    old = obj.data
    obj.modifiers.clear()
    obj.data = new
    if old.users == 0:
        bpy.data.meshes.remove(old)
    return obj


def bevel(obj, width, segments=1, angle=40):
    m = obj.modifiers.new('bevel', 'BEVEL')
    m.width, m.segments, m.limit_method = width, segments, 'ANGLE'
    m.angle_limit = math.radians(angle)
    m.harden_normals = False
    return m


def boolean_cut(obj, cutters, solver='EXACT'):
    for c in cutters:
        m = obj.modifiers.new('cut', 'BOOLEAN')
        m.operation, m.object, m.solver = 'DIFFERENCE', c, solver
    apply_modifiers(obj)
    for c in cutters:
        bpy.data.objects.remove(c, do_unlink=True)
    return obj


def join(objs, name):
    """Unisce oggetti (con modifiers applicati) in un'unica mesh, preservando i materiali."""
    dg = bpy.context.evaluated_depsgraph_get()
    bm = bmesh.new()
    mats, mat_index = [], {}
    for o in objs:
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
        me.transform(o.matrix_world)
        remap = []
        for m in me.materials:
            if m is None:
                remap.append(0)
                continue
            if m.name not in mat_index:
                mat_index[m.name] = len(mats)
                mats.append(m)
            remap.append(mat_index[m.name])
        for p in me.polygons:
            p.material_index = remap[p.material_index] if remap else 0
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    coll = objs[0].users_collection[0]
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)
    out = bpy.data.meshes.new(name)
    bm.to_mesh(out)
    bm.free()
    for m in mats:
        out.materials.append(m)
    obj = bpy.data.objects.new(name, out)
    coll.objects.link(obj)
    return obj


# ---------------------------------------------------------------------------
# Solidi elementari
# ---------------------------------------------------------------------------

def box(name, x0, x1, y0, y1, z0, z1, mat, coll, bev=0.0, bev_seg=1, uv_scale=1.0):
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    o = mesh_obj(name, v, f, mat, coll, uv_scale=uv_scale)
    if bev > 0:
        bevel(o, bev, bev_seg)
    return o


def prism_xz(name, poly_xz, y0, y1, mat, coll, uv_scale=1.0, smooth=False):
    """Estrude un poligono definito nel piano XZ (facciata) tra y0 e y1."""
    n = len(poly_xz)
    v = [(x, y0, z) for x, z in poly_xz] + [(x, y1, z) for x, z in poly_xz]
    f = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
    f += [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    return mesh_obj(name, v, f, mat, coll, smooth=smooth, sharp_deg=35, uv_scale=uv_scale)


def arch_poly(cx, z_bottom, width, z_spring, segs=40, rise=None):
    """Contorno (XZ) di un'apertura rettangolare con arco a tutto sesto (o ribassato con rise)."""
    r = width / 2
    pts = [(cx - r, z_bottom), (cx + r, z_bottom), (cx + r, z_spring)]
    rr = rise if rise is not None else r
    for i in range(1, segs):
        t = math.pi * i / segs
        pts.append((cx + r * math.cos(t), z_spring + rr * math.sin(t)))
    pts.append((cx - r, z_spring))
    return pts


def lathe(name, profile_rz, mat, coll, segs=32, smooth=True, uv_scale=0.5):
    """Solido di rivoluzione attorno a Z. profile_rz: [(r, z)] dal basso all'alto."""
    v, f = [], []
    prof = list(profile_rz)
    if prof[0][0] > 0:
        prof.insert(0, (0.0, prof[0][1]))
    if prof[-1][0] > 0:
        prof.append((0.0, prof[-1][1]))
    rows = len(prof)
    for s in range(segs):
        a = 2 * math.pi * s / segs
        ca, sa = math.cos(a), math.sin(a)
        for r, z in prof:
            v.append((r * ca, r * sa, z))
    for s in range(segs):
        s2 = (s + 1) % segs
        for j in range(rows - 1):
            a, b = s * rows + j, s2 * rows + j
            f.append((a, b, b + 1, a + 1))
    return mesh_obj(name, v, f, mat, coll, smooth=smooth, sharp_deg=50, uv_scale=uv_scale)


def fluted_shaft(name, radius, height, mat, coll, flutes=24, depth=None, entasis=0.06, rings=8, engaged=True):
    """Fusto scanalato (scanalature concave separate da listelli), con lieve entasi."""
    depth = depth or radius * 0.09
    per = 8
    n = flutes * per
    v, f = [], []
    for k in range(rings + 1):
        t = k / rings
        z = height * t
        rk = radius * (1 - entasis * max(0.0, t - 0.33) / 0.67)
        for i in range(n):
            a = 2 * math.pi * i / n
            fr = (i % per) / per  # posizione nella scanalatura
            if fr < 0.18:
                r = rk
            else:
                u = (fr - 0.18) / 0.82
                r = rk - depth * (rk / radius) * math.sin(math.pi * u)
            v.append((r * math.cos(a), r * math.sin(a), z))
    for k in range(rings):
        for i in range(n):
            i2 = (i + 1) % n
            f.append((k * n + i, k * n + i2, (k + 1) * n + i2, (k + 1) * n + i))
    v += [(0, 0, 0), (0, 0, height)]
    c0, c1 = len(v) - 2, len(v) - 1
    for i in range(n):
        i2 = (i + 1) % n
        f.append((c0, i2, i))
        f.append((c1, rings * n + i, rings * n + i2))
    return mesh_obj(name, v, f, mat, coll, smooth=True, sharp_deg=28, uv_scale=0.6)


def fluted_pilaster(name, width, height, proj, mat, coll, flutes=7):
    """Lesena scanalata: blocco rettangolare con scanalature verticali sul fronte (y = -proj)."""
    per = 8
    fw = width * 0.86 / flutes
    margin = width * 0.07
    xs, ds = [-width / 2, -width / 2 + margin], [0.0, 0.0]
    for k in range(flutes):
        x0 = -width / 2 + margin + k * fw
        for i in range(1, per + 1):
            u = i / per
            xs.append(x0 + fw * u)
            fillet = 0.16
            ds.append(0.0 if (u < fillet or u > 1 - 1e-6) else fw * 0.32 * math.sin(math.pi * (u - fillet) / (1 - fillet)))
    xs.append(width / 2)
    ds.append(0.0)
    m = len(xs)
    v = []
    for z in (0.0, height):
        for x, d in zip(xs, ds):
            v.append((x, -proj + d, z))
    for z in (0.0, height):
        v += [(width / 2, 0.02, z), (-width / 2, 0.02, z)]
    f = []
    for i in range(m - 1):
        f.append((i, i + 1, m + i + 1, m + i))
    b0, b1 = 2 * m, 2 * m + 2
    f.append((m - 1, b0, b1, 2 * m - 1))
    f.append((b0 + 1, 0, m, b1 + 1))
    f.append((b0, b0 + 1, b1 + 1, b1))
    f.append(tuple([b0 + 1, b0] + list(range(m - 1, -1, -1))))
    f.append(tuple(list(range(m, 2 * m)) + [b1, b1 + 1]))
    return mesh_obj(name, v, f, mat, coll, smooth=True, sharp_deg=30, uv_scale=0.6)


# ---------------------------------------------------------------------------
# Modanature (sweep di profili)
# ---------------------------------------------------------------------------

def sweep_h(name, path_xy, z, profile, mat, coll, uv_scale=1.0):
    """Modanatura orizzontale lungo una polilinea XY (con giunti a 45° esatti).

    profile: [(d, h)] — d = sporgenza verso l'esterno, h = quota relativa a z.
    Il profilo deve partire dal muro in basso (0, h0) e finire al muro in alto (0, h1):
    viene chiuso automaticamente sul muro. L'esterno è a destra del verso di percorrenza.
    """
    pts = [Vector((p[0], p[1])) for p in path_xy]
    segs = [(pts[i + 1] - pts[i]).normalized() for i in range(len(pts) - 1)]
    normals = [Vector((s.y, -s.x)) for s in segs]
    miters = []
    for i in range(len(pts)):
        if i == 0:
            m = normals[0]
        elif i == len(pts) - 1:
            m = normals[-1]
        else:
            n1, n2 = normals[i - 1], normals[i]
            m = (n1 + n2) / (1 + n1.dot(n2))
        miters.append(m)
    prof = list(profile)
    np_ = len(prof)
    v = []
    for p, m in zip(pts, miters):
        for d, h in prof:
            v.append((p.x + m.x * d, p.y + m.y * d, z + h))
    f = []
    for i in range(len(pts) - 1):
        for j in range(np_):
            j2 = (j + 1) % np_
            f.append((i * np_ + j, (i + 1) * np_ + j, (i + 1) * np_ + j2, i * np_ + j2))
    last = (len(pts) - 1) * np_
    f.append(tuple(range(np_ - 1, -1, -1)))
    f.append(tuple(range(last, last + np_)))
    return mesh_obj(name, v, f, mat, coll, smooth=True, sharp_deg=32, uv_scale=uv_scale)


def sweep_arc(name, cx, cz, radius, profile, mat, coll, a0=0.0, a1=math.pi, segs=48, y0=0.0, uv_scale=1.0, extend=0.0):
    """Archivolto: profilo [(r_off, d)] estruso lungo un arco nel piano XZ di centro (cx, cz).

    r_off = scostamento radiale rispetto a radius; d = sporgenza verso la strada.
    Il profilo è chiuso sul muro (d = 0). extend prolunga i piedritti verso il basso.
    """
    prof = list(profile)
    np_ = len(prof)
    path = []
    if extend > 0:
        path.append((a0, -extend))
    for i in range(segs + 1):
        path.append((a0 + (a1 - a0) * i / segs, 0.0))
    if extend > 0:
        path.append((a1, -extend))
    v = []
    for a, dz in path:
        ca, sa = math.cos(a), math.sin(a)
        for r, d in prof:
            rr = radius + r
            v.append((cx + rr * ca, y0 - d, cz + rr * sa + dz))
    f = []
    rows = len(path)
    for i in range(rows - 1):
        for j in range(np_):
            j2 = (j + 1) % np_
            f.append((i * np_ + j, (i + 1) * np_ + j, (i + 1) * np_ + j2, i * np_ + j2))
    last = (rows - 1) * np_
    f.append(tuple(range(np_ - 1, -1, -1)))
    f.append(tuple(range(last, last + np_)))
    return mesh_obj(name, v, f, mat, coll, smooth=True, sharp_deg=32, uv_scale=uv_scale)


def frame_rect(name, x0, x1, z0, z1, profile, mat, coll, y0=0.0, uv_scale=1.0):
    """Cornice (chambranle) attorno a un'apertura rettangolare: sweep chiuso con angoli a 45°."""
    # Percorso in senso orario visto dalla strada -> esterno del riquadro a destra del verso.
    path = [(x0, z0), (x0, z1), (x1, z1), (x1, z0)]
    pts = [Vector(p) for p in path]
    n = len(pts)
    segs = [(pts[(i + 1) % n] - pts[i]).normalized() for i in range(n)]
    normals = [Vector((-s.y, s.x)) for s in segs]  # normali rivolte verso l'esterno dell'apertura
    v = []
    prof = list(profile)
    np_ = len(prof)
    for i in range(n):
        n1, n2 = normals[i - 1], normals[i]
        m = (n1 + n2) / (1 + n1.dot(n2))
        for r, d in prof:  # r = distanza dal filo dell'apertura verso l'esterno (profilo chiuso)
            p = pts[i] + m * r
            v.append((p.x, y0 - d, p.y))
    f = []
    for i in range(n):
        i2 = (i + 1) % n
        for j in range(np_):
            j2 = (j + 1) % np_
            f.append((i * np_ + j, i2 * np_ + j, i2 * np_ + j2, i * np_ + j2))
    return mesh_obj(name, v, f, mat, coll, smooth=True, sharp_deg=32, uv_scale=uv_scale)


# ---------------------------------------------------------------------------
# Elementi decorativi
# ---------------------------------------------------------------------------

def spiral_band(name, a, b, turns, width_ratio, thickness, mat, coll, steps=160):
    """Voluta ionica: nastro a spirale logaritmica nel piano XZ, spessore lungo Y."""
    outer, inner = [], []
    for i in range(steps + 1):
        t = turns * 2 * math.pi * i / steps
        r = a * math.exp(-b * t)
        w = r * width_ratio
        outer.append((r * math.cos(t), r * math.sin(t)))
        inner.append(((r - w) * math.cos(t), (r - w) * math.sin(t)))
    poly = outer + inner[::-1]
    n = len(poly)
    v = [(x, -thickness / 2, z) for x, z in poly] + [(x, thickness / 2, z) for x, z in poly]
    f = []
    for i in range(steps):
        # facce frontali/posteriori come strisce di quad (evita n-gon concavi)
        o0, o1, i0, i1 = i, i + 1, n - 1 - i, n - 2 - i
        f.append((o0, o1, i1, i0))
        f.append((n + i0, n + i1, n + o1, n + o0))
    for i in range(n):
        i2 = (i + 1) % n
        f.append((i, n + i, n + i2, i2))
    return mesh_obj(name, v, f, mat, coll, smooth=True, sharp_deg=40, uv_scale=0.4)


def baluster_profile(h):
    """Profilo di balaustro a vaso (r, z) per altezza h."""
    k = h / 0.62
    p = [
        (0.060, 0.000), (0.060, 0.030), (0.052, 0.036), (0.050, 0.050), (0.040, 0.060),
        (0.034, 0.075), (0.040, 0.095), (0.055, 0.140), (0.066, 0.200), (0.068, 0.240),
        (0.060, 0.290), (0.044, 0.350), (0.030, 0.420), (0.026, 0.450), (0.032, 0.470),
        (0.040, 0.480), (0.032, 0.492), (0.030, 0.520), (0.044, 0.540), (0.052, 0.560),
        (0.056, 0.580), (0.056, 0.600), (0.060, 0.605), (0.060, 0.620),
    ]
    return [(r * k, z * k) for r, z in p]


def tube_path(name, pts, radius, mat, coll, segs=6, closed=False):
    """Tubo a sezione circolare lungo una polilinea 3D (ferro battuto)."""
    P = [Vector(p) for p in pts]
    n = len(P)
    v, f = [], []
    up_ref = Vector((0, 1, 0))
    for i in range(n):
        if closed:
            t = (P[(i + 1) % n] - P[i - 1]).normalized()
        else:
            t = (P[min(i + 1, n - 1)] - P[max(i - 1, 0)]).normalized()
        a = t.cross(up_ref)
        if a.length < 1e-4:
            a = t.cross(Vector((1, 0, 0)))
        a.normalize()
        b = t.cross(a).normalized()
        for s in range(segs):
            ang = 2 * math.pi * s / segs
            v.append(tuple(P[i] + (a * math.cos(ang) + b * math.sin(ang)) * radius))
    rings = n if closed else n - 1
    for i in range(rings):
        i2 = (i + 1) % n
        for s in range(segs):
            s2 = (s + 1) % segs
            f.append((i * segs + s, i * segs + s2, i2 * segs + s2, i2 * segs + s))
    if not closed:
        f.append(tuple(range(segs - 1, -1, -1)))
        f.append(tuple(range((n - 1) * segs, n * segs)))
    return mesh_obj(name, v, f, mat, coll, smooth=True, sharp_deg=70, uv_scale=None)


def scroll_pts(cx, cz, r0, turns=1.6, steps=40, flip=1, y=0.0, start=0.0):
    """Punti di una voluta (spirale) in ferro battuto nel piano XZ."""
    pts = []
    for i in range(steps + 1):
        t = start + turns * 2 * math.pi * i / steps
        r = r0 * math.exp(-0.18 * (t - start))
        pts.append((cx + flip * r * math.cos(t), y, cz + r * math.sin(t)))
    return pts
