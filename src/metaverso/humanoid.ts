import * as THREE from 'three';
import { groundRingMaterial, hologramMaterial } from './materials';

/**
 * Umanoide olografico costruito con primitive (capsule e sfere).
 * Guarda verso -Z: con rotation.y = yaw la direzione "avanti" è (-sin yaw, 0, -cos yaw).
 */
export class Humanoid {
  readonly root = new THREE.Group();
  readonly material = hologramMaterial();
  private readonly body = new THREE.Group();
  private readonly ringMat = groundRingMaterial();
  private readonly hips: THREE.Group[] = [];
  private readonly knees: THREE.Group[] = [];
  private readonly shoulders: THREE.Group[] = [];
  private readonly elbows: THREE.Group[] = [];
  private readonly torso = new THREE.Group();
  private readonly head = new THREE.Group();
  private phase = 0;
  private amp = 0;
  private t = 0;

  constructor() {
    const m = this.material;
    const capsule = (r: number, len: number) => new THREE.Mesh(new THREE.CapsuleGeometry(r, len, 6, 14), m);

    this.root.add(this.body);
    this.body.position.y = 0.98;

    // bacino e busto
    const pelvis = capsule(0.13, 0.12);
    pelvis.rotation.z = Math.PI / 2;
    pelvis.scale.set(1, 1.05, 0.75);
    this.body.add(pelvis);

    this.torso.position.y = 0.08;
    this.body.add(this.torso);
    const chest = capsule(0.17, 0.26);
    chest.position.y = 0.3;
    chest.scale.set(1.2, 1, 0.68);
    this.torso.add(chest);
    const abs = capsule(0.13, 0.12);
    abs.position.y = 0.08;
    abs.scale.set(1.05, 1, 0.7);
    this.torso.add(abs);

    // testa
    this.head.position.y = 0.56;
    this.torso.add(this.head);
    const neck = new THREE.Mesh(new THREE.CylinderGeometry(0.045, 0.055, 0.12, 12), m);
    neck.position.y = 0.02;
    this.head.add(neck);
    const skull = new THREE.Mesh(new THREE.SphereGeometry(0.12, 24, 18), m);
    skull.position.y = 0.17;
    skull.scale.set(0.86, 1.08, 0.98);
    this.head.add(skull);
    const eyeMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(2.6, 2.3, 1.5) });
    for (const s of [-1, 1]) {
      const eye = new THREE.Mesh(new THREE.SphereGeometry(0.011, 10, 8), eyeMat);
      eye.position.set(s * 0.042, 0.18, -0.105);
      eye.scale.set(1.6, 0.8, 0.6);
      this.head.add(eye);
    }

    // braccia
    for (const s of [-1, 1]) {
      const shoulder = new THREE.Group();
      shoulder.position.set(s * 0.25, 0.44, 0);
      shoulder.rotation.z = s * 0.08;
      this.torso.add(shoulder);
      const deltoid = new THREE.Mesh(new THREE.SphereGeometry(0.07, 16, 12), m);
      shoulder.add(deltoid);
      const upper = capsule(0.052, 0.2);
      upper.position.y = -0.16;
      shoulder.add(upper);
      const elbow = new THREE.Group();
      elbow.position.y = -0.31;
      shoulder.add(elbow);
      const fore = capsule(0.044, 0.2);
      fore.position.y = -0.14;
      elbow.add(fore);
      const hand = new THREE.Mesh(new THREE.SphereGeometry(0.048, 12, 10), m);
      hand.position.y = -0.3;
      hand.scale.set(0.8, 1.2, 0.6);
      elbow.add(hand);
      this.shoulders.push(shoulder);
      this.elbows.push(elbow);
    }

    // gambe
    for (const s of [-1, 1]) {
      const hip = new THREE.Group();
      hip.position.set(s * 0.1, -0.04, 0);
      this.body.add(hip);
      const thigh = capsule(0.075, 0.3);
      thigh.position.y = -0.22;
      hip.add(thigh);
      const knee = new THREE.Group();
      knee.position.y = -0.45;
      hip.add(knee);
      const shin = capsule(0.058, 0.3);
      shin.position.y = -0.2;
      knee.add(shin);
      const foot = capsule(0.045, 0.12);
      foot.rotation.x = Math.PI / 2;
      foot.position.set(0, -0.46, -0.05);
      knee.add(foot);
      this.hips.push(hip);
      this.knees.push(knee);
    }

    // alone sul pavimento
    const ring = new THREE.Mesh(new THREE.PlaneGeometry(1.6, 1.6), this.ringMat);
    ring.rotation.x = -Math.PI / 2;
    ring.position.y = 0.015;
    ring.renderOrder = 2;
    this.root.add(ring);

    // l'ologramma va disegnato dopo il resto (blending additivo)
    this.root.traverse((o) => {
      if ((o as THREE.Mesh).isMesh && (o as THREE.Mesh).material === m) o.renderOrder = 5;
    });
  }

  /** speed in m/s (negativa all'indietro), maxSpeed per normalizzare l'ampiezza del passo. */
  update(dt: number, speed: number, maxSpeed: number) {
    this.t += dt;
    const target = Math.min(1, Math.abs(speed) / maxSpeed);
    this.amp += (target - this.amp) * (1 - Math.exp(-dt * 8));
    this.phase += speed * dt * 2.7;

    const a = this.amp;
    const p = this.phase;
    for (let i = 0; i < 2; i++) {
      const side = i === 0 ? 1 : -1;
      const swing = Math.sin(p + (i === 0 ? 0 : Math.PI));
      this.hips[i].rotation.x = swing * 0.55 * a;
      // il ginocchio si piega solo all'indietro, di più durante il ritorno della gamba
      const lift = Math.max(0, Math.sin(p + (i === 0 ? 0 : Math.PI) - 1.2));
      this.knees[i].rotation.x = -(0.08 + lift * 1.0) * a;
      this.shoulders[i].rotation.x = -swing * 0.5 * a;
      this.shoulders[i].rotation.z = side * -0.08 - side * 0.04 * (1 - a);
      this.elbows[i].rotation.x = (0.15 + 0.35 * a * (0.5 + 0.5 * swing)) * 1;
    }

    const breathe = Math.sin(this.t * 1.8) * 0.008 * (1 - a);
    this.body.position.y = 0.98 + Math.abs(Math.cos(p)) * 0.045 * a + breathe;
    this.torso.rotation.y = Math.sin(p) * 0.1 * a;
    this.torso.rotation.x = 0.06 * a * Math.sign(speed || 1);
    this.head.rotation.y = -Math.sin(p) * 0.08 * a + Math.sin(this.t * 0.6) * 0.06 * (1 - a);

    this.material.uniforms.uTime.value = this.t;
    this.ringMat.uniforms.uTime.value = this.t;
    this.ringMat.uniforms.uStrength.value = 0.7 + a * 0.5;
  }

  /** Effetto "materializzazione" dopo un teletrasporto. */
  setOpacity(o: number) {
    this.material.uniforms.uOpacity.value = o;
  }
}
