import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApi } from '../../hooks/useApi'
import { api, DEFAULT_USER } from '../../api/client'
import GlassCard from '../../components/ui/GlassCard'
import Badge from '../../components/ui/Badge'
import { CheckIcon, RefreshIcon, UploadIcon } from '../../icons/icons'
import CharacterCreature3D from '../../components/character/CharacterCreature3D'
import LiveIngestionPulse from '../../components/ingestion/LiveIngestionPulse'

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
  const { data: summary, loading, error: summaryError, refetch } = useApi(() => api.getCognitiveSummary(), [])
  // Extraction failures the browser extension already decided to drop (e.g.
  // a DOM selector gone stale after YouTube/Instagram changes their markup)
  // — same class of bug as the "untitled" caption issue, now surfaced
  // instead of only living in the extension's own console.
  const { data: extractionWarnings } = useApi(
    () => api.getAdminErrors('extension_extraction_failed', 20), []
  )
  const warningList = extractionWarnings?.errors || []
  const [seeding, setSeeding] = useState(false)
  const [seedResult, setSeedResult] = useState(null)
  const [error, setError] = useState(null)

  // Data-export import
  const fileInputRef = useRef(null)
  const [importing, setImporting] = useState(false)
  const [importProgress, setImportProgress] = useState(0)
  const [importResult, setImportResult] = useState(null)
  const [importError, setImportError] = useState(null)
  const [dragging, setDragging] = useState(false)

  const cur = summary?.current_identity || {}
  const platformBreakdown = summary?.platform_breakdown || {}
  const platformTotal = Object.values(platformBreakdown).reduce((a, b) => a + b, 0)
  const PLATFORM_META = {
    instagram: { label: 'Instagram', color: '#ec4899', icon: '📸' },
    youtube: { label: 'YouTube', color: '#f43f5e', icon: '▶️' },
  }

  const runImport = async (fileObj) => {
    if (!fileObj) return
    setImportError(null); setImportResult(null); setImporting(true); setImportProgress(0)
    try {
      const res = await api.importArchive(fileObj, undefined, setImportProgress)
      setImportResult(res)
      // The whole point of an import is the numbers changing, so pull the
      // summary again rather than leaving stale counts on screen.
      refetch()
    } catch (err) {
      setImportError(err?.response?.data?.detail || err.message || 'Import failed')
    } finally {
      setImporting(false)
    }
  }

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
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 32 }}>
        <div style={{ width: 68, height: 68, flexShrink: 0, margin: '-8px 0' }}>
          <CharacterCreature3D size={68} variant="portal" confidence={summary?.behavior_object_count ? 0.7 : 0.35} topics={Object.keys(platformBreakdown)} thinking={loading || seeding} showLabels={false} />
        </div>
        <div>
          <h1 className="gradient-text" style={{ fontSize: 32, fontWeight: 800, letterSpacing: '-0.03em', marginBottom: 6 }}>
            Data Ingestion
          </h1>
          <p style={{ color: 'var(--text-tertiary)', fontSize: 15 }}>
            How behavioral data flows into your cognitive twin
          </p>
        </div>
      </div>

      {summaryError && (
        <div className="empty-state" style={{ marginBottom: 20, padding: '24px 20px' }}>
          <div className="empty-state-icon" style={{ fontSize: 32, marginBottom: 8 }}>⚠️</div>
          <div className="empty-state-title" style={{ fontSize: 15 }}>Couldn't load your ingestion summary</div>
          <div className="empty-state-description">{typeof summaryError === 'string' ? summaryError : 'Something went wrong talking to the backend.'}</div>
          <button className="btn btn-secondary" onClick={refetch} style={{ marginTop: 12 }}>Try again</button>
        </div>
      )}

      {warningList.length > 0 && (
        <GlassCard style={{ marginBottom: 20, border: '1px solid rgba(244,63,94,0.25)', background: 'rgba(244,63,94,0.06)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <span style={{ fontSize: 16 }}>⚠️</span>
            <h3 style={{ fontSize: 14, fontWeight: 600, color: '#fca5a5' }}>
              {warningList.length} extraction warning{warningList.length === 1 ? '' : 's'} from the browser extension
            </h3>
          </div>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 10 }}>
            The extension couldn't read a watched item's title/creator — usually means Instagram or YouTube changed
            their page structure and a selector needs updating. That item was dropped rather than recorded wrong.
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, maxHeight: 140, overflow: 'auto' }}>
            {warningList.slice(0, 8).map(w => (
              <div key={w.id} style={{ fontSize: 11, color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)' }}>
                {w.created_at?.slice(0, 19).replace('T', ' ')} — {w.message}
              </div>
            ))}
          </div>
        </GlassCard>
      )}

      <div style={{ marginBottom: 20 }}>
        <LiveIngestionPulse />
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

      {/* Platform mix — real per-platform event counts from the events table */}
      {!loading && platformTotal > 0 && (
        <GlassCard gradient style={{ marginTop: 24 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600 }}>Source Mix</h3>
            <Badge variant="neutral">{platformTotal} events tracked</Badge>
          </div>
          <div style={{ display: 'flex', height: 10, borderRadius: 6, overflow: 'hidden', marginBottom: 14 }}>
            {Object.entries(platformBreakdown).map(([platform, count]) => {
              const meta = PLATFORM_META[platform] || { label: platform, color: '#94a3b8' }
              return (
                <div key={platform} style={{ width: `${(count / platformTotal) * 100}%`, background: meta.color }} title={`${meta.label}: ${count}`} />
              )
            })}
          </div>
          <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap' }}>
            {Object.entries(platformBreakdown).map(([platform, count]) => {
              const meta = PLATFORM_META[platform] || { label: platform, color: '#94a3b8', icon: '•' }
              return (
                <div key={platform} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 16 }}>{meta.icon}</span>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>{meta.label}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{count} events · {Math.round((count / platformTotal) * 100)}%</div>
                  </div>
                </div>
              )
            })}
          </div>
        </GlassCard>
      )}

      {/* The two real ingestion paths */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, margin: '24px 0' }}>
        {/* Live extension */}
        <GlassCard>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
            <div style={{ fontSize: 24 }}>🧩</div>
            <h3 style={{ fontSize: 16, fontWeight: 600 }}>Live tracking (extension)</h3>
          </div>
          <p style={{ fontSize: 13, color: 'var(--text-tertiary)', lineHeight: 1.6, marginBottom: 14 }}>
            The AIMirror browser extension captures each Instagram Reel and YouTube
            video/Short you watch — creator, caption, hashtags, watch time,
            likes/subscriptions — and streams it here automatically as you browse.
          </p>
          <ol style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.9, paddingLeft: 18, margin: 0 }}>
            <li><code>chrome://extensions</code> → enable Developer mode</li>
            <li>Load unpacked → the <code>chrome-extension</code> folder</li>
            <li>Browse instagram.com/reels or youtube.com — both are tracked</li>
          </ol>
          <div style={{ marginTop: 14, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            <Badge variant="indigo">user: {DEFAULT_USER}</Badge>
            <Badge variant="neutral">📸 Instagram</Badge>
            <Badge variant="neutral">▶️ YouTube</Badge>
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

      {/* Data-export import — the third ingestion path, and the only one that
          does not depend on scraping a live logged-in session. */}
      <GlassCard gradient style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
          <div style={{ fontSize: 24 }}>📦</div>
          <h3 style={{ fontSize: 16, fontWeight: 600 }}>Import a data export</h3>
          <Badge variant="emerald">Fastest way to fill your twin</Badge>
        </div>
        <p style={{ fontSize: 13, color: 'var(--text-tertiary)', lineHeight: 1.6, marginBottom: 16 }}>
          Upload the official export from Instagram or Google — your whole history at
          once, no extension required. Instagram: <em>Settings → Accounts Center →
          Your information and permissions → Download your information</em> (choose
          <strong> JSON</strong>). YouTube: <em>Google Takeout → YouTube and YouTube
          Music → history</em>.
        </p>

        <div
          onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault(); setDragging(false)
            if (!importing) runImport(e.dataTransfer.files?.[0])
          }}
          onClick={() => !importing && fileInputRef.current?.click()}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if ((e.key === 'Enter' || e.key === ' ') && !importing) {
              e.preventDefault(); fileInputRef.current?.click()
            }
          }}
          style={{
            padding: '28px 20px', borderRadius: 14, textAlign: 'center',
            border: `1.5px dashed ${dragging ? 'var(--indigo-400)' : 'var(--border-strong)'}`,
            background: dragging ? 'rgba(99,102,241,0.10)' : 'rgba(148,163,184,0.04)',
            cursor: importing ? 'wait' : 'pointer',
            transition: 'all var(--dur-base) var(--ease-swift)',
          }}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".zip,.json,application/zip,application/json"
            style={{ display: 'none' }}
            onChange={(e) => { runImport(e.target.files?.[0]); e.target.value = '' }}
          />
          <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 10, color: 'var(--indigo-300)' }}>
            {importing
              ? <div style={{ animation: 'spin 1s linear infinite', display: 'flex' }}><RefreshIcon /></div>
              : <UploadIcon />}
          </div>
          <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 4 }}>
            {importing ? 'Running your history through the pipeline…' : 'Drop your export here, or click to choose'}
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
            .zip archive or a single .json file · up to 200MB
          </div>

          {/* Upload progress only covers the transfer. Processing afterwards has
              no honest percentage to report, so none is invented. */}
          {importing && importProgress > 0 && importProgress < 1 && (
            <div style={{ marginTop: 14, height: 4, borderRadius: 2, background: 'rgba(148,163,184,0.15)', overflow: 'hidden' }}>
              <div style={{
                height: '100%', width: `${Math.round(importProgress * 100)}%`,
                background: 'var(--accent-gradient)', transition: 'width 0.2s linear',
              }} />
            </div>
          )}
        </div>

        {importError && (
          <div style={{ marginTop: 14, padding: 12, borderRadius: 8, fontSize: 13, color: '#fca5a5', background: 'rgba(244,63,94,0.08)', border: '1px solid rgba(244,63,94,0.2)' }}>
            {importError}
          </div>
        )}

        {importResult && (
          <div style={{ marginTop: 14, padding: 14, borderRadius: 10, background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.2)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, fontWeight: 600, color: '#34d399', marginBottom: 8 }}>
              <CheckIcon /> Imported {importResult.events_stored} events
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 8 }}>
              {Object.entries(importResult.sources || {}).map(([source, count]) => (
                <Badge key={source} variant="indigo">{source.replace(/_/g, ' ')}: {count}</Badge>
              ))}
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.7 }}>
              {importResult.events_found} found in file
              {importResult.duplicates_removed > 0 && ` · ${importResult.duplicates_removed} duplicates skipped`}
              {importResult.identity_version != null && ` · identity now v${importResult.identity_version}`}
              {importResult.truncated && ' · truncated at the per-import limit — upload again to continue'}
            </div>
            <button
              onClick={() => navigate('/report')}
              className="btn-3d"
              style={{
                marginTop: 12, padding: '8px 16px', borderRadius: 9,
                background: 'rgba(99,102,241,0.15)', border: '1px solid rgba(99,102,241,0.3)',
                color: '#a5b4fc', fontSize: 13, fontWeight: 600, cursor: 'pointer',
              }}
            >
              See what changed →
            </button>
          </div>
        )}
      </GlassCard>

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
