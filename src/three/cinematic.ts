import { gsap } from 'gsap';

/**
 * Stato condiviso della sequenza cinematografica della home (scritto da GSAP, letto nei useFrame).
 * La sequenza parte da sola, come un filmato: non dipende da scroll o mouse.
 *
 * - writeClock: secondi dall'inizio della scrittura nel cielo (continua a crescere: il fumo deriva)
 * - flight: avanzamento 0..1 del volo (facciata → tetto → Roma → Colosseo)
 * - introDz: arretramento iniziale della camera (carrellata d'ingresso)
 */
export const cinematic = {
  writeClock: 0,
  writing: false,
  flight: 0,
  introDz: 16,
  paused: false,
  /** durata della scrittura in secondi */
  writeDuration: 13,
};

type Listener = (paused: boolean) => void;
const listeners = new Set<Listener>();
let master: gsap.core.Timeline | null = null;
let pausedByUser = false;

export function onPauseChange(fn: Listener) {
  listeners.add(fn);
  fn(cinematic.paused);
  return () => listeners.delete(fn);
}

function setPausedState(p: boolean) {
  cinematic.paused = p;
  if (p) master?.pause();
  else master?.resume();
  listeners.forEach((l) => l(p));
}

/** Pausa/riproduzione richiesta dall'utente (pulsante nella home). */
export function toggleUserPause() {
  if (!master) return;
  pausedByUser = !cinematic.paused;
  setPausedState(pausedByUser);
}

/** Pausa automatica quando la home esce dallo schermo (non sovrascrive la scelta dell'utente). */
export function setVisible(visible: boolean) {
  if (!master || pausedByUser) return;
  setPausedState(!visible);
}

/**
 * Costruisce e avvia la sequenza: carrellata d'ingresso e scrittura DOMUS RE, poi il volo sopra Roma
 * fino al Colosseo, sosta, dissolvenza e ritorno al palazzo (in ciclo, la scritta resta nel cielo).
 */
export function startSequence({ reduce, fade }: { reduce: boolean; fade: string }) {
  master?.kill();
  if (reduce) {
    // movimento ridotto: nessun avvio automatico, scritta già completa
    cinematic.introDz = 0;
    cinematic.writing = true;
    cinematic.writeClock = cinematic.writeDuration + 30;
    master = gsap.timeline({ paused: true });
    buildLoop(master, fade);
    pausedByUser = true;
    setPausedState(true);
    return master;
  }
  master = gsap.timeline();
  master.to(cinematic, { introDz: 0, duration: 5, ease: 'power3.out' }, 0);
  master.call(() => void (cinematic.writing = true), undefined, 1.6);
  const loop = gsap.timeline({ repeat: -1 });
  buildLoop(loop, fade);
  master.add(loop, 1.6 + cinematic.writeDuration + 2.5);
  pausedByUser = false;
  setPausedState(false);
  return master;
}

function buildLoop(tl: gsap.core.Timeline, fade: string) {
  tl.to(cinematic, { flight: 1, duration: 30, ease: 'sine.inOut' })
    .to({}, { duration: 3.5 })
    .to(fade, { autoAlpha: 1, duration: 1.4, ease: 'power2.in' })
    .set(cinematic, { flight: 0, introDz: 10 })
    .to({}, { duration: 0.9 }) // la camera raggiunge il palazzo mentre lo schermo è nero
    .to(fade, { autoAlpha: 0, duration: 1.6, ease: 'power2.out' })
    .to(cinematic, { introDz: 0, duration: 4, ease: 'power3.out' }, '<')
    .to({}, { duration: 5 });
}
