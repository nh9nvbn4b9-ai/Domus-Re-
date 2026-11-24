import { useEffect, useMemo, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { Html, useGLTF, useTexture } from '@react-three/drei';
import { Mesh, MeshPhysicalMaterial, MeshStandardMaterial, SRGBColorSpace, type Material, type Object3D, type Texture } from 'three';
import { bakedMaterial } from './baked';
import { cinematic } from './cinematic';
import { PALAZZO, fromBlender } from './coords';
import { asset } from './assets';

const URL = asset('/models/appartamento.glb');
const MAPS = {
  normale: '/models/lm_appartamento.webp',
  pianta: '/models/lm_appartamento_pianta.webp',
  alto: '/models/lm_appartamento_alto.webp',
  muri: '/models/lm_pianta_muri.webp',
};
const PIANTA = PALAZZO.appartamento_pianta;

const GROUPS = ['LM_Appartamento', 'LM_AppartamentoAlto', 'LM_PiantaMuri'];

/** Gruppo di appartenenza (nome esatto del nodo: le mesh figlie si chiamano LM_..._1, _2, ...). */
function groupOf(o: Object3D) {
  for (let p: Object3D | null = o; p; p = p.parent) {
    if (GROUPS.includes(p.name)) return p.name;
  }
  return '';
}

/**
 * Appartamento dimostrativo al 3° piano: stesso edificio, stesse finestre, stessa luce del palazzo.
 * Luce Cycles in due versioni sulle stesse UV: "normale" (soffitto chiuso) e "pianta" (sezione a 2,40 m),
 * scambiate quando la camera attraversa il soffitto per la planimetria 3D.
 */
export function Appartamento() {
  const { scene } = useGLTF(URL, false, true);
  const maps = useTexture(MAPS) as Record<keyof typeof MAPS, Texture>;
  const lowMats = useRef<Material[]>([]);
  const groups = useRef<{ alto: Object3D[]; muri: Object3D[] }>({ alto: [], muri: [] });
  const shown = useRef<boolean | null>(null);

  const glass = useMemo(
    () => new MeshPhysicalMaterial({ color: '#d8e0e2', roughness: 0.03, transparent: true, opacity: 0.16, depthWrite: false }),
    [],
  );

  useEffect(() => {
    for (const t of Object.values(maps)) {
      t.flipY = false;
      t.colorSpace = SRGBColorSpace;
      t.channel = 1;
      t.needsUpdate = true;
    }
    lowMats.current = [];
    groups.current = { alto: [], muri: [] };
    scene.traverse((o) => {
      if (!(o instanceof Mesh)) return;
      const g = groupOf(o);
      if (g === 'LM_AppartamentoAlto') groups.current.alto.push(o);
      if (g === 'LM_PiantaMuri') groups.current.muri.push(o);
      const lm = g === 'LM_AppartamentoAlto' ? maps.alto : g === 'LM_PiantaMuri' ? maps.muri : maps.normale;
      const tune = (src: Material): Material => {
        if (!(src instanceof MeshStandardMaterial)) return src;
        if (/Vetro/.test(src.name)) return glass;
        if (!o.geometry.attributes.uv1) return src;
        // metalli (acciaio, ottone): nessuna luce diffusa da cuocere, restano riflettenti col cielo
        if (src.metalness > 0.5) return src;
        if (src.emissiveIntensity > 0 && src.emissive.getHex() !== 0) {
          // paralumi, braci: restano luminosi (bloom)
          const m = src.clone();
          m.lightMap = lm;
          m.lightMapIntensity = Math.PI * 6;
          m.emissiveIntensity = 2.2;
          return m;
        }
        const m = bakedMaterial(src, lm, 1.0);
        if (g === 'LM_Appartamento') lowMats.current.push(m);
        return m;
      };
      o.material = Array.isArray(o.material) ? o.material.map(tune) : tune(o.material);
    });
    shown.current = null; // riapplica lo stato (planimetria o no) ai gruppi appena registrati
  }, [scene, maps, glass]);

  // planimetria: soffitti e muri alti nascosti, muri spessi in sezione, luce "pianta"
  useFrame(() => {
    const p = cinematic.planimetria;
    if (shown.current === p) return;
    shown.current = p;
    groups.current.alto.forEach((o) => (o.visible = !p));
    groups.current.muri.forEach((o) => (o.visible = p));
    for (const m of lowMats.current) {
      (m as MeshStandardMaterial).lightMap = p ? maps.pianta : maps.normale;
    }
  });

  const labels = useMemo(
    () =>
      PIANTA.stanze.filter((s) => !s.nome.startsWith('Disimpegno')).map((s) => ({
        nome: s.nome,
        mq: s.mq,
        pos: fromBlender([(s.x0 + s.x1) / 2, (s.y0 + s.y1) / 2, PIANTA.quota + 0.05]),
      })),
    [],
  );

  return (
    <>
      <primitive object={scene} />
      <Etichette labels={labels} />
    </>
  );
}

function Etichette({ labels }: { labels: { nome: string; mq: number; pos: ReturnType<typeof fromBlender> }[] }) {
  const ref = useRef<HTMLDivElement[]>([]);
  useFrame(() => {
    const o = cinematic.planimetria ? '1' : '0';
    for (const el of ref.current) if (el && el.style.opacity !== o) el.style.opacity = o;
  });
  return (
    <>
      {labels.map((l, i) => (
        <Html key={l.nome} position={l.pos} center zIndexRange={[5, 0]} pointerEvents="none">
          <div
            ref={(el) => {
              if (el) ref.current[i] = el;
            }}
            className="pianta-etichetta"
            style={{ opacity: 0 }}
          >
            <span className="pianta-etichetta__nome">{l.nome}</span>
            <span className="pianta-etichetta__mq">{String(l.mq).replace('.', ',')} m²</span>
          </div>
        </Html>
      ))}
    </>
  );
}

