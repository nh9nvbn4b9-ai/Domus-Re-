import { Vector3 } from 'three';
import palazzo from '../data/palazzo.json';

export const PALAZZO = palazzo;

/** Blender (Z in alto, facciata verso -Y) → Three.js (Y in alto, facciata verso +Z). */
export const fromBlender = ([x, y, z]: number[]) => new Vector3(x, z, -y);

/** Direzione verso il sole (stessa dei bake Cycles): bassa da sud-ovest, ora d'oro. */
export const SUN_DIR = fromBlender([-0.74, -0.64, 0.2]).normalize();

/** Rotazione del cielo HDRI perché il sole dell'immagine coincida con SUN_DIR. */
export const HDRI_SUN_U = 0.612;
export const ENV_ROTATION_Y = (() => {
  const srcAz = (HDRI_SUN_U - 0.5) * 2 * Math.PI; // atan2(z, x) del sole nell'HDRI (convenzione three)
  const dstAz = Math.atan2(SUN_DIR.z, SUN_DIR.x);
  return srcAz - dstAz;
})();
