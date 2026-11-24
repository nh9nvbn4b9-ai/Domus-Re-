// Contenuti ufficiali del sito Domus Re. I testi dei servizi sono riportati alla lettera.

export const AGENZIA = {
  nome: 'Domus Re',
  sottotitolo: 'Immobiliare',
  indirizzo: 'Via Giuseppe Garibaldi, 37',
  cap: '00045',
  citta: 'Genzano di Roma',
  provincia: 'RM',
} as const;

export const INDIRIZZO_COMPLETO = `${AGENZIA.indirizzo}, ${AGENZIA.cap} ${AGENZIA.citta} ${AGENZIA.provincia}`;

const mapsQuery = encodeURIComponent(INDIRIZZO_COMPLETO);
export const MAPS_URL = `https://www.google.com/maps/search/?api=1&query=${mapsQuery}`;
export const MAPS_DIREZIONI_URL = `https://www.google.com/maps/dir/?api=1&destination=${mapsQuery}`;

export const CONTATTI = {
  telefonoVisibile: '351 689 1297',
  telefonoHref: 'tel:+393516891297',
  whatsappHref: 'https://wa.me/393516891297',
  email: 'agenziadomusre@gmail.com',
  emailHref: 'mailto:agenziadomusre@gmail.com',
  facebookHref: 'https://www.facebook.com/share/1LnMXwQwah/?mibextid=wwXIfr',
} as const;

export const whatsappConTesto = (testo: string) =>
  `${CONTATTI.whatsappHref}?text=${encodeURIComponent(testo)}`;

export const SEZIONI = [
  { id: 'home', label: 'Home' },
  { id: 'chi-siamo', label: 'Chi siamo' },
  { id: 'servizi', label: 'I nostri servizi' },
  { id: 'ricerca', label: 'Ricerca appartamenti' },
  { id: 'contatti', label: 'Contatti' },
  { id: 'orari', label: 'Orari' },
  { id: 'approfondimenti', label: 'Approfondimenti' },
  { id: 'dove-ci-troviamo', label: 'Dove ci troviamo' },
] as const;

export type SezioneId = (typeof SEZIONI)[number]['id'];

export const SERVIZI = [
  {
    id: 'compravendita',
    titolo: 'Compravendita',
    testo:
      'Un servizio globale e personalizzato volto a soddisfare qualsiasi esigenza collegata al processo di compravendita.',
  },
  {
    id: 'tecnologia-360',
    titolo: 'Tecnologia 360 gradi',
    testo:
      'Con questa nuova tecnologia puoi visitare virtualmente gli immobili che ti interessano e vedere gli ambienti in ogni dettaglio.',
  },
  {
    id: 'affitto-protetto',
    titolo: 'Affitto protetto',
    testo:
      'Tranquillità di affittare attraverso contratti chiari, consulenza fiscale e registrazione presso l’agenzia delle Entrate.',
  },
  {
    id: 'valutazioni',
    titolo: 'Valutazioni',
    testo:
      "Siamo in grado di provvedere alla individuazione del prezzo realizzabile dalla vendita dell'immobile sia residenziale che commerciale.",
  },
  {
    id: 'affitto-concordato',
    titolo: 'Affitto concordato',
    testo: 'Approfitta degli enormi vantaggi del contratto di locazione a canone concordato',
  },
] as const;

export const CITTA = [
  'Albano Laziale',
  'Genzano di Roma',
  'Lanuvio',
  'Velletri',
  'Marino',
  'Ariccia',
  'Nemi',
  'Frascati',
  'Roma',
] as const;

export type Citta = (typeof CITTA)[number];

/** Fasce orarie in minuti dalla mezzanotte, ora di Roma. Indice 0 = lunedì. */
export type Fascia = readonly [apertura: number, chiusura: number];

const h = (ore: number, minuti = 0) => ore * 60 + minuti;
const GIORNATA_PIENA: readonly Fascia[] = [
  [h(9), h(13)],
  [h(15, 30), h(19, 30)],
];

export const ORARI: readonly { giorno: string; fasce: readonly Fascia[] }[] = [
  { giorno: 'Lunedì', fasce: GIORNATA_PIENA },
  { giorno: 'Martedì', fasce: GIORNATA_PIENA },
  { giorno: 'Mercoledì', fasce: GIORNATA_PIENA },
  { giorno: 'Giovedì', fasce: GIORNATA_PIENA },
  { giorno: 'Venerdì', fasce: GIORNATA_PIENA },
  { giorno: 'Sabato', fasce: [[h(9), h(13)]] },
  { giorno: 'Domenica', fasce: [] },
];
