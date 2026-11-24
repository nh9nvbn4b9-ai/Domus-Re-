/**
 * Controller sullo schermo, sagoma da gamepad moderno, nero con dettagli gialli.
 * Analogico sinistro: avanti / indietro. Analogico destro: visuale.
 * La croce direzionale fa le stesse cose (su/giù cammina, sinistra/destra gira).
 */

const KNOB_TRAVEL = 18; // corsa massima della levetta, in unità SVG
const HIT_R = 48;

const TEMPLATE = /* html */ `
<div class="pad" role="group" aria-label="Controller: analogico sinistro per camminare avanti e indietro, analogico destro per muovere la visuale">
  <svg viewBox="0 0 400 260" aria-hidden="true">
    <defs>
      <linearGradient id="padBody" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#202020"/>
        <stop offset="0.55" stop-color="#0d0d0d"/>
        <stop offset="1" stop-color="#050505"/>
      </linearGradient>
      <linearGradient id="padSheen" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#ffffff" stop-opacity="0.10"/>
        <stop offset="0.4" stop-color="#ffffff" stop-opacity="0"/>
      </linearGradient>
      <radialGradient id="knobTop" cx="0.4" cy="0.35" r="0.75">
        <stop offset="0" stop-color="#3a3a3a"/>
        <stop offset="0.6" stop-color="#151515"/>
        <stop offset="1" stop-color="#060606"/>
      </radialGradient>
      <filter id="padGlow" x="-50%" y="-50%" width="200%" height="200%">
        <feGaussianBlur stdDeviation="2.4" result="b"/>
        <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
      </filter>
    </defs>

    <path class="pad-body" d="M100 36 C150 24 250 24 300 36 C342 45 368 70 381 112 C394 158 398 206 378 230 C358 252 322 246 306 222 C292 200 282 192 262 190 C230 186 170 186 138 190 C118 192 108 200 94 222 C78 246 42 252 22 230 C2 206 6 158 19 112 C32 70 58 45 100 36 Z" fill="url(#padBody)"/>
    <path d="M100 36 C150 24 250 24 300 36 C342 45 368 70 381 112 C394 158 398 206 378 230 C358 252 322 246 306 222 C292 200 282 192 262 190 C230 186 170 186 138 190 C118 192 108 200 94 222 C78 246 42 252 22 230 C2 206 6 158 19 112 C32 70 58 45 100 36 Z" fill="url(#padSheen)" stroke="#ffc61a" stroke-opacity="0.55" stroke-width="1.4"/>

    <!-- finiture gialle sulle impugnature -->
    <path d="M30 150 C26 185 30 212 44 228" class="trim"/>
    <path d="M370 150 C374 185 370 212 356 228" class="trim"/>

    <!-- touchpad con il marchio -->
    <rect x="140" y="38" width="120" height="70" rx="14" fill="#090909" stroke="#2c2c2c"/>
    <path d="M134 46 V100" class="lightbar"/>
    <path d="M266 46 V100" class="lightbar"/>
    <text x="200" y="76" class="pad-brand">DOMUS RE</text>
    <text x="200" y="92" class="pad-sub">IMMOBILIARE</text>

    <!-- tasti piccoli -->
    <rect x="108" y="50" width="9" height="18" rx="4.5" fill="#151515" stroke="#333"/>
    <rect x="283" y="50" width="9" height="18" rx="4.5" fill="#151515" stroke="#333"/>
    <circle cx="200" cy="134" r="10" fill="#0a0a0a" stroke="#ffc61a" stroke-opacity="0.8"/>
    <text x="200" y="137.5" class="pad-home">DR</text>

    <!-- croce direzionale (funzionante) -->
    <g transform="translate(78 104)">
      <g class="dpad" data-dir="up"><rect x="-10" y="-34" width="20" height="25" rx="4"/><path d="M0 -27 L-5 -19 H5 Z"/></g>
      <g class="dpad" data-dir="down"><rect x="-10" y="9" width="20" height="25" rx="4"/><path d="M0 27 L-5 19 H5 Z"/></g>
      <g class="dpad" data-dir="left"><rect x="-34" y="-10" width="25" height="20" rx="4"/><path d="M-27 0 L-19 -5 V5 Z"/></g>
      <g class="dpad" data-dir="right"><rect x="9" y="-10" width="25" height="20" rx="4"/><path d="M27 0 L19 -5 V5 Z"/></g>
    </g>

    <!-- tasti frontali (decorativi) -->
    <g transform="translate(322 104)" class="face">
      <g transform="translate(0 -24)"><circle r="12"/><path d="M0 -5.5 L5.5 4 H-5.5 Z" class="sym"/></g>
      <g transform="translate(24 0)"><circle r="12"/><circle r="5.5" class="sym"/></g>
      <g transform="translate(0 24)"><circle r="12"/><path d="M-4.5 -4.5 L4.5 4.5 M4.5 -4.5 L-4.5 4.5" class="sym"/></g>
      <g transform="translate(-24 0)"><circle r="12"/><rect x="-4.5" y="-4.5" width="9" height="9" class="sym"/></g>
    </g>

    <!-- levette analogiche -->
    <g class="stick" data-side="left" transform="translate(148 152)">
      <circle r="31" class="well"/>
      <g class="knob">
        <circle r="21" fill="url(#knobTop)" stroke="#3a3a3a"/>
        <circle r="15" class="knob-ring"/>
      </g>
      <circle r="${HIT_R}" class="hit"/>
    </g>
    <g class="stick" data-side="right" transform="translate(252 152)">
      <circle r="31" class="well"/>
      <g class="knob">
        <circle r="21" fill="url(#knobTop)" stroke="#3a3a3a"/>
        <circle r="15" class="knob-ring"/>
      </g>
      <circle r="${HIT_R}" class="hit"/>
    </g>
  </svg>
  <div class="pad-legend" aria-hidden="true"><span>Cammina</span><span>Visuale</span></div>
</div>`;

interface StickState {
  x: number;
  y: number;
  pointer: number | null;
  group: SVGGElement;
  knob: SVGGElement;
  hit: SVGCircleElement;
}

export class Controller {
  readonly el: HTMLElement;
  readonly left: StickState;
  readonly right: StickState;
  /** croce direzionale: x -1..1 (sinistra/destra), y -1..1 (su/giù) */
  readonly dpad = { x: 0, y: 0 };
  private readonly dpadPointers = new Map<number, string>();

  constructor(parent: HTMLElement) {
    parent.insertAdjacentHTML('beforeend', TEMPLATE);
    this.el = parent.lastElementChild as HTMLElement;
    const get = (side: string): StickState => {
      const group = this.el.querySelector<SVGGElement>(`.stick[data-side="${side}"]`)!;
      return {
        x: 0,
        y: 0,
        pointer: null,
        group,
        knob: group.querySelector<SVGGElement>('.knob')!,
        hit: group.querySelector<SVGCircleElement>('.hit')!,
      };
    };
    this.left = get('left');
    this.right = get('right');
    this.bindStick(this.left);
    this.bindStick(this.right);
    this.bindDpad();
    this.el.addEventListener('contextmenu', (e) => e.preventDefault());
  }

  private bindStick(s: StickState) {
    const move = (e: PointerEvent) => {
      const r = s.hit.getBoundingClientRect();
      const cx = r.left + r.width / 2;
      const cy = r.top + r.height / 2;
      const maxPx = (KNOB_TRAVEL * r.width) / (HIT_R * 2);
      let dx = (e.clientX - cx) / maxPx;
      let dy = (e.clientY - cy) / maxPx;
      const len = Math.hypot(dx, dy);
      if (len > 1) {
        dx /= len;
        dy /= len;
      }
      s.x = dx;
      s.y = dy;
      this.showKnob(s, dx, dy);
    };
    const release = (e: PointerEvent) => {
      if (e.pointerId !== s.pointer) return;
      s.pointer = null;
      s.x = s.y = 0;
      s.group.classList.remove('active');
      s.knob.classList.add('return');
      this.showKnob(s, 0, 0);
    };
    s.hit.addEventListener('pointerdown', (e) => {
      e.preventDefault();
      s.pointer = e.pointerId;
      s.hit.setPointerCapture(e.pointerId);
      s.group.classList.add('active');
      s.knob.classList.remove('return');
      move(e);
    });
    s.hit.addEventListener('pointermove', (e) => {
      if (e.pointerId === s.pointer) move(e);
    });
    s.hit.addEventListener('pointerup', release);
    s.hit.addEventListener('pointercancel', release);
    s.hit.addEventListener('lostpointercapture', release);
  }

  private bindDpad() {
    const refresh = () => {
      const dirs = new Set(this.dpadPointers.values());
      this.dpad.x = (dirs.has('right') ? 1 : 0) - (dirs.has('left') ? 1 : 0);
      this.dpad.y = (dirs.has('down') ? 1 : 0) - (dirs.has('up') ? 1 : 0);
      this.el.querySelectorAll<SVGGElement>('.dpad').forEach((g) => {
        g.classList.toggle('active', dirs.has(g.dataset.dir!));
      });
    };
    this.el.querySelectorAll<SVGGElement>('.dpad').forEach((g) => {
      g.addEventListener('pointerdown', (e) => {
        e.preventDefault();
        g.setPointerCapture(e.pointerId);
        this.dpadPointers.set(e.pointerId, g.dataset.dir!);
        refresh();
      });
      const up = (e: PointerEvent) => {
        this.dpadPointers.delete(e.pointerId);
        refresh();
      };
      g.addEventListener('pointerup', up);
      g.addEventListener('pointercancel', up);
      g.addEventListener('lostpointercapture', up);
    });
  }

  private showKnob(s: StickState, x: number, y: number) {
    s.knob.setAttribute('transform', `translate(${(x * KNOB_TRAVEL).toFixed(2)} ${(y * KNOB_TRAVEL).toFixed(2)})`);
  }

  /** Mostra sullo schermo i valori di un controller fisico, se non si sta toccando la levetta. */
  mirror(side: 'left' | 'right', x: number, y: number) {
    const s = this[side];
    if (s.pointer !== null) return;
    s.knob.classList.remove('return');
    s.group.classList.toggle('active', Math.hypot(x, y) > 0.2);
    this.showKnob(s, x, y);
  }
}
