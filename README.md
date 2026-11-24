# Domus Re Immobiliare — sito web

Sito one-page dell'agenzia immobiliare **Domus Re** di Genzano di Roma, con home cinematografica in 3D in tempo reale.

## Avvio

```bash
npm install
npm run dev       # sviluppo su http://localhost:5173
npm run build     # build di produzione in dist/
npm run preview   # anteprima della build
npm run lint
```

## Tecnologie

| Ambito | Libreria |
|---|---|
| Interfaccia | React 19, TypeScript, Vite |
| 3D in tempo reale | Three.js, React Three Fiber, drei, postprocessing |
| Animazioni | GSAP + ScrollTrigger, Lenis (scroll fluido) |
| Modellazione / luce precalcolata | Blender (modulo Python `bpy`) con Cycles → glTF |
| Texture e arredi | Poly Haven (CC0) — texture fotografiche PBR e modelli scansionati |
| Font (self-hosted) | Cinzel, Cormorant Garamond, Manrope |

## Struttura

```
src/
  data/site.ts         contatti, orari, servizi (testi ufficiali), città
  data/immobili.ts     catalogo immobili (vuoto: inserire solo immobili reali)
  components/          header con menu a tendina, logo, footer
  sections/            Home (3D), Chi siamo, Servizi, Ricerca, Contatti, Orari, Approfondimenti, Dove ci troviamo
  three/               scena 3D della home
  lib/                 scroll fluido e preferenze di movimento
reference/             foto originali fornite (palazzo, logo, sede)
scripts/               ricalco del logo in SVG, preparazione immagini
public/images/         immagini ottimizzate per il web
```

## Script

- `node scripts/trace-logo.mjs reference/logo-originale.jpg src/assets/logo-domus-re.svg` — ricalca il logo in vettoriale.
- `node scripts/prepare-images.mjs` — genera WebP ottimizzati e favicon.

## Pipeline 3D (palazzo)

La scena della home è generata da script, non a mano: rieseguendoli si ottiene sempre lo stesso risultato.

1. **Misure dalla foto** — `pipeline/blender/palazzo_spec.py`: ogni quota è presa in pixel da
   `reference/palazzo-riferimento.jpg` e convertita in metri. Esporta anche `src/data/palazzo.json`
   (piani, assi delle finestre, balcone dell'appartamento, luci, camere) usato dal sito.
2. **Asset CC0** — `python3 pipeline/polyhaven.py texture|hdri|model <id>` scarica da Poly Haven in
   `pipeline/cache/` (non versionata); `python3 pipeline/prepare_textures.py` crea le tinte calibrate sulla foto.
3. **Modellazione + luce** — `pipeline/blender/build_palazzo.py` (Blender 5.3 come modulo Python `bpy`):
   costruisce palazzo, strada e contesto, calcola la luce con Cycles nelle lightmap (denoise OIDN)
   e esporta `pipeline/cache/palazzo_raw.glb`. Con `--render foto|hero` produce un render di controllo.
4. **Alberi** — `pipeline/blender/render_billboards.py`: alberi scansionati renderizzati su sfondo trasparente.
5. **Ottimizzazione web** — `node scripts/optimize-glb.mjs pipeline/cache/palazzo_raw.glb public/models/palazzo.glb`
   (meshopt, WebP, deduplica).

6. **Roma e Colosseo** — `pipeline/blender/build_roma.py` (Colosseo da misure reali in `colosseo.py`,
   isolati, parchi, pini, colli) → `colosseo_raw.glb` con lightmap e `roma_raw.glb`; `--skip-colosseo`
   rigenera solo la città. Texture: `python3 pipeline/prepare_city_textures.py`.
7. **Aereo** — `pipeline/blender/build_aereo.py` → `public/models/aereo.glb`.

```bash
python3 -m venv .venv-blender && .venv-blender/bin/pip install bpy==5.3.0 pillow numpy
.venv-blender/bin/python pipeline/blender/build_palazzo.py --no-trees --lm-size 2048 --lm-samples 64
node scripts/optimize-glb.mjs pipeline/cache/palazzo_raw.glb public/models/palazzo.glb
.venv-blender/bin/python pipeline/blender/build_roma.py --lm-size 2048 --lm-samples 48
node scripts/optimize-glb.mjs pipeline/cache/colosseo_raw.glb public/models/colosseo.glb
node scripts/optimize-glb.mjs pipeline/cache/roma_raw.glb public/models/roma.glb
.venv-blender/bin/python pipeline/blender/build_aereo.py
```

## Note

- L'appartamento mostrato nella home è una **ricostruzione dimostrativa immaginaria**, non un immobile in vendita.
- Gli immobili della ricerca si aggiungono in `src/data/immobili.ts` (o collegando il gestionale).
- Su dispositivi senza WebGL la home mostra la foto di riferimento del palazzo.
