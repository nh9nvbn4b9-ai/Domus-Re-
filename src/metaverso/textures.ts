import * as THREE from 'three';

export const YELLOW = '#ffc61a';
export const WARM_WHITE = '#fff4d2';

interface TextOptions {
  width: number;
  height: number;
  size: number;
  weight?: number;
  family?: string;
  color?: string;
  glow?: number;
  letterSpacing?: number;
  /** Disegna uno spessore sotto il testo, come lettere in rilievo. */
  depth?: number;
}

/** Testo su canvas, ridotto automaticamente se non entra nella larghezza. */
export function textTexture(text: string, o: TextOptions): THREE.CanvasTexture {
  const canvas = document.createElement('canvas');
  canvas.width = o.width;
  canvas.height = o.height;
  const g = canvas.getContext('2d')!;
  const family = o.family ?? 'Cinzel, serif';
  const color = o.color ?? YELLOW;
  let size = o.size;
  const setFont = () => {
    g.font = `${o.weight ?? 700} ${size}px ${family}`;
    g.letterSpacing = `${(o.letterSpacing ?? 0) * size}px`;
  };
  setFont();
  while (g.measureText(text).width > o.width * 0.92 && size > 8) {
    size *= 0.94;
    setFont();
  }
  g.textAlign = 'center';
  g.textBaseline = 'middle';
  const x = o.width / 2;
  const y = o.height / 2;

  if (o.depth) {
    g.fillStyle = '#5a4300';
    for (let i = o.depth; i > 0; i--) g.fillText(text, x, y + i);
  }
  if (o.glow) {
    g.shadowColor = color;
    g.shadowBlur = o.glow;
  }
  g.fillStyle = color;
  g.fillText(text, x, y);
  g.shadowBlur = 0;

  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 8;
  return tex;
}

/** Piano con testo, pronto da mettere in scena. */
export function textPlane(
  text: string,
  worldWidth: number,
  o: TextOptions,
  brightness = 1,
): THREE.Mesh<THREE.PlaneGeometry, THREE.MeshBasicMaterial> {
  const tex = textTexture(text, o);
  const mat = new THREE.MeshBasicMaterial({
    map: tex,
    transparent: true,
    depthWrite: false,
    color: new THREE.Color(1, 1, 1).multiplyScalar(brightness),
  });
  const geo = new THREE.PlaneGeometry(worldWidth, (worldWidth * o.height) / o.width);
  return new THREE.Mesh(geo, mat);
}

/** Puntino morbido per le particelle. */
export function dotTexture(): THREE.CanvasTexture {
  const c = document.createElement('canvas');
  c.width = c.height = 64;
  const g = c.getContext('2d')!;
  const grad = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  grad.addColorStop(0, 'rgba(255,255,255,1)');
  grad.addColorStop(0.35, 'rgba(255,255,255,0.45)');
  grad.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = grad;
  g.fillRect(0, 0, 64, 64);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}
