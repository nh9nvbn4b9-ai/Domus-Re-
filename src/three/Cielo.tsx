import { useEffect } from 'react';
import { useThree } from '@react-three/fiber';
import { Environment, useTexture } from '@react-three/drei';
import { EquirectangularReflectionMapping, SRGBColorSpace } from 'three';
import { ENV_ROTATION_Y } from './coords';

/** Scala con cui il cielo HDR è stato codificato nel JPEG di sfondo (pipeline: sky 4k). */
const SKY_SCALE = 2;

/**
 * Cielo dell'ora d'oro (Poly Haven, CC0), ruotato in modo che il sole coincida con quello del bake.
 * Illuminazione/riflessi: HDR 1k. Sfondo visibile: JPEG 4k (più nitido e leggero).
 */
export function Cielo({ intensity = 0.48 }: { intensity?: number }) {
  const scene = useThree((s) => s.scene);
  const sky = useTexture('/hdri/cielo-4k.jpg');

  useEffect(() => {
    sky.mapping = EquirectangularReflectionMapping;
    sky.colorSpace = SRGBColorSpace;
    sky.needsUpdate = true;
    const prev = scene.background;
    scene.background = sky;
    scene.backgroundIntensity = intensity * SKY_SCALE;
    scene.backgroundRotation.set(0, ENV_ROTATION_Y, 0);
    return () => {
      scene.background = prev;
    };
  }, [scene, sky, intensity]);

  return <Environment files="/hdri/cielo-1k.hdr" environmentIntensity={0.45} environmentRotation={[0, ENV_ROTATION_Y, 0]} />;
}
