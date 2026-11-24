/**
 * Lettere a tratto singolo per la scrittura nel cielo (come fa un aereo: tratti continui, fumo
 * acceso/spento fra un tratto e l'altro). Coordinate in "em": altezza 1, origine in basso a sinistra.
 */
export type Stroke = [number, number][];
export interface Glyph {
  width: number;
  strokes: Stroke[];
}

const arc = (cx: number, cy: number, rx: number, ry: number, a0: number, a1: number, n = 18): Stroke =>
  Array.from({ length: n + 1 }, (_, i) => {
    const a = a0 + ((a1 - a0) * i) / n;
    return [cx + rx * Math.cos(a), cy + ry * Math.sin(a)] as [number, number];
  });

const D: Glyph = {
  width: 0.72,
  strokes: [[[0, 0], [0, 1], [0.3, 1], ...arc(0.3, 0.5, 0.42, 0.5, Math.PI / 2, -Math.PI / 2).slice(1), [0, 0]]],
};
const O: Glyph = { width: 0.8, strokes: [arc(0.4, 0.5, 0.4, 0.5, Math.PI / 2, Math.PI / 2 + Math.PI * 2, 36)] };
const M: Glyph = {
  width: 0.86,
  strokes: [[[0, 0], [0, 1], [0.43, 0.38], [0.86, 1], [0.86, 0]]],
};
const U: Glyph = {
  width: 0.72,
  strokes: [[[0, 1], [0, 0.36], ...arc(0.36, 0.36, 0.36, 0.36, Math.PI, Math.PI * 2).slice(1), [0.72, 1]]],
};
const S: Glyph = {
  width: 0.66,
  strokes: [
    [
      ...arc(0.33, 0.75, 0.3, 0.25, 0.15, Math.PI * 1.5, 22),
      ...arc(0.33, 0.25, 0.3, 0.25, Math.PI / 2, -Math.PI * 0.85, 22).slice(1),
    ],
  ],
};
const R: Glyph = {
  width: 0.7,
  strokes: [[[0, 0], [0, 1], [0.34, 1], ...arc(0.34, 0.75, 0.3, 0.25, Math.PI / 2, -Math.PI / 2).slice(1), [0, 0.5], [0.22, 0.5], [0.66, 0]]],
};
const E: Glyph = {
  width: 0.6,
  strokes: [
    [[0.6, 1], [0, 1], [0, 0], [0.6, 0]],
    [[0, 0.52], [0.48, 0.52]],
  ],
};

export const GLYPHS: Record<string, Glyph> = { D, O, M, U, S, R, E };
export const LETTER_GAP = 0.32;
export const SPACE = 0.55;

/** Larghezza in em di una riga di testo. */
export function lineWidth(text: string) {
  let w = 0;
  for (const ch of text) w += ch === ' ' ? SPACE : GLYPHS[ch].width + LETTER_GAP;
  return w - LETTER_GAP;
}
