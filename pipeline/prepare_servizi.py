"""Converte i render Cycles dell'appartamento nelle immagini dei servizi del sito (WebP)."""
import os

from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
R = os.path.join(ROOT, 'pipeline', 'cache', 'renders')
OUT = os.path.join(ROOT, 'public', 'images', 'servizi')
os.makedirs(OUT, exist_ok=True)
MAPPA = {
    'compravendita': 'appartamento-portone.png',
    'tecnologia-360': 'appartamento-salone_est.png',
    'affitto-protetto': 'appartamento-porta.png',
    'valutazioni': 'appartamento-planimetria.png',
    'affitto-concordato': 'appartamento-cucina.png',
}
for sid, f in MAPPA.items():
    p = os.path.join(R, f)
    if not os.path.exists(p):
        print('manca', f)
        continue
    im = Image.open(p).convert('RGB')
    w, h = im.size
    th = int(w * 10 / 16)            # ritaglio 16:10
    top = max(0, (h - th) // 2)
    im = im.crop((0, top, w, top + min(th, h))).resize((1200, 750), Image.LANCZOS)
    im.save(os.path.join(OUT, f'{sid}.webp'), quality=84, method=6)
    print('→', sid)
pano = os.path.join(R, 'appartamento-panorama.png')
if os.path.exists(pano):
    Image.open(pano).convert('RGB').save(os.path.join(OUT, 'salone-360.webp'), quality=82, method=6)
    print('→ salone-360')
