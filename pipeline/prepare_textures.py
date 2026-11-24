"""Texture derivate per i materiali del palazzo (tinte calibrate sulla foto di riferimento)."""
import os
import numpy as np
from PIL import Image

C = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')
OUT = os.path.join(C, 'derived')
os.makedirs(OUT, exist_ok=True)


def tint(src, dst, color, contrast=0.55, gain=1.0):
    """Mantiene la variazione di luminanza della texture fotografica e la riporta su un colore target (sRGB)."""
    im = np.asarray(Image.open(src).convert('RGB')).astype(np.float32) / 255.0
    lin = im ** 2.2
    lum = lin @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    rel = (lum / lum.mean()) ** contrast
    target = (np.array(color, np.float32) / 255.0) ** 2.2
    out = np.clip(target[None, None, :] * rel[..., None] * gain, 0, 1) ** (1 / 2.2)
    Image.fromarray((out * 255).astype(np.uint8)).save(dst, quality=92)
    print('→', dst)


tx = lambda a, f: os.path.join(C, 'textures', a, f)
# Pietra calcarea color crema della facciata (campionata sulla foto in luce diffusa).
tint(tx('plaster_grey_04', 'plaster_grey_04_diff_2k.jpg'), os.path.join(OUT, 'stone_cream_diff.jpg'), (214, 202, 182), 0.5)
# Variante leggermente più calda per le lastre (lunetta, specchiature) e il marciapiede.
tint(tx('marble_01', 'marble_01_diff_2k.jpg'), os.path.join(OUT, 'slab_cream_diff.jpg'), (206, 196, 178), 0.7)
tint(tx('marble_01', 'marble_01_diff_2k.jpg'), os.path.join(OUT, 'pavement_diff.jpg'), (188, 180, 168), 0.8)
# Pietra dell'edificio adiacente: più grigia, per distinguerlo.
tint(tx('plaster_grey_04', 'plaster_grey_04_diff_2k.jpg'), os.path.join(OUT, 'stone_neighbor_diff.jpg'), (196, 188, 174), 0.6)
# Ardesia della mansarda: più scura e fredda, come in foto.
tint(tx('roof_slates_03', 'roof_slates_03_diff_2k.jpg'), os.path.join(OUT, 'slate_dark_diff.jpg'), (74, 76, 82), 0.9)
# Intonaci romani per gli edifici di contesto (ocra e terracotta).
tint(tx('plaster_grey_04', 'plaster_grey_04_diff_2k.jpg'), os.path.join(OUT, 'plaster_ochre_diff.jpg'), (196, 146, 92), 0.7)
tint(tx('plaster_grey_04', 'plaster_grey_04_diff_2k.jpg'), os.path.join(OUT, 'plaster_terracotta_diff.jpg'), (178, 108, 72), 0.7)
