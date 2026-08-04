import { useRef, useMemo, useLayoutEffect } from 'react'
import { useFrame, useThree, extend } from '@react-three/fiber'
import { Text, Billboard, Sparkles, Line, shaderMaterial, View } from '@react-three/drei'
import * as THREE from 'three'

function fibonacciSphere(count, radius) {
  const points = []
  const goldenAngle = Math.PI * (3 - Math.sqrt(5))
  for (let i = 0; i < count; i++) {
    const y = count > 1 ? 1 - (i / (count - 1)) * 2 : 0
    const r = Math.sqrt(Math.max(0, 1 - y * y))
    const theta = goldenAngle * i
    points.push([Math.cos(theta) * r * radius, y * radius, Math.sin(theta) * r * radius])
  }
  return points
}

// Fresnel-rim "hologram" material: view-dependent glow + a slow vertical
// scanline shimmer. No scene lighting needed — it reads purely off the
// camera-relative normal, which is what makes it read as a projected
// construct rather than a lit solid object.
const HoloMaterial = shaderMaterial(
  { uColor: new THREE.Color('#818cf8'), uOpacity: 1, uTime: 0 },
  `
  varying vec3 vNormal;
  varying vec3 vViewDir;
  void main() {
    vNormal = normalize(normalMatrix * normal);
    vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
    vViewDir = normalize(-mvPosition.xyz);
    gl_Position = projectionMatrix * mvPosition;
  }
  `,
  `
  uniform vec3 uColor;
  uniform float uOpacity;
  uniform float uTime;
  varying vec3 vNormal;
  varying vec3 vViewDir;
  void main() {
    float fresnel = pow(1.0 - max(dot(normalize(vNormal), normalize(vViewDir)), 0.0), 2.5);
    float scan = sin((vNormal.y * 24.0) + uTime * 3.0) * 0.08 + 0.92;
    vec3 color = uColor * (0.45 + fresnel * 1.6) * scan;
    float alpha = clamp(fresnel * 1.3 + 0.3, 0.0, 1.0) * uOpacity;
    gl_FragColor = vec4(color, alpha);
  }
  `
)
extend({ HoloMaterial })

/**
 * A small holographic creature — a Pokemon-shaped silhouette (round body,
 * ears, tail, big eyes for personality) rendered as a projected energy
 * construct rather than a solid character. Every dynamic property maps to
 * real state, same contract as CharacterOrb:
 *   confidence -> glow opacity/solidity
 *   moodColor  -> hologram tint (RL Q-value / wellbeing signal)
 *   thinking   -> faster bob/spin + a brighter sparkle burst
 */
function Creature({ colorHex, glowIntensity, thinking }) {
  const group = useRef(null)
  const matRefs = useRef([])

  useFrame((state) => {
    const t = state.clock.elapsedTime
    const speed = thinking ? 2.6 : 1
    matRefs.current.forEach((m) => { if (m) m.uTime = t })
    if (group.current) {
      group.current.rotation.y = t * 0.35 * speed
      group.current.position.y = Math.sin(t * 1.4 * speed) * 0.08
    }
  })

  const setRef = (i) => (r) => { matRefs.current[i] = r }

  return (
    <group ref={group}>
      {/* body */}
      <mesh scale={[1, 0.92, 1]}>
        <sphereGeometry args={[0.8, 32, 32]} />
        <holoMaterial ref={setRef(0)} uColor={colorHex} uOpacity={glowIntensity} transparent depthWrite={false} side={THREE.DoubleSide} />
      </mesh>
      {/* ears */}
      <mesh position={[-0.35, 0.72, 0]} rotation={[0, 0, 0.35]}>
        <coneGeometry args={[0.16, 0.48, 16]} />
        <holoMaterial ref={setRef(1)} uColor={colorHex} uOpacity={glowIntensity} transparent depthWrite={false} side={THREE.DoubleSide} />
      </mesh>
      <mesh position={[0.35, 0.72, 0]} rotation={[0, 0, -0.35]}>
        <coneGeometry args={[0.16, 0.48, 16]} />
        <holoMaterial ref={setRef(2)} uColor={colorHex} uOpacity={glowIntensity} transparent depthWrite={false} side={THREE.DoubleSide} />
      </mesh>
      {/* tail */}
      <mesh position={[0, -0.05, -0.78]} rotation={[0.7, 0, 0]}>
        <coneGeometry args={[0.14, 0.55, 16]} />
        <holoMaterial ref={setRef(3)} uColor={colorHex} uOpacity={glowIntensity} transparent depthWrite={false} side={THREE.DoubleSide} />
      </mesh>
      {/* eyes */}
      <mesh position={[-0.27, 0.12, 0.72]}>
        <sphereGeometry args={[0.11, 16, 16]} />
        <meshBasicMaterial color="#ffffff" transparent opacity={glowIntensity} />
      </mesh>
      <mesh position={[0.27, 0.12, 0.72]}>
        <sphereGeometry args={[0.11, 16, 16]} />
        <meshBasicMaterial color="#ffffff" transparent opacity={glowIntensity} />
      </mesh>
    </group>
  )
}

/**
 * A small holographic robot — Android-mascot silhouette (domed head, two
 * splayed antennae, cylindrical body, stub arms/legs) for surfaces about
 * the system/AI core itself rather than the conversational companion.
 * Same real-state contract as Creature above.
 */
function Robot({ colorHex, glowIntensity, thinking }) {
  const group = useRef(null)
  const matRefs = useRef([])

  useFrame((state) => {
    const t = state.clock.elapsedTime
    const speed = thinking ? 2.6 : 1
    matRefs.current.forEach((m) => { if (m) m.uTime = t })
    if (group.current) {
      group.current.rotation.y = t * 0.3 * speed
      group.current.position.y = Math.sin(t * 1.3 * speed) * 0.07
    }
  })

  const setRef = (i) => (r) => { matRefs.current[i] = r }
  const mat = (i) => ({ ref: setRef(i), uColor: colorHex, uOpacity: glowIntensity, transparent: true, depthWrite: false, side: THREE.DoubleSide })

  return (
    <group ref={group}>
      {/* body */}
      <mesh position={[0, -0.32, 0]}>
        <cylinderGeometry args={[0.42, 0.5, 0.75, 24]} />
        <holoMaterial {...mat(0)} />
      </mesh>
      {/* head (dome) */}
      <mesh position={[0, 0.32, 0]}>
        <sphereGeometry args={[0.46, 24, 16, 0, Math.PI * 2, 0, Math.PI / 2]} />
        <holoMaterial {...mat(1)} />
      </mesh>
      <mesh position={[0, 0.32, 0]} rotation={[Math.PI, 0, 0]}>
        <cylinderGeometry args={[0.46, 0.46, 0.02, 24]} />
        <holoMaterial {...mat(2)} />
      </mesh>
      {/* antennae */}
      <mesh position={[-0.16, 0.86, 0]} rotation={[0, 0, 0.25]}>
        <cylinderGeometry args={[0.02, 0.02, 0.3, 8]} />
        <holoMaterial {...mat(3)} />
      </mesh>
      <mesh position={[0.16, 0.86, 0]} rotation={[0, 0, -0.25]}>
        <cylinderGeometry args={[0.02, 0.02, 0.3, 8]} />
        <holoMaterial {...mat(4)} />
      </mesh>
      <mesh position={[-0.235, 1.02, 0]}>
        <sphereGeometry args={[0.05, 12, 12]} />
        <meshBasicMaterial color={colorHex} transparent opacity={glowIntensity} />
      </mesh>
      <mesh position={[0.235, 1.02, 0]}>
        <sphereGeometry args={[0.05, 12, 12]} />
        <meshBasicMaterial color={colorHex} transparent opacity={glowIntensity} />
      </mesh>
      {/* arms */}
      <mesh position={[-0.56, -0.25, 0]} rotation={[0, 0, Math.PI / 2]}>
        <cylinderGeometry args={[0.08, 0.08, 0.42, 12]} />
        <holoMaterial {...mat(5)} />
      </mesh>
      <mesh position={[0.56, -0.25, 0]} rotation={[0, 0, Math.PI / 2]}>
        <cylinderGeometry args={[0.08, 0.08, 0.42, 12]} />
        <holoMaterial {...mat(6)} />
      </mesh>
      {/* legs */}
      <mesh position={[-0.2, -0.85, 0]}>
        <cylinderGeometry args={[0.09, 0.09, 0.32, 12]} />
        <holoMaterial {...mat(7)} />
      </mesh>
      <mesh position={[0.2, -0.85, 0]}>
        <cylinderGeometry args={[0.09, 0.09, 0.32, 12]} />
        <holoMaterial {...mat(8)} />
      </mesh>
      {/* eyes */}
      <mesh position={[-0.16, 0.32, 0.42]}>
        <sphereGeometry args={[0.08, 16, 16]} />
        <meshBasicMaterial color="#ffffff" transparent opacity={glowIntensity} />
      </mesh>
      <mesh position={[0.16, 0.32, 0.42]}>
        <sphereGeometry args={[0.08, 16, 16]} />
        <meshBasicMaterial color="#ffffff" transparent opacity={glowIntensity} />
      </mesh>
    </group>
  )
}

const SHIELD_SHAPE = (() => {
  const s = new THREE.Shape()
  s.moveTo(-0.5, 0.35)
  s.quadraticCurveTo(-0.5, 0.55, -0.25, 0.55)
  s.lineTo(0.25, 0.55)
  s.quadraticCurveTo(0.5, 0.55, 0.5, 0.35)
  s.lineTo(0.5, 0)
  s.quadraticCurveTo(0.5, -0.35, 0, -0.7)
  s.quadraticCurveTo(-0.5, -0.35, -0.5, 0)
  s.lineTo(-0.5, 0.35)
  return s
})()
const SHIELD_EXTRUDE = { depth: 0.07, bevelEnabled: true, bevelThickness: 0.02, bevelSize: 0.02, bevelSegments: 2 }

/**
 * A holographic shield — for surfaces about protection/risk (Guardian),
 * not a companion. Stands its ground rather than spinning: a slow
 * protective sway instead of continuous rotation, plus a pulsing core
 * gem whose speed reflects how actively risk is being (re)assessed.
 */
function Shield({ colorHex, glowIntensity, thinking }) {
  const group = useRef(null)
  const matRefs = useRef([])
  const gemRef = useRef(null)

  useFrame((state) => {
    const t = state.clock.elapsedTime
    const speed = thinking ? 2.2 : 1
    matRefs.current.forEach((m) => { if (m) m.uTime = t })
    if (group.current) {
      group.current.rotation.y = Math.sin(t * 0.5 * speed) * 0.35
      group.current.position.y = Math.sin(t * 1.1 * speed) * 0.05
    }
    if (gemRef.current) {
      const pulse = 0.7 + 0.3 * Math.sin(t * (thinking ? 5 : 2))
      gemRef.current.scale.setScalar(pulse)
    }
  })

  const setRef = (i) => (r) => { matRefs.current[i] = r }

  return (
    <group ref={group}>
      <mesh position={[0, 0, -0.035]}>
        <extrudeGeometry args={[SHIELD_SHAPE, SHIELD_EXTRUDE]} />
        <holoMaterial ref={setRef(0)} uColor={colorHex} uOpacity={glowIntensity} transparent depthWrite={false} side={THREE.DoubleSide} />
      </mesh>
      <mesh ref={gemRef} position={[0, 0.05, 0.08]}>
        <octahedronGeometry args={[0.16, 0]} />
        <meshBasicMaterial color="#ffffff" transparent opacity={glowIntensity} />
      </mesh>
    </group>
  )
}

/**
 * A holographic data-crystal cluster — for surfaces about the exportable
 * identity data itself (Insights Export), not a character. A large core
 * gem plus smaller satellite shards, all rotating independently, evoking
 * "crystallized/structured data" rather than a companion or a guard.
 */
function Crystal({ colorHex, glowIntensity, thinking }) {
  const group = useRef(null)
  const matRefs = useRef([])
  const shardRefs = useRef([])
  const SHARDS = [
    { pos: [0.55, 0.3, 0.1], scale: 0.28, speed: 1.4 },
    { pos: [-0.5, -0.15, 0.25], scale: 0.22, speed: 1.9 },
    { pos: [0.1, -0.5, -0.3], scale: 0.24, speed: 1.1 },
  ]

  useFrame((state) => {
    const t = state.clock.elapsedTime
    const speed = thinking ? 2.4 : 1
    matRefs.current.forEach((m) => { if (m) m.uTime = t })
    if (group.current) {
      group.current.rotation.y = t * 0.28 * speed
      group.current.rotation.x = Math.sin(t * 0.3) * 0.15
    }
    shardRefs.current.forEach((s, i) => {
      if (!s) return
      s.rotation.y = t * SHARDS[i].speed * speed
      s.rotation.x = t * SHARDS[i].speed * 0.6
    })
  })

  const setRef = (i) => (r) => { matRefs.current[i] = r }

  return (
    <group ref={group}>
      <mesh>
        <octahedronGeometry args={[0.62, 0]} />
        <holoMaterial ref={setRef(0)} uColor={colorHex} uOpacity={glowIntensity} transparent depthWrite={false} side={THREE.DoubleSide} />
      </mesh>
      {SHARDS.map((s, i) => (
        <mesh key={i} ref={(r) => { shardRefs.current[i] = r }} position={s.pos}>
          <octahedronGeometry args={[s.scale, 0]} />
          <holoMaterial ref={setRef(i + 1)} uColor={colorHex} uOpacity={glowIntensity} transparent depthWrite={false} side={THREE.DoubleSide} />
        </mesh>
      ))}
    </group>
  )
}

/**
 * A holographic neural-network cluster — for surfaces about stored
 * memory/knowledge structure (Memory tab), not a character. Nodes on a
 * Fibonacci sphere connected to their nearest neighbors, each node
 * pulsing on its own phase like independent memory traces; the whole
 * cluster breathes together only when "thinking".
 */
function NeuralNet({ colorHex, glowIntensity, thinking }) {
  const group = useRef(null)
  const nodeRefs = useRef([])
  const NODE_COUNT = 14
  const RADIUS = 0.75

  const nodes = useMemo(() => fibonacciSphere(NODE_COUNT, RADIUS), [])
  const edges = useMemo(() => {
    const pairs = []
    for (let i = 0; i < nodes.length; i++) {
      const dists = nodes
        .map((p, j) => ({ j, d: j === i ? Infinity : Math.hypot(p[0] - nodes[i][0], p[1] - nodes[i][1], p[2] - nodes[i][2]) }))
        .sort((a, b) => a.d - b.d)
        .slice(0, 2)
      dists.forEach(({ j }) => {
        const key = [i, j].sort().join('-')
        if (!pairs.some(p => p.key === key)) pairs.push({ key, a: nodes[i], b: nodes[j] })
      })
    }
    return pairs
  }, [nodes])

  useFrame((state) => {
    const t = state.clock.elapsedTime
    const speed = thinking ? 2.4 : 1
    if (group.current) group.current.rotation.y = t * 0.22 * speed
    nodeRefs.current.forEach((n, i) => {
      if (!n) return
      const pulse = 0.7 + 0.3 * Math.sin(t * (1.5 + (i % 4) * 0.3) * speed + i)
      n.scale.setScalar(pulse)
    })
  })

  return (
    <group ref={group}>
      {edges.map(({ key, a, b }) => (
        <Line key={key} points={[a, b]} color={colorHex} transparent opacity={0.25 * glowIntensity + 0.1} lineWidth={1} />
      ))}
      {nodes.map((p, i) => (
        <mesh key={i} ref={(r) => { nodeRefs.current[i] = r }} position={p}>
          <sphereGeometry args={[0.06, 12, 12]} />
          <meshBasicMaterial color={colorHex} transparent opacity={Math.min(1, glowIntensity + 0.2)} />
        </mesh>
      ))}
    </group>
  )
}

/** Dashboard: aggregate twin state as a core pulse with expanding rings — a heartbeat, not a character. */
function Pulse({ colorHex, glowIntensity, thinking }) {
  const group = useRef(null)
  const coreMatRef = useRef(null)
  const ringRefs = useRef([])
  const RING_COUNT = 3

  useFrame((state) => {
    const t = state.clock.elapsedTime
    const speed = thinking ? 2.5 : 1
    if (coreMatRef.current) coreMatRef.current.uTime = t
    if (group.current) group.current.rotation.y = t * 0.15
    ringRefs.current.forEach((r, i) => {
      if (!r) return
      const phase = ((t * speed * 0.5) + i / RING_COUNT) % 1
      const s = 0.35 + phase * 1.3
      r.scale.set(s, s, s)
      r.material.opacity = (1 - phase) * 0.55 * glowIntensity
    })
  })

  return (
    <group ref={group}>
      <mesh>
        <sphereGeometry args={[0.4, 32, 32]} />
        <holoMaterial ref={coreMatRef} uColor={colorHex} uOpacity={glowIntensity} transparent depthWrite={false} side={THREE.DoubleSide} />
      </mesh>
      {Array.from({ length: RING_COUNT }).map((_, i) => (
        <mesh key={i} ref={(r) => { ringRefs.current[i] = r }} rotation={[Math.PI / 2, 0, 0]}>
          <torusGeometry args={[0.55, 0.015, 8, 48]} />
          <meshBasicMaterial color={colorHex} transparent opacity={0} />
        </mesh>
      ))}
    </group>
  )
}

/** Identity: a double helix of small nodes — evolution across versions, not a static object. */
function Helix({ colorHex, glowIntensity, thinking }) {
  const group = useRef(null)
  const STRAND_COUNT = 10
  const strand = useMemo(() => {
    const a = [], b = [], rungs = []
    for (let i = 0; i < STRAND_COUNT; i++) {
      const yy = (i / (STRAND_COUNT - 1) - 0.5) * 1.4
      const angle = i * 0.9
      const r = 0.35
      const pa = [Math.cos(angle) * r, yy, Math.sin(angle) * r]
      const pb = [Math.cos(angle + Math.PI) * r, yy, Math.sin(angle + Math.PI) * r]
      a.push(pa); b.push(pb)
      if (i % 2 === 0) rungs.push([pa, pb])
    }
    return { a, b, rungs }
  }, [])

  useFrame((state) => {
    const t = state.clock.elapsedTime
    const speed = thinking ? 2.2 : 1
    if (group.current) group.current.rotation.y = t * 0.3 * speed
  })

  return (
    <group ref={group}>
      {[...strand.a, ...strand.b].map((p, i) => (
        <mesh key={i} position={p}>
          <sphereGeometry args={[0.07, 12, 12]} />
          <meshBasicMaterial color={colorHex} transparent opacity={glowIntensity} />
        </mesh>
      ))}
      {strand.rungs.map(([pa, pb], i) => (
        <Line key={i} points={[pa, pb]} color={colorHex} transparent opacity={0.3 * glowIntensity + 0.1} lineWidth={1} />
      ))}
    </group>
  )
}

/** Evidence: a small cluster of floating flat cards — the raw observational record. */
function Archive({ colorHex, glowIntensity, thinking }) {
  const group = useRef(null)
  const matRefs = useRef([])
  const CARDS = [
    { pos: [0, 0.25, 0], rot: [0.1, 0.3, 0.05] },
    { pos: [0.15, 0.05, 0.1], rot: [-0.05, -0.2, 0.1] },
    { pos: [-0.12, -0.1, -0.08], rot: [0.15, 0.5, -0.1] },
    { pos: [0.05, -0.28, 0.05], rot: [-0.1, 0.1, 0.15] },
  ]

  useFrame((state) => {
    const t = state.clock.elapsedTime
    const speed = thinking ? 2.3 : 1
    matRefs.current.forEach((m) => { if (m) m.uTime = t })
    if (group.current) group.current.rotation.y = t * 0.25 * speed
  })

  const setRef = (i) => (r) => { matRefs.current[i] = r }

  return (
    <group ref={group}>
      {CARDS.map((c, i) => (
        <mesh key={i} position={c.pos} rotation={c.rot}>
          <boxGeometry args={[0.55, 0.7, 0.03]} />
          <holoMaterial ref={setRef(i)} uColor={colorHex} uOpacity={glowIntensity} transparent depthWrite={false} side={THREE.DoubleSide} />
        </mesh>
      ))}
    </group>
  )
}

/** Behavior: a core with topics orbiting like planets, at distances that read as "importance". */
function Orbital({ colorHex, glowIntensity, thinking }) {
  const group = useRef(null)
  const coreMatRef = useRef(null)
  const planetRefs = useRef([])
  const PLANETS = [
    { radius: 0.85, size: 0.09, speed: 0.6 },
    { radius: 1.15, size: 0.06, speed: 0.4 },
    { radius: 1.4, size: 0.11, speed: 0.28 },
  ]

  useFrame((state) => {
    const t = state.clock.elapsedTime
    const speed = thinking ? 2.4 : 1
    if (coreMatRef.current) coreMatRef.current.uTime = t
    planetRefs.current.forEach((p, i) => {
      if (!p) return
      const a = t * PLANETS[i].speed * speed
      p.position.set(Math.cos(a) * PLANETS[i].radius, Math.sin(a * 0.6) * 0.2, Math.sin(a) * PLANETS[i].radius)
    })
  })

  return (
    <group ref={group}>
      <mesh>
        <sphereGeometry args={[0.42, 32, 32]} />
        <holoMaterial ref={coreMatRef} uColor={colorHex} uOpacity={glowIntensity} transparent depthWrite={false} side={THREE.DoubleSide} />
      </mesh>
      {PLANETS.map((p, i) => (
        <mesh key={i} ref={(r) => { planetRefs.current[i] = r }}>
          <sphereGeometry args={[p.size, 16, 16]} />
          <meshBasicMaterial color={colorHex} transparent opacity={glowIntensity} />
        </mesh>
      ))}
    </group>
  )
}

/** Planning: connected waypoints with a traveling light — the planner's execution path. */
function Pathway({ colorHex, glowIntensity, thinking }) {
  const group = useRef(null)
  const matRefs = useRef([])
  const pulseRef = useRef(null)
  const SEGMENTS = 6
  const points = useMemo(() => {
    const pts = []
    for (let i = 0; i < SEGMENTS; i++) {
      const a = (i / (SEGMENTS - 1)) * Math.PI * 1.3 - Math.PI * 0.65
      pts.push([Math.sin(a) * 0.9, (i / (SEGMENTS - 1) - 0.5) * 1.1, Math.cos(a) * 0.3 - 0.3])
    }
    return pts
  }, [])

  useFrame((state) => {
    const t = state.clock.elapsedTime
    const speed = thinking ? 2.5 : 1
    matRefs.current.forEach((m) => { if (m) m.uTime = t })
    if (group.current) group.current.rotation.y = t * 0.2
    if (pulseRef.current) {
      const phase = (t * speed * 0.35) % 1
      const idx = phase * (SEGMENTS - 1)
      const i0 = Math.floor(idx), i1 = Math.min(SEGMENTS - 1, i0 + 1)
      const f = idx - i0
      const p0 = points[i0], p1 = points[i1]
      pulseRef.current.position.set(
        p0[0] + (p1[0] - p0[0]) * f,
        p0[1] + (p1[1] - p0[1]) * f,
        p0[2] + (p1[2] - p0[2]) * f,
      )
    }
  })

  const setRef = (i) => (r) => { matRefs.current[i] = r }

  return (
    <group ref={group}>
      {points.map((p, i) => (
        <mesh key={i} position={p}>
          <sphereGeometry args={[0.09, 16, 16]} />
          <holoMaterial ref={setRef(i)} uColor={colorHex} uOpacity={glowIntensity} transparent depthWrite={false} side={THREE.DoubleSide} />
        </mesh>
      ))}
      {points.slice(0, -1).map((p, i) => (
        <Line key={`l${i}`} points={[p, points[i + 1]]} color={colorHex} transparent opacity={0.3 * glowIntensity + 0.15} lineWidth={1.5} />
      ))}
      <mesh ref={pulseRef}>
        <sphereGeometry args={[0.05, 12, 12]} />
        <meshBasicMaterial color="#ffffff" transparent opacity={glowIntensity} />
      </mesh>
    </group>
  )
}

/** Decision: a balance scale tilting — fact fusion weighing evidence against conflicts. */
function Scale({ colorHex, glowIntensity, thinking }) {
  const group = useRef(null)
  const beamRef = useRef(null)
  const panLRef = useRef(null)
  const panRRef = useRef(null)
  const matRefs = useRef([])

  useFrame((state) => {
    const t = state.clock.elapsedTime
    const speed = thinking ? 3 : 1
    matRefs.current.forEach((m) => { if (m) m.uTime = t })
    const tilt = Math.sin(t * speed * 0.7) * 0.18
    if (beamRef.current) beamRef.current.rotation.z = tilt
    if (panLRef.current) panLRef.current.position.y = 0.3 - Math.sin(tilt) * 0.55
    if (panRRef.current) panRRef.current.position.y = 0.3 + Math.sin(tilt) * 0.55
  })

  const setRef = (i) => (r) => { matRefs.current[i] = r }

  return (
    <group ref={group}>
      <mesh position={[0, -0.1, 0]}>
        <cylinderGeometry args={[0.03, 0.05, 0.85, 12]} />
        <holoMaterial ref={setRef(0)} uColor={colorHex} uOpacity={glowIntensity} transparent depthWrite={false} side={THREE.DoubleSide} />
      </mesh>
      <mesh position={[0, -0.52, 0]}>
        <cylinderGeometry args={[0.22, 0.22, 0.04, 24]} />
        <holoMaterial ref={setRef(1)} uColor={colorHex} uOpacity={glowIntensity} transparent depthWrite={false} side={THREE.DoubleSide} />
      </mesh>
      <group ref={beamRef} position={[0, 0.32, 0]}>
        <mesh rotation={[0, 0, Math.PI / 2]}>
          <cylinderGeometry args={[0.02, 0.02, 1.3, 8]} />
          <holoMaterial ref={setRef(2)} uColor={colorHex} uOpacity={glowIntensity} transparent depthWrite={false} side={THREE.DoubleSide} />
        </mesh>
      </group>
      <mesh ref={panLRef} position={[-0.62, 0.3, 0]}>
        <cylinderGeometry args={[0.16, 0.16, 0.02, 20]} />
        <meshBasicMaterial color={colorHex} transparent opacity={glowIntensity * 0.8} />
      </mesh>
      <mesh ref={panRRef} position={[0.62, 0.3, 0]}>
        <cylinderGeometry args={[0.16, 0.16, 0.02, 20]} />
        <meshBasicMaterial color={colorHex} transparent opacity={glowIntensity * 0.8} />
      </mesh>
    </group>
  )
}

/** Learning: a compass whose needle sweeps toward the best learned action. */
function Compass({ colorHex, glowIntensity, thinking }) {
  const group = useRef(null)
  const needleRef = useRef(null)
  const matRefs = useRef([])
  const TICK_COUNT = 12

  useFrame((state) => {
    const t = state.clock.elapsedTime
    const speed = thinking ? 3 : 1
    matRefs.current.forEach((m) => { if (m) m.uTime = t })
    if (group.current) group.current.rotation.x = 0.5
    if (needleRef.current) needleRef.current.rotation.y = t * speed * 0.5 + Math.sin(t * 0.3) * 0.4
  })

  const setRef = (i) => (r) => { matRefs.current[i] = r }

  return (
    <group ref={group}>
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[0.6, 0.02, 8, 48]} />
        <holoMaterial ref={setRef(0)} uColor={colorHex} uOpacity={glowIntensity} transparent depthWrite={false} side={THREE.DoubleSide} />
      </mesh>
      {Array.from({ length: TICK_COUNT }).map((_, i) => {
        const a = (i / TICK_COUNT) * Math.PI * 2
        return (
          <mesh key={i} position={[Math.cos(a) * 0.6, 0, Math.sin(a) * 0.6]}>
            <sphereGeometry args={[0.02, 6, 6]} />
            <meshBasicMaterial color={colorHex} transparent opacity={glowIntensity * 0.7} />
          </mesh>
        )
      })}
      <group ref={needleRef}>
        <mesh position={[0.22, 0, 0]} rotation={[0, 0, -Math.PI / 2]}>
          <coneGeometry args={[0.06, 0.36, 3]} />
          <meshBasicMaterial color={colorHex} transparent opacity={glowIntensity} />
        </mesh>
        <mesh position={[-0.22, 0, 0]} rotation={[0, 0, Math.PI / 2]}>
          <coneGeometry args={[0.06, 0.36, 3]} />
          <meshBasicMaterial color="#ffffff" transparent opacity={glowIntensity * 0.6} />
        </mesh>
      </group>
    </group>
  )
}

/** Pipeline: interlocking rings — the stage-by-stage execution chain. */
function Chain({ colorHex, glowIntensity, thinking }) {
  const group = useRef(null)
  const matRefs = useRef([])
  const LINKS = 5

  useFrame((state) => {
    const t = state.clock.elapsedTime
    const speed = thinking ? 2.6 : 1
    matRefs.current.forEach((m, i) => { if (m) m.uTime = t + i * 0.3 })
    if (group.current) group.current.rotation.y = t * 0.2 * speed
  })

  const setRef = (i) => (r) => { matRefs.current[i] = r }

  return (
    <group ref={group}>
      {Array.from({ length: LINKS }).map((_, i) => {
        const x = (i - (LINKS - 1) / 2) * 0.32
        const alt = i % 2 === 0
        return (
          <mesh key={i} position={[x, Math.sin(i * 1.3) * 0.1, 0]} rotation={[0, alt ? 0 : Math.PI / 2, 0]}>
            <torusGeometry args={[0.22, 0.045, 12, 32]} />
            <holoMaterial ref={setRef(i)} uColor={colorHex} uOpacity={glowIntensity} transparent depthWrite={false} side={THREE.DoubleSide} />
          </mesh>
        )
      })}
    </group>
  )
}

/** Analytics: an equalizer of oscillating bars — trend lines rendered as motion. */
function Equalizer({ colorHex, glowIntensity, thinking }) {
  const group = useRef(null)
  const barRefs = useRef([])
  const BAR_COUNT = 9

  useFrame((state) => {
    const t = state.clock.elapsedTime
    const speed = thinking ? 2.8 : 1
    if (group.current) group.current.rotation.y = Math.sin(t * 0.25) * 0.3
    barRefs.current.forEach((b, i) => {
      if (!b) return
      const h = 0.3 + (0.5 + 0.5 * Math.sin(t * speed * (1.3 + i * 0.17) + i)) * 0.7
      b.scale.y = h
      b.position.y = h * 0.35 - 0.3
    })
  })

  return (
    <group ref={group}>
      {Array.from({ length: BAR_COUNT }).map((_, i) => (
        <mesh key={i} ref={(r) => { barRefs.current[i] = r }} position={[(i - (BAR_COUNT - 1) / 2) * 0.16, 0, 0]}>
          <boxGeometry args={[0.09, 0.7, 0.09]} />
          <meshBasicMaterial color={colorHex} transparent opacity={glowIntensity * 0.85} />
        </mesh>
      ))}
    </group>
  )
}

/** Settings: two counter-rotating gears — configuration, systems working in sync. */
function Gear({ colorHex, glowIntensity, thinking }) {
  const group = useRef(null)
  const outerRef = useRef(null)
  const innerRef = useRef(null)
  const matRefs = useRef([])
  const TEETH = 10

  useFrame((state) => {
    const t = state.clock.elapsedTime
    const speed = thinking ? 2.6 : 1
    matRefs.current.forEach((m) => { if (m) m.uTime = t })
    if (outerRef.current) outerRef.current.rotation.z = t * 0.5 * speed
    if (innerRef.current) innerRef.current.rotation.z = -t * 0.9 * speed
  })

  const setRef = (i) => (r) => { matRefs.current[i] = r }

  return (
    <group ref={group}>
      <group ref={outerRef} rotation={[Math.PI / 2, 0, 0]}>
        <mesh>
          <cylinderGeometry args={[0.5, 0.5, 0.1, 32]} />
          <holoMaterial ref={setRef(0)} uColor={colorHex} uOpacity={glowIntensity} transparent depthWrite={false} side={THREE.DoubleSide} />
        </mesh>
        {Array.from({ length: TEETH }).map((_, i) => {
          const a = (i / TEETH) * Math.PI * 2
          return (
            <mesh key={i} position={[Math.cos(a) * 0.55, 0, Math.sin(a) * 0.55]} rotation={[0, -a, 0]}>
              <boxGeometry args={[0.1, 0.1, 0.08]} />
              <holoMaterial ref={setRef(i + 1)} uColor={colorHex} uOpacity={glowIntensity} transparent depthWrite={false} side={THREE.DoubleSide} />
            </mesh>
          )
        })}
      </group>
      <group ref={innerRef} rotation={[Math.PI / 2, 0, 0]} position={[0, 0, 0.15]}>
        <mesh>
          <cylinderGeometry args={[0.22, 0.22, 0.08, 20]} />
          <meshBasicMaterial color="#ffffff" transparent opacity={glowIntensity * 0.7} />
        </mesh>
      </group>
    </group>
  )
}

/** Import: a gateway ring with particles flowing inward — data entering the twin. */
function Portal({ colorHex, glowIntensity, thinking }) {
  const group = useRef(null)
  const ringRef = useRef(null)
  const matRefs = useRef([])
  const PARTICLE_COUNT = 10
  const particleRefs = useRef([])

  useFrame((state) => {
    const t = state.clock.elapsedTime
    const speed = thinking ? 2.6 : 1
    matRefs.current.forEach((m) => { if (m) m.uTime = t })
    if (ringRef.current) ringRef.current.rotation.z = t * 0.3 * speed
    particleRefs.current.forEach((p, i) => {
      if (!p) return
      const phase = ((t * speed * 0.3) + i / PARTICLE_COUNT) % 1
      const angle = (i / PARTICLE_COUNT) * Math.PI * 2
      const r = 1.0 * (1 - phase)
      p.position.set(Math.cos(angle) * r, Math.sin(angle) * r * 0.4, (1 - phase) * 0.6 - 0.3)
      p.material.opacity = phase < 0.9 ? glowIntensity * 0.8 : glowIntensity * 0.8 * (1 - (phase - 0.9) * 10)
    })
  })

  const setRef = (i) => (r) => { matRefs.current[i] = r }

  return (
    <group ref={group}>
      <mesh ref={ringRef}>
        <torusGeometry args={[0.65, 0.05, 12, 40]} />
        <holoMaterial ref={setRef(0)} uColor={colorHex} uOpacity={glowIntensity} transparent depthWrite={false} side={THREE.DoubleSide} />
      </mesh>
      {Array.from({ length: PARTICLE_COUNT }).map((_, i) => (
        <mesh key={i} ref={(r) => { particleRefs.current[i] = r }}>
          <sphereGeometry args={[0.04, 8, 8]} />
          <meshBasicMaterial color={colorHex} transparent opacity={0} />
        </mesh>
      ))}
    </group>
  )
}

/** Documentation: an open book with glowing lines of text — the reference material. */
function Tome({ colorHex, glowIntensity, thinking }) {
  const group = useRef(null)
  const matRefs = useRef([])
  const LINES = 4

  useFrame((state) => {
    const t = state.clock.elapsedTime
    const speed = thinking ? 2.3 : 1
    matRefs.current.forEach((m) => { if (m) m.uTime = t })
    if (group.current) group.current.rotation.y = Math.sin(t * 0.3 * speed) * 0.4
  })

  const setRef = (i) => (r) => { matRefs.current[i] = r }

  return (
    <group ref={group} rotation={[0.3, 0, 0]}>
      <mesh position={[-0.32, 0, 0]} rotation={[0, 0.5, 0]}>
        <boxGeometry args={[0.6, 0.8, 0.02]} />
        <holoMaterial ref={setRef(0)} uColor={colorHex} uOpacity={glowIntensity} transparent depthWrite={false} side={THREE.DoubleSide} />
      </mesh>
      <mesh position={[0.32, 0, 0]} rotation={[0, -0.5, 0]}>
        <boxGeometry args={[0.6, 0.8, 0.02]} />
        <holoMaterial ref={setRef(1)} uColor={colorHex} uOpacity={glowIntensity} transparent depthWrite={false} side={THREE.DoubleSide} />
      </mesh>
      {Array.from({ length: LINES }).map((_, i) => (
        <mesh key={i} position={[0.32, 0.22 - i * 0.14, 0.012]} rotation={[0, -0.5, 0]}>
          <boxGeometry args={[0.4 - i * 0.05, 0.03, 0.005]} />
          <meshBasicMaterial color="#ffffff" transparent opacity={glowIntensity * 0.5} />
        </mesh>
      ))}
    </group>
  )
}

/** Guide: a beacon spire with a sweeping rotating light — wayfinding. */
function Beacon({ colorHex, glowIntensity, thinking }) {
  const group = useRef(null)
  const beamRef = useRef(null)
  const matRefs = useRef([])

  useFrame((state) => {
    const t = state.clock.elapsedTime
    const speed = thinking ? 3 : 1
    matRefs.current.forEach((m) => { if (m) m.uTime = t })
    if (beamRef.current) beamRef.current.rotation.y = t * speed * 1.2
    if (group.current) group.current.position.y = Math.sin(t * 1.2) * 0.04
  })

  const setRef = (i) => (r) => { matRefs.current[i] = r }

  return (
    <group ref={group}>
      <mesh position={[0, -0.1, 0]}>
        <coneGeometry args={[0.28, 1.0, 20]} />
        <holoMaterial ref={setRef(0)} uColor={colorHex} uOpacity={glowIntensity} transparent depthWrite={false} side={THREE.DoubleSide} />
      </mesh>
      <mesh position={[0, 0.45, 0]}>
        <sphereGeometry args={[0.12, 16, 16]} />
        <meshBasicMaterial color="#ffffff" transparent opacity={glowIntensity} />
      </mesh>
      <group ref={beamRef} position={[0, 0.45, 0]}>
        <mesh position={[0.5, 0, 0]} rotation={[0, 0, -Math.PI / 2]}>
          <coneGeometry args={[0.25, 1.3, 3, 1, true]} />
          <meshBasicMaterial color={colorHex} transparent opacity={glowIntensity * 0.25} side={THREE.DoubleSide} />
        </mesh>
      </group>
    </group>
  )
}

function OrbitingLabels({ topics, colorHex }) {
  const items = useMemo(() => topics.slice(0, 6).map((t, i, arr) => ({
    label: t.length > 18 ? t.slice(0, 16) + '…' : t,
    angle: (i / arr.length) * Math.PI * 2,
    radius: 1.9 + (i % 2) * 0.25,
    tilt: (i % 3) * 0.35 - 0.35,
    speed: 0.18 + (i % 3) * 0.05,
  })), [topics.join('|')])

  const refs = useRef([])

  useFrame((state) => {
    const t = state.clock.elapsedTime
    items.forEach((item, i) => {
      const g = refs.current[i]
      if (!g) return
      const a = item.angle + t * item.speed
      g.position.set(Math.cos(a) * item.radius, item.tilt + Math.sin(t * 0.6 + i) * 0.1, Math.sin(a) * item.radius)
    })
  })

  return (
    <>
      {items.map((item, i) => (
        <group key={item.label + i} ref={(r) => { refs.current[i] = r }}>
          <Billboard>
            <Text fontSize={0.16} color={colorHex} anchorX="center" anchorY="middle" outlineWidth={0.006} outlineColor="#000000" outlineOpacity={0.6}>
              {item.label}
            </Text>
          </Billboard>
        </group>
      ))}
    </>
  )
}

// All CharacterCreature3D instances share a single <Canvas> mounted once at
// the app shell (see AppShell.jsx) and rendered into via <View>, so route
// navigation never tears down/recreates a WebGL context. Since only one
// instance is ever visible at a time in this app, each active View is free
// to point the shared camera at its own preferred framing on mount.
function CameraRig({ distance, fov }) {
  const camera = useThree((s) => s.camera)
  useLayoutEffect(() => {
    camera.position.set(0, 0, distance)
    camera.fov = fov
    camera.updateProjectionMatrix()
  }, [camera, distance, fov])
  return null
}

export default function CharacterCreature3D({
  confidence = 0.5,
  topics = [],
  moodColor = null,
  thinking = false,
  size = 160,
  showLabels = true,
  variant = 'creature',
}) {
  const colorHex = moodColor || '#818cf8'
  const glowIntensity = 0.45 + confidence * 0.55
  const BEINGS = {
    robot: Robot, shield: Shield, crystal: Crystal, neural: NeuralNet, creature: Creature,
    pulse: Pulse, helix: Helix, archive: Archive, orbital: Orbital, pathway: Pathway,
    scale: Scale, compass: Compass, chain: Chain, equalizer: Equalizer, gear: Gear,
    portal: Portal, tome: Tome, beacon: Beacon,
  }
  const Being = BEINGS[variant] || Creature

  return (
    <View style={{ width: size, height: size }}>
      <CameraRig distance={showLabels ? 4.4 : 3.1} fov={38} />
      <ambientLight intensity={0.3} />
      <Being colorHex={colorHex} glowIntensity={glowIntensity} thinking={thinking} />
      {showLabels && topics.length > 0 && <OrbitingLabels topics={topics} colorHex={colorHex} />}
      <Sparkles
        count={thinking ? 60 : 28}
        scale={[2.4, 2.4, 2.4]}
        size={thinking ? 2.5 : 1.5}
        speed={thinking ? 0.8 : 0.3}
        color={colorHex}
        opacity={0.6}
      />
    </View>
  )
}
