import { useEffect, useMemo, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { useGLTF, useTexture } from '@react-three/drei';
import { bakedMaterial, LM_SCALE } from './baked';
import { SECTION } from './clip';
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
import { asset } from './assets';

const URL = asset('/models/palazzo.glb');
/** Materiali con emissione propria: restano PBR (la luce emessa non è nella lightmap). */
const EMISSIVI = new Set(['TendaSottile', 'SoffittiInterni', 'LuceCalda']);
const LIGHTMAPS = {
  LM_Palazzo: asset('/models/lm_palazzo.webp'),
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
 * L'illuminazione è calcolata con Cycles e applicata come lightMap (seconda UV) su materiali
 * che ignorano le luci in tempo reale: luce del tramonto, uplight sulle colonne, rimbalzi e ombre
 * morbide come nel render, identici su desktop e telefono. L'HDRI resta per i riflessi dei vetri.
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
        const baked = group && o.geometry.attributes.uv1;
        if (baked && !EMISSIVI.has(src.name)) return bakedMaterial(src, maps[group], exposure);
        const m = src.clone();
        if (baked) {
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
        }
        return m;
      };
      o.material = Array.isArray(o.material) ? o.material.map(tune) : tune(o.material);
      // sezione della planimetria: il palazzo si taglia sopra il pavimento del 3° piano
      for (const m of Array.isArray(o.material) ? o.material : [o.material]) m.clippingPlanes = [SECTION];
      o.castShadow = false;
      o.receiveShadow = false;
    });
  }, [scene, glass, maps, exposure]);

  return <primitive object={scene} />;
}

useGLTF.preload(URL, false, true);
