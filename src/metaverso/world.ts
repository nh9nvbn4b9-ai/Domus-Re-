import * as THREE from 'three';
import { MAX_GLOWS, hexFloorMaterial, horizonMaterial, portalMaterial, roomWallMaterial } from './materials';
import { WARM_WHITE, YELLOW, dotTexture, textPlane } from './textures';

export type AreaId = 'hall' | 'chi-siamo' | 'immobili' | 'contatti';

export const AREA_NAMES: Record<AreaId, string> = {
  hall: 'Hall',
  'chi-siamo': 'Chi siamo',
  immobili: 'Immobili',
  contatti: 'Contatti',
};

export interface Portal {
  group: THREE.Group;
  target: AreaId;
  ringMat: THREE.MeshBasicMaterial;
  surface: THREE.ShaderMaterial;
  label: THREE.Mesh;
  near: number;
}

export interface Area {
  id: AreaId;
  group: THREE.Group;
  origin: THREE.Vector3;
  /** raggio massimo per l'umanoide */
  walk: number;
  /** raggio massimo per la telecamera (stanze chiuse) */
  cam: number;
  spawn: { pos: THREE.Vector3; yaw: number };
  portals: Portal[];
  floor: THREE.ShaderMaterial;
  animated: THREE.ShaderMaterial[];
  tick?: (t: number) => void;
}

const RING_R = 2.3;
const RING_Y = 2.15;

/** yaw per guardare lungo la direzione (dx, dz) sul piano. */
export const yawFor = (dx: number, dz: number) => Math.atan2(-dx, -dz);

function buildPortal(label: string, target: AreaId): Portal {
  const group = new THREE.Group();

  const ringMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(YELLOW).multiplyScalar(3.2) });
  const ring = new THREE.Mesh(new THREE.TorusGeometry(RING_R, 0.075, 16, 128), ringMat);
  ring.position.y = RING_Y;
  group.add(ring);

  // anello esterno sottile, più tenue
  const halo = new THREE.Mesh(
    new THREE.TorusGeometry(RING_R + 0.2, 0.012, 8, 128),
    new THREE.MeshBasicMaterial({ color: new THREE.Color(YELLOW).multiplyScalar(1.2), transparent: true, opacity: 0.6 }),
  );
  halo.position.y = RING_Y;
  group.add(halo);

  const surface = portalMaterial();
  const disc = new THREE.Mesh(new THREE.CircleGeometry(RING_R - 0.03, 96), surface);
  disc.position.y = RING_Y;
  disc.renderOrder = 1;
  group.add(disc);

  const text = textPlane(label.toUpperCase(), 3.7, {
    width: 1024,
    height: 256,
    size: 150,
    color: WARM_WHITE,
    glow: 10,
    letterSpacing: 0.03,
  }, 1);
  text.position.set(0, RING_Y, 0.05);
  text.renderOrder = 3;
  group.add(text);

  // basamento: un piccolo arco luminoso a terra
  const base = new THREE.Mesh(
    new THREE.RingGeometry(0.6, 2.6, 64, 1, Math.PI * 0.08, Math.PI * 0.84),
    new THREE.MeshBasicMaterial({
      color: new THREE.Color(YELLOW).multiplyScalar(0.35),
      transparent: true,
      opacity: 0.5,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    }),
  );
  base.rotation.x = -Math.PI / 2;
  base.position.set(0, 0.012, 0.1);
  base.scale.set(1, 0.55, 1);
  group.add(base);

  return { group, target, ringMat, surface, label: text, near: 0 };
}

function setGlows(floor: THREE.ShaderMaterial, points: THREE.Vector3[], strength = 1) {
  const arr = floor.uniforms.uGlows.value as THREE.Vector3[];
  for (let i = 0; i < MAX_GLOWS; i++) {
    const p = points[i];
    if (p) arr[i].set(p.x, strength, p.z);
    else arr[i].set(0, 0, -1e4);
  }
}

/* -------------------------------------------------------------------------- */
/* Hall                                                                        */
/* -------------------------------------------------------------------------- */

function buildHall(): Area {
  const origin = new THREE.Vector3(0, 0, 0);
  const group = new THREE.Group();

  const floor = hexFloorMaterial(origin, 46);
  const floorMesh = new THREE.Mesh(new THREE.CircleGeometry(48, 128), floor);
  floorMesh.rotation.x = -Math.PI / 2;
  group.add(floorMesh);

  const horizon = new THREE.Mesh(new THREE.CylinderGeometry(60, 60, 30, 96, 1, true), horizonMaterial());
  horizon.position.y = 14;
  group.add(horizon);

  // DOMUS RE scritto sul pavimento
  const logo = textPlane('DOMUS RE', 15, {
    width: 2048,
    height: 512,
    size: 330,
    color: YELLOW,
    glow: 34,
    letterSpacing: 0.08,
    depth: 10,
  }, 1.1);
  logo.rotation.x = -Math.PI / 2;
  logo.position.set(0, 0.02, 4.2);
  logo.renderOrder = 1;
  group.add(logo);

  const tagline = textPlane('AGENZIA IMMOBILIARE', 6.4, {
    width: 1024,
    height: 128,
    size: 64,
    weight: 600,
    color: WARM_WHITE,
    letterSpacing: 0.5,
  }, 0.75);
  tagline.rotation.x = -Math.PI / 2;
  tagline.position.set(0, 0.021, 6.6);
  tagline.renderOrder = 1;
  group.add(tagline);

  // tre portali ad arco, rivolti verso il punto di partenza
  const focus = new THREE.Vector3(0, 0, 10);
  const defs: [string, AreaId, number][] = [
    ['Chi siamo', 'chi-siamo', -36],
    ['Immobili', 'immobili', 0],
    ['Contatti', 'contatti', 36],
  ];
  const portals: Portal[] = [];
  for (const [label, target, deg] of defs) {
    const p = buildPortal(label, target);
    const a = THREE.MathUtils.degToRad(deg);
    const dist = 19;
    p.group.position.set(focus.x + Math.sin(a) * dist, 0, focus.z - Math.cos(a) * dist);
    p.group.lookAt(focus.x, 0, focus.z);
    group.add(p.group);
    portals.push(p);
  }
  setGlows(floor, portals.map((p) => p.group.position));

  // pulviscolo dorato sospeso
  const count = 520;
  const pos = new Float32Array(count * 3);
  for (let i = 0; i < count; i++) {
    const r = 3 + Math.sqrt(Math.random()) * 34;
    const a = Math.random() * Math.PI * 2;
    pos[i * 3] = Math.cos(a) * r;
    pos[i * 3 + 1] = 0.3 + Math.random() * 12;
    pos[i * 3 + 2] = Math.sin(a) * r;
  }
  const dustGeo = new THREE.BufferGeometry();
  dustGeo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  const dust = new THREE.Points(
    dustGeo,
    new THREE.PointsMaterial({
      color: new THREE.Color(YELLOW).multiplyScalar(1.2),
      map: dotTexture(),
      size: 0.07,
      transparent: true,
      opacity: 0.8,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    }),
  );
  group.add(dust);

  return {
    id: 'hall',
    group,
    origin,
    walk: 30,
    cam: Infinity,
    spawn: { pos: new THREE.Vector3(0, 0, 10), yaw: 0 },
    portals,
    floor,
    animated: [floor, ...portals.map((p) => p.surface)],
    tick: (t) => {
      dust.rotation.y = t * 0.012;
      dust.position.y = Math.sin(t * 0.3) * 0.25;
    },
  };
}

/* -------------------------------------------------------------------------- */
/* Stanze (vuote, per ora)                                                    */
/* -------------------------------------------------------------------------- */

const ROOM_R = 16;

function buildRoom(id: AreaId, x: number): Area {
  const origin = new THREE.Vector3(x, 0, 0);
  const group = new THREE.Group();
  group.position.copy(origin);

  const floor = hexFloorMaterial(origin, ROOM_R + 2);
  const floorMesh = new THREE.Mesh(new THREE.CircleGeometry(ROOM_R, 96), floor);
  floorMesh.rotation.x = -Math.PI / 2;
  group.add(floorMesh);

  const wallMat = roomWallMaterial();
  const walls = new THREE.Mesh(new THREE.CylinderGeometry(ROOM_R, ROOM_R, 11, 96, 1, true), wallMat);
  walls.position.y = 5.5;
  group.add(walls);

  // anello di luce a terra al centro della stanza
  const centerRing = new THREE.Mesh(
    new THREE.RingGeometry(4.6, 4.7, 128),
    new THREE.MeshBasicMaterial({ color: new THREE.Color(YELLOW).multiplyScalar(1.1), transparent: true, depthWrite: false }),
  );
  centerRing.rotation.x = -Math.PI / 2;
  centerRing.position.y = 0.02;
  group.add(centerRing);

  const title = textPlane(AREA_NAMES[id].toUpperCase(), 17, {
    width: 2048,
    height: 400,
    size: 260,
    color: YELLOW,
    glow: 30,
    letterSpacing: 0.08,
  }, 1.5);
  title.position.set(0, 5.4, -ROOM_R + 1.2);
  group.add(title);

  const sub = textPlane('Stanza in allestimento', 7, {
    width: 1024,
    height: 128,
    size: 60,
    weight: 500,
    family: '"Manrope Variable", system-ui, sans-serif',
    color: WARM_WHITE,
    letterSpacing: 0.25,
  }, 0.8);
  sub.position.set(0, 3.4, -ROOM_R + 1.2);
  group.add(sub);

  // portale di ritorno alle spalle del punto di partenza
  const exit = buildPortal('Hall', 'hall');
  exit.group.position.set(0, 0, 12.8);
  exit.group.rotation.y = Math.PI;
  group.add(exit.group);
  const exitWorld = exit.group.position.clone().add(origin);
  setGlows(floor, [exitWorld, origin], 0.8);

  return {
    id,
    group,
    origin,
    walk: ROOM_R - 2.2,
    cam: ROOM_R - 0.8,
    spawn: { pos: new THREE.Vector3(x, 0, 2.5), yaw: 0 },
    portals: [exit],
    floor,
    animated: [floor, wallMat, exit.surface],
  };
}

export function buildWorld(scene: THREE.Scene) {
  const areas: Record<AreaId, Area> = {
    hall: buildHall(),
    'chi-siamo': buildRoom('chi-siamo', 400),
    immobili: buildRoom('immobili', 800),
    contatti: buildRoom('contatti', 1200),
  };
  for (const a of Object.values(areas)) {
    a.group.visible = false;
    scene.add(a.group);
  }
  return areas;
}
