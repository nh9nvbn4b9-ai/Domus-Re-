import { Suspense, useEffect, useRef } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { useTexture } from '@react-three/drei';
import { BackSide, MathUtils, SRGBColorSpace } from 'three';

/** Sfera con il panorama equirettangolare (render Cycles del salone), esplorabile trascinando. */
function Panorama({ src }: { src: string }) {
  const tex = useTexture(src, (t) => {
    // spazio colore impostato al caricamento (texture sRGB del render)
    (Array.isArray(t) ? t : [t]).forEach((x) => (x.colorSpace = SRGBColorSpace));
  });
  const camera = useThree((s) => s.camera);
  const gl = useThree((s) => s.gl);
  const look = useRef({ lon: 0, lat: 0, dragging: false, x: 0, y: 0, idle: 0 });

  useEffect(() => {
    const el = gl.domElement;
    const st = look.current;
    const down = (e: PointerEvent) => {
      st.dragging = true;
      st.x = e.clientX;
      st.y = e.clientY;
      el.setPointerCapture(e.pointerId);
    };
    const move = (e: PointerEvent) => {
      if (!st.dragging) return;
      st.lon -= (e.clientX - st.x) * 0.18;
      st.lat = MathUtils.clamp(st.lat + (e.clientY - st.y) * 0.18, -70, 70);
      st.x = e.clientX;
      st.y = e.clientY;
      st.idle = 0;
    };
    const up = () => (st.dragging = false);
    const key = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft') st.lon -= 10;
      if (e.key === 'ArrowRight') st.lon += 10;
      if (e.key === 'ArrowUp') st.lat = Math.min(70, st.lat + 8);
      if (e.key === 'ArrowDown') st.lat = Math.max(-70, st.lat - 8);
      st.idle = 0;
    };
    el.addEventListener('pointerdown', down);
    el.addEventListener('pointermove', move);
    el.addEventListener('pointerup', up);
    window.addEventListener('keydown', key);
    return () => {
      el.removeEventListener('pointerdown', down);
      el.removeEventListener('pointermove', move);
      el.removeEventListener('pointerup', up);
      window.removeEventListener('keydown', key);
    };
  }, [gl]);

  useFrame((_, dt) => {
    const st = look.current;
    st.idle += dt;
    if (!st.dragging && st.idle > 2.5) st.lon += dt * 4; // rotazione lenta quando non si interagisce
    const phi = MathUtils.degToRad(90 - st.lat);
    const theta = MathUtils.degToRad(st.lon);
    camera.lookAt(Math.sin(phi) * Math.cos(theta), Math.cos(phi), Math.sin(phi) * Math.sin(theta));
  });

  return (
    <mesh scale={[-1, 1, 1]}>
      <sphereGeometry args={[50, 64, 32]} />
      <meshBasicMaterial map={tex} side={BackSide} toneMapped={false} />
    </mesh>
  );
}

export default function Visita360({ src, onClose }: { src: string; onClose: () => void }) {
  const closeRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    closeRef.current?.focus();
    const esc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
      // finestra modale: il Tab resta sul pulsante Chiudi (unico elemento interattivo)
      if (e.key === 'Tab') {
        e.preventDefault();
        closeRef.current?.focus();
      }
    };
    window.addEventListener('keydown', esc);
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      window.removeEventListener('keydown', esc);
      document.body.style.overflow = prev;
    };
  }, [onClose]);

  return (
    <div className="visita360" role="dialog" aria-modal="true" aria-label="Visita virtuale a 360 gradi del salone">
      <Canvas className="visita360__canvas" camera={{ fov: 70, position: [0, 0, 0.01] }} dpr={[1, 2]}>
        <Suspense fallback={null}>
          <Panorama src={src} />
        </Suspense>
      </Canvas>
      <div className="visita360__ui">
        <p className="visita360__titolo">
          Salone · appartamento dimostrativo
          <span>Trascina per guardarti intorno · frecce della tastiera</span>
        </p>
        <button ref={closeRef} type="button" className="pill pill--ghost" onClick={onClose}>
          Chiudi
        </button>
      </div>
    </div>
  );
}
