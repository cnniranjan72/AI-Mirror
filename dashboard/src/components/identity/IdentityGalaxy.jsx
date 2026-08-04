import { useEffect, useRef } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { OrbitControls, Text, Billboard, Sparkles } from '@react-three/drei'

const TREND_COLOR = {
  growing: '#34d399',
  declining: '#f87171',
  stable: '#818cf8',
  emerging: '#fbbf24',
}

function Core({ confidence }) {
  const ref = useRef()
  useFrame((state) => {
    if (ref.current) ref.current.rotation.y = state.clock.elapsedTime * 0.15
  })
  return (
    <group>
      <mesh ref={ref}>
        <icosahedronGeometry args={[0.55, 1]} />
        <meshStandardMaterial color="#818cf8" emissive="#818cf8" emissiveIntensity={0.4 + confidence * 0.6} wireframe />
      </mesh>
      <mesh>
        <sphereGeometry args={[0.3, 16, 16]} />
        <meshBasicMaterial color="#c7d2fe" transparent opacity={0.6} />
      </mesh>
    </group>
  )
}

function Planet({ topic, angle, radius, size, color, onSelect, selected }) {
  const groupRef = useRef()
  const speed = 0.12 / Math.max(0.5, radius)
  useFrame((state) => {
    const t = state.clock.elapsedTime * speed + angle
    if (groupRef.current) {
      groupRef.current.position.set(Math.cos(t) * radius, Math.sin(t * 0.4) * 0.5, Math.sin(t) * radius)
    }
  })
  return (
    <group ref={groupRef}>
      <mesh onClick={(e) => { e.stopPropagation(); onSelect(topic) }}>
        <sphereGeometry args={[size, 24, 24]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={selected ? 1.1 : 0.4}
          roughness={0.4}
        />
      </mesh>
      {selected && (
        <mesh>
          <ringGeometry args={[size * 1.3, size * 1.45, 32]} />
          <meshBasicMaterial color={color} transparent opacity={0.6} side={2} />
        </mesh>
      )}
      <Billboard>
        <Text
          position={[0, size + 0.32, 0]}
          fontSize={0.2}
          color="#e2e8f0"
          anchorX="center"
          anchorY="middle"
          outlineWidth={0.006}
          outlineColor="#000000"
          outlineOpacity={0.7}
        >
          {topic.topic}
        </Text>
      </Billboard>
    </group>
  )
}

/**
 * topics: [{ topic, trend, strength, confidence, frequency }] — real interest_graph.dominant_interests
 * confidence: identity.overall_confidence
 */
export default function IdentityGalaxy({ topics, confidence, onSelectTopic, selectedTopic, style }) {
  // This page (like every route) is React.lazy-loaded, so this component can
  // mount before the surrounding grid/card layout has finished settling.
  // R3F's Canvas measures its container once on mount via ResizeObserver;
  // if that first measurement lands during the pre-layout moment, the
  // canvas gets stuck at the browser's ~300x150 fallback size forever
  // (verified live — nothing subsequently re-triggers a re-measure).
  // Dispatching a resize event a tick after mount forces R3F to re-read the
  // container's real, settled size.
  useEffect(() => {
    const id = setTimeout(() => window.dispatchEvent(new Event('resize')), 50)
    return () => clearTimeout(id)
  }, [])

  if (!topics || topics.length === 0) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-muted)', fontSize: 13, ...style }}>
        No dominant topics yet — your identity galaxy forms as your behavior objects accumulate confidence.
      </div>
    )
  }

  return (
    <div style={style}>
      <Canvas camera={{ position: [0, 3.2, 8.5], fov: 45 }} gl={{ alpha: true, antialias: true }} dpr={[1, 2]}>
        <ambientLight intensity={0.35} />
        <pointLight position={[5, 5, 5]} intensity={1.1} color="#a5b4fc" />
        <pointLight position={[-5, -3, -5]} intensity={0.4} color="#f472b6" />
        <Core confidence={confidence} />
        {topics.map((t, i) => (
          <Planet
            key={t.topic}
            topic={t}
            angle={(i / topics.length) * Math.PI * 2}
            radius={2.1 + i * 0.85}
            size={0.22 + Math.min(1, t.strength || t.confidence || 0.2) * 0.9}
            color={TREND_COLOR[t.trend] || TREND_COLOR.stable}
            onSelect={onSelectTopic}
            selected={selectedTopic === t.topic}
          />
        ))}
        <Sparkles count={80} scale={[10, 6, 10]} size={1.2} speed={0.2} color="#818cf8" opacity={0.3} />
        <OrbitControls enableZoom enablePan={false} autoRotate autoRotateSpeed={0.35} minDistance={4} maxDistance={16} />
      </Canvas>
    </div>
  )
}
