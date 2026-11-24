// Ottimizza il GLB esportato da Blender per il web:
// deduplica, saldatura vertici, compressione meshopt, texture WebP con risoluzione per tipo.
// Uso: node scripts/optimize-glb.mjs pipeline/cache/palazzo_raw.glb public/models/palazzo.glb
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { dedup, prune, weld, reorder, quantize, meshopt, textureCompress, flatten, join } from '@gltf-transform/functions';
import { MeshoptEncoder, MeshoptDecoder } from 'meshoptimizer';
import sharp from 'sharp';
import { statSync } from 'node:fs';

const [input, output, ...flags] = process.argv.slice(2);
// --solo-colore: modelli con luce precalcolata (lightmap): nel sito usano solo il colore della texture,
// quindi rilievo, rugosità e occlusione si possono togliere (file molto più leggero)
const SOLO_COLORE = flags.includes('--solo-colore');
await MeshoptEncoder.ready;
await MeshoptDecoder.ready;
const io = new NodeIO()
  .registerExtensions(ALL_EXTENSIONS)
  .registerDependencies({ 'meshopt.encoder': MeshoptEncoder, 'meshopt.decoder': MeshoptDecoder });

const doc = await io.read(input);
const root = doc.getRoot();

// Rimuove riferimenti a texture senza immagine (esportazioni fallite).
for (const tex of root.listTextures()) {
  if (!tex.getImage() || tex.getImage().byteLength === 0) tex.dispose();
}

if (SOLO_COLORE) {
  for (const m of root.listMaterials()) {
    const keep = /Vetro|Glass/i.test(m.getName()) || m.getEmissiveTexture();
    if (keep) continue;
    m.setNormalTexture(null);
    m.setMetallicRoughnessTexture(null);
    m.setOcclusionTexture(null);
  }
}

await doc.transform(
  dedup(),
  flatten(),
  join({ keepNamed: true }),
  weld(),
  prune({ keepAttributes: true }),
  // Pietra della facciata e lastre a 2048 px, normali 1024, resto 1024/512.
  textureCompress({ encoder: sharp, targetFormat: 'webp', quality: 82, resize: [2048, 2048], pattern: /stone_cream|slab_cream/ }),
  textureCompress({ encoder: sharp, targetFormat: 'webp', quality: 80, resize: [1024, 1024], pattern: /^(?!.*(stone_cream|slab_cream)).*$/ }),
  reorder({ encoder: MeshoptEncoder }),
  quantize(),
  meshopt({ encoder: MeshoptEncoder, level: 'high' }),
);

await io.write(output, doc);
const mb = (f) => (statSync(f).size / 1e6).toFixed(2);
console.log(`${input} (${mb(input)} MB) → ${output} (${mb(output)} MB)`);
console.log('mesh:', root.listMeshes().length, 'materiali:', root.listMaterials().length, 'texture:', root.listTextures().length);
