import sys, re, numpy as np
from PIL import Image

def read_hdr(path):
    with open(path, 'rb') as f:
        data = f.read()
    head_end = data.index(b'\n\n') + 2
    m = re.search(rb'-Y (\d+) \+X (\d+)\n', data[head_end:head_end + 64])
    h, w = int(m.group(1)), int(m.group(2))
    p = head_end + m.end()
    img = np.zeros((h, w, 4), np.uint8)
    for y in range(h):
        p += 4  # RLE scanline header
        for c in range(4):
            x = 0
            while x < w:
                n = data[p]; p += 1
                if n > 128:
                    n -= 128; img[y, x:x + n, c] = data[p]; p += 1
                else:
                    img[y, x:x + n, c] = np.frombuffer(data[p:p + n], np.uint8); p += n
                x += n
    e = img[..., 3].astype(np.float32)
    scale = np.where(e > 0, np.ldexp(1.0, (e - 136).astype(np.int32)), 0)
    return img[..., :3].astype(np.float32) * scale[..., None]

if __name__ == '__main__':
    rgb = read_hdr(sys.argv[1])
    print('max', rgb.max(), 'mean', rgb.mean(), 'sun px', np.unravel_index(rgb.sum(2).argmax(), rgb.shape[:2]), rgb.shape)
    x = rgb * float(sys.argv[3]) if len(sys.argv) > 3 else rgb
    x = x / (1 + x)
    Image.fromarray((np.clip(x ** (1 / 2.2), 0, 1) * 255).astype(np.uint8)).save(sys.argv[2])
