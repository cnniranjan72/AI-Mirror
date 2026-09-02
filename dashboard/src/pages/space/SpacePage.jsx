import { useMemo, useRef, useState } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { api } from '../../api/client'
import { useApi } from '../../hooks/useApi'
import GlassCard from '../../components/ui/GlassCard'
import Badge from '../../components/ui/Badge'
import AsyncState from '../../components/ui/AsyncState'
import SceneBoundary from '../../three/SceneBoundary'
import { hasWebGL } from '../../three/webgl'
import { useReducedMotion } from '../../hooks/useMotion'

/**
 * Behaviour Space — every piece of content the system embedded, as a shape.
 *
 * The 384-dimensional vectors behind every claim have never been shown to
 * anyone. This is the raw material the rest of the product argues about.
 *
 * The projection is PCA and the page says so, because the choice carries a
 * claim. t-SNE and UMAP separate clusters far more attractively and produce a
 * different picture on every run; a product arguing that its reasoning
 * reproduces cannot hand someone a map of themselves that rearranges each time
 * they open it. The same history draws the same shape.
 *
 * The variance figure is displayed as prominently as the cloud. Three
 * components out of 384 capture a minority of the structure — around 40% on
 * real data — and a convincing 3D picture shown without that number would
 * invite people to read clusters that are mostly projection artefact.
 */

const PALETTE = [
  '#818cf8', '#34d399', '#fbbf24', '#fb7185',
  '#22d3ee', '#c084fc', '#a3e635', '#f97316',
]

function Cloud({ points, labels, active, reduced }) {
  const group = useRef()

  // Slow rotation only. Anything faster reads as a screensaver and makes the
  // positions — which are the actual information — harder to compare.
  useFrame((_state, delta) => {
    if (group.current && !reduced) group.current.rotation.y += delta * 0.08
  })

  const colourFor = useMemo(() => {
    const map = new Map()
    labels.forEach((l, i) => map.set(l, PALETTE[i % PALETTE.length]))
    return map
  }, [labels])

  return (
    <group ref={group}>
      {points.map((p, i) => {
        const dimmed = active && p.label !== active
        return (
          <mesh key={i} position={[p.x * 2.2, p.y * 2.2, p.z * 2.2]}>
            <sphereGeometry args={[dimmed ? 0.022 : 0.038, 10, 10]} />
            <meshBasicMaterial
              color={colourFor.get(p.label) || '#818cf8'}
              transparent
              opacity={dimmed ? 0.12 : 0.85}
            />
          </mesh>
        )
      })}
    </group>
  )
}

export default function SpacePage() {
  const { data, loading, error, refetch } = useApi(() => api.getBehaviourSpace(), [])
  const [active, setActive] = useState(null)
  const reduced = useReducedMotion()
  const webgl = useMemo(() => hasWebGL(), [])

  const points = data?.points || []
  const labels = data?.labels || []

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 className="gradient-text" style={{ fontSize: 32, fontWeight: 800, letterSpacing: '-0.03em', marginBottom: 6 }}>
          Behaviour Space
        </h1>
        <p style={{ color: 'var(--text-tertiary)', fontSize: 15, maxWidth: 740 }}>
          Every piece of content the system embedded, projected from 384 dimensions into
          three. This is the raw material every other claim in the product is built from.
        </p>
      </div>

      <AsyncState loading={loading} error={error} onRetry={refetch}>
        {!data?.measurable ? (
          <GlassCard gradient>
            <Badge variant="slate">
              {data?.degenerate ? 'No shape to show' : 'Not enough data'}
            </Badge>
            <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginTop: 10, lineHeight: 1.6 }}>
              {data?.note}
            </p>
          </GlassCard>
        ) : (
          <>
            {/* The disclosure sits above the picture on purpose. Below it, it
                reads as a footnote to something already believed. */}
            <GlassCard style={{ marginBottom: 16 }}>
              <div style={{ display: 'flex', gap: 26, flexWrap: 'wrap', alignItems: 'baseline' }}>
                <div>
                  <div style={{ fontSize: 26, fontWeight: 800, color: '#a5b4fc' }}>
                    {Math.round(data.variance_captured * 100)}%
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                    of the structure is visible here
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 26, fontWeight: 800, color: 'var(--text-secondary)' }}>
                    {data.dimensions_in}&nbsp;&rarr;&nbsp;3
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>dimensions</div>
                </div>
                <div style={{ flex: '1 1 260px', fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                  {data.note}
                </div>
              </div>
            </GlassCard>

            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 14 }}>
              {labels.map((l, i) => (
                <button
                  key={l}
                  onClick={() => setActive(active === l ? null : l)}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 6,
                    padding: '4px 10px', borderRadius: 999, cursor: 'pointer',
                    fontSize: 12,
                    border: `1px solid ${active === l ? PALETTE[i % PALETTE.length] : 'var(--border-subtle)'}`,
                    background: active === l ? 'rgba(148,163,184,0.10)' : 'transparent',
                    color: active === l ? 'var(--text-primary)' : 'var(--text-tertiary)',
                  }}
                >
                  <span style={{
                    width: 8, height: 8, borderRadius: 999,
                    background: PALETTE[i % PALETTE.length],
                  }} />
                  {l}
                </button>
              ))}
            </div>

            <GlassCard style={{ padding: 0, overflow: 'hidden' }}>
              {webgl ? (
                <SceneBoundary
                  fallback={
                    <div style={{ padding: 40, textAlign: 'center', fontSize: 13, color: 'var(--text-muted)' }}>
                      The 3D view could not start. The figures above still describe the space.
                    </div>
                  }
                >
                  <div style={{ height: 460 }}>
                    <Canvas camera={{ position: [0, 0, 5.4], fov: 50 }} dpr={[1, 2]}>
                      <Cloud points={points} labels={labels} active={active} reduced={reduced} />
                    </Canvas>
                  </div>
                </SceneBoundary>
              ) : (
                <div style={{ padding: 40, textAlign: 'center', fontSize: 13, color: 'var(--text-muted)' }}>
                  This browser has no WebGL, so the cloud is not drawn. The figures above
                  still describe the space.
                </div>
              )}
            </GlassCard>

            <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 12, lineHeight: 1.6 }}>
              {points.length} items shown. Distance between points is similarity of meaning,
              as the embedding model measures it. Because the projection is deterministic,
              this shape is stable: opening the page again draws the same map.
            </p>
          </>
        )}
      </AsyncState>
    </div>
  )
}
