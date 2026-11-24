"""Scarica asset CC0 da Poly Haven (texture, HDRI, modelli) in pipeline/cache/.

Uso:
  python3 pipeline/polyhaven.py texture <id> [res=2k] [maps=diff,nor_gl,rough,arm,disp]
  python3 pipeline/polyhaven.py hdri <id> [res=4k]
  python3 pipeline/polyhaven.py model <id> [res=2k]
"""
import json, os, sys, urllib.request

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')
UA = {'User-Agent': 'domus-re-asset-pipeline'}


def get_json(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return json.load(r)


def download(url, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return dest
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r, open(dest + '.part', 'wb') as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)
    os.replace(dest + '.part', dest)
    return dest


def texture(asset, res='2k', maps=('Diffuse', 'nor_gl', 'Rough', 'arm', 'Displacement')):
    files = get_json(f'https://api.polyhaven.com/files/{asset}')
    out = {}
    for m in maps:
        if m not in files or res not in files[m]:
            continue
        fmt = 'jpg' if 'jpg' in files[m][res] else 'png'
        url = files[m][res][fmt]['url']
        out[m] = download(url, os.path.join(ROOT, 'textures', asset, os.path.basename(url)))
    return out


def hdri(asset, res='4k'):
    files = get_json(f'https://api.polyhaven.com/files/{asset}')
    url = files['hdri'][res]['hdr']['url']
    return download(url, os.path.join(ROOT, 'hdri', os.path.basename(url)))


def model(asset, res='2k'):
    files = get_json(f'https://api.polyhaven.com/files/{asset}')
    g = files['gltf'][res]['gltf']
    base = os.path.join(ROOT, 'models', asset)
    main = download(g['url'], os.path.join(base, os.path.basename(g['url'])))
    for rel, info in g.get('include', {}).items():
        download(info['url'], os.path.join(base, rel))
    return main


if __name__ == '__main__':
    kind, asset, *rest = sys.argv[1:]
    if kind == 'texture':
        res = rest[0] if rest else '2k'
        maps = rest[1].split(',') if len(rest) > 1 else ('Diffuse', 'nor_gl', 'Rough', 'arm', 'Displacement')
        print(json.dumps(texture(asset, res, maps), indent=1))
    elif kind == 'hdri':
        print(hdri(asset, rest[0] if rest else '4k'))
    elif kind == 'model':
        print(model(asset, rest[0] if rest else '2k'))
