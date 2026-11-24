import * as THREE from 'three';
import { YELLOW } from './textures';

const yellow = () => new THREE.Color(YELLOW);

/* -------------------------------------------------------------------------- */
/* Pavimento a esagoni neri con fughe gialle                                  */
/* -------------------------------------------------------------------------- */

export const MAX_GLOWS = 4;

export function hexFloorMaterial(center: THREE.Vector3, radius: number) {
  const glows = Array.from({ length: MAX_GLOWS }, () => new THREE.Vector3(0, 0, -1e4));
  return new THREE.ShaderMaterial({
    uniforms: {
      uTime: { value: 0 },
      uColor: { value: yellow() },
      uCenter: { value: new THREE.Vector2(center.x, center.z) },
      uRadius: { value: radius },
      uPlayer: { value: new THREE.Vector3(center.x, 0, center.z) },
      uGlows: { value: glows },
    },
    vertexShader: /* glsl */ `
      varying vec3 vWorld;
      void main() {
        vec4 w = modelMatrix * vec4(position, 1.0);
        vWorld = w.xyz;
        gl_Position = projectionMatrix * viewMatrix * w;
      }
    `,
    fragmentShader: /* glsl */ `
      uniform float uTime;
      uniform vec3 uColor;
      uniform vec2 uCenter;
      uniform float uRadius;
      uniform vec3 uPlayer;
      uniform vec3 uGlows[${MAX_GLOWS}];
      varying vec3 vWorld;

      float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
      float hexDist(vec2 p) {
        p = abs(p);
        return max(dot(p, normalize(vec2(1.0, 1.7320508))), p.x);
      }
      vec4 hexCoords(vec2 uv) {
        vec2 r = vec2(1.0, 1.7320508);
        vec2 h = r * 0.5;
        vec2 a = mod(uv, r) - h;
        vec2 b = mod(uv - h, r) - h;
        vec2 gv = dot(a, a) < dot(b, b) ? a : b;
        return vec4(gv, uv - gv);
      }

      void main() {
        vec2 p = vWorld.xz;
        vec4 hc = hexCoords(p * 0.85);
        float d = hexDist(hc.xy);
        float w = fwidth(d);
        float line = smoothstep(0.478 - w, 0.478 + w, d);
        float far = 1.0 - smoothstep(0.03, 0.14, w);   // niente sfarfallio in lontananza

        float r = length(p - uCenter);
        float fade = 1.0 - smoothstep(uRadius * 0.35, uRadius, r);

        float cell = hash(hc.zw);
        float player = exp(-length(p - uPlayer.xz) * 0.55);
        float wave = smoothstep(0.92, 1.0, sin(r * 0.45 - uTime * 1.6)) * 0.6;
        float twinkle = step(0.965, cell) * (0.5 + 0.5 * sin(uTime * 2.0 + cell * 40.0));

        float glow = 0.0;
        for (int i = 0; i < ${MAX_GLOWS}; i++) {
          glow += exp(-length(p - uGlows[i].xz) * 0.42) * uGlows[i].y;
        }

        // piastrella: nero lucido con leggera variazione e bordo smussato
        vec3 tile = vec3(0.006 + cell * 0.006) + vec3(0.012) * smoothstep(0.32, 0.47, d);
        tile += uColor * (player * 0.025 + glow * 0.02 + twinkle * 0.03);

        float lineI = (0.035 + player * 0.55 + glow * 0.45 + wave * 0.12) * far;
        vec3 col = mix(tile, uColor * lineI, line);
        col *= fade;
        gl_FragColor = vec4(col, 1.0);
      }
    `,
  });
}

/* -------------------------------------------------------------------------- */
/* Ologramma dell'umanoide                                                    */
/* -------------------------------------------------------------------------- */

export function hologramMaterial() {
  return new THREE.ShaderMaterial({
    uniforms: {
      uTime: { value: 0 },
      uColor: { value: yellow() },
      uOpacity: { value: 1 },
    },
    vertexShader: /* glsl */ `
      varying vec3 vN;
      varying vec3 vView;
      varying vec3 vWorld;
      void main() {
        vec4 w = modelMatrix * vec4(position, 1.0);
        vWorld = w.xyz;
        vN = normalize(mat3(modelMatrix) * normal);
        vView = cameraPosition - w.xyz;
        gl_Position = projectionMatrix * viewMatrix * w;
      }
    `,
    fragmentShader: /* glsl */ `
      uniform vec3 uColor;
      uniform float uTime;
      uniform float uOpacity;
      varying vec3 vN;
      varying vec3 vView;
      varying vec3 vWorld;
      void main() {
        float f = 1.0 - abs(dot(normalize(vN), normalize(vView)));
        f = pow(f, 1.8);
        float scan = 0.5 + 0.5 * sin(vWorld.y * 90.0 - uTime * 8.0);
        float band = smoothstep(0.96, 1.0, sin(vWorld.y * 2.5 - uTime * 2.2));
        vec3 c = uColor * (0.025 + f * 1.15 + scan * 0.03 + band * 0.25);
        c += vec3(1.0, 0.92, 0.7) * pow(f, 5.0) * 0.35;
        gl_FragColor = vec4(c, (0.25 + f * 0.75) * uOpacity);
      }
    `,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    side: THREE.FrontSide,
  });
}

/* -------------------------------------------------------------------------- */
/* Superficie interna del portale                                             */
/* -------------------------------------------------------------------------- */

export function portalMaterial() {
  return new THREE.ShaderMaterial({
    uniforms: {
      uTime: { value: 0 },
      uColor: { value: yellow() },
      uNear: { value: 0 },
    },
    vertexShader: /* glsl */ `
      varying vec2 vUv;
      void main() {
        vUv = uv;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: /* glsl */ `
      uniform float uTime;
      uniform vec3 uColor;
      uniform float uNear;
      varying vec2 vUv;
      void main() {
        vec2 p = vUv * 2.0 - 1.0;
        float r = length(p);
        if (r > 1.0) discard;
        float a = atan(p.y, p.x);
        float swirl = 0.5 + 0.5 * sin(a * 5.0 + r * 9.0 - uTime * (1.6 + uNear * 2.0));
        float edge = smoothstep(0.45, 1.0, r);
        float core = (1.0 - r) * uNear;
        vec3 col = mix(vec3(0.004), uColor * 0.55, edge * (0.3 + 0.4 * swirl));
        col += uColor * core * 0.35;
        gl_FragColor = vec4(col, 0.6 + edge * 0.3);
      }
    `,
    transparent: true,
    depthWrite: false,
    side: THREE.DoubleSide,
  });
}

/* -------------------------------------------------------------------------- */
/* Pareti delle stanze: nero con strisce LED gialle                           */
/* -------------------------------------------------------------------------- */

export function roomWallMaterial() {
  return new THREE.ShaderMaterial({
    uniforms: { uTime: { value: 0 }, uColor: { value: yellow() } },
    vertexShader: /* glsl */ `
      varying vec2 vUv;
      void main() {
        vUv = uv;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: /* glsl */ `
      uniform float uTime;
      uniform vec3 uColor;
      varying vec2 vUv;
      void main() {
        float y = vUv.y;
        float s = vUv.x * 40.0;
        float fx = fract(s);
        float w = fwidth(s);
        float rib = 1.0 - smoothstep(0.0, w * 1.5, min(fx, 1.0 - fx));
        float floorBand = exp(-y * 14.0);
        float led = exp(-abs(y - 0.42) * 260.0);
        float pulse = 0.75 + 0.25 * sin(uTime * 1.3 + vUv.x * 6.2831 * 2.0);
        vec3 c = vec3(0.012) + vec3(0.02) * (1.0 - y);
        c += uColor * (rib * 0.05 * (1.0 - y) + floorBand * 0.22 + led * 1.8 * pulse);
        c *= 1.0 - smoothstep(0.55, 1.0, y) * 0.92;
        gl_FragColor = vec4(c, 1.0);
      }
    `,
    side: THREE.BackSide,
  });
}

/* -------------------------------------------------------------------------- */
/* Orizzonte della hall: un alone giallo basso, come una città lontana        */
/* -------------------------------------------------------------------------- */

export function horizonMaterial() {
  return new THREE.ShaderMaterial({
    uniforms: { uColor: { value: yellow() } },
    vertexShader: /* glsl */ `
      varying vec2 vUv;
      void main() {
        vUv = uv;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: /* glsl */ `
      uniform vec3 uColor;
      varying vec2 vUv;
      void main() {
        float y = vUv.y;
        vec3 c = vec3(0.004) + uColor * exp(-y * 14.0) * 0.07;
        gl_FragColor = vec4(c, 1.0);
      }
    `,
    side: THREE.BackSide,
  });
}

/** Alone radiale sul pavimento (sotto l'umanoide). */
export function groundRingMaterial() {
  return new THREE.ShaderMaterial({
    uniforms: { uColor: { value: yellow() }, uTime: { value: 0 }, uStrength: { value: 1 } },
    vertexShader: /* glsl */ `
      varying vec2 vUv;
      void main() {
        vUv = uv;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: /* glsl */ `
      uniform vec3 uColor;
      uniform float uTime;
      uniform float uStrength;
      varying vec2 vUv;
      void main() {
        float r = length(vUv * 2.0 - 1.0);
        float ring = exp(-abs(r - 0.62) * 30.0);
        float pulse = exp(-abs(r - fract(uTime * 0.6)) * 18.0) * (1.0 - r);
        float disc = (1.0 - smoothstep(0.0, 0.7, r)) * 0.25;
        float a = (ring * 0.9 + pulse * 0.6 + disc) * uStrength;
        gl_FragColor = vec4(uColor * a * 0.9, 1.0);
      }
    `,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  });
}
