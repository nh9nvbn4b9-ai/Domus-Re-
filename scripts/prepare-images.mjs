// Converte le foto di riferimento in WebP ottimizzati per il sito e genera la favicon dal logo.
import sharp from 'sharp';
import { readFile, writeFile } from 'node:fs/promises';

const jobs = [
  // Solo come fallback per dispositivi senza WebGL (la home è una scena 3D).
  ['reference/palazzo-riferimento.jpg', 'public/images/palazzo-fallback.webp', 1200],
  ['reference/sede-giorno.jpg', 'public/images/sede-domus-re.webp', 1600],
];
for (const [src, out, width] of jobs) {
  await sharp(src).resize({ width, withoutEnlargement: true }).webp({ quality: 82 }).toFile(out);
  console.log('→', out);
}

const logo = await readFile('src/assets/logo-domus-re.svg', 'utf8');
const gold = logo.replace('fill="currentColor"', 'fill="#C9A23A"');
await writeFile('public/favicon.svg', gold);
await sharp(Buffer.from(gold)).resize(180, 180, { fit: 'contain', background: '#0E0D0B' })
  .flatten({ background: '#0E0D0B' }).png().toFile('public/apple-touch-icon.png');
console.log('→ favicon.svg, apple-touch-icon.png');
