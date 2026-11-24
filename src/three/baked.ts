import { MeshBasicMaterial, type MeshStandardMaterial, type Texture } from 'three';

/** Scala con cui le lightmap Cycles sono codificate nel WebP (vedi pipeline/blender: LM_SCALE). */
export const LM_SCALE = 6;

/**
 * Materiale "cotto": colore della texture × luce calcolata con Cycles.
 * È un MeshBasicMaterial, quindi ignora le luci in tempo reale (il sole della città non si somma
 * alla luce già presente nella lightmap). MeshBasic divide la lightmap per π: qui si compensa.
 */
export function bakedMaterial(src: MeshStandardMaterial, lightMap: Texture, exposure = 1): MeshBasicMaterial {
  const m = new MeshBasicMaterial({
    name: `${src.name}_baked`,
    map: src.map,
    color: src.color.clone(),
    lightMap,
    lightMapIntensity: Math.PI * LM_SCALE * exposure,
    transparent: src.transparent,
    opacity: src.opacity,
    alphaTest: src.alphaTest,
    side: src.side,
  });
  return m;
}
