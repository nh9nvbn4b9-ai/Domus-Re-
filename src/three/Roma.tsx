import { useEffect, useLayoutEffect, useMemo, useRef } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import { useGLTF, useTexture } from '@react-three/drei';
import {
  Color,
  InstancedMesh,
  Matrix4,
  Mesh,
  MeshStandardMaterial,
  Quaternion,
  SRGBColorSpace,
  Vector3,
  type DirectionalLight,
  type Material,
} from 'three';
import pini from '../data/pini.json';
import { bakedMaterial } from './baked';
import { SUN_DIR } from './coords';

const CITY_URL = '/models/roma.glb';
const COLOSSEO_URL = '/models/colosseo.glb';
/** colore della foschia: orizzonte caldo dell'ora d'oro */
export const HAZE = new Color('#c8b8a4');

/**
 * Sole dell'ora d'oro per la città (le ombre si calcolano una sola volta: la scena è statica).
 * Il palazzo e il Colosseo hanno luce precalcolata e materiali che non ricevono questa luce.
 */
function Sole({ shadowSize }: { shadowSize: number }) {
  const ref = useRef<DirectionalLight>(null);
  const gl = useThree((s) => s.gl);
  const target = useMemo(() => new Vector3(-170, 0, 260), []);
  useLayoutEffect(() => {
    const l = ref.current;
    if (!l) return;
    l.target.position.copy(target);
    l.target.updateMatrixWorld();
    const c = l.shadow.camera;
    c.left = -820;
    c.right = 820;
    c.top = 820;
    c.bottom = -820;
    c.near = 10;
    c.far = 4000;
    c.updateProjectionMatrix();
    gl.shadowMap.autoUpdate = false;
    gl.shadowMap.needsUpdate = true;
  }, [gl, target]);
  return (
    <directionalLight
      ref={ref}
      position={SUN_DIR.clone().multiplyScalar(1600).add(target)}
      intensity={3.2}
      color="#ffb780"
      castShadow
      shadow-mapSize={[shadowSize, shadowSize]}
      shadow-bias={-0.0006}
      shadow-normalBias={0.6}
    />
  );
}

/** Roma attorno al palazzo: Colosseo (luce Cycles), isolati, parchi, pini, colli all'orizzonte. */
export function Roma({ mobile }: { mobile: boolean }) {
  const city = useGLTF(CITY_URL, false, true).scene;
  const colosseo = useGLTF(COLOSSEO_URL, false, true).scene;
  const lm = useTexture('/models/lm_colosseo.webp');
  const gl = useThree((s) => s.gl);
  const frames = useRef(0);

  useEffect(() => {
    lm.flipY = false;
    lm.colorSpace = SRGBColorSpace;
    lm.channel = 1;
    lm.needsUpdate = true;
    colosseo.traverse((o) => {
      if (!(o instanceof Mesh)) return;
      const tune = (m: Material) => (m instanceof MeshStandardMaterial && o.geometry.attributes.uv1 ? bakedMaterial(m, lm, 1.0) : m);
      o.material = Array.isArray(o.material) ? o.material.map(tune) : tune(o.material);
    });
    city.traverse((o) => {
      if (!(o instanceof Mesh)) return;
      const name = o.name + (o.parent?.name ?? '');
      if (/Colli|Tiburtini|Campagna/.test(name)) {
        // rilievi lontani: velati dalla prospettiva aerea, senza nebbia esponenziale che li cancellerebbe
        const m = (o.material as MeshStandardMaterial).clone();
        m.color.set('#8f9aa3');
        m.fog = false;
        m.roughness = 1;
        o.material = m;
        return;
      }
      if (/PinoPrototipo/.test(name)) {
        o.visible = false;
        return;
      }
      o.castShadow = !/Suolo|Piazza/.test(name);
      o.receiveShadow = true;
      const mats = Array.isArray(o.material) ? o.material : [o.material];
      for (const m of mats) {
        if (m instanceof MeshStandardMaterial && m.name.startsWith('Facciata')) m.emissiveIntensity = 0.35;
      }
    });
    gl.shadowMap.needsUpdate = true;
  }, [city, colosseo, lm, gl]);

  // pini domestici come istanze GPU (prototipo dal GLB, posizioni da src/data/pini.json)
  const pines = useMemo(() => {
    const proto = city.getObjectByName('PinoPrototipo');
    if (!proto) return [];
    const parts: Mesh[] = [];
    proto.traverse((o) => o instanceof Mesh && parts.push(o));
    const m4 = new Matrix4();
    const q = new Quaternion();
    const up = new Vector3(0, 1, 0);
    proto.updateWorldMatrix(true, true);
    return parts.map((p) => {
      const inst = new InstancedMesh(p.geometry, p.material, pini.length);
      // la geometria è quantizzata: la scala reale è nella trasformazione del nodo
      const local = p.matrixWorld.clone();
      pini.forEach((t, i) => {
        q.setFromAxisAngle(up, t.r);
        m4.compose(new Vector3(t.p[0], t.p[1], t.p[2]), q, new Vector3(t.s, t.s, t.s)).multiply(local);
        inst.setMatrixAt(i, m4);
      });
      inst.instanceMatrix.needsUpdate = true;
      inst.castShadow = true;
      inst.receiveShadow = true;
      inst.computeBoundingSphere();
      return inst;
    });
  }, [city]);

  // le ombre statiche vanno ricalcolate quando tutto è in scena (primi fotogrammi)
  useFrame(() => {
    if (frames.current < 3) {
      gl.shadowMap.needsUpdate = true;
      frames.current++;
    }
  });

  return (
    <>
      <Sole shadowSize={mobile ? 2048 : 4096} />
      <primitive object={city} />
      <primitive object={colosseo} />
      {pines.map((p, i) => (
        <primitive key={i} object={p} />
      ))}
    </>
  );
}

useGLTF.preload(CITY_URL, false, true);
useGLTF.preload(COLOSSEO_URL, false, true);
