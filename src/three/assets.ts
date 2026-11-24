/**
 * Telefoni e tablet: stesse scene, texture più piccole (public/models/m, scripts/mobile-variants.mjs).
 * Riduce download e soprattutto memoria video, il vero limite dei telefoni.
 */
export const MOBILE = typeof window !== 'undefined' && window.matchMedia('(max-width: 820px), (pointer: coarse)').matches;

const VARIANTI = new Set([
  '/models/palazzo.glb',
  '/models/roma.glb',
  '/models/appartamento.glb',
  '/models/colosseo.glb',
  '/models/lm_palazzo.webp',
  '/models/lm_colosseo.webp',
]);

/** Percorso dell'asset adatto al dispositivo. */
export function asset(path: string) {
  if (!MOBILE) return path;
  if (path === '/hdri/cielo-4k.jpg') return '/hdri/cielo-2k.jpg';
  return VARIANTI.has(path) ? path.replace('/models/', '/models/m/') : path;
}
