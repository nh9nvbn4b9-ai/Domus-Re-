import { useEffect, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { MathUtils, PerspectiveCamera, Vector3 } from 'three';
import { PALAZZO } from './coords';
import { prefersReducedMotion } from '../lib/motion';

gsap.registerPlugin(ScrollTrigger);

const HERO = PALAZZO.camere.hero;

/**
 * Camera "architettonica": resta orizzontale e decentra l'ottica (come un obiettivo basculabile),
 * così le verticali del palazzo restano parallele come nella foto di riferimento.
 *
 * Stato animato (GSAP): ingresso dalla distanza, poi avvicinamento legato allo scroll della home.
 * Fase 5: questa timeline diventerà la sequenza completa (Roma, balcone, salone, planimetria).
 */
export function CameraRig() {
  const state = useRef({ x: 0, y: HERO.pos[1], z: HERO.pos[2] + 18, centerY: HERO.centro_y + 2, fov: HERO.fov_v });
  const pointer = useRef({ x: 0, y: 0 });
  const tmp = useRef(new Vector3());

  useEffect(() => {
    const st = state.current;
    const reduce = prefersReducedMotion();
    const intro = gsap.to(st, {
      z: HERO.pos[2],
      centerY: HERO.centro_y,
      duration: reduce ? 0 : 4.2,
      ease: 'power3.out',
    });
    const scroll = gsap.timeline({
      scrollTrigger: { trigger: '#home', start: 'top top', end: 'bottom top', scrub: 1.2 },
    });
    // anteprima della sequenza: avvicinamento al balcone del piano 3 (fase 5: percorso completo)
    scroll.to(st, { z: 20, y: 9, centerY: 15.2, fov: 42, ease: 'none' }, 0);
    const onMove = (e: PointerEvent) => {
      pointer.current.x = (e.clientX / window.innerWidth) * 2 - 1;
      pointer.current.y = (e.clientY / window.innerHeight) * 2 - 1;
    };
    if (!reduce) window.addEventListener('pointermove', onMove, { passive: true });
    return () => {
      intro.kill();
      scroll.scrollTrigger?.kill();
      scroll.kill();
      window.removeEventListener('pointermove', onMove);
    };
  }, []);

  useFrame((three, dt) => {
    const camera = three.camera as PerspectiveCamera;
    const size = three.size;
    const st = state.current;
    const portrait = size.width / size.height < 0.8;
    // su schermi verticali allarga il campo perché la facciata (12 m) entri in larghezza
    const fov = portrait ? Math.max(st.fov, 2 * MathUtils.radToDeg(Math.atan(7.6 / (st.z * (size.width / size.height))))) : st.fov;
    const px = pointer.current.x * 0.7;
    const py = -pointer.current.y * 0.25;
    tmp.current.set(st.x + px, st.y + py, st.z);
    camera.position.lerp(tmp.current, 1 - Math.exp(-dt * 3));
    camera.rotation.set(0, 0, 0);
    camera.fov = fov;
    camera.updateProjectionMatrix();
    // decentramento verticale: il centro quadro sulla facciata (z = 0) è a quota centerY
    const dist = Math.max(1, camera.position.z);
    const shift = (st.centerY - camera.position.y) / dist / Math.tan(MathUtils.degToRad(camera.fov / 2));
    camera.projectionMatrix.elements[9] = shift;
    camera.projectionMatrixInverse.copy(camera.projectionMatrix).invert();
  });

  return null;
}
