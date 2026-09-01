import { useRef, useMemo, useEffect, Suspense } from 'react'
import { Canvas, useFrame, useThree, extend } from '@react-three/fiber'
import { shaderMaterial } from '@react-three/drei'
import * as THREE from 'three'
import { useLocation } from 'react-router-dom'
import { usePointerField, useReducedMotion, useDeviceTier, usePageVisible } from '../hooks/useMotion'
import { hasWebGL, NOISE_GLSL } from './webgl'
import SceneBoundary from './SceneBoundary'

/* ---------------------------------------------------------------- nebula */

/**
 * Domain-warped fbm — the drifting aurora the whole app sits on. Three fbm
 * passes (warp, warp, sample) is what turns flat noise into something that
 * looks like it's flowing rather than just shimmering in place.
 */
const NebulaMaterial = shaderMaterial(
  {
    uTime: 0,
    uAspect: 1,
    uIntensity: 1,
    uColorA: new THREE.Color('#4f46e5'),
    uColorB: new THREE.Color('#22d3ee'),
    uColorC: new THREE.Color('#ec4899'),
    uFocus: new THREE.Vector2(0, 0),
  },
  /* glsl */`
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
  `,
  /* glsl */`
  uniform float uTime;
  uniform float uAspect;
  uniform float uIntensity;
  uniform vec3 uColorA;
  uniform vec3 uColorB;
  uniform vec3 uColorC;
  uniform vec2 uFocus;
  varying vec2 vUv;

  ${NOISE_GLSL}

  void main() {
    vec2 uv = vUv * 2.0 - 1.0;
    uv.x *= uAspect;

    float t = uTime * 0.035;

    // Two levels of domain warping: q displaces the sample point, r displaces
    // it again using q. The result flows and folds instead of scrolling.
    vec2 q = vec2(fbm(uv * 0.9 + t), fbm(uv * 0.9 + vec2(5.2, 1.3) - t));
    vec2 r = vec2(
      fbm(uv * 0.9 + 1.8 * q + vec2(1.7, 9.2) + t * 1.15),
      fbm(uv * 0.9 + 1.8 * q + vec2(8.3, 2.8) - t * 0.85)
    );
    float f = fbm(uv * 0.9 + 1.9 * r);

    vec3 col = mix(uColorA, uColorB, clamp(f * f * 2.4, 0.0, 1.0));
    col = mix(col, uColorC, clamp(length(r) * 0.75, 0.0, 1.0));

    // Brighten toward the cursor so the field feels aware of the pointer.
    float focus = 1.0 - smoothstep(0.0, 1.5, distance(uv, uFocus * vec2(uAspect, 1.0)));
    col += col * focus * 0.5;

    // Vignette keeps the glow off the page edges, where it would fight the
    // sidebar and the card borders for attention. Written as 1 - smoothstep
    // rather than smoothstep(hi, lo, x): GLSL leaves the result UNDEFINED when
    // edge0 >= edge1, so the reversed form is a driver-dependent gamble.
    float vig = 1.0 - smoothstep(0.2, 2.0, length(uv));
    float alpha = (f * 0.55 + 0.30) * vig * uIntensity;

    gl_FragColor = vec4(col, clamp(alpha, 0.0, 1.0));
  }
  `
)

/* ------------------------------------------------------------- particles */

const StarMaterial = shaderMaterial(
  { uTime: 0, uSize: 26, uOpacity: 1, uPointer: new THREE.Vector2(0, 0) },
  /* glsl */`
  uniform float uTime;
  uniform float uSize;
  uniform vec2 uPointer;
  attribute float aScale;
  attribute float aSeed;
  attribute vec3 aColor;
  varying vec3 vColor;
  varying float vTwinkle;

  void main() {
    vColor = aColor;

    vec3 p = position;
    float s = aSeed * 6.2831;
    // Each particle drifts on its own lissajous path. Cheap enough to run on
    // thousands of points, and non-repeating enough that the field never
    // reads as a looping animation.
    p.x += sin(uTime * 0.18 + s) * 0.55;
    p.y += cos(uTime * 0.14 + s * 1.7) * 0.45;
    p.z += sin(uTime * 0.11 + s * 2.3) * 0.35;

    // Parallax: nearer particles react more to the pointer, which is what
    // sells the depth of the field. Range matches the slab built in JS.
    float depth = smoothstep(-6.0, 4.0, p.z);
    p.xy += uPointer * mix(0.10, 0.65, depth);

    vec4 mv = modelViewMatrix * vec4(p, 1.0);
    vTwinkle = 0.55 + 0.45 * sin(uTime * 1.6 + s * 3.0);
    gl_PointSize = aScale * uSize * (1.0 / max(0.35, -mv.z)) * 3.0;
    gl_Position = projectionMatrix * mv;
  }
  `,
  /* glsl */`
  uniform float uOpacity;
  varying vec3 vColor;
  varying float vTwinkle;

  void main() {
    // Soft round sprite — a squared falloff reads as a glow rather than a
    // hard disc, and costs one length() per fragment.
    float d = length(gl_PointCoord - 0.5);
    float a = smoothstep(0.5, 0.0, d);
    a *= a;
    gl_FragColor = vec4(vColor * (0.7 + vTwinkle * 0.9), a * vTwinkle * uOpacity);
  }
  `
)

extend({ NebulaMaterial, StarMaterial })

const PALETTE = ['#818cf8', '#22d3ee', '#a78bfa', '#f472b6', '#e0e7ff', '#34d399']

function Nebula({ intensity, accent, pointer, reduced }) {
  const matRef = useRef()
  const { viewport, size } = useThree()

  // Cheap enough to rebuild only when the accent actually changes; the shader
  // lerps toward these rather than snapping (see useFrame below).
  const target = useMemo(() => ({
    a: new THREE.Color(accent.a),
    b: new THREE.Color(accent.b),
    c: new THREE.Color(accent.c),
  }), [accent.a, accent.b, accent.c])

  useFrame((state, delta) => {
    const m = matRef.current
    if (!m) return
    // Reduced motion still gets the field — it just stops evolving, so the
    // page has depth without anything moving.
    if (!reduced) m.uTime = state.clock.elapsedTime
    m.uAspect = size.width / Math.max(1, size.height)
    m.uIntensity = intensity

    const p = pointer.current
    m.uFocus.x += ((p.active ? p.x : 0) - m.uFocus.x) * Math.min(1, delta * 2.2)
    m.uFocus.y += ((p.active ? p.y : 0) - m.uFocus.y) * Math.min(1, delta * 2.2)

    // Route accent changes glide over ~1s instead of cutting, so navigation
    // reads as the same world shifting mood.
    const k = Math.min(1, delta * 1.4)
    m.uColorA.lerp(target.a, k)
    m.uColorB.lerp(target.b, k)
    m.uColorC.lerp(target.c, k)
  })

  return (
    // depthTest off + a very negative renderOrder: this is a backdrop, so it
    // must never occlude (or be occluded by) the particles in front of it.
    <mesh renderOrder={-10} scale={[viewport.width * 1.25, viewport.height * 1.25, 1]}>
      <planeGeometry args={[1, 1]} />
      <nebulaMaterial
        ref={matRef}
        transparent
        depthTest={false}
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </mesh>
  )
}

function Starfield({ count, opacity, pointer, reduced }) {
  const matRef = useRef()
  const groupRef = useRef()

  const geometry = useMemo(() => {
    const positions = new Float32Array(count * 3)
    const colors = new Float32Array(count * 3)
    const scales = new Float32Array(count)
    const seeds = new Float32Array(count)
    const c = new THREE.Color()

    for (let i = 0; i < count; i++) {
      // The slab must stay wider than the camera frustum at its OWN far edge,
      // or the cloud's rectangular bounds become visible as a hard-edged box
      // of stars floating in the middle of the screen. At z=-6 the camera is
      // 15 units away (fov 60), which sees ~17 units of height and ~39 of
      // width on a wide monitor — hence 48 x 26 over a deliberately shallow
      // 10-unit depth.
      positions[i * 3 + 0] = (Math.random() - 0.5) * 48
      positions[i * 3 + 1] = (Math.random() - 0.5) * 26
      positions[i * 3 + 2] = (Math.random() - 0.5) * 10 - 1

      c.set(PALETTE[Math.floor(Math.random() * PALETTE.length)])
      colors[i * 3 + 0] = c.r
      colors[i * 3 + 1] = c.g
      colors[i * 3 + 2] = c.b

      // Cubed random skews toward small: a few bright anchors, mostly dust.
      scales[i] = 0.25 + Math.pow(Math.random(), 3) * 1.6
      seeds[i] = Math.random()
    }

    const g = new THREE.BufferGeometry()
    g.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    g.setAttribute('aColor', new THREE.BufferAttribute(colors, 3))
    g.setAttribute('aScale', new THREE.BufferAttribute(scales, 1))
    g.setAttribute('aSeed', new THREE.BufferAttribute(seeds, 1))
    return g
  }, [count])

  // BufferGeometry holds GPU buffers — React won't free those for us.
  useEffect(() => () => geometry.dispose(), [geometry])

  useFrame((state, delta) => {
    const m = matRef.current
    if (m) {
      if (!reduced) m.uTime = state.clock.elapsedTime
      m.uOpacity = opacity
      const p = pointer.current
      m.uPointer.x += ((p.active ? p.x : 0) - m.uPointer.x) * Math.min(1, delta * 1.6)
      m.uPointer.y += ((p.active ? p.y : 0) - m.uPointer.y) * Math.min(1, delta * 1.6)
    }
    if (groupRef.current && !reduced) {
      // A barely-perceptible roll. Enough that the field is never static,
      // slow enough that it's never the thing you notice.
      groupRef.current.rotation.z = Math.sin(state.clock.elapsedTime * 0.04) * 0.06
      groupRef.current.position.y = -pointer.current.scroll * 2.2
    }
  })

  return (
    <group ref={groupRef}>
      <points geometry={geometry}>
        <starMaterial
          ref={matRef}
          transparent
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </points>
    </group>
  )
}

/**
 * A slowly tumbling wireframe polyhedron — the one hard-edged element in an
 * otherwise soft scene, which is what keeps the background from reading as a
 * generic gradient blur.
 */
function Lattice({ pointer, reduced, accent }) {
  const ref = useRef()
  const color = useMemo(() => new THREE.Color(accent.b), [accent.b])

  useFrame((state, delta) => {
    const g = ref.current
    if (!g) return
    if (!reduced) {
      g.rotation.x += delta * 0.045
      g.rotation.y += delta * 0.07
    }
    const p = pointer.current
    const tx = (p.active ? p.x : 0) * 0.5
    const ty = (p.active ? p.y : 0) * 0.35
    g.position.x += (7.5 + tx - g.position.x) * Math.min(1, delta * 1.5)
    g.position.y += (2.4 + ty - g.position.y) * Math.min(1, delta * 1.5)
  })

  return (
    <group ref={ref} position={[7.5, 2.4, -4]}>
      <mesh>
        <icosahedronGeometry args={[2.6, 1]} />
        <meshBasicMaterial color={color} wireframe transparent opacity={0.13} depthWrite={false} />
      </mesh>
      <mesh rotation={[0.6, 0.4, 0]}>
        <icosahedronGeometry args={[1.7, 0]} />
        <meshBasicMaterial color={accent.c} wireframe transparent opacity={0.1} depthWrite={false} />
      </mesh>
    </group>
  )
}

/* --------------------------------------------------------- route accents */

/**
 * Each area of the app tints the same field differently, so moving between
 * sections has a felt identity even though the geometry never changes.
 * Anything unlisted falls back to the product's indigo/cyan/violet.
 */
const ROUTE_ACCENTS = {
  '/': { a: '#4f46e5', b: '#22d3ee', c: '#ec4899' },
  '/dashboard': { a: '#4f46e5', b: '#22d3ee', c: '#8b5cf6' },
  '/identity': { a: '#6366f1', b: '#a78bfa', c: '#22d3ee' },
  '/character': { a: '#7c3aed', b: '#f472b6', c: '#22d3ee' },
  '/chat': { a: '#4f46e5', b: '#34d399', c: '#22d3ee' },
  '/guardian': { a: '#e11d48', b: '#f59e0b', c: '#8b5cf6' },
  '/learning': { a: '#059669', b: '#22d3ee', c: '#6366f1' },
  '/memory': { a: '#d97706', b: '#8b5cf6', c: '#22d3ee' },
  '/evidence': { a: '#059669', b: '#6366f1', c: '#22d3ee' },
  '/graph': { a: '#0891b2', b: '#8b5cf6', c: '#ec4899' },
  '/pipeline': { a: '#4f46e5', b: '#22d3ee', c: '#34d399' },
  '/insights': { a: '#7c3aed', b: '#22d3ee', c: '#f472b6' },
}
const DEFAULT_ACCENT = { a: '#4f46e5', b: '#22d3ee', c: '#8b5cf6' }

/* ------------------------------------------------------------- component */

/**
 * The app's persistent ambient scene. Mounted ONCE at the router root and
 * never unmounted, so navigating between routes changes uniforms rather than
 * tearing down and re-acquiring a WebGL context (which is what makes 3D-heavy
 * SPAs stutter on every link click).
 *
 * Everything about it is defensive by design: no WebGL, reduced motion, a
 * hidden tab, or a low-end device each degrade it a step further, and a
 * thrown error inside the scene removes it entirely without touching the app
 * (SceneBoundary). The page underneath is fully functional in every one of
 * those states — the CSS aurora in design-system.css is always there.
 */
export default function AmbientField() {
  const location = useLocation()
  const pointer = usePointerField()
  const reduced = useReducedMotion()
  const tier = useDeviceTier()
  const visible = usePageVisible()

  const supported = useMemo(() => hasWebGL(), [])
  if (!supported || tier === 'low') return null

  const accent = ROUTE_ACCENTS[location.pathname] || DEFAULT_ACCENT
  const isLanding = location.pathname === '/'

  // The landing page is the one place the scene is the content, so it gets a
  // brighter field; inside the app it stays a backdrop behind real data — but
  // not so far back that it disappears, since cards now sit at 0.66 alpha and
  // swallow a dim field entirely.
  // The landing page is the one place the scene is the content, so it gets a
  // brighter field; inside the app it stays a backdrop behind real data — but
  // not so far back that it disappears, since cards now sit at 0.66 alpha and
  // swallow a dim field entirely.
  const intensity = isLanding ? 0.85 : 0.6
  // Counts scale with the slab's volume — it covers ~3x the area it used to,
  // so the same numbers would read as a thin scatter rather than a field.
  const starCount = tier === 'high' ? (isLanding ? 3600 : 2400) : 1600
  const starOpacity = isLanding ? 0.95 : 0.8

  return (
    <SceneBoundary>
      <Canvas
        className="ambient-canvas"
        // A soft, out-of-focus backdrop gains nothing from retina pixels, and
        // this shader is fill-rate bound — capping DPR here is the single
        // biggest perf decision in the scene.
        dpr={[1, 1.25]}
        gl={{ alpha: true, antialias: false, powerPreference: 'high-performance', depth: false, stencil: false }}
        camera={{ position: [0, 0, 9], fov: 60, near: 0.1, far: 60 }}
        // Hidden tab: stop rendering entirely rather than letting the browser
        // throttle it into a stuttering background drain.
        frameloop={visible ? 'always' : 'never'}
        // Positioning MUST be inline, not left to the .ambient-canvas class:
        // r3f writes `position: relative; width: 100%; height: 100%` inline on
        // its own container div, and an inline declaration beats a class rule.
        // Styling this from CSS alone left the scene as a 150px-tall block in
        // normal flow at the top of the page instead of a fixed backdrop.
        // (AppShell's shared <View> canvas positions itself inline for the
        // same reason.)
        style={{
          position: 'fixed', inset: 0,
          width: '100vw', height: '100vh',
          pointerEvents: 'none', zIndex: 0,
        }}
      >
        <Suspense fallback={null}>
          <Nebula intensity={intensity} accent={accent} pointer={pointer} reduced={reduced} />
          <Starfield count={starCount} opacity={starOpacity} pointer={pointer} reduced={reduced} />
          {tier === 'high' && <Lattice pointer={pointer} reduced={reduced} accent={accent} />}
        </Suspense>
      </Canvas>
    </SceneBoundary>
  )
}
