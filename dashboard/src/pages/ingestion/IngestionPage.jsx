import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApi } from '../../hooks/useApi'
import { api, DEFAULT_USER } from '../../api/client'
import GlassCard from '../../components/ui/GlassCard'
import Badge from '../../components/ui/Badge'
import { CheckIcon, RefreshIcon } from '../../icons/icons'

const PIPELINE_STAGES = [
  'Behavior Gateway', 'Content Intelligence', 'Knowledge Consolidation',
  'Behavior Objects', 'Evidence', 'Inference', 'Reflection', 'Identity',
]

function Stat({ label, value, accent }) {
  return (
    <div style={{ textAlign: 'center', padding: '18px 8px', background: 'rgba(148,163,184,0.04)', borderRadius: 12, border: '1px solid var(--border-subtle)' }}>
      <div style={{ fontSize: 26, fontWeight: 800, color: `var(--${accent}-400, #818cf8)` }}>{value}</div>
      <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>{label}</div>
    </div>
  )
}

export default function IngestionPage() {
  const navigate = useNavigate()
  const { data: summary, loading, refetch } = useApi(() => api.getCognitiveSummary(), [])
  const [seeding, setSeeding] = useState(false)
  const [seedResult, setSeedResult] = useState(null)
  const [error, setError] = useState(null)

  const cur = summary?.current_identity || {}

  const runSeed = async () => {
    setError(null); setSeeding(true); setSeedResult(null)
    try {
      const res = await api.seedDemo()
      setSeedResult(res)
      refetch()
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || 'Seeding failed')
    } finally {
      setSeeding(false)
    }
  }

  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>
      <div style={{ marginBottom: 32 }}>
        <h1 className="gradient-text" style={{ fontSize: 32, fontWeight: 800, letterSpacing: '-0.03em', marginBottom: 6 }}>
          Data Ingestion
        </h1>
        <p style={{ color: 'var(--text-tertiary)', fontSize: 15 }}>
          How behavioral data flows into your cognitive twin
        </p>
      </div>

      {/* Current twin state — real data */}
      <GlassCard gradient>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600 }}>Your Twin Right Now</h3>
          <Badge variant={summary?.behavior_object_count ? 'emerald' : 'neutral'} dot>
            {summary?.behavior_object_count ? 'Data connected' : 'No data yet'}
          </Badge>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(130px, 1fr))', gap: 12 }}>
          <Stat label="Behavior Objects" value={loading ? '—' : (summary?.behavior_object_count ?? 0)} accent="indigo" />
          <Stat label="Evidence" value={loading ? '—' : (summary?.evidence_count ?? 0)} accent="violet" />
          <Stat label="Snapshots" value={loading ? '—' : (summary?.snapshot_count ?? 0)} accent="pink" />
          <Stat label="Reflections" value={loading ? '—' : (summary?.reflection_count ?? 0)} accent="amber" />
          <Stat label="Identity" value={loading ? '—' : (cur.identity_version ? `v${cur.identity_version}` : '—')} accent="cyan" />
          <Stat label="Confidence" value={loading ? '—' : (cur.overall_confidence != null ? `${Math.round(cur.overall_confidence * 100)}%` : '—')} accent="emerald" />
        </div>
      </GlassCard>

      {/* The two real ingestion paths */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, margin: '24px 0' }}>
        {/* Live extension */}
        <GlassCard>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
            <div style={{ fontSize: 24 }}>🧩</div>
            <h3 style={{ fontSize: 16, fontWeight: 600 }}>Live tracking (extension)</h3>
          </div>
          <p style={{ fontSize: 13, color: 'var(--text-tertiary)', lineHeight: 1.6, marginBottom: 14 }}>
            The AIMirror browser extension captures each Reel you watch — creator,
            caption, hashtags, audio, watch time, likes/saves — and streams it here
            automatically as you browse.
          </p>
          <ol style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.9, paddingLeft: 18, margin: 0 }}>
            <li><code>chrome://extensions</code> → enable Developer mode</li>
            <li>Load unpacked → the <code>chrome-extension</code> folder</li>
            <li>Open instagram.com/reels and scroll</li>
          </ol>
          <div style={{ marginTop: 14 }}>
            <Badge variant="indigo">user: {DEFAULT_USER}</Badge>
          </div>
        </GlassCard>

        {/* Demo seed — real backend call */}
        <GlassCard>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
            <div style={{ fontSize: 24 }}>⚡</div>
            <h3 style={{ fontSize: 16, fontWeight: 600 }}>Generate demo data</h3>
          </div>
          <p style={{ fontSize: 13, color: 'var(--text-tertiary)', lineHeight: 1.6, marginBottom: 14 }}>
            Runs synthetic behavioral events through the real V3 pipeline
            (embeddings → behavior objects → evidence → identity). Takes a
            moment; results below are returned by the backend.
          </p>
          <button
            onClick={runSeed}
            disabled={seeding}
            style={{
              padding: '10px 20px', borderRadius: 10, border: 'none',
              background: seeding ? 'rgba(148,163,184,0.15)' : 'var(--accent-gradient)',
              color: 'white', fontSize: 14, fontWeight: 600,
              cursor: seeding ? 'wait' : 'pointer',
              display: 'inline-flex', alignItems: 'center', gap: 8,
            }}
          >
            {seeding ? (<><div style={{ animation: 'spin 1s linear infinite', display: 'flex' }}><RefreshIcon /></div> Running pipeline…</>)
              : 'Run demo seed'}
          </button>
          {error && <div style={{ marginTop: 12, fontSize: 13, color: '#f87171' }}>{error}</div>}
          {seedResult && (
            <div style={{ marginTop: 14, padding: 12, borderRadius: 8, background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.2)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, fontWeight: 600, color: '#34d399', marginBottom: 6 }}>
                <CheckIcon /> Seeded user {seedResult.user_id}
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.7 }}>
                {seedResult.events_stored} events · {seedResult.pipeline_result?.behavior_object_count ?? 0} behavior objects ·
                {' '}{seedResult.pipeline_result?.evidence_count ?? 0} evidence · identity v{seedResult.pipeline_result?.identity_version ?? '?'}
              </div>
            </div>
          )}
        </GlassCard>
      </div>

      {/* The real pipeline stages */}
      <GlassCard gradient>
        <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 6 }}>Cognitive Pipeline</h3>
        <p style={{ fontSize: 13, color: 'var(--text-tertiary)', marginBottom: 20 }}>
          Every ingested event flows through these stages before it reaches your identity.
        </p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center' }}>
          {PIPELINE_STAGES.map((s, i) => (
            <div key={s} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={{ padding: '8px 14px', borderRadius: 8, background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.2)', fontSize: 13, color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
                {s}
              </div>
              {i < PIPELINE_STAGES.length - 1 && <span style={{ color: 'var(--text-muted)' }}>→</span>}
            </div>
          ))}
        </div>
        <button
          onClick={() => navigate('/pipeline')}
          style={{ marginTop: 20, padding: '8px 16px', borderRadius: 8, border: '1px solid var(--border-subtle)', background: 'transparent', color: 'var(--text-secondary)', fontSize: 13, cursor: 'pointer' }}
        >
          View live pipeline traces →
        </button>
      </GlassCard>
    </div>
  )
}
