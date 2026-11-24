// Ricalca il logo (oro su nero) in un SVG vettoriale monocromatico.
// Uso: node scripts/trace-logo.mjs reference/logo-originale.jpg src/assets/logo-domus-re.svg
import sharp from 'sharp';
import potrace from 'potrace';
import { writeFile } from 'node:fs/promises';

const [input, output] = process.argv.slice(2);
if (!input || !output) {
  console.error('Uso: node scripts/trace-logo.mjs <input> <output.svg>');
  process.exit(1);
}

// Upscale + maschera: tutto ciò che è "oro" (luminanza/saturazione alta) diventa nero su bianco.
const { data, info } = await sharp(input)
  .resize({ width: 2400 })
  .raw()
  .toBuffer({ resolveWithObject: true });

const mask = Buffer.alloc(info.width * info.height);
for (let i = 0, p = 0; i < mask.length; i++, p += info.channels) {
  const r = data[p], g = data[p + 1], b = data[p + 2];
  const lum = 0.2126 * r + 0.7152 * g + 0.0722 * b;
  mask[i] = lum > 55 ? 0 : 255; // logo nero, sfondo bianco per potrace
}

const png = await sharp(mask, { raw: { width: info.width, height: info.height, channels: 1 } })
  .median(5)
  .png()
  .toBuffer();

const svg = await new Promise((resolve, reject) =>
  potrace.trace(
    png,
    { threshold: 128, turdSize: 60, optTolerance: 0.4, color: 'currentColor', background: 'transparent' },
    (err, out) => (err ? reject(err) : resolve(out)),
  ),
);

// Ritaglia il viewBox sul contenuto reale.
const pathMatch = svg.match(/d="([^"]+)"/);
const nums = [...pathMatch[1].matchAll(/-?\d+(\.\d+)?/g)].map((m) => Number(m[0]));
const xs = nums.filter((_, i) => i % 2 === 0), ys = nums.filter((_, i) => i % 2 === 1);
const pad = 20;
const minX = Math.max(0, Math.min(...xs) - pad), minY = Math.max(0, Math.min(...ys) - pad);
const maxX = Math.max(...xs) + pad, maxY = Math.max(...ys) + pad;
const viewBox = `${minX.toFixed(0)} ${minY.toFixed(0)} ${(maxX - minX).toFixed(0)} ${(maxY - minY).toFixed(0)}`;

const clean = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${viewBox}" fill="currentColor" role="img" aria-label="Logo Domus Re"><path fill-rule="evenodd" d="${pathMatch[1]}"/></svg>\n`;
await writeFile(output, clean);
console.log('Logo tracciato →', output, 'viewBox', viewBox, `${(clean.length / 1024).toFixed(1)} KB`);
