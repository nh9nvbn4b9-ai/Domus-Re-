"""Colosseo (Anfiteatro Flavio) generato da misure reali.

Dimensioni: ellisse esterna 188 x 156 m, altezza 48,5 m; arena 86 x 54 m; 80 campate per anello.
Prospetto esterno: tre ordini di arcate (tuscanico, ionico, corinzio) e attico con lesene, finestrelle
e mensole. Stato attuale: l'anello esterno sopravvive sul lato nord, chiuso dai contrafforti in
laterizio (Stern a est, Valadier a ovest); a sud è visibile il secondo anello. All'interno la cavea è
ridotta ai muri radiali e anulari in laterizio; l'arena mostra gli ipogei, con la piattaforma lignea
ricostruita sul lato est.

Coordinate locali: centro nell'origine, asse maggiore lungo X, nord locale = +Y.
"""
import math
import random

import bpy

A_OUT, B_OUT = 94.0, 78.0          # semiassi esterni
N_BAYS = 80
LEVELS = [  # (quota base, quota imposta archi, quota chiave archi, quota sommità, ordine)
    (0.0, 4.9, 7.2, 10.6),
    (10.6, 16.6, 19.0, 22.4),
    (22.4, 28.1, 30.4, 33.7),
]
ATTIC = (33.7, 48.5)
ARCH_W = 4.2
OUTER_T = 2.4                      # spessore dell'anello esterno


class MeshBuilder:
    """Accumula geometria con slot di materiale e crea un unico oggetto."""

    def __init__(self):
        self.v, self.f, self.mi = [], [], []

    def quad_prism(self, pts_bottom, z0, z1, m):
        """Prisma verticale da un poligono (lista di (x, y)) tra z0 e z1."""
        n = len(pts_bottom)
        b = len(self.v)
        self.v += [(x, y, z0) for x, y in pts_bottom] + [(x, y, z1) for x, y in pts_bottom]
        self.f.append(tuple(range(b + n - 1, b - 1, -1)))
        self.f.append(tuple(range(b + n, b + 2 * n)))
        for i in range(n):
            j = (i + 1) % n
            self.f.append((b + i, b + j, b + n + j, b + n + i))
        self.mi += [m] * (n + 2)

    def solid(self, verts, faces, m):
        b = len(self.v)
        self.v += list(verts)
        self.f += [tuple(b + i for i in fc) for fc in faces]
        self.mi += [m] * len(faces)

    def build(self, name, mats, coll, uv_scale=2.0, smooth=False):
        import lib
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.v, [], self.f)
        me.validate()
        for m in mats:
            me.materials.append(m)
        for p, mi in zip(me.polygons, self.mi):
            p.material_index = mi
        lib._finish(me, smooth=smooth, sharp_deg=40, uv_scale=uv_scale)
        o = bpy.data.objects.new(name, me)
        coll.objects.link(o)
        return o


class Ellipse:
    """Ellisse campionata per lunghezza d'arco: mappa (s, v) -> punto (v = offset lungo la normale esterna)."""

    def __init__(self, a, b, n=4000):
        self.a, self.b = a, b
        ts = [2 * math.pi * i / n for i in range(n + 1)]
        pts = [(a * math.cos(t), b * math.sin(t)) for t in ts]
        self.cum = [0.0]
        for i in range(1, len(pts)):
            self.cum.append(self.cum[-1] + math.dist(pts[i], pts[i - 1]))
        self.L = self.cum[-1]
        self.ts = ts

    def t_at(self, s):
        s = s % self.L
        lo, hi = 0, len(self.cum) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if self.cum[mid] <= s:
                lo = mid
            else:
                hi = mid
        k = (s - self.cum[lo]) / max(1e-9, self.cum[hi] - self.cum[lo])
        return self.ts[lo] + (self.ts[hi] - self.ts[lo]) * k

    def map(self, s, v):
        t = self.t_at(s)
        x, y = self.a * math.cos(t), self.b * math.sin(t)
        nx, ny = self.b * math.cos(t), self.a * math.sin(t)
        ln = math.hypot(nx, ny)
        return x + nx / ln * v, y + ny / ln * v

    def angle_of(self, s):
        return self.t_at(s)


def curved_box(mb, E, s0, s1, v0, v1, z0, z1, m, segs=1):
    """Blocco che segue l'ellisse tra le ascisse s0..s1 e gli offset v0..v1."""
    ss = [s0 + (s1 - s0) * k / segs for k in range(segs + 1)]
    outer = [E.map(s, v1) for s in ss]
    inner = [E.map(s, v0) for s in reversed(ss)]
    mb.quad_prism(outer + inner, z0, z1, m)


def spandrel(mb, E, sc, half, v0, v1, z_spring, z_top, m, segs=10):
    """Parete sopra un arco a tutto sesto (pennacchi) seguendo l'ellisse."""
    r = half
    prof = [(-r, z_spring)]
    for i in range(1, segs):
        a = math.pi - math.pi * i / segs
        prof.append((r * math.cos(a), z_spring + r * math.sin(a)))
    prof += [(r, z_spring), (r, z_top), (-r, z_top)]
    n = len(prof)
    verts = [(*E.map(sc + u, v1), z) for u, z in prof] + [(*E.map(sc + u, v0), z) for u, z in prof]
    faces = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
    faces += [(i, n + i, n + (i + 1) % n, (i + 1) % n) for i in range(n)]
    mb.solid(verts, faces, m)


def half_column(mb, E, sc, v_wall, r, z0, z1, m, segs=10):
    """Semicolonna addossata (lato esterno)."""
    pts = []
    for k in range(segs + 1):
        a = math.pi * k / segs
        pts.append((sc + r * math.cos(a), v_wall + r * math.sin(a)))
    pts.append((sc - r, v_wall - 0.2))
    pts.append((sc + r, v_wall - 0.2))
    mp = [E.map(s, v) for s, v in pts]
    mb.quad_prism(mp[:segs + 1] + [mp[-2], mp[-1]], z0, z1, m)


def build(coll, MAT, location=(0, 0, 0), rot_z=0.0, seed=7):
    """Costruisce il Colosseo e restituisce l'oggetto (materiali: travertino, laterizio, legno, terra)."""
    rnd = random.Random(seed)
    mats = [MAT['travertino'], MAT['laterizio'], MAT['legno'], MAT['terra']]
    TRAV, BRICK, WOOD, DIRT = 0, 1, 2, 3
    mb = MeshBuilder()
    E = Ellipse(A_OUT, B_OUT)
    bay = E.L / N_BAYS
    vo0, vo1 = -OUTER_T, 0.0

    def surviving(i):
        """Anello esterno conservato sul lato nord (circa 36 campate), con estremità a gradoni."""
        ang = (E.angle_of((i + 0.5) * bay) % (2 * math.pi))
        return 0.38 * math.pi < ang < 1.03 * math.pi

    north = [i for i in range(N_BAYS) if surviving(i)]
    first, last = min(north), max(north)

    # ------------------------------------------------------------------ anello esterno
    for i in range(N_BAYS):
        s0 = i * bay
        sc = s0 + bay / 2
        if i in north:
            top_cut = ATTIC[1]
            if i in (first, last):
                top_cut = LEVELS[2][3]
            mat_ring = TRAV
            for (zb, zsp, zk, zt) in LEVELS:
                if zb >= top_cut:
                    break
                half = ARCH_W / 2
                # piedritti
                curved_box(mb, E, s0, sc - half, vo0, vo1, zb, zsp, mat_ring)
                curved_box(mb, E, sc + half, s0 + bay, vo0, vo1, zb, zsp, mat_ring)
                spandrel(mb, E, sc, half, vo0, vo1, zsp, zt - 1.2, mat_ring)
                # trabeazione sporgente
                curved_box(mb, E, s0, s0 + bay, vo0, vo1 + 0.35, zt - 1.2, zt, mat_ring)
                # semicolonne sui piedritti (ai bordi della campata)
                half_column(mb, E, s0, vo1, 0.45, zb + (1.1 if zb > 0 else 0), zt - 1.2, mat_ring)
                if zb > 0:  # podio dell'ordine
                    curved_box(mb, E, s0, s0 + bay, vo0, vo1 + 0.15, zb, zb + 1.1, mat_ring)
            if top_cut >= ATTIC[1]:
                za, zt = ATTIC
                # attico pieno con finestrelle a campate alterne
                if i % 2 == 0:
                    curved_box(mb, E, s0, sc - 0.9, vo0, vo1, za, zt - 1.4, TRAV)
                    curved_box(mb, E, sc + 0.9, s0 + bay, vo0, vo1, za, zt - 1.4, TRAV)
                    curved_box(mb, E, sc - 0.9, sc + 0.9, vo0, vo1, za, za + 5.6, TRAV)
                    curved_box(mb, E, sc - 0.9, sc + 0.9, vo0, vo1, za + 8.0, zt - 1.4, TRAV)
                else:
                    curved_box(mb, E, s0, s0 + bay, vo0, vo1, za, zt - 1.4, TRAV)
                curved_box(mb, E, s0, s0 + bay, vo0, vo1 + 0.45, zt - 1.4, zt, TRAV)
                curved_box(mb, E, s0 - 0.35, s0 + 0.35, vo1, vo1 + 0.22, za + 1.0, zt - 1.4, TRAV)  # lesena
                for k in (0.25, 0.5, 0.75):  # mensole per i pali del velario
                    curved_box(mb, E, s0 + bay * k - 0.25, s0 + bay * k + 0.25, vo1, vo1 + 0.4, zt - 3.4, zt - 2.6, TRAV)
        # sperone/contrafforte alle estremità del tratto conservato
        if i == first - 1 or i == last + 1:
            steps = 6
            for k in range(steps):
                h = LEVELS[2][3] * (1 - k / steps)
                curved_box(mb, E, s0 + bay * k / steps, s0 + bay * (k + 1) / steps, vo0 - 1.0, vo1 + 1.2 * (1 - k / steps),
                           0.0, h, BRICK)

    # ------------------------------------------------------------------ secondo anello (arcate interne)
    E2 = Ellipse(A_OUT - 6.6, B_OUT - 6.6)
    bay2 = E2.L / N_BAYS
    for i in range(N_BAYS):
        s0 = i * bay2
        sc = s0 + bay2 / 2
        ang = E2.angle_of(sc) % (2 * math.pi)
        is_north = 0.38 * math.pi < ang < 1.03 * math.pi
        top = LEVELS[2][3] + 4.0 if is_north else rnd.uniform(18.5, 24.5)
        for (zb, zsp, zk, zt) in LEVELS:
            if zb >= top:
                break
            zt_eff = min(zt, top)
            half = 1.9
            curved_box(mb, E2, s0, sc - half, -1.8, 0.0, zb, min(zsp, zt_eff), TRAV)
            curved_box(mb, E2, sc + half, s0 + bay2, -1.8, 0.0, zb, min(zsp, zt_eff), TRAV)
            if zt_eff > zsp + 0.5:
                spandrel(mb, E2, sc, half, -1.8, 0.0, zsp, zt_eff, TRAV, segs=8)
        # volta dell'ambulacro tra anello esterno e secondo anello (solaio)
        if is_north:
            for zt in (LEVELS[0][3], LEVELS[1][3]):
                curved_box(mb, E, s0 * (E.L / E2.L), (s0 + bay2) * (E.L / E2.L), -6.6, -OUTER_T, zt - 0.8, zt, TRAV)

    # ------------------------------------------------------------------ anelli interni e muri radiali (laterizio)
    for (da, h_n, h_s, th) in ((13.0, 30.0, 19.0, 1.6), (19.0, 22.0, 15.0, 1.3), (25.0, 15.0, 11.0, 1.1)):
        Ei = Ellipse(A_OUT - da, B_OUT - da)
        bi = Ei.L / N_BAYS
        for i in range(N_BAYS):
            sc = (i + 0.5) * bi
            ang = Ei.angle_of(sc) % (2 * math.pi)
            h = (h_n if 0.38 * math.pi < ang < 1.03 * math.pi else h_s) * rnd.uniform(0.85, 1.0)
            # aperture alterne verso gli ambulacri
            if i % 2:
                curved_box(mb, Ei, i * bi, (i + 1) * bi, -th, 0.0, 0.0, h, BRICK)
            else:
                curved_box(mb, Ei, i * bi, sc - 1.2, -th, 0.0, 0.0, h, BRICK)
                curved_box(mb, Ei, sc + 1.2, (i + 1) * bi, -th, 0.0, 0.0, h, BRICK)
                curved_box(mb, Ei, sc - 1.2, sc + 1.2, -th, 0.0, 4.2, h, BRICK)

    A_POD, B_POD = 47.0, 31.0  # muro del podio attorno all'arena
    for i in range(N_BAYS):
        t = 2 * math.pi * (i + 0.5) / N_BAYS
        # i muri radiali uniscono punti con lo stesso parametro su due ellissi (direzione ~ radiale)
        ao, bo = A_OUT - 13.0, B_OUT - 13.0
        p_out = (ao * math.cos(t), bo * math.sin(t))
        p_in = (A_POD * math.cos(t), B_POD * math.sin(t))
        dx, dy = p_out[0] - p_in[0], p_out[1] - p_in[1]
        ln = math.hypot(dx, dy)
        nx, ny = -dy / ln * 0.55, dx / ln * 0.55
        is_north = 0.38 * math.pi < (t % (2 * math.pi)) < 1.03 * math.pi
        h_out = (24.0 if is_north else 17.0) * rnd.uniform(0.6, 1.0)
        h_in = 4.0 + rnd.uniform(0, 2.0)
        cut = rnd.uniform(0.0, 0.25)  # rovina: parte interna mancante
        q_in = (p_in[0] + dx * cut, p_in[1] + dy * cut)
        h_q = h_in + (h_out - h_in) * cut
        verts = [(q_in[0] - nx, q_in[1] - ny, 0), (p_out[0] - nx, p_out[1] - ny, 0), (p_out[0] + nx, p_out[1] + ny, 0),
                 (q_in[0] + nx, q_in[1] + ny, 0),
                 (q_in[0] - nx, q_in[1] - ny, h_q), (p_out[0] - nx, p_out[1] - ny, h_out), (p_out[0] + nx, p_out[1] + ny, h_out),
                 (q_in[0] + nx, q_in[1] + ny, h_q)]
        mb.solid(verts, [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)], BRICK)
        # masse delle volte della cavea tra i muri radiali (rovina irregolare)
        if rnd.random() < 0.85:
            t2 = 2 * math.pi * (i + 1.0) / N_BAYS
            pb_out = (ao * math.cos(t2), bo * math.sin(t2))
            pb_in = (A_POD * math.cos(t2), B_POD * math.sin(t2))
            k0 = rnd.uniform(0.05, 0.45)
            k1 = rnd.uniform(0.55, 1.0)
            fill = rnd.uniform(0.55, 0.98)

            def lerp(a_, b_, k):
                return (a_[0] + (b_[0] - a_[0]) * k, a_[1] + (b_[1] - a_[1]) * k)
            qa0, qa1 = lerp(p_in, p_out, k0), lerp(p_in, p_out, k1)
            qb0, qb1 = lerp(pb_in, pb_out, k0), lerp(pb_in, pb_out, k1)
            h0 = (h_in + (h_out - h_in) * k0) * fill
            h1 = (h_in + (h_out - h_in) * k1) * fill
            vv = [(*qa0, 0), (*qa1, 0), (*qb1, 0), (*qb0, 0), (*qa0, h0), (*qa1, h1), (*qb1, h1), (*qb0, h0)]
            mb.solid(vv, [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)], BRICK)
        # gradinate superstiti in alcuni settori (lato nord-ovest)
        if is_north and i % 3 == 0:
            t2 = 2 * math.pi * (i + 1.5) / N_BAYS
            pa_out = (ao * math.cos(t2), bo * math.sin(t2))
            pa_in = (A_POD * math.cos(t2), B_POD * math.sin(t2))
            sv = [(p_in[0], p_in[1], h_in), (p_out[0], p_out[1], h_out - 1.5), (pa_out[0], pa_out[1], h_out - 1.5),
                  (pa_in[0], pa_in[1], h_in)]
            sv += [(x, y, z - 0.6) for x, y, z in sv]
            mb.solid(sv, [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)], TRAV)

    # ------------------------------------------------------------------ arena: podio, ipogei, piattaforma
    EP = Ellipse(A_POD, B_POD)
    bp = EP.L / N_BAYS
    for i in range(N_BAYS):
        curved_box(mb, EP, i * bp, (i + 1) * bp, -1.4, 0.0, -6.0, 3.6, BRICK, segs=2)
    A_AR, B_AR = A_POD - 1.4, B_POD - 1.4
    # fondo degli ipogei
    fondo = [(A_AR * math.cos(2 * math.pi * k / 64), B_AR * math.sin(2 * math.pi * k / 64)) for k in range(64)]
    mb.quad_prism(fondo, -6.4, -6.0, DIRT)
    # muri longitudinali degli ipogei (paralleli all'asse maggiore), con corridoio centrale più largo
    for k in range(-8, 9):
        y = k * 2.9 + (1.6 if k > 0 else (-1.6 if k < 0 else 0))
        if k == 0 or abs(y) >= B_AR - 1.0:
            continue
        xmax = A_AR * math.sqrt(max(0.0, 1 - (y / B_AR) ** 2)) - 0.8
        x = -xmax
        while x < xmax:
            seg = min(xmax - x, rnd.uniform(6.0, 14.0))
            h = rnd.uniform(-1.8, -0.4)
            mb.quad_prism([(x, y - 0.45), (x + seg, y - 0.45), (x + seg, y + 0.45), (x, y + 0.45)], -6.0, h, BRICK)
            x += seg + rnd.uniform(0.8, 2.2)
    for xk in range(-38, 39, 7):  # muri trasversali
        ymax = B_AR * math.sqrt(max(0.0, 1 - (xk / A_AR) ** 2)) - 1.0
        if ymax < 3:
            continue
        mb.quad_prism([(xk - 0.4, -ymax), (xk + 0.4, -ymax), (xk + 0.4, ymax), (xk - 0.4, ymax)], -6.0, rnd.uniform(-2.5, -1.0), BRICK)
    # piattaforma lignea ricostruita (lato est dell'arena)
    t0 = math.acos(14.0 / A_AR)
    deck = [(A_AR * math.cos(-t0 + 2 * t0 * k / 24), B_AR * math.sin(-t0 + 2 * t0 * k / 24)) for k in range(25)]
    mb.quad_prism(deck, -0.35, 0.0, WOOD)

    obj = mb.build('Colosseo', mats, coll, uv_scale=2.5)
    obj.location = location
    obj.rotation_euler = (0, 0, rot_z)
    return obj


def arco_costantino(coll, MAT, location, rot_z):
    """Arco di Costantino: 25,9 x 7,4 x 21 m, tre fornici, colonne libere e attico."""
    import lib
    W, D, H = 25.9, 7.4, 21.0
    body = lib.box('ArcoCostantino', -W / 2, W / 2, -D / 2, D / 2, 0.0, 15.2, MAT['marmo'], coll, uv_scale=2.0)
    cuts = [lib.prism_xz('cut', lib.arch_poly(0.0, -0.1, 6.5, 11.5 - 3.25), -5, 5, None, coll, uv_scale=None)]
    for s in (-1, 1):
        cuts.append(lib.prism_xz('cut', lib.arch_poly(s * 8.0, -0.1, 3.4, 7.4 - 1.7), -5, 5, None, coll, uv_scale=None))
    lib.boolean_cut(body, cuts)
    lib.cube_uv(body.data, 2.0)
    parts = [body, lib.box('ArcoAttico', -W / 2, W / 2, -D / 2 + 0.3, D / 2 - 0.3, 15.2, H, MAT['marmo'], coll, bev=0.05, uv_scale=2.0)]
    parts.append(lib.box('ArcoCornice', -W / 2 - 0.4, W / 2 + 0.4, -D / 2 - 0.4, D / 2 + 0.4, 14.6, 15.4, MAT['marmo'], coll, uv_scale=2.0))
    for side in (-1, 1):
        for x in (-11.0, -4.9, 4.9, 11.0):
            c = lib.lathe('ArcoColonna', [(0.45, 0), (0.45, 8.3), (0.55, 8.6), (0.6, 9.2)], MAT['marmo'], coll, segs=16)
            c.location = (x, side * (D / 2 + 0.9), 3.6)
            parts.append(c)
            parts.append(lib.box('ArcoPlinto', x - 0.9, x + 0.9, side * (D / 2 + 0.9) - 0.9, side * (D / 2 + 0.9) + 0.9, 0, 3.6,
                                 MAT['marmo'], coll, uv_scale=2.0))
            parts.append(lib.box('ArcoStatua', x - 0.35, x + 0.35, side * (D / 2 + 0.6) - 0.3, side * (D / 2 + 0.6) + 0.3, 15.4, 18.2,
                                 MAT['marmo'], coll, uv_scale=2.0))
    obj = lib.join(parts, 'ArcoCostantino')
    obj.location = location
    obj.rotation_euler = (0, 0, rot_z)
    return obj
