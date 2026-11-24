/**
 * Stato condiviso della sequenza cinematografica (aggiornato da GSAP, letto nei useFrame).
 * - writeClock: secondi trascorsi dall'inizio della scrittura nel cielo (continua a crescere: il fumo deriva)
 * - scroll: avanzamento 0..1 della home "agganciata" durante lo scroll
 */
export const cinematic = {
  writeClock: 0,
  writing: false,
  scroll: 0,
  /** durata della scrittura in secondi, calcolata dal percorso dell'aereo */
  writeDuration: 13,
};
