import type { Citta } from './site';

export type Contratto = 'affitto' | 'acquisto';
export type TipoImmobile = 'appartamento' | 'villa';

export interface Immobile {
  id: string;
  titolo: string;
  contratto: Contratto;
  citta: Citta;
  /** € totali per l'acquisto, € al mese per l'affitto */
  prezzo: number;
  tipo: TipoImmobile;
  giardino: boolean;
  mq: number;
  locali: number;
  bagni: number;
  /** Percorsi in /public, es. "/immobili/via-roma-12/1.webp" */
  foto: string[];
  descrizione: string;
  /** Link facoltativo al tour virtuale a 360° */
  tour360?: string;
}

/**
 * Catalogo degli immobili pubblicati.
 * Volutamente vuoto: qui vanno inseriti solo immobili reali dell'agenzia
 * (oppure verrà collegato il gestionale). Nessun annuncio dimostrativo.
 */
export const IMMOBILI: Immobile[] = [];

export const FASCE_BUDGET: Record<Contratto, { id: string; label: string; min: number; max: number }[]> = {
  affitto: [
    { id: 'a1', label: 'Fino a 500 €/mese', min: 0, max: 500 },
    { id: 'a2', label: '500 – 800 €/mese', min: 500, max: 800 },
    { id: 'a3', label: '800 – 1.200 €/mese', min: 800, max: 1200 },
    { id: 'a4', label: '1.200 – 2.000 €/mese', min: 1200, max: 2000 },
    { id: 'a5', label: 'Oltre 2.000 €/mese', min: 2000, max: Infinity },
  ],
  acquisto: [
    { id: 'v1', label: 'Fino a 100.000 €', min: 0, max: 100_000 },
    { id: 'v2', label: '100.000 – 200.000 €', min: 100_000, max: 200_000 },
    { id: 'v3', label: '200.000 – 300.000 €', min: 200_000, max: 300_000 },
    { id: 'v4', label: '300.000 – 500.000 €', min: 300_000, max: 500_000 },
    { id: 'v5', label: 'Oltre 500.000 €', min: 500_000, max: Infinity },
  ],
};
