import { Canvas } from '@react-three/fiber';
import { Sky } from '@react-three/drei';
import { AgXToneMapping, SRGBColorSpace } from 'three';

/**
 * Canvas WebGL della home.
 * Fase 1: solo infrastruttura (renderer, tone mapping, cielo al tramonto).
 * Fase 2+: palazzo ricostruito, Roma, aereo, appartamento — tutto nello stesso mondo in metri.
 */
export default function Experience() {
  return (
    <Canvas
      className="home__canvas"
      shadows
      dpr={[1, 2]}
      camera={{ fov: 35, near: 0.1, far: 20000, position: [0, 1.7, 40] }}
      gl={{ antialias: true, toneMapping: AgXToneMapping, outputColorSpace: SRGBColorSpace, powerPreference: 'high-performance' }}
    >
      <Sky distance={4500} sunPosition={[-60, 9, -100]} turbidity={6} rayleigh={1.6} mieCoefficient={0.006} mieDirectionalG={0.86} />
    </Canvas>
  );
}
