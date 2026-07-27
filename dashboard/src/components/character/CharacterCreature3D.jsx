import { useRef, useMemo } from 'react'
import { Canvas, useFrame, extend } from '@react-three/fiber'
import { Text, Billboard, Sparkles, Line, shaderMaterial } from '@react-three/drei'
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
  const BEINGS = { robot: Robot, shield: Shield, crystal: Crystal, neural: NeuralNet, creature: Creature }
  const Being = BEINGS[variant] || Creature

  return (
    <div style={{ width: size, height: size }}>
      <Canvas
        camera={{ position: [0, 0, showLabels ? 4.4 : 3.1], fov: 38 }}
        gl={{ alpha: true, antialias: true }}
        dpr={[1, 2]}
      >
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
      </Canvas>
    </div>
  )
}
