import { useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import { CatmullRomCurve3, MathUtils, Matrix4, PerspectiveCamera, Quaternion, Vector3 } from 'three';
import { PALAZZO } from './coords';
import { cinematic } from './cinematic';
import { setSection } from './clip';

const HERO = PALAZZO.camere.hero;
/** decentramento ottico dell'inquadratura iniziale (verticali parallele, come la foto) */
const HERO_SHIFT = (HERO.centro_y - HERO.pos[1]) / HERO.pos[2] / Math.tan(MathUtils.degToRad(HERO.fov_v / 2));

/**
 * Volo della home (coordinate three, metri; -Z = nord, il Colosseo è a sud-ovest, +X = est).
 * Ogni tappa ha posizione, punto guardato, decentramento e campo visivo; t = istante nel volo (0..1).
 * Le rotazioni passano per una vista dall'alto sopra il tetto, così la camera si gira verso sud senza scatti.
 */
const KEYS = [
  // palazzo e volo su Roma
  { t: 0.0, pos: [0, HERO.pos[1], HERO.pos[2]], look: [0, HERO.pos[1], 0], shift: HERO_SHIFT, fov: HERO.fov_v },
  { t: 0.07, pos: [0, 30, 72], look: [0, 30, -40], shift: 0.28, fov: 47 },
  { t: 0.15, pos: [8, 72, 40], look: [0, 8, -6], shift: 0, fov: 50 },
  { t: 0.27, pos: [125, 235, -175], look: [-200, 0, 420], shift: 0, fov: 45 },
  { t: 0.37, pos: [-55, 175, 140], look: [-260, 5, 470], shift: 0, fov: 42 },
  { t: 0.45, pos: [-145, 115, 300], look: [-262, 12, 470], shift: 0, fov: 40 },
  // ritorno sopra il Colle Oppio e arrivo al balcone del 3° piano
  { t: 0.56, pos: [-30, 60, 110], look: [0, 18, 0], shift: 0, fov: 42 },
  { t: 0.64, pos: [0, 17.2, 16], look: [0, 15.4, 0], shift: 0, fov: 45 },
  { t: 0.69, pos: [0, 15.7, 1.6], look: [0, 15.6, -6], shift: 0, fov: 52 },
  // nel salone: dalla portafinestra verso il camino
  { t: 0.74, pos: [0.2, 15.8, -2.4], look: [-4.0, 15.2, -3.4], shift: 0, fov: 58 },
  { t: 0.8, pos: [0.7, 15.9, -6.2], look: [-4.2, 15.0, -2.2], shift: 0, fov: 58 },
  // attraverso il soffitto: planimetria 3D in sezione, lenta orbita
  { t: 0.85, pos: [0.4, 19.2, -6.0], look: [0, 14.3, -6.2], shift: 0, fov: 55 },
  { t: 0.91, pos: [7, 33, 5], look: [0, 14.3, -7.8], shift: 0, fov: 45 },
  { t: 0.96, pos: [-8, 33, 3], look: [0, 14.3, -7.8], shift: 0, fov: 45 },
  // di nuovo sul balcone: vista su Colle Oppio e Colosseo
  { t: 0.985, pos: [0.9, 15.6, 0.65], look: [-260, 10, 470], shift: 0, fov: 50 },
  { t: 1.0, pos: [0.9, 15.65, 0.85], look: [-260, 10, 470], shift: 0, fov: 48 },
] as const;
/** tratto del film in cui la camera, sopra il soffitto, mostra la planimetria */
const PLAN_WINDOW = [0.82, 0.975];
const CEILING = PALAZZO.appartamento_pianta.soffitto;

/** Camera della home, guidata solo dal tempo (cinematic.flight / introDz), con una lieve oscillazione "a mano". */
export function CameraRig() {
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

  useFrame((three, dt) => {
    const camera = three.camera as PerspectiveCamera;
    const aspect = three.size.width / three.size.height;
    const p = MathUtils.clamp(cinematic.flight, 0, 1);
    let k = 0;
    while (k < KEYS.length - 2 && p > KEYS[k + 1].t) k++;
    const a = KEYS[k];
    const b = KEYS[k + 1];
    const l = MathUtils.clamp((p - a.t) / (b.t - a.t), 0, 1);
    const u = (k + l) / (KEYS.length - 1);

    path.curve.getPoint(u, tmp.p);
    const heroW = 1 - MathUtils.smoothstep(p, 0, 0.12);
    const time = three.clock.elapsedTime;
    tmp.p.z += cinematic.introDz * heroW;
    // respiro della camera, appena percettibile, indipendente dall'utente
    tmp.p.x += Math.sin(time * 0.21) * 0.35 * heroW;
    tmp.p.y += Math.sin(time * 0.17 + 1.3) * 0.12 * heroW;
    camera.position.lerp(tmp.p, 1 - Math.exp(-dt * 5));
    tmp.q.slerpQuaternions(path.quats[k], path.quats[k + 1], MathUtils.smootherstep(l, 0, 1) * 0.35 + l * 0.65);
    camera.quaternion.slerp(tmp.q, 1 - Math.exp(-dt * 5));

    let fov = MathUtils.lerp(a.fov, b.fov, l);
    if (aspect < 0.8) {
      // schermi verticali: allarga il campo perché la facciata (12 m) entri in larghezza
      const z = Math.max(1, camera.position.z);
      fov = MathUtils.lerp(fov, Math.max(fov, 2 * MathUtils.radToDeg(Math.atan(8.6 / (z * aspect)))), heroW);
      fov = Math.max(fov, MathUtils.lerp(fov, 58, 1 - heroW));
    }
    camera.fov = fov;
    // piano vicino adattivo: precisione della profondità sia a terra sia in volo sopra la città
    camera.near = p > 0.6 && p < 0.99 ? 0.05 : MathUtils.clamp(camera.position.y * 0.015, 0.1, 4);
    camera.far = 40000;
    camera.updateProjectionMatrix();
    camera.projectionMatrix.elements[9] = MathUtils.lerp(a.shift, b.shift, l);
    // planimetria: quando la camera ha attraversato il soffitto
    const plan = p > PLAN_WINDOW[0] && p < PLAN_WINDOW[1] && camera.position.y > CEILING - 0.2;
    if (plan !== cinematic.planimetria) {
      cinematic.planimetria = plan;
      setSection(plan);
    }
    camera.projectionMatrixInverse.copy(camera.projectionMatrix).invert();
  });

  return null;
}
