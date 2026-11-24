import { Suspense, useEffect, useMemo, useState } from 'react';
import { Canvas } from '@react-three/fiber';
import { useProgress } from '@react-three/drei';
import { EffectComposer, Bloom, ToneMapping, Vignette, SMAA, BrightnessContrast } from '@react-three/postprocessing';
import { ToneMappingMode } from 'postprocessing';
import { NoToneMapping, SRGBColorSpace } from 'three';
import { Palazzo } from './Palazzo';
import { CameraRig } from './CameraRig';
import { Cielo } from './Cielo';
import { PALAZZO } from './coords';

const HERO = PALAZZO.camere.hero;

function Loader({ onDone }: { onDone: () => void }) {
  const { progress, active } = useProgress();
  useEffect(() => {
    if (!active && progress >= 100) onDone();
  }, [active, progress, onDone]);
  return null;
}

/**
 * Scena della home. L'illuminazione dei modelli è precalcolata con Cycles (lightmap),
 * quindi non servono ombre né luci in tempo reale: stessa resa su desktop e telefono.
 */
export default function Experience() {
  const [ready, setReady] = useState(false);
  const { progress } = useProgress();
  const mobile = useMemo(() => window.matchMedia('(max-width: 820px), (pointer: coarse)').matches, []);

  return (
    <>
      <Canvas
        className="home__canvas"
        dpr={mobile ? [1, 1.5] : [1, 2]}
        camera={{ fov: HERO.fov_v, near: 0.1, far: 4000, position: [HERO.pos[0], HERO.pos[1], HERO.pos[2] + 18] }}
        gl={{ antialias: false, toneMapping: NoToneMapping, outputColorSpace: SRGBColorSpace, powerPreference: 'high-performance', stencil: false }}
      >
        <Suspense fallback={null}>
          <Cielo />
          <Palazzo exposure={1.1} />
        </Suspense>
        <CameraRig />
        <EffectComposer multisampling={0} enableNormalPass={false}>
          <Bloom mipmapBlur intensity={0.65} luminanceThreshold={0.92} luminanceSmoothing={0.25} />
          <ToneMapping mode={ToneMappingMode.AGX} />
          <BrightnessContrast contrast={0.1} />
          <Vignette offset={0.3} darkness={0.5} />
          <SMAA />
        </EffectComposer>
        <Loader onDone={() => setReady(true)} />
      </Canvas>
      <div className={`home__loader ${ready ? 'is-done' : ''}`} aria-hidden={ready}>
        <span className="home__loader-label">Caricamento della scena 3D</span>
        <span className="home__loader-bar">
          <span style={{ transform: `scaleX(${progress / 100})` }} />
        </span>
      </div>
    </>
  );
}
