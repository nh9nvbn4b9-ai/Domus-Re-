import '@fontsource/cinzel/600.css';
import '@fontsource/cinzel/700.css';
import '@fontsource-variable/manrope';
import './metaverso.css';
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { Controller } from './controller';
import { Humanoid } from './humanoid';
import { YELLOW } from './textures';
import { AREA_NAMES, type Area, type AreaId, buildWorld, yawFor } from './world';

/* -------------------------------------------------------------------------- */
/* Interfaccia                                                                 */
/* -------------------------------------------------------------------------- */

const root = document.getElementById('mv')!;
root.innerHTML = /* html */ `
  <canvas class="mv-canvas" aria-label="Spazio 3D di Domus Re"></canvas>
  <header class="mv-top">
    <div class="mv-brand">
      <span class="mv-mark">DR</span>
      <span><b>DOMUS RE</b><small>Immobiliare</small></span>
    </div>
    <div class="mv-nav">
      <span class="mv-where" aria-live="polite">Hall</span>
      <button class="mv-menu-btn" type="button" aria-expanded="false" aria-controls="mv-menu" aria-label="Vai a una sezione">
        <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true"><path d="M2 5h14M2 9h14M2 13h14" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>
      </button>
      <nav id="mv-menu" class="mv-menu" hidden>
        ${(Object.keys(AREA_NAMES) as AreaId[])
          .map((id) => `<button type="button" data-go="${id}">${AREA_NAMES[id]}</button>`)
          .join('')}
      </nav>
    </div>
  </header>
  <div class="mv-hint"><b class="mv-hint-title">Benvenuto in Domus Re</b><span class="mv-hint-text">Analogico sinistro: cammina avanti e indietro. Analogico destro: muovi la visuale. Attraversa un portale per entrare.</span></div>
  <div class="mv-title" aria-hidden="true"></div>
  <div class="mv-fade"></div>
  <div class="mv-loading">DOMUS RE</div>
`;

const $ = <T extends Element>(s: string) => root.querySelector<T>(s)!;
const canvas = $<HTMLCanvasElement>('.mv-canvas');
const whereEl = $<HTMLElement>('.mv-where');
const hintEl = $<HTMLElement>('.mv-hint');
const hintText = $<HTMLElement>('.mv-hint-text');
const hintTitle = $<HTMLElement>('.mv-hint-title');
const titleEl = $<HTMLElement>('.mv-title');
const fadeEl = $<HTMLElement>('.mv-fade');
const loadingEl = $<HTMLElement>('.mv-loading');
const menuBtn = $<HTMLButtonElement>('.mv-menu-btn');
const menu = $<HTMLElement>('.mv-menu');

const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
const controller = new Controller(root);

/* -------------------------------------------------------------------------- */
/* Avvio                                                                       */
/* -------------------------------------------------------------------------- */

async function start() {
  await Promise.all([
    document.fonts.load('700 64px Cinzel'),
    document.fonts.load('600 64px Cinzel'),
    document.fonts.load('500 32px "Manrope Variable"'),
  ]).catch(() => undefined);

  let renderer: THREE.WebGLRenderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, antialias: false, powerPreference: 'high-performance' });
  } catch {
    loadingEl.innerHTML =
      '<p>Il tuo browser non supporta la grafica 3D (WebGL). Prova con una versione aggiornata di Chrome, Safari o Firefox.</p>';
    return;
  }
  run(renderer);
}

function run(renderer: THREE.WebGLRenderer) {
  const pixelRatio = Math.min(devicePixelRatio, 1.75);
  renderer.setPixelRatio(pixelRatio);
  renderer.toneMapping = THREE.NeutralToneMapping;
  renderer.toneMappingExposure = 1;

  const scene = new THREE.Scene();
  scene.background = new THREE.Color('#020202');
  const camera = new THREE.PerspectiveCamera(55, 1, 0.1, 160);

  const areas = buildWorld(scene);
  const player = new Humanoid();
  scene.add(player.root);
  scene.updateMatrixWorld(true);

  const rt = new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType, samples: 4 });
  const composer = new EffectComposer(renderer, rt);
  composer.addPass(new RenderPass(scene, camera));
  const bloom = new UnrealBloomPass(new THREE.Vector2(1, 1), 0.45, 0.2, 0.85);
  if (!new URLSearchParams(location.search).has('nobloom')) composer.addPass(bloom);
  composer.addPass(new OutputPass());

  let portrait = false;
  const resize = () => {
    const w = root.clientWidth;
    const h = root.clientHeight;
    portrait = h > w;
    camera.aspect = w / h;
    // il centro ottico sta sopra la metà dello schermo, così l'umanoide non finisce dietro al controller
    const c = portrait ? 0.42 : 0.4;
    const fullH = 2 * h * (1 - c);
    const fov = portrait ? 64 : 52;
    camera.fov = THREE.MathUtils.radToDeg(2 * Math.atan(Math.tan(THREE.MathUtils.degToRad(fov / 2)) * (fullH / h)));
    camera.setViewOffset(w, fullH, 0, fullH - h, w, h);
    camera.updateProjectionMatrix();
    renderer.setSize(w, h, false);
    composer.setPixelRatio(pixelRatio);
    composer.setSize(w, h);
  };
  addEventListener('resize', resize);
  resize();

  /* ------------------------------------------------------------ stato */

  const MAX_FWD = 4.4;
  const MAX_BACK = 2.8;
  const CAM_DIST = 6.2;
  const forward = new THREE.Vector3();
  const pos = new THREE.Vector3();
  let yaw = 0;
  let pitch = 0.2;
  let speed = 0;
  let area: Area = areas.hall;
  let mode: 'intro' | 'play' | 'transition' = 'intro';
  let introT = reducedMotion ? 1 : 0;
  let materialize = 1;
  let travelled = 0;
  let hintTimer = 0;

  const camPos = new THREE.Vector3();
  const camLook = new THREE.Vector3();
  const tmp = new THREE.Vector3();
  const tmp2 = new THREE.Vector3();

  function showArea(next: Area) {
    for (const a of Object.values(areas)) a.group.visible = a === next;
    area = next;
    whereEl.textContent = AREA_NAMES[next.id];
    menu.querySelectorAll<HTMLButtonElement>('button').forEach((b) => {
      b.setAttribute('aria-current', String(b.dataset.go === next.id));
    });
  }

  function placeAt(p: THREE.Vector3, y: number) {
    pos.copy(p);
    yaw = y;
    pitch = 0.2;
    speed = 0;
    computeCamera(1, true);
  }

  function hint(text: string, seconds = 6, title = 'Benvenuto in Domus Re') {
    hintTitle.textContent = title;
    hintText.textContent = text;
    hintEl.classList.remove('off');
    hintTimer = seconds;
  }

  function enter(target: AreaId) {
    if (mode === 'transition' || target === area.id) return;
    const from = area.id;
    mode = 'transition';
    fadeEl.classList.add('on');
    setTimeout(
      () => {
        const next = areas[target];
        showArea(next);
        if (target === 'hall' && from !== 'hall') {
          // di fronte al portale da cui si è usciti, girati verso il centro della hall
          const portal = next.portals.find((p) => p.target === from)!;
          const n = tmp2.set(0, 0, 1).transformDirection(portal.group.matrixWorld);
          placeAt(tmp.copy(portal.group.position).addScaledVector(n, 7.5), yawFor(n.x, n.z));
        } else {
          placeAt(next.spawn.pos, next.spawn.yaw);
        }
        materialize = 0;
        titleEl.innerHTML = `${AREA_NAMES[target].toUpperCase()}<small>${target === 'hall' ? 'Domus Re' : 'Stanza in allestimento'}</small>`;
        titleEl.classList.remove('show');
        void titleEl.offsetWidth;
        titleEl.classList.add('show');
        if (target !== 'hall') hint('Il portale HALL è alle tue spalle: gira la visuale o cammina all\'indietro per tornare.', 6, AREA_NAMES[target]);
        else hintEl.classList.add('off');
        fadeEl.classList.remove('on');
        setTimeout(() => (mode = 'play'), 250);
      },
      reducedMotion ? 160 : 440,
    );
  }

  /* ------------------------------------------------------------ menu */

  menuBtn.addEventListener('click', () => {
    const open = menu.hidden;
    menu.hidden = !open;
    menuBtn.setAttribute('aria-expanded', String(open));
  });
  menu.addEventListener('click', (e) => {
    const b = (e.target as HTMLElement).closest<HTMLButtonElement>('button[data-go]');
    if (!b) return;
    menu.hidden = true;
    menuBtn.setAttribute('aria-expanded', 'false');
    if (mode === 'intro') introT = 1;
    mode = 'play';
    enter(b.dataset.go as AreaId);
  });
  addEventListener('pointerdown', (e) => {
    if (!menu.hidden && !(e.target as HTMLElement).closest('.mv-nav')) {
      menu.hidden = true;
      menuBtn.setAttribute('aria-expanded', 'false');
    }
  });

  /* ------------------------------------------------------------ input */

  const keys = new Set<string>();
  addEventListener('keydown', (e) => {
    if (e.code === 'Escape') {
      menu.hidden = true;
      menuBtn.setAttribute('aria-expanded', 'false');
    }
    if (/^(Arrow|Key[WASD])/.test(e.code) && !(e.target as HTMLElement).closest('button')) e.preventDefault();
    keys.add(e.code);
  });
  addEventListener('keyup', (e) => keys.delete(e.code));
  addEventListener('blur', () => keys.clear());
  const key = (...codes: string[]) => (codes.some((c) => keys.has(c)) ? 1 : 0);

  // trascinare sullo schermo muove la visuale (mouse o dito)
  let drag: { id: number; x: number; y: number } | null = null;
  const lookDelta = { x: 0, y: 0 };
  canvas.addEventListener('pointerdown', (e) => {
    drag = { id: e.pointerId, x: e.clientX, y: e.clientY };
    canvas.setPointerCapture(e.pointerId);
  });
  canvas.addEventListener('pointermove', (e) => {
    if (!drag || e.pointerId !== drag.id) return;
    lookDelta.x += e.clientX - drag.x;
    lookDelta.y += e.clientY - drag.y;
    drag.x = e.clientX;
    drag.y = e.clientY;
  });
  const endDrag = (e: PointerEvent) => {
    if (drag && e.pointerId === drag.id) drag = null;
  };
  canvas.addEventListener('pointerup', endDrag);
  canvas.addEventListener('pointercancel', endDrag);

  const dead = (v: number, d = 0.12) => (Math.abs(v) < d ? 0 : (v - Math.sign(v) * d) / (1 - d));
  const curve = (v: number) => Math.sign(v) * Math.abs(v) ** 1.5;
  const clamp1 = (v: number) => Math.max(-1, Math.min(1, v));

  function readInput() {
    let move = -dead(controller.left.y, 0.08) - controller.dpad.y + key('KeyW', 'ArrowUp') - key('KeyS', 'ArrowDown');
    let turn = curve(dead(controller.right.x, 0.08)) + controller.dpad.x * 0.8 + key('KeyD', 'ArrowRight') - key('KeyA', 'ArrowLeft');
    let look = curve(dead(controller.right.y, 0.08));

    for (const gp of navigator.getGamepads?.() ?? []) {
      if (!gp || gp.axes.length < 4) continue;
      const [, ly, rx, ry] = gp.axes;
      controller.mirror('left', 0, ly);
      controller.mirror('right', rx, ry);
      move += -dead(ly);
      turn += curve(dead(rx));
      look += curve(dead(ry));
      if (gp.buttons[12]?.pressed) move += 1;
      if (gp.buttons[13]?.pressed) move -= 1;
      break;
    }
    return { move: clamp1(move), turn: clamp1(turn), look: clamp1(look) };
  }

  /* ------------------------------------------------------------ telecamera */

  const ease = (x: number) => (x < 0.5 ? 4 * x * x * x : 1 - (-2 * x + 2) ** 3 / 2);

  function computeCamera(k: number, snap = false) {
    forward.set(-Math.sin(yaw), 0, -Math.cos(yaw));
    const e = ease(Math.min(1, introT));
    const angle = yaw + Math.PI * (1 - e);
    const dist = THREE.MathUtils.lerp(1.15, CAM_DIST, e);
    const elev = THREE.MathUtils.lerp(0.04, pitch, e);
    const pivotY = THREE.MathUtils.lerp(1.66, 1.5, e);

    tmp.set(
      pos.x + Math.sin(angle) * Math.cos(elev) * dist,
      pos.y + pivotY + Math.sin(elev) * dist,
      pos.z + Math.cos(angle) * Math.cos(elev) * dist,
    );
    tmp.y = Math.max(0.35, tmp.y);
    // nelle stanze la telecamera resta dentro le pareti
    const dx = tmp.x - area.origin.x;
    const dz = tmp.z - area.origin.z;
    const r = Math.hypot(dx, dz);
    if (r > area.cam) {
      tmp.x = area.origin.x + (dx / r) * area.cam;
      tmp.z = area.origin.z + (dz / r) * area.cam;
    }

    tmp2.set(pos.x, pos.y + THREE.MathUtils.lerp(1.66, 1.35, e), pos.z).addScaledVector(forward, 1.2 * e);

    if (snap) {
      camPos.copy(tmp);
      camLook.copy(tmp2);
    } else {
      camPos.lerp(tmp, k);
      camLook.lerp(tmp2, k);
    }
    camera.position.copy(camPos);
    camera.lookAt(camLook);
  }

  /* ------------------------------------------------------------ ciclo */

  showArea(areas.hall);
  placeAt(areas.hall.spawn.pos, areas.hall.spawn.yaw);
  hintEl.classList.add('off');

  let last = performance.now();
  let time = 0;
  const yellow = new THREE.Color(YELLOW);

  function frame(now: number) {
    const dt = Math.min(0.05, (now - last) / 1000);
    last = now;
    time += dt;

    const input = readInput();

    if (mode === 'intro') {
      introT += dt / 3.4;
      if (introT >= 1) {
        introT = 1;
        mode = 'play';
        hint(
          portrait || matchMedia('(pointer: coarse)').matches
            ? 'Analogico sinistro: cammina avanti e indietro. Analogico destro: muovi la visuale. Attraversa un portale per entrare.'
            : 'Analogico sinistro (o W/S): cammina. Analogico destro (o A/D, trascina col mouse): visuale. Attraversa un portale per entrare.',
          12,
        );
      }
    }

    let targetSpeed = 0;
    if (mode === 'play') {
      yaw -= input.turn * 2.3 * dt + lookDelta.x * 0.0055;
      pitch = THREE.MathUtils.clamp(pitch + input.look * 1.3 * dt + lookDelta.y * 0.004, -0.22, 0.85);
      targetSpeed = input.move > 0 ? input.move * MAX_FWD : input.move * MAX_BACK;
    }
    lookDelta.x = lookDelta.y = 0;
    speed += (targetSpeed - speed) * (1 - Math.exp(-dt * 9));
    if (Math.abs(speed) < 0.01 && targetSpeed === 0) speed = 0;

    forward.set(-Math.sin(yaw), 0, -Math.cos(yaw));
    pos.addScaledVector(forward, speed * dt);
    travelled += Math.abs(speed * dt);
    const dx = pos.x - area.origin.x;
    const dz = pos.z - area.origin.z;
    const r = Math.hypot(dx, dz);
    if (r > area.walk) {
      pos.x = area.origin.x + (dx / r) * area.walk;
      pos.z = area.origin.z + (dz / r) * area.walk;
    }

    player.root.position.copy(pos);
    player.root.rotation.y = yaw;
    player.update(dt, speed, MAX_FWD);
    materialize = Math.min(1, materialize + dt * 1.6);
    player.setOpacity(materialize);

    // portali: luce quando ci si avvicina, ingresso quando si attraversa l'anello
    for (const p of area.portals) {
      p.group.worldToLocal(tmp.copy(pos));
      const d = Math.hypot(tmp.x, tmp.z);
      const nearTarget = THREE.MathUtils.clamp(1 - (d - 1.5) / 7, 0, 1);
      p.near += (nearTarget - p.near) * (1 - Math.exp(-dt * 6));
      p.surface.uniforms.uNear.value = p.near;
      p.ringMat.color.copy(yellow).multiplyScalar(3.2 + p.near * 3 + Math.sin(time * 3) * 0.3 * p.near);
      p.label.scale.setScalar(1 + p.near * 0.08);
      if (mode === 'play' && Math.abs(tmp.z) < 0.45 && Math.abs(tmp.x) < 1.65) enter(p.target);
    }

    for (const m of area.animated) m.uniforms.uTime.value = time;
    area.floor.uniforms.uPlayer.value.copy(pos);
    area.tick?.(time);

    computeCamera(1 - Math.exp(-dt * 9));

    if (hintTimer > 0) {
      hintTimer -= dt;
      if (hintTimer <= 0 || (area.id === 'hall' && travelled > 14 && hintTimer < 10)) {
        hintTimer = 0;
        hintEl.classList.add('off');
      }
    }

    composer.render(dt);
    requestAnimationFrame(frame);
  }

  requestAnimationFrame((t) => {
    last = t;
    loadingEl.classList.add('done');
    frame(t);
  });
}

void start();
