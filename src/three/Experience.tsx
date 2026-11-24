import { Suspense, useEffect, useMemo, useState } from 'react';
import { Canvas } from '@react-three/fiber';
import { useProgress } from '@react-three/drei';
import { EffectComposer, Bloom, ToneMapping, Vignette, SMAA, BrightnessContrast, HueSaturation } from '@react-three/postprocessing';
import { ToneMappingMode } from 'postprocessing';
import { NoToneMapping, SRGBColorSpace } from 'three';
import { Palazzo } from './Palazzo';
import { CameraRig } from './CameraRig';
import { Cielo } from './Cielo';
import { Roma, HAZE } from './Roma';
import { Scrittura } from './Scrittura';
import { PALAZZO } from './coords';

const HERO = PALAZZO.camere.hero;
const EXPOSURE = 0.95;

/** Segnala che la prima scena (cielo + palazzo) è pronta: la città arriva dopo, in background. */
function Ready({ onReady }: { onReady: () => void }) {
  useEffect(() => onReady(), [onReady]);
  return null;
}

/**
 * Scena della home: palazzo e Colosseo con luce precalcolata (Cycles), città con il sole in tempo
 * reale e ombre statiche, aereo che scrive DOMUS RE, volo sopra Roma guidato dallo scroll.
 */
export default function Experience() {
  const [ready, setReady] = useState(false);
  const { progress } = useProgress();
  const mobile = useMemo(() => window.matchMedia('(max-width: 820px), (pointer: coarse)').matches, []);
  // ?exp=0.8 permette di tarare l'esposizione in sviluppo
  const exposure = useMemo(() => Number(new URLSearchParams(window.location.search).get('exp')) || EXPOSURE, []);

  return (
    <>
      <Canvas
        className="home__canvas"
        shadows="percentage"
        dpr={mobile ? [1, 1.5] : [1, 2]}
        camera={{ fov: HERO.fov_v, near: 0.1, far: 40000, position: [HERO.pos[0], HERO.pos[1], HERO.pos[2] + 16] }}
        gl={{ antialias: false, toneMapping: NoToneMapping, outputColorSpace: SRGBColorSpace, powerPreference: 'high-performance', stencil: false }}
      >
        <fogExp2 attach="fog" args={[HAZE, 0.0003]} />
        <Suspense fallback={null}>
          <Cielo />
          <Palazzo exposure={exposure} />
          <Ready onReady={() => setReady(true)} />
        </Suspense>
        <Suspense fallback={null}>
          <Scrittura />
        </Suspense>
        <Suspense fallback={null}>
          <Roma mobile={mobile} />
        </Suspense>
        <CameraRig />
        <EffectComposer multisampling={0} enableNormalPass={false}>
          <Bloom mipmapBlur intensity={0.65} luminanceThreshold={0.92} luminanceSmoothing={0.25} />
          <ToneMapping mode={ToneMappingMode.AGX} />
          <BrightnessContrast contrast={0.14} />
          <HueSaturation saturation={0.1} />
          <Vignette offset={0.3} darkness={0.5} />
          <SMAA />
        </EffectComposer>
      </Canvas>
      <div className={`home__loader ${ready ? 'is-done' : ''}`} aria-hidden={ready}>
        <span className="home__loader-label">Caricamento della scena 3D</span>
        <span className="home__loader-bar">
          <span style={{ transform: `scaleX(${Math.min(1, progress / 100)})` }} />
        </span>
      </div>
    </>
  );
}
