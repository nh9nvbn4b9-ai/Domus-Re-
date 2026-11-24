import { useEffect, useMemo, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { CatmullRomCurve3, MathUtils, Matrix4, PerspectiveCamera, Quaternion, Vector3 } from 'three';
import { PALAZZO } from './coords';
import { cinematic } from './cinematic';
import { prefersReducedMotion } from '../lib/motion';

gsap.registerPlugin(ScrollTrigger);

const HERO = PALAZZO.camere.hero;
/** decentramento ottico dell'inquadratura iniziale (verticali parallele, come la foto) */
const HERO_SHIFT = (HERO.centro_y - HERO.pos[1]) / HERO.pos[2] / Math.tan(MathUtils.degToRad(HERO.fov_v / 2));

/**
 * Sequenza della home (coordinate three, metri; -Z = nord, il Colosseo è a sud-ovest, +X = est).
 * t = avanzamento dello scroll; ogni tappa ha posizione, punto guardato, decentramento e campo visivo.
 * Le rotazioni passano per una vista dall'alto sopra il tetto, così la camera si gira verso sud senza scatti.
 */
const KEYS = [
  { t: 0.0, pos: [0, HERO.pos[1], HERO.pos[2]], look: [0, HERO.pos[1], 0], shift: HERO_SHIFT, fov: HERO.fov_v },
  { t: 0.16, pos: [0, 30, 72], look: [0, 30, -40], shift: 0.28, fov: 47 },
  { t: 0.34, pos: [8, 72, 40], look: [0, 8, -6], shift: 0, fov: 50 },
  { t: 0.56, pos: [125, 235, -175], look: [-200, 0, 420], shift: 0, fov: 45 },
  { t: 0.8, pos: [-55, 175, 140], look: [-260, 5, 470], shift: 0, fov: 42 },
  { t: 1.0, pos: [-145, 115, 300], look: [-262, 12, 470], shift: 0, fov: 40 },
] as const;

const smooth = (x: number) => x * x * (3 - 2 * x);

export function CameraRig() {
  const pointer = useRef({ x: 0, y: 0 });
  const intro = useRef({ dz: 16 });
  const scroll = useRef({ p: 0 });

  const path = useMemo(() => {
    const curve = new CatmullRomCurve3(KEYS.map((k) => new Vector3(...k.pos)), false, 'centripetal');
    const m = new Matrix4();
    const quats = KEYS.map((k) => {
      m.lookAt(new Vector3(...k.pos), new Vector3(...k.look), new Vector3(0, 1, 0));
      return new Quaternion().setFromRotationMatrix(m);
    });
    return { curve, quats };
  }, []);
  const tmp = useMemo(() => ({ p: new Vector3(), q: new Quaternion() }), []);

  useEffect(() => {
    const reduce = prefersReducedMotion();
    const introTw = gsap.to(intro.current, { dz: 0, duration: reduce ? 0 : 4.5, ease: 'power3.out' });
    // la home resta agganciata per tre schermate: lo scroll guida il volo sopra Roma
    const tl = gsap.timeline({
      scrollTrigger: {
        trigger: '#home',
        start: 'top top',
        end: '+=300%',
        pin: true,
        scrub: reduce ? true : 1.4,
        anticipatePin: 1,
      },
    });
    tl.to(scroll.current, { p: 1, ease: 'none', onUpdate: () => (cinematic.scroll = scroll.current.p) });
    tl.to('.home__overlay', { autoAlpha: 0, duration: 0.08, ease: 'none' }, 0.02);
    const onMove = (e: PointerEvent) => {
      pointer.current.x = (e.clientX / window.innerWidth) * 2 - 1;
      pointer.current.y = (e.clientY / window.innerHeight) * 2 - 1;
    };
    if (!reduce) window.addEventListener('pointermove', onMove, { passive: true });
    return () => {
      introTw.kill();
      tl.scrollTrigger?.kill();
      tl.kill();
      window.removeEventListener('pointermove', onMove);
    };
  }, []);

  useFrame((three, dt) => {
    const camera = three.camera as PerspectiveCamera;
    const aspect = three.size.width / three.size.height;
    const p = MathUtils.clamp(scroll.current.p, 0, 1);
    let k = 0;
    while (k < KEYS.length - 2 && p > KEYS[k + 1].t) k++;
    const a = KEYS[k];
    const b = KEYS[k + 1];
    const l = smooth(MathUtils.clamp((p - a.t) / (b.t - a.t), 0, 1));
    const u = (k + l) / (KEYS.length - 1);

    path.curve.getPoint(u, tmp.p);
    const heroW = 1 - smooth(MathUtils.clamp(p / 0.12, 0, 1));
    tmp.p.z += intro.current.dz * heroW;
    tmp.p.x += pointer.current.x * 0.8 * heroW;
    tmp.p.y += -pointer.current.y * 0.3 * heroW;
    camera.position.lerp(tmp.p, 1 - Math.exp(-dt * 6));
    tmp.q.slerpQuaternions(path.quats[k], path.quats[k + 1], l);
    camera.quaternion.slerp(tmp.q, 1 - Math.exp(-dt * 6));

    let fov = MathUtils.lerp(a.fov, b.fov, l);
    if (aspect < 0.8) {
      // schermi verticali: allarga il campo perché la facciata (12 m) entri in larghezza
      const z = Math.max(1, camera.position.z);
      fov = MathUtils.lerp(fov, Math.max(fov, 2 * MathUtils.radToDeg(Math.atan(8.6 / (z * aspect)))), heroW);
      fov = Math.max(fov, MathUtils.lerp(fov, 58, 1 - heroW));
    }
    camera.fov = fov;
    // piano vicino adattivo: precisione della profondità sia a terra sia in volo sopra la città
    camera.near = MathUtils.clamp(camera.position.y * 0.015, 0.1, 4);
    camera.far = 40000;
    camera.updateProjectionMatrix();
    const shift = MathUtils.lerp(a.shift, b.shift, l);
    camera.projectionMatrix.elements[9] = shift;
    camera.projectionMatrixInverse.copy(camera.projectionMatrix).invert();
  });

  return null;
}
