"""Texture per la Roma attorno al Colosseo.

- tinte calibrate (travertino, laterizio, coppi, prati, asfalto) dalle texture fotografiche Poly Haven;
- facciate degli isolati generate: intonaco fotografico tinto + griglia di finestre con persiane,
  davanzali, colature e alcune finestre accese (mappa emissiva) per l'ora del tramonto.
  Un modulo = 4 campate (3,2 m) x 4 piani (3,4 m) = 12,8 x 13,6 m.
"""
import os
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

C = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')
OUT = os.path.join(C, 'derived')
os.makedirs(OUT, exist_ok=True)
tx = lambda a, f: os.path.join(C, 'textures', a, f)  # noqa: E731


def tint_img(src, color, contrast=0.6, size=None):
    im = Image.open(src).convert('RGB')
    if size:
        im = im.resize(size, Image.LANCZOS)
    a = np.asarray(im).astype(np.float32) / 255.0
    lin = a ** 2.2
    lum = lin @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    rel = (lum / lum.mean()) ** contrast
    target = (np.array(color, np.float32) / 255.0) ** 2.2
    out = np.clip(target[None, None, :] * rel[..., None], 0, 1) ** (1 / 2.2)
    return Image.fromarray((out * 255).astype(np.uint8))


def save(im, name):
    p = os.path.join(OUT, name)
    im.save(p, quality=90)
    print('→', p)


save(tint_img(tx('worn_rock_natural_01', 'worn_rock_natural_01_diff_2k.jpg'), (178, 164, 140), 1.15), 'travertino_diff.jpg')
save(tint_img(tx('medieval_red_brick', 'medieval_red_brick_diff_1k.jpg'), (152, 96, 68), 0.9), 'laterizio_diff.jpg')
save(tint_img(tx('clay_roof_tiles_02', 'clay_roof_tiles_02_diff_1k.jpg'), (168, 88, 58), 0.9), 'coppi_diff.jpg')
save(tint_img(tx('clay_roof_tiles_02', 'clay_roof_tiles_02_diff_1k.jpg'), (142, 92, 70), 0.9), 'coppi_vecchi_diff.jpg')
save(tint_img(tx('leafy_grass', 'leafy_grass_diff_1k.jpg'), (78, 94, 50), 0.8), 'prato_diff.jpg')
save(tint_img(tx('sparse_grass', 'sparse_grass_diff_1k.jpg'), (112, 104, 66), 0.8), 'prato_secco_diff.jpg')
save(tint_img(tx('park_dirt', 'park_dirt_diff_1k.jpg'), (128, 118, 104), 0.8), 'piazza_diff.jpg')
save(tint_img(tx('aerial_asphalt_01', 'aerial_asphalt_01_diff_1k.jpg'), (86, 86, 88), 0.8), 'asfalto_diff.jpg')

# ---------------------------------------------------------------- facciate generate
VARIANTI = {
    'ocra': (200, 150, 92),
    'terracotta': (182, 110, 74),
    'giallo': (214, 176, 108),
    'avorio': (214, 198, 170),
    'rosa': (196, 140, 118),
}
PERSIANE = [(46, 70, 50), (60, 78, 58), (92, 64, 42), (70, 72, 66)]
W, H = 512, 544        # 12,8 x 13,6 m  -> 40 px/m
BAY, FLOOR = W // 4, H // 4

for nome, col in VARIANTI.items():
    rnd = random.Random(nome)
    base = tint_img(tx('plaster_grey_04', 'plaster_grey_04_diff_1k.jpg'), col, 0.6, size=(W, H))
    d = ImageDraw.Draw(base)
    em = Image.new('RGB', (W, H), (0, 0, 0))
    de = ImageDraw.Draw(em)
    grime = Image.new('L', (W, H), 0)
    dg = ImageDraw.Draw(grime)
    pers = PERSIANE[rnd.randrange(len(PERSIANE))]
    for fl in range(4):
        y_top = H - (fl + 1) * FLOOR  # i piani partono dal basso
        # marcapiano chiaro
        d.rectangle([0, y_top + FLOOR - 4, W, y_top + FLOOR - 1], fill=tuple(min(255, c + 22) for c in col))
        for b in range(4):
            cx = b * BAY + BAY // 2
            ww, wh = 44, 76
            x0, y0 = cx - ww // 2, y_top + 22
            x1, y1 = x0 + ww, y0 + wh
            # cornice e davanzale in pietra
            d.rectangle([x0 - 5, y0 - 5, x1 + 5, y1 + 3], fill=tuple(min(255, c + 30) for c in col))
            d.rectangle([x0 - 8, y1 + 3, x1 + 8, y1 + 8], fill=(214, 206, 190))
            lit = rnd.random() < 0.1
            glass = (170, 120, 70) if lit else (38, 40, 44)
            d.rectangle([x0, y0, x1, y1], fill=glass)
            d.line([cx, y0, cx, y1], fill=(30, 28, 26), width=3)
            d.line([x0, y0 + 26, x1, y0 + 26], fill=(30, 28, 26), width=3)
            if lit:
                de.rectangle([x0, y0, x1, y1], fill=(255, 170, 90))
            # persiane: aperte, socchiuse o chiuse
            st = rnd.random()
            if st < 0.55:
                d.rectangle([x0 - 26, y0, x0 - 4, y1], fill=pers)
                d.rectangle([x1 + 4, y0, x1 + 26, y1], fill=pers)
                for yy in range(y0 + 3, y1, 5):
                    d.line([x0 - 25, yy, x0 - 5, yy], fill=tuple(max(0, c - 18) for c in pers))
                    d.line([x1 + 5, yy, x1 + 25, yy], fill=tuple(max(0, c - 18) for c in pers))
            elif st < 0.8 and not lit:
                d.rectangle([x0, y0, x1, y1], fill=pers)
                for yy in range(y0 + 3, y1, 5):
                    d.line([x0, yy, x1, yy], fill=tuple(max(0, c - 18) for c in pers))
            # colature sotto il davanzale
            dg.rectangle([x0 - 6, y1 + 8, x1 + 6, min(H, y1 + 8 + rnd.randint(18, 40))], fill=rnd.randint(30, 60))
    grime = grime.filter(ImageFilter.GaussianBlur(6))
    g = np.asarray(grime).astype(np.float32)[..., None] / 255.0
    a = np.asarray(base).astype(np.float32) * (1 - 0.35 * g)
    save(Image.fromarray(a.astype(np.uint8)), f'facciata_{nome}_diff.jpg')
    save(em.filter(ImageFilter.GaussianBlur(1)), f'facciata_{nome}_emit.jpg')
