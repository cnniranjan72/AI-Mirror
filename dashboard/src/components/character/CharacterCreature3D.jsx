import { useRef, useMemo } from 'react'
import { Canvas, useFrame, extend } from '@react-three/fiber'
import { Text, Billboard, Sparkles, shaderMaterial } from '@react-three/drei'
import * as THREE from 'three'

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
}) {
  const colorHex = moodColor || '#818cf8'
  const glowIntensity = 0.45 + confidence * 0.55

  return (
    <div style={{ width: size, height: size }}>
      <Canvas
        camera={{ position: [0, 0, showLabels ? 4.4 : 3.1], fov: 38 }}
        gl={{ alpha: true, antialias: true }}
        dpr={[1, 2]}
      >
        <ambientLight intensity={0.3} />
        <Creature colorHex={colorHex} glowIntensity={glowIntensity} thinking={thinking} />
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
