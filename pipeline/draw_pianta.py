"""Pianta 2D quotata dell'appartamento dimostrativo, generata dalla stessa specifica del modello 3D.

Uso: python3 pipeline/draw_pianta.py  ->  public/images/pianta-appartamento.png
"""
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'blender'))
import palazzo_spec as P  # noqa: E402

S = 95                      # pixel per metro
ML, MR, MT, MB = 190, 230, 250, 230
X_MIN, X_MAX = -P.HALF_W, P.HALF_W
Y_MIN, Y_MAX = -1.25, P.DEPTH
W = int(ML + MR + (X_MAX - X_MIN) * S)
H = int(MT + MB + (Y_MAX - Y_MIN) * S)

INK = (32, 28, 22)
GOLD = (168, 128, 42)
WALL = (40, 36, 30)
FLOOR = {'parquet': (238, 226, 205), 'marmo': (232, 232, 228)}
FONT_DIR = '/usr/share/fonts/truetype/dejavu'
F = lambda n, s: ImageFont.truetype(os.path.join(FONT_DIR, n), s)  # noqa: E731
f_title, f_room, f_small, f_tiny = F('DejaVuSerif.ttf', 38), F('DejaVuSerif.ttf', 23), F('DejaVuSans.ttf', 17), F('DejaVuSans.ttf', 14)

im = Image.new('RGB', (W, H), (250, 248, 243))
d = ImageDraw.Draw(im)


def px(x, y):
    return ML + (x - X_MIN) * S, MT + (Y_MAX - y) * S


def rect(x0, x1, y0, y1, **kw):
    a, b = px(x0, y1), px(x1, y0)
    d.rectangle([a, b], **kw)


def rot_pts(cx, cy, pts, deg):
    a = math.radians(deg)
    return [px(cx + x * math.cos(a) - y * math.sin(a), cy + x * math.sin(a) + y * math.cos(a)) for x, y in pts]


# ------------------------------------------------------------------ pavimenti e stanze
for name, x0, x1, y0, y1, fl in P.APT_ROOMS:
    rect(x0, x1, y0, y1, fill=FLOOR[fl])
_, cx0, cx1, cy0, cy1 = P.APT_CORE
rect(cx0, cx1, cy0, cy1, fill=(226, 223, 216))
# tratteggio delle parti comuni, ritagliato sul vano scala
hatch = Image.new('L', im.size, 0)
hd_ = ImageDraw.Draw(hatch)
for k in range(-40, 60):
    x = cx0 + k * 0.25
    hd_.line([px(x, cy0), px(x + (cy1 - cy0), cy1)], fill=255, width=1)
mask = Image.new('L', im.size, 0)
ImageDraw.Draw(mask).rectangle([px(cx0, cy1), px(cx1, cy0)], fill=255)
from PIL import ImageChops  # noqa: E402
im.paste((196, 192, 184), (0, 0), ImageChops.multiply(hatch, mask))
d = ImageDraw.Draw(im)
_, bx0, bx1, by0, by1 = P.APT_BALCONY
rect(bx0, bx1, by0, by1, fill=(232, 226, 214))

# ------------------------------------------------------------------ arredi (contorni)
OUT = (120, 108, 92)
for t, x, y, w, dpt, rot in P.APT_FURNITURE:
    hw, hd = w / 2, dpt / 2
    box = [(-hw, -hd), (hw, -hd), (hw, hd), (-hw, hd)]
    if t in ('pianta', 'vaso_balcone', 'busto', 'tavolino_balcone', 'sgabello'):
        r = min(w, dpt) / 2 * S
        c = px(x, y)
        d.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], outline=OUT, width=2)
        if t == 'pianta':
            d.ellipse([c[0] - r * 0.5, c[1] - r * 0.5, c[0] + r * 0.5, c[1] + r * 0.5], outline=OUT, width=1)
        continue
    if t == 'tappeto':
        d.polygon(rot_pts(x, y, box, rot), outline=(196, 180, 150), width=2)
        inner = [(-hw + 0.12, -hd + 0.12), (hw - 0.12, -hd + 0.12), (hw - 0.12, hd - 0.12), (-hw + 0.12, hd - 0.12)]
        d.polygon(rot_pts(x, y, inner, rot), outline=(214, 200, 172), width=1)
        continue
    d.polygon(rot_pts(x, y, box, rot), outline=OUT, width=2, fill=(250, 247, 240) if t != 'camino' else (224, 220, 212))
    if t in ('divano', 'poltrona', 'poltrona_lettura'):  # schienale e braccioli
        d.polygon(rot_pts(x, y, [(-hw, hd - 0.2), (hw, hd - 0.2), (hw, hd), (-hw, hd)], rot), fill=(226, 216, 198), outline=OUT)
        for s_ in (-1, 1):
            d.polygon(rot_pts(x, y, [(s_ * hw - (0.16 if s_ > 0 else 0), -hd), (s_ * hw + (0.16 if s_ < 0 else 0), -hd),
                                     (s_ * hw + (0.16 if s_ < 0 else 0), hd), (s_ * hw - (0.16 if s_ > 0 else 0), hd)], rot), outline=OUT)
    elif t == 'letto':
        d.polygon(rot_pts(x, y, [(-hw, hd - 0.12), (hw, hd - 0.12), (hw, hd), (-hw, hd)], rot), fill=(214, 204, 186), outline=OUT)
        for s_ in (-1, 1):
            q = [(s_ * hw * 0.5 - 0.32, hd - 0.55), (s_ * hw * 0.5 + 0.32, hd - 0.55), (s_ * hw * 0.5 + 0.32, hd - 0.2),
                 (s_ * hw * 0.5 - 0.32, hd - 0.2)]
            d.polygon(rot_pts(x, y, q, rot), outline=OUT)
        d.line(rot_pts(x, y, [(-hw, hd - 0.75), (hw, hd - 0.75)], rot), fill=OUT, width=1)
    elif t == 'tavolo':
        for k in (-0.7, 0.0, 0.7):
            for s_ in (-1, 1):
                c = rot_pts(x, y, [(k, s_ * (hd + 0.28))], rot)[0]
                d.rectangle([c[0] - 0.22 * S, c[1] - 0.22 * S, c[0] + 0.22 * S, c[1] + 0.22 * S], outline=OUT, width=1)
    elif t == 'vasca':
        pa, pb = rot_pts(x, y, [(-hw + 0.08, -hd + 0.1), (hw - 0.08, hd - 0.1)], rot)
        d.ellipse([min(pa[0], pb[0]), min(pa[1], pb[1]), max(pa[0], pb[0]), max(pa[1], pb[1])], outline=OUT, width=1)
    elif t == 'doccia':
        d.line(rot_pts(x, y, [(-hw, -hd), (hw, hd)], rot), fill=OUT, width=1)
        d.line(rot_pts(x, y, [(-hw, hd), (hw, -hd)], rot), fill=OUT, width=1)
    elif t in ('wc', 'bidet', 'lavabo'):
        c = rot_pts(x, y, [(0, -0.05)], rot)[0]
        r = 0.15 * S
        d.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], outline=OUT, width=1)
    elif t == 'lavabo_doppio':
        for k in (-0.4, 0.4):
            c = rot_pts(x, y, [(k, 0)], rot)[0]
            d.ellipse([c[0] - 0.16 * S, c[1] - 0.12 * S, c[0] + 0.16 * S, c[1] + 0.12 * S], outline=OUT, width=1)
    elif t == 'armadio':
        n = max(2, round(w / 0.6))
        for k in range(1, n):
            xx = -hw + w * k / n
            d.line(rot_pts(x, y, [(xx, -hd), (xx, hd)], rot), fill=OUT, width=1)
        d.line(rot_pts(x, y, [(-hw, -hd), (hw, hd)], rot), fill=(200, 190, 175), width=1)

# ------------------------------------------------------------------ muri perimetrali
HW = P.HALF_W
rect(X_MIN, X_MAX, 0.0, P.WALL_T, fill=WALL)                      # facciata
rect(X_MIN, X_MIN + 0.5, P.WALL_T, P.DEPTH, fill=WALL)             # lato ovest
rect(X_MAX - 0.5, X_MAX, P.WALL_T, P.DEPTH, fill=WALL)             # lato est
rect(X_MIN, X_MAX, P.DEPTH - 0.5, P.DEPTH, fill=WALL)              # retro
for wdw in P.APT_WINDOWS:
    x0, x1 = wdw['x'] - wdw['w'] / 2, wdw['x'] + wdw['w'] / 2
    y0, y1 = (0.0, P.WALL_T) if wdw['wall'] == 'facciata' else (P.DEPTH - 0.5, P.DEPTH)
    rect(x0, x1, y0, y1, fill=(250, 248, 243))
    for yy in ((y0 + y1) / 2 - 0.05, (y0 + y1) / 2 + 0.05):
        d.line([px(x0, yy), px(x1, yy)], fill=INK, width=2)
    d.line([px(x0, y0), px(x0, y1)], fill=INK, width=2)
    d.line([px(x1, y0), px(x1, y1)], fill=INK, width=2)
# balaustra del balcone
for seg in ((bx0, by0, bx1, by0), (bx0, by0, bx0, 0.0), (bx1, by0, bx1, 0.0)):
    a, b = px(seg[0], seg[1]), px(seg[2], seg[3])
    d.line([a, b], fill=INK, width=6)

# ------------------------------------------------------------------ tramezzi e porte
for wl in P.APT_WALLS:
    x0, x1, y0, y1 = wl['r']
    horiz = (x1 - x0) > (y1 - y0)
    segs = [(x0, x1)] if horiz else [(y0, y1)]
    for a0, a1 in sorted(wl['doors']):
        new = []
        for s0, s1 in segs:
            if a0 >= s1 or a1 <= s0:
                new.append((s0, s1))
            else:
                if a0 > s0:
                    new.append((s0, a0))
                if a1 < s1:
                    new.append((a1, s1))
        segs = new
    for s0, s1 in segs:
        if horiz:
            rect(s0, s1, y0, y1, fill=WALL)
        else:
            rect(x0, x1, s0, s1, fill=WALL)
    for a0, a1 in wl['doors']:
        wdt = a1 - a0
        if horiz:
            leaves = [(a0, wdt / 2, 1), (a1, wdt / 2, -1)] if wdt > 1.2 else [(a0, wdt, 1)]
            for hx, lw, sgn in leaves:
                hinge = px(hx, y0)
                r = lw * S
                d.line([hinge, (hinge[0], hinge[1] + r)], fill=INK, width=2)
                start, end = (0, 90) if sgn > 0 else (90, 180)
                d.arc([hinge[0] - r, hinge[1] - r, hinge[0] + r, hinge[1] + r], start, end, fill=(150, 140, 125), width=1)
        else:
            hinge = px(x1, a0)
            r = wdt * S
            d.line([hinge, (hinge[0] + r, hinge[1])], fill=INK, width=2)
            d.arc([hinge[0] - r, hinge[1] - r, hinge[0] + r, hinge[1] + r], 270, 360, fill=(150, 140, 125), width=1)

# ------------------------------------------------------------------ etichette
areas = P.apt_areas()
LABEL_POS = {'Disimpegno notte': (2.51, 6.0), 'Disimpegno giorno': (-2.45, 8.4), 'Bagno': (-4.5, 8.75),
             'Salone': (-1.3, 4.6), 'Ingresso': (0.1, 9.0), 'Cucina': (-3.7, 14.6), 'Camera': (3.9, 1.6),
             'Camera padronale': (4.2, 10.3), 'Bagno padronale': (4.4, 8.6)}
for name, x0, x1, y0, y1, _ in P.APT_ROOMS:
    cx, cy = LABEL_POS.get(name, ((x0 + x1) / 2, (y0 + y1) / 2))
    c = px(cx, cy)
    small = name.startswith('Disimpegno')
    label = name.replace('Disimpegno ', 'Disimp.\n') if small else name
    fnt = f_tiny if small else f_room
    d.multiline_text(c, label, fill=INK, font=fnt, anchor='mm', align='center', spacing=2)
    d.text((c[0], c[1] + (26 if small else 24)), f'{areas[name]:.1f} m²'.replace('.', ','), fill=GOLD, font=f_tiny if small else f_small,
           anchor='mm')
c = px((cx0 + cx1) / 2, (cy0 + cy1) / 2)
d.multiline_text(c, 'Vano scala\ne ascensore\n(parti comuni)', fill=(110, 104, 94), font=f_tiny, anchor='mm', align='center')
c = px(0, -0.62)
d.text(c, 'Balcone 4,4 m²', fill=INK, font=f_small, anchor='mm')

# ------------------------------------------------------------------ quote


def dim_h(x0, x1, y, txt, off=0):
    a, b = px(x0, y), px(x1, y)
    yy = a[1] + off
    d.line([(a[0], yy), (b[0], yy)], fill=GOLD, width=2)
    for xx in (a[0], b[0]):
        d.line([(xx, yy - 9), (xx, yy + 9)], fill=GOLD, width=2)
    d.text(((a[0] + b[0]) / 2, yy - 16), txt, fill=GOLD, font=f_small, anchor='mm')


def dim_v(y0, y1, x, txt, off=0):
    a, b = px(x, y0), px(x, y1)
    xx = a[0] + off
    d.line([(xx, a[1]), (xx, b[1])], fill=GOLD, width=2)
    for yy in (a[1], b[1]):
        d.line([(xx - 9, yy), (xx + 9, yy)], fill=GOLD, width=2)
    tmp = Image.new('RGBA', (200, 30), (0, 0, 0, 0))
    ImageDraw.Draw(tmp).text((100, 15), txt, fill=GOLD + (255,), font=f_small, anchor='mm')
    tmp = tmp.rotate(90, expand=True)
    im.paste(tmp, (int(xx + 6), int((a[1] + b[1]) / 2 - 100)), tmp)


fmt = lambda v: f'{v:.2f}'.replace('.', ',')  # noqa: E731
dim_h(X_MIN, X_MAX, Y_MIN, f'{fmt(X_MAX - X_MIN)} m (facciata)', off=70)
dim_h(P.APT_X0, 1.85, Y_MIN, fmt(1.85 - P.APT_X0), off=26)
dim_h(1.97, P.APT_X1, Y_MIN, fmt(P.APT_X1 - 1.97), off=26)
dim_v(0.0, P.DEPTH, X_MAX, f'{fmt(P.DEPTH)} m', off=110)
dim_v(P.APT_Y0, 7.5, X_MAX, fmt(7.5 - P.APT_Y0), off=40)
dim_v(9.52, P.APT_Y1, X_MAX, fmt(P.APT_Y1 - 9.52), off=40)

# ------------------------------------------------------------------ titolo, nord, scala, nota
d.text((ML - 40, 60), 'Appartamento dimostrativo · Piano 3', fill=INK, font=f_title)
d.text((ML - 40, 112), f'Superficie netta {sum(areas.values()):.0f} m² · balcone 4,4 m² · altezza interna '
       f'{fmt(P.APT_CEIL - P.APT_FLOOR)} m'.replace('.', ','), fill=(96, 88, 76), font=f_small)
d.text((ML - 40, 140), 'Ricostruzione immaginaria progettata sulla struttura del palazzo: non è un immobile in vendita.',
       fill=GOLD, font=f_small)
nx, ny = W - 120, 90
d.polygon([(nx, ny - 40), (nx - 16, ny + 12), (nx, ny), (nx + 16, ny + 12)], fill=INK)
d.text((nx, ny + 34), 'N', fill=INK, font=f_room, anchor='mm')
sx, sy = ML - 40, H - 70
for k in range(5):
    d.rectangle([sx + k * S, sy, sx + (k + 1) * S, sy + 10], fill=INK if k % 2 == 0 else (250, 248, 243), outline=INK)
d.text((sx, sy + 26), '0', fill=INK, font=f_tiny, anchor='mm')
d.text((sx + 5 * S, sy + 26), '5 m', fill=INK, font=f_tiny, anchor='mm')
d.text((W / 2, H - 40), 'Strada / facciata principale', fill=(96, 88, 76), font=f_small, anchor='mm')

out = os.path.join(os.path.dirname(__file__), '..', 'public', 'images', 'pianta-appartamento.png')
im.save(out, optimize=True)
print('pianta', os.path.abspath(out), im.size)
