import { useEffect, useMemo, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { useGLTF, useTexture } from '@react-three/drei';
import {
  Color,
  DoubleSide,
  Mesh,
  MeshBasicMaterial,
  MeshPhysicalMaterial,
  MeshStandardMaterial,
  SRGBColorSpace,
  type Material,
  type Object3D,
  type Texture,
} from 'three';

const URL = '/models/palazzo.glb';
/** Scala di codifica delle lightmap (pipeline/blender/build_palazzo.py: LM_SCALE). */
const LM_SCALE = 6;
const LIGHTMAPS = {
  LM_Palazzo: '/models/lm_palazzo.webp',
  LM_Contesto: '/models/lm_contesto.webp',
  LM_Strada: '/models/lm_strada.webp',
  LM_Interni: '/models/lm_interni.webp',
} as const;
type LMKey = keyof typeof LIGHTMAPS;

function lightmapGroup(o: Object3D): LMKey | null {
  for (let p: Object3D | null = o; p; p = p.parent) {
    if (p.name in LIGHTMAPS) return p.name as LMKey;
  }
  return null;
}

/**
 * Palazzo ricostruito dalla foto (Blender → glTF + meshopt).
 * L'illuminazione è calcolata con Cycles e applicata come lightMap (seconda UV):
 * luce del tramonto, uplight sulle colonne, rimbalzi e ombre morbide identici al render,
 * senza luci in tempo reale (leggero anche su telefono). L'HDRI resta per i riflessi.
 */
export function Palazzo({ exposure = 1 }: { exposure?: number }) {
  const { scene } = useGLTF(URL, false, true);
  const maps = useTexture(LIGHTMAPS as unknown as Record<LMKey, string>) as Record<LMKey, Texture>;

  const glass = useMemo(
    () =>
      new MeshPhysicalMaterial({
        name: 'VetroWeb',
        color: new Color('#1d1a16'),
        roughness: 0.03,
        metalness: 0,
        transparent: true,
        opacity: 0.2,
        envMapIntensity: 1.5,
        clearcoat: 1,
        clearcoatRoughness: 0.02,
        depthWrite: false,
      }),
    [],
  );

  // Materiali riflettenti: ricevono l'HDRI come envMap esplicita (intensità per materiale),
  // mentre l'ambiente globale resta minimo perché la luce diffusa è già nelle lightmap.
  const reflective = useRef<{ m: MeshStandardMaterial; i: number }[]>([]);
  const envAssigned = useRef(false);
  useFrame(({ scene: s }) => {
    if (envAssigned.current || !s.environment) return;
    for (const { m, i } of reflective.current) {
      m.envMap = s.environment;
      m.envMapIntensity = i;
      m.needsUpdate = true;
    }
    envAssigned.current = true;
  });

  useEffect(() => {
    reflective.current = [{ m: glass, i: 1.6 }];
    envAssigned.current = false;
    for (const t of Object.values(maps)) {
      t.flipY = false;
      t.colorSpace = SRGBColorSpace;
      t.channel = 1;
      t.needsUpdate = true;
    }
    scene.traverse((o) => {
      if (!(o instanceof Mesh)) return;
      const group = lightmapGroup(o);
      const tune = (src: Material): Material => {
        if (!(src instanceof MeshStandardMaterial)) return src;
        if (src.name === 'Vetro') return glass;
        if (src.name.startsWith('AlberoBillboard')) {
          // la luce è già nell'immagine renderizzata con Cycles
          return new MeshBasicMaterial({ map: src.map, alphaTest: 0.45, side: DoubleSide, color: new Color(0.78, 0.78, 0.78) });
        }
        const m = src.clone();
        if (group && o.geometry.attributes.uv1) {
          m.lightMap = maps[group];
          m.lightMapIntensity = Math.PI * LM_SCALE * exposure;
        }
        switch (m.name) {
          case 'TendaSottile':
            m.emissive.set('#ff9d55');
            m.emissiveIntensity = 0.6;
            break;
          case 'SoffittiInterni':
            m.emissive.set('#ffc184');
            m.emissiveIntensity = 0.55;
            break;
          case 'LuceCalda':
            m.emissive.set('#ffc07a');
            m.emissiveIntensity = 14;
            m.toneMapped = false;
            break;
          case 'FerroVerniciato':
          case 'Ottone':
          case 'Bronzo':
            reflective.current.push({ m, i: 1.1 });
            break;
        }
        return m;
      };
      o.material = Array.isArray(o.material) ? o.material.map(tune) : tune(o.material);
      o.castShadow = false;
      o.receiveShadow = false;
    });
  }, [scene, glass, maps, exposure]);

  return <primitive object={scene} />;
}

useGLTF.preload(URL, false, true);
