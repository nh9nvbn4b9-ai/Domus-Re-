import { useEffect, useMemo, useRef, useState } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import { useGLTF } from '@react-three/drei';
import {
  CanvasTexture,
  Color,
  CubicBezierCurve3,
  InstancedBufferAttribute,
  InstancedBufferGeometry,
  Matrix4,
  NormalBlending,
  PlaneGeometry,
  Quaternion,
  ShaderMaterial,
  Vector3,
  type Group,
  type Object3D,
} from 'three';
import { GLYPHS, LETTER_GAP, SPACE, lineWidth } from './glyphs';
import { cinematic } from './cinematic';
import { PALAZZO } from './coords';

const HERO = PALAZZO.camere.hero;
const BUILDING_TOP = PALAZZO.altezza_totale;
/** piano verticale della scritta, alle spalle del palazzo (coordinate three: -Z = nord) */
const TEXT_Z = -360;
const PLANE_SCALE = 3.0;

interface PathData {
  pts: Vector3[];
  smoke: boolean[];
  cum: number[];
  length: number;
  emit: { p: Vector3; s: number }[];
  em: number;
}

/** Impagina DOMUS RE nella fascia di cielo sopra il palazzo, vista dall'inquadratura iniziale. */
function layout(aspect: number) {
  const camY = HERO.pos[1];
  const camZ = HERO.pos[2];
  const portrait = aspect < 0.8;
  const fov = portrait ? Math.max(HERO.fov_v, (2 * Math.atan(8.6 / (camZ * aspect)) * 180) / Math.PI) : HERO.fov_v;
  const tanV = Math.tan(((fov / 2) * Math.PI) / 180);
  const c0 = (HERO.centro_y - camY) / camZ;
  const t0 = (BUILDING_TOP - camY) / camZ + 0.045;
  const t1 = c0 + tanV - 0.11; // margine per la barra del menu
  const d = camZ - TEXT_Z;
  const bandH = (t1 - t0) * d;
  const widthAvail = (aspect < 0.8 ? 0.72 : 0.8) * 2 * tanV * aspect * d;
  const single = Math.min(bandH * 0.86, widthAvail / lineWidth('DOMUS RE'));
  const two = Math.min((bandH * 0.92) / 2.35, widthAvail / lineWidth('DOMUS'));
  const lines = two > single * 1.25 ? ['DOMUS', 'RE'] : ['DOMUS RE'];
  const em = lines.length > 1 ? two : single;
  const yMid = camY + d * ((t0 + t1) / 2);
  const totalH = lines.length > 1 ? 2.35 * em : em;
  return { lines, em, top: yMid + totalH / 2 };
}

function buildPath(aspect: number): PathData {
  const { lines, em, top } = layout(aspect);
  const strokes: Vector3[][] = [];
  lines.forEach((line, li) => {
    const w = lineWidth(line) * em;
    let x = -w / 2;
    const yBase = top - em - li * 1.35 * em;
    for (const ch of line) {
      if (ch === ' ') {
        x += SPACE * em;
        continue;
      }
      const g = GLYPHS[ch];
      for (const st of g.strokes) strokes.push(st.map(([u, v]) => new Vector3(x + u * em, yBase + v * em, TEXT_Z)));
      x += (g.width + LETTER_GAP) * em;
    }
  });

  const pts: Vector3[] = [];
  const smoke: boolean[] = [];
  const push = (p: Vector3, s: boolean) => {
    pts.push(p);
    smoke.push(s);
  };
  const first = strokes[0][0];
  let cur = new Vector3(first.x - 420, first.y + 60, TEXT_Z + 120);
  let dir = new Vector3(1, -0.1, -0.25).normalize();
  for (const st of strokes) {
    const start = st[0];
    const sdir = st[1].clone().sub(st[0]).normalize();
    const k = Math.max(30, cur.distanceTo(start) * 0.45);
    const bez = new CubicBezierCurve3(cur, cur.clone().addScaledVector(dir, k), start.clone().addScaledVector(sdir, -k), start);
    const n = Math.max(8, Math.ceil(bez.getLength() / 2));
    for (let i = 0; i < n; i++) push(bez.getPoint(i / n), false);
    for (let i = 0; i < st.length - 1; i++) {
      const a = st[i];
      const b = st[i + 1];
      const segN = Math.max(1, Math.ceil(a.distanceTo(b) / 1.2));
      for (let j = 0; j < segN; j++) push(a.clone().lerp(b, j / segN), true);
    }
    cur = st[st.length - 1].clone();
    dir = cur.clone().sub(st[st.length - 2]).normalize();
  }
  const exitP = new Vector3(cur.x + 520, cur.y + 160, TEXT_Z - 260);
  const bez = new CubicBezierCurve3(cur, cur.clone().addScaledVector(dir, 120), exitP.clone().add(new Vector3(-200, -40, 80)), exitP);
  for (let i = 0; i <= 60; i++) push(bez.getPoint(i / 60), false);

  // ascisse curvilinee e punti di emissione del fumo (uno ogni ~2 m)
  const cum = [0];
  for (let i = 1; i < pts.length; i++) cum.push(cum[i - 1] + pts[i].distanceTo(pts[i - 1]));
  const emit: { p: Vector3; s: number }[] = [];
  let next = 0;
  for (let i = 1; i < pts.length; i++) {
    if (!smoke[i]) continue;
    while (next <= cum[i]) {
      if (next >= cum[i - 1]) {
        const k = (next - cum[i - 1]) / Math.max(1e-6, cum[i] - cum[i - 1]);
        emit.push({ p: pts[i - 1].clone().lerp(pts[i], k), s: next });
      }
      next += 2.0;
    }
  }
  return { pts, smoke, cum, length: cum[cum.length - 1], emit, em };
}

/** Sbuffo di fumo procedurale: alfa = densità, rosso = illuminazione (sole da sinistra). */
function puffTexture() {
  const S = 128;
  const c = document.createElement('canvas');
  c.width = c.height = S;
  const ctx = c.getContext('2d')!;
  let seed = 7;
  const rand = () => ((seed = (seed * 16807) % 2147483647) - 1) / 2147483646;
  for (let i = 0; i < 70; i++) {
    const a = rand() * Math.PI * 2;
    const r = Math.sqrt(rand()) * S * 0.28;
    const x = S / 2 + Math.cos(a) * r;
    const y = S / 2 + Math.sin(a) * r;
    const rr = S * (0.1 + rand() * 0.16);
    const g = ctx.createRadialGradient(x, y, 0, x, y, rr);
    g.addColorStop(0, 'rgba(255,255,255,0.22)');
    g.addColorStop(1, 'rgba(255,255,255,0)');
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, S, S);
  }
  const img = ctx.getImageData(0, 0, S, S);
  for (let y = 0; y < S; y++) {
    for (let x = 0; x < S; x++) {
      const i = (y * S + x) * 4;
      const dx = (x - S / 2) / (S / 2);
      const dy = (y - S / 2) / (S / 2);
      const edge = Math.max(0, 1 - Math.hypot(dx, dy));
      const light = Math.min(1, Math.max(0, 0.55 - dx * 0.35 - dy * 0.25 + (1 - edge) * 0.15));
      img.data[i] = img.data[i + 1] = img.data[i + 2] = Math.round(light * 255);
      img.data[i + 3] = Math.round(Math.min(255, img.data[i + 3] * 1.4) * Math.min(1, edge * 2.2));
    }
  }
  ctx.putImageData(img, 0, 0);
  const t = new CanvasTexture(c);
  t.needsUpdate = true;
  return t;
}

const VERT = /* glsl */ `
attribute vec3 aCenter;
attribute float aBirth;
attribute float aSeed;
uniform float uClock;
uniform float uScale;
varying vec2 vUv;
varying float vAlpha;
void main() {
  float age = uClock - aBirth;
  if (age < 0.0) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); return; }
  float grow = 1.0 - exp(-age / 3.2);
  float size = (mix(2.2, 12.0, grow) + age * 0.05) * uScale;
  vec3 drift = vec3(0.6, 0.18, 0.0) * age * 0.25 * uScale
    + vec3(sin(aSeed * 12.0 + age * 0.21), cos(aSeed * 7.0 + age * 0.17), sin(aSeed * 3.0)) * grow * 2.2 * uScale;
  vec4 mv = modelViewMatrix * vec4(aCenter + drift, 1.0);
  float r = aSeed * 6.2831 + age * 0.03;
  vec2 c = position.xy;
  c = vec2(c.x * cos(r) - c.y * sin(r), c.x * sin(r) + c.y * cos(r));
  mv.xy += c * size;
  gl_Position = projectionMatrix * mv;
  vUv = uv;
  vAlpha = smoothstep(0.0, 0.3, age) * mix(0.9, 0.62, grow);
}`;

const FRAG = /* glsl */ `
uniform sampler2D uPuff;
uniform vec3 uLit;
uniform vec3 uShadow;
varying vec2 vUv;
varying float vAlpha;
void main() {
  vec4 p = texture2D(uPuff, vUv);
  float a = p.a * vAlpha;
  if (a < 0.008) discard;
  gl_FragColor = vec4(mix(uShadow, uLit, p.r), a);
  #include <colorspace_fragment>
}`;

/**
 * Aereo che scrive DOMUS RE nel cielo sopra il palazzo, con scia di fumo che resta visibile.
 * La scrittura è guidata dal tempo (cinematic.writeClock, avviata dalla sequenza in cinematic.ts).
 */
export function Scrittura() {
  const size = useThree((s) => s.size);
  const aspect = size.width / size.height;
  // il percorso si calcola una sola volta all'avvio, sull'orientamento dello schermo iniziale
  const [initialAspect] = useState(aspect);
  const path = useMemo(() => buildPath(initialAspect), [initialAspect]);
  const { scene: plane } = useGLTF('/models/aereo.glb');
  const planeRef = useRef<Group>(null);
  const prop = useRef<Object3D | null>(null);
  const roll = useRef(0);

  useEffect(() => {
    prop.current = plane.getObjectByName('Elica') ?? null;
  }, [plane]);

  const { geometry, material } = useMemo(() => {
    const speed = path.length / cinematic.writeDuration;
    const n = path.emit.length * 2;
    const base = new PlaneGeometry(1, 1);
    const g = new InstancedBufferGeometry();
    g.index = base.index;
    g.setAttribute('position', base.getAttribute('position'));
    g.setAttribute('uv', base.getAttribute('uv'));
    const centers = new Float32Array(n * 3);
    const births = new Float32Array(n);
    const seeds = new Float32Array(n);
    let seed = 11;
    const rand = () => ((seed = (seed * 16807) % 2147483647) - 1) / 2147483646;
    path.emit.forEach((e, i) => {
      for (let k = 0; k < 2; k++) {
        const j = i * 2 + k;
        centers[j * 3] = e.p.x + (rand() - 0.5) * 1.4;
        centers[j * 3 + 1] = e.p.y + (rand() - 0.5) * 1.4;
        centers[j * 3 + 2] = e.p.z + (rand() - 0.5) * 1.4;
        births[j] = e.s / speed + k * 0.05;
        seeds[j] = rand();
      }
    });
    g.setAttribute('aCenter', new InstancedBufferAttribute(centers, 3));
    g.setAttribute('aBirth', new InstancedBufferAttribute(births, 1));
    g.setAttribute('aSeed', new InstancedBufferAttribute(seeds, 1));
    g.instanceCount = n;
    const m = new ShaderMaterial({
      vertexShader: VERT,
      fragmentShader: FRAG,
      uniforms: {
        uClock: { value: 0 },
        uScale: { value: Math.min(1, Math.max(0.42, path.em / 55)) },
        uPuff: { value: puffTexture() },
        uLit: { value: new Color(1.0, 0.9, 0.78).multiplyScalar(1.25) },
        uShadow: { value: new Color(0.52, 0.56, 0.68) },
      },
      transparent: true,
      depthWrite: false,
      blending: NormalBlending,
    });
    return { geometry: g, material: m };
  }, [path]);

  const tmp = useMemo(() => ({ m: new Matrix4(), q: new Quaternion(), f: new Vector3(), u: new Vector3(), r: new Vector3() }), []);

  useFrame((_, dt) => {
    if (cinematic.writing && !cinematic.paused) cinematic.writeClock += Math.min(dt, 0.1);
    material.uniforms.uClock.value = cinematic.writeClock;
    const g = planeRef.current;
    if (!g) return;
    const speed = path.length / cinematic.writeDuration;
    const s = cinematic.writeClock * speed;
    const cum = path.cum;
    if (s >= path.length || !cinematic.writing) {
      g.visible = s < path.length && cinematic.writing;
      return;
    }
    g.visible = true;
    let lo = 1;
    let hi = cum.length - 1;
    while (lo < hi) {
      const mid = (lo + hi) >> 1;
      if (cum[mid] < s) lo = mid + 1;
      else hi = mid;
    }
    const i = Math.max(1, lo);
    const k = (s - cum[i - 1]) / Math.max(1e-6, cum[i] - cum[i - 1]);
    g.position.copy(path.pts[i - 1]).lerp(path.pts[i], k);
    const ahead = path.pts[Math.min(path.pts.length - 1, i + 6)];
    const behind = path.pts[Math.max(0, i - 6)];
    tmp.f.copy(ahead).sub(behind).normalize();
    // virata: inclinazione proporzionale alla curvatura nel piano della scritta
    const a1 = path.pts[Math.min(path.pts.length - 1, i + 14)].clone().sub(g.position);
    const turn = tmp.f.x * a1.y - tmp.f.y * a1.x;
    roll.current += (Math.max(-1.1, Math.min(1.1, turn * 0.04)) - roll.current) * Math.min(1, dt * 4);
    // l'aereo vola nel piano verticale della scritta (cabrate e picchiate): lo si vede di profilo
    tmp.u.set(0, 0, 1).cross(tmp.f).normalize();
    tmp.u.applyAxisAngle(tmp.f, roll.current);
    tmp.r.crossVectors(tmp.f, tmp.u).normalize();
    tmp.u.crossVectors(tmp.r, tmp.f).normalize();
    tmp.m.makeBasis(tmp.f, tmp.u, tmp.r);
    g.quaternion.setFromRotationMatrix(tmp.m);
    if (prop.current) prop.current.rotation.x += dt * 60;
  });

  return (
    <>
      <mesh geometry={geometry} material={material} frustumCulled={false} renderOrder={5} />
      <group ref={planeRef} scale={PLANE_SCALE} visible={false}>
        <primitive object={plane} />
      </group>
    </>
  );
}

useGLTF.preload('/models/aereo.glb');
