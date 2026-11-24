import { useEffect, useRef, useState } from 'react';
import { cinematic } from '../three/cinematic';
import { AGENZIA } from '../data/site';

/** Didascalie del film della home, sincronizzate con l'avanzamento della camera (cinematic.flight). */
const CAPITOLI = [
  { da: 0.0, a: 0.13, titolo: 'Domus Re Immobiliare', sotto: `Agenzia immobiliare · ${AGENZIA.citta}` },
  { da: 0.22, a: 0.5, titolo: 'Roma', sotto: 'Colosseo e Colle Oppio' },
  { da: 0.6, a: 0.71, titolo: 'Il palazzo', sotto: 'Ricostruzione 3D dalla fotografia' },
  { da: 0.72, a: 0.83, titolo: 'Appartamento dimostrativo', sotto: 'Salone · 51,7 m²' },
  { da: 0.85, a: 0.975, titolo: 'Planimetria 3D', sotto: '148 m² · 2 camere · 2 bagni · balcone' },
  { da: 0.978, a: 1.01, titolo: 'Vista dal balcone', sotto: 'Colle Oppio e Colosseo' },
];

export function Didascalie() {
  const [i, setI] = useState(0);
  const last = useRef(0);
  useEffect(() => {
    let raf = 0;
    const tick = () => {
      const f = cinematic.flight;
      const k = CAPITOLI.findIndex((c) => f >= c.da && f < c.a);
      if (k !== last.current) {
        last.current = k;
        setI(k);
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, []);
  const c = i >= 0 ? CAPITOLI[i] : null;
  return (
    <p className={`didascalia ${c ? 'is-visible' : ''}`} aria-live="off">
      <span className="didascalia__titolo">{c?.titolo ?? ''}</span>
      <span className="didascalia__sotto">{c?.sotto ?? ''}</span>
    </p>
  );
}
