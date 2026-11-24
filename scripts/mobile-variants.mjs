// Varianti leggere per telefoni e tablet (stessa geometria, texture più piccole):
// meno dati da scaricare e soprattutto meno memoria video, che sui telefoni è il limite reale.
// Uso: node scripts/mobile-variants.mjs  (dopo aver aggiornato i modelli in public/models)
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { textureCompress } from '@gltf-transform/functions';
import { MeshoptEncoder, MeshoptDecoder } from 'meshoptimizer';
import sharp from 'sharp';
import { mkdirSync, statSync } from 'node:fs';

const OUT = 'public/models/m';
mkdirSync(OUT, { recursive: true });
await MeshoptEncoder.ready;
await MeshoptDecoder.ready;
const io = new NodeIO()
  .registerExtensions(ALL_EXTENSIONS)
  .registerDependencies({ 'meshopt.encoder': MeshoptEncoder, 'meshopt.decoder': MeshoptDecoder });
const mb = (f) => (statSync(f).size / 1e6).toFixed(2);

for (const name of ['palazzo', 'roma', 'appartamento', 'colosseo']) {
  const src = `public/models/${name}.glb`;
  const dst = `${OUT}/${name}.glb`;
  const doc = await io.read(src);
  await doc.transform(
    // pietra della facciata 1024 px (in primo piano nella home), tutto il resto 512 px
    textureCompress({ encoder: sharp, targetFormat: 'webp', quality: 80, resize: [1024, 1024], pattern: /stone_cream|slab_cream/ }),
    textureCompress({ encoder: sharp, targetFormat: 'webp', quality: 78, resize: [512, 512], pattern: /^(?!.*(stone_cream|slab_cream)).*$/ }),
  );
  await io.write(dst, doc);
  console.log(`${src} (${mb(src)} MB) → ${dst} (${mb(dst)} MB)`);
}

// luce precalcolata di palazzo e Colosseo a 1024 px (quella dell'appartamento resta a 2048: si vede da vicino)
for (const name of ['lm_palazzo', 'lm_colosseo']) {
  const src = `public/models/${name}.webp`;
  const dst = `${OUT}/${name}.webp`;
  await sharp(src).resize(1024, 1024).webp({ quality: 90 }).toFile(dst);
  console.log(`${src} (${mb(src)} MB) → ${dst} (${mb(dst)} MB)`);
}

// cielo di sfondo a 2k
await sharp('public/hdri/cielo-4k.jpg').resize(2048, 1024).jpeg({ quality: 88, mozjpeg: true }).toFile('public/hdri/cielo-2k.jpg');
console.log(`public/hdri/cielo-2k.jpg (${mb('public/hdri/cielo-2k.jpg')} MB)`);
