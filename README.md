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

## Note

- L'appartamento mostrato nella home è una **ricostruzione dimostrativa immaginaria**, non un immobile in vendita.
- Gli immobili della ricerca si aggiungono in `src/data/immobili.ts` (o collegando il gestionale).
- Su dispositivi senza WebGL la home mostra la foto di riferimento del palazzo.
