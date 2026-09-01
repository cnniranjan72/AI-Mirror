import { useRef, useMemo, useEffect, Suspense } from 'react'
import { Canvas, useFrame, extend } from '@react-three/fiber'
import { shaderMaterial, Sparkles } from '@react-three/drei'
import * as THREE from 'three'
import { usePointerField, useReducedMotion, useDeviceTier, usePageVisible } from '../hooks/useMotion'
import { hasWebGL, NOISE3_GLSL } from './webgl'
import SceneBoundary from './SceneBoundary'

/* ------------------------------------------------------------------ core */

/**
 * The mirror core's surface. Two ideas do all the work:
 *
 *  - Vertex displacement by 3D fbm makes the shell BREATHE, so it reads as
 *    something alive being modelled rather than a spinning primitive.
 *  - An iq cosine palette driven by fresnel + local displacement gives
 *    view-dependent iridescence, which is what makes a single untextured
 *    mesh look like a material instead of a flat-shaded blob.
 *
 * No scene lighting is involved anywhere — every value here comes off the
 * camera-relative normal, matching how CharacterCreature3D's hologram works.
 */
const CoreMaterial = shaderMaterial(
  {
    uTime: 0,
    uAmp: 0.16,
    uFreq: 1.5,
    uPulse: 0,
    uColorA: new THREE.Color('#6366f1'),
    uColorB: new THREE.Color('#22d3ee'),
    uColorC: new THREE.Color('#f472b6'),
    uOpacity: 0.55,
  },
  /* glsl */`
  uniform float uTime;
  uniform float uAmp;
  uniform float uFreq;
  uniform float uPulse;

  varying vec3 vNormal;
  varying vec3 vView;
  varying float vDisp;

  ${NOISE3_GLSL}

  void main() {
    vec3 p = position;

    // Two octaves at different speeds: the slow one is the shape's "breath",
    // the fast one is surface detail crawling over it.
    float n1 = gnoise3(p * uFreq + vec3(0.0, uTime * 0.25, 0.0));
    float n2 = gnoise3(p * uFreq * 2.4 - vec3(uTime * 0.18, 0.0, uTime * 0.12));
    float disp = n1 * 0.75 + n2 * 0.35;
    disp += uPulse * 0.5;

    p += normal * disp * uAmp;
    vDisp = disp;

    vec4 mv = modelViewMatrix * vec4(p, 1.0);
    vNormal = normalize(normalMatrix * normal);
    vView = normalize(-mv.xyz);
    gl_Position = projectionMatrix * mv;
  }
  `,
  /* glsl */`
  uniform vec3 uColorA;
  uniform vec3 uColorB;
  uniform vec3 uColorC;
  uniform float uOpacity;
  uniform float uTime;

  varying vec3 vNormal;
  varying vec3 vView;
  varying float vDisp;

  // iq's cosine palette — three cheap cosines stand in for a gradient LUT.
  vec3 palette(float t) {
    vec3 a = vec3(0.5, 0.45, 0.6);
    vec3 b = vec3(0.45, 0.42, 0.4);
    vec3 c = vec3(1.0, 1.0, 1.0);
    vec3 d = vec3(0.0, 0.28, 0.55);
    return a + b * cos(6.28318 * (c * t + d));
  }

  void main() {
    float fres = pow(1.0 - max(dot(normalize(vNormal), normalize(vView)), 0.0), 2.2);

    vec3 irid = palette(fres * 0.8 + vDisp * 0.45 + uTime * 0.02);
    vec3 base = mix(uColorA, uColorB, clamp(vDisp * 1.6 + 0.5, 0.0, 1.0));
    vec3 col = mix(base, irid, 0.55) + uColorC * fres * 0.85;

    // Horizontal scan bands: the tell that this is a projection, tying the
    // core visually to the holographic character elsewhere in the product.
    float scan = 0.94 + 0.06 * sin(vNormal.y * 30.0 + uTime * 2.2);
    col *= scan;

    // Rim-weighted alpha keeps the centre translucent so the inner glow and
    // the far side of the shell both read through it. The flat term is kept
    // very low deliberately: any more and the additive blend fills the middle
    // in until the object reads as a solid milky ball sitting on top of the
    // headline, instead of a shell the copy shows through.
    float alpha = clamp(fres * 1.45 + 0.04, 0.0, 1.0) * uOpacity;
    gl_FragColor = vec4(col * (0.55 + fres * 1.5), alpha);
  }
  `
)

extend({ CoreMaterial })

function Core({ reduced }) {
  const matRef = useRef()
  const meshRef = useRef()

  useFrame((state, delta) => {
    if (matRef.current && !reduced) {
      matRef.current.uTime = state.clock.elapsedTime
      // A slow heartbeat on top of the noise — regular enough to feel like a
      // pulse, subtle enough not to read as a scale animation.
      matRef.current.uPulse = Math.sin(state.clock.elapsedTime * 0.9) * 0.12
    }
    if (meshRef.current && !reduced) {
      meshRef.current.rotation.y += delta * 0.16
      meshRef.current.rotation.x += delta * 0.045
    }
  })

  return (
    <mesh ref={meshRef}>
      {/* detail 5 (~20k tris) — the displacement is per-vertex, so silhouette
          smoothness is bought entirely with subdivision here. */}
      <icosahedronGeometry args={[1.35, 5]} />
      <coreMaterial
        ref={matRef}
        transparent
        depthWrite={false}
        side={THREE.DoubleSide}
        blending={THREE.AdditiveBlending}
      />
    </mesh>
  )
}

/** Solid inner glow — gives the translucent shell something to contain. */
function InnerGlow({ reduced }) {
  const ref = useRef()
  useFrame((state) => {
    if (!ref.current || reduced) return
    const s = 0.66 + Math.sin(state.clock.elapsedTime * 1.15) * 0.035
    ref.current.scale.setScalar(s)
  })
  return (
    <mesh ref={ref} scale={0.66}>
      <sphereGeometry args={[1, 32, 32]} />
      <meshBasicMaterial color="#c7d2fe" transparent opacity={0.05} blending={THREE.AdditiveBlending} depthWrite={false} />
    </mesh>
  )
}

/** Counter-rotating wireframe cage. */
function Cage({ reduced }) {
  const ref = useRef()
  useFrame((state, delta) => {
    if (!ref.current || reduced) return
    ref.current.rotation.y -= delta * 0.09
    ref.current.rotation.z += delta * 0.05
  })
  return (
    <mesh ref={ref}>
      <icosahedronGeometry args={[2.05, 1]} />
      <meshBasicMaterial color="#818cf8" wireframe transparent opacity={0.13} depthWrite={false} />
    </mesh>
  )
}

/**
 * An orbit ring with a node riding it. The node is the part that matters —
 * a bare ring reads as static geometry, a ring with something travelling it
 * reads as a system doing work.
 */
function Orbit({ radius, tilt, speed, color, nodeSize = 0.075, reduced }) {
  const groupRef = useRef()
  const nodeRef = useRef()

  useFrame((state, delta) => {
    if (reduced) return
    if (groupRef.current) groupRef.current.rotation.z += delta * speed * 0.35
    if (nodeRef.current) {
      const t = state.clock.elapsedTime * speed
      nodeRef.current.position.set(Math.cos(t) * radius, Math.sin(t) * radius, 0)
    }
  })

  return (
    <group rotation={tilt}>
      <group ref={groupRef}>
        <mesh>
          <torusGeometry args={[radius, 0.006, 8, 128]} />
          <meshBasicMaterial color={color} transparent opacity={0.32} blending={THREE.AdditiveBlending} depthWrite={false} />
        </mesh>
        <mesh ref={nodeRef} position={[radius, 0, 0]}>
          <sphereGeometry args={[nodeSize, 16, 16]} />
          <meshBasicMaterial color={color} transparent opacity={0.8} blending={THREE.AdditiveBlending} depthWrite={false} />
        </mesh>
      </group>
    </group>
  )
}

/** Dust shell around the core, drifting on the same lissajous idea as the
 *  ambient field so the two scenes feel like one system. */
function Halo({ count, reduced }) {
  const ref = useRef()

  const geometry = useMemo(() => {
    const positions = new Float32Array(count * 3)
    const colors = new Float32Array(count * 3)
    const c = new THREE.Color()
    const palette = ['#818cf8', '#22d3ee', '#f472b6', '#e0e7ff']

    for (let i = 0; i < count; i++) {
      // Uniform on a spherical shell (acos of a uniform, not a uniform angle —
      // otherwise everything piles up at the poles).
      const u = Math.random()
      const v = Math.random()
      const theta = 2 * Math.PI * u
      const phi = Math.acos(2 * v - 1)
      const r = 2.2 + Math.random() * 1.8

      positions[i * 3 + 0] = r * Math.sin(phi) * Math.cos(theta)
      positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta)
      positions[i * 3 + 2] = r * Math.cos(phi)

      c.set(palette[Math.floor(Math.random() * palette.length)])
      colors[i * 3 + 0] = c.r
      colors[i * 3 + 1] = c.g
      colors[i * 3 + 2] = c.b
    }

    const g = new THREE.BufferGeometry()
    g.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    g.setAttribute('color', new THREE.BufferAttribute(colors, 3))
    return g
  }, [count])

  useEffect(() => () => geometry.dispose(), [geometry])

  useFrame((state, delta) => {
    if (!ref.current || reduced) return
    ref.current.rotation.y += delta * 0.05
    ref.current.rotation.x = Math.sin(state.clock.elapsedTime * 0.15) * 0.12
  })

  return (
    <points ref={ref} geometry={geometry}>
      <pointsMaterial
        size={0.035}
        vertexColors
        transparent
        opacity={0.45}
        sizeAttenuation
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </points>
  )
}

/**
 * Pointer/scroll response for the whole assembly. Applied to a parent group
 * rather than the camera so the core leans toward the cursor while the
 * background field behind it stays put — the parallax between the two is what
 * gives the hero its depth.
 */
function Rig({ children, pointer, reduced }) {
  const ref = useRef()

  useFrame((state, delta) => {
    const g = ref.current
    if (!g) return
    const p = pointer.current
    const k = Math.min(1, delta * 2.4)

    const targetY = (p.active ? p.x : 0) * 0.42
    const targetX = (p.active ? -p.y : 0) * 0.3
    g.rotation.y += (targetY - g.rotation.y) * k
    g.rotation.x += (targetX - g.rotation.x) * k

    if (!reduced) {
      // Sinks and shrinks slightly as the page scrolls away from the hero,
      // handing focus to the content below.
      const s = 1 - p.scroll * 0.28
      g.scale.setScalar(Math.max(0.6, s))
      g.position.y = -p.scroll * 1.4 + Math.sin(state.clock.elapsedTime * 0.6) * 0.06
    }
  })

  return <group ref={ref}>{children}</group>
}

/**
 * The landing page's focal 3D object: a translucent, breathing "cognitive
 * core" wrapped in orbiting rings and dust.
 *
 * Renders its own Canvas (the landing page is outside the app shell's shared
 * <View> canvas) and degrades exactly like AmbientField — no WebGL, reduced
 * motion, hidden tab, or low-end device each step it down, and a scene error
 * removes it without touching the page.
 */
export default function HeroCore({ height = 520 }) {
  const pointer = usePointerField()
  const reduced = useReducedMotion()
  const tier = useDeviceTier()
  const visible = usePageVisible()

  const supported = useMemo(() => hasWebGL(), [])
  if (!supported) return null

  const haloCount = tier === 'high' ? 900 : 420

  return (
    <SceneBoundary>
      <div style={{ position: 'absolute', inset: 0, height, pointerEvents: 'none' }} aria-hidden="true">
        <Canvas
          dpr={[1, tier === 'high' ? 2 : 1.5]}
          gl={{ alpha: true, antialias: true, powerPreference: 'high-performance' }}
          camera={{ position: [0, 0, 9.2], fov: 42 }}
          frameloop={visible ? 'always' : 'never'}
          style={{ pointerEvents: 'none' }}
        >
          <Suspense fallback={null}>
            <Rig pointer={pointer} reduced={reduced}>
              <Core reduced={reduced} />
              <InnerGlow reduced={reduced} />
              <Cage reduced={reduced} />
              <Halo count={haloCount} reduced={reduced} />

              {/* Three orbits on distinct axes — one plane reads as a ring,
                  three reading against each other read as a system. */}
              <Orbit radius={2.35} tilt={[1.35, 0.2, 0]} speed={0.55} color="#22d3ee" reduced={reduced} />
              <Orbit radius={2.75} tilt={[0.5, 0.9, 0.4]} speed={-0.38} color="#a78bfa" reduced={reduced} />
              <Orbit radius={3.15} tilt={[1.9, -0.4, 0.8]} speed={0.27} color="#f472b6" nodeSize={0.055} reduced={reduced} />

              {tier === 'high' && !reduced && (
                <Sparkles count={60} scale={9} size={2} speed={0.3} opacity={0.35} color="#c7d2fe" />
              )}
            </Rig>
          </Suspense>
        </Canvas>
      </div>
    </SceneBoundary>
  )
}
