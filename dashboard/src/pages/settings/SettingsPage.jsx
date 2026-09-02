import { useState, useEffect } from 'react'
import { useV3Health } from '../../hooks/useApi'
import { api, DEFAULT_USER, activeUser, isAuthed, clearAuth } from '../../api/client'
import GlassCard from '../../components/ui/GlassCard'
import Badge from '../../components/ui/Badge'
import { RefreshIcon, CpuIcon, NetworkIcon, CheckIcon, XIcon, DownloadIcon, AlertIcon, CompassIcon } from '../../icons/icons'
import CharacterCreature3D from '../../components/character/CharacterCreature3D'
import AuthModal from '../../components/auth/AuthModal'

/**
 * Stands in for a section that needs a real account. Both the AI Provider and
 * Research Participation cards were gated on `authed` and rendered NOTHING when
 * signed out — so a visitor had no way to learn the feature existed, let alone
 * that signing in unlocks it. An empty space reads as "this app doesn't do
 * that"; this reads as "not yet".
 */
function SignInRequired({ icon: Icon, title, description, accent, onSignIn }) {
  return (
    <GlassCard style={{ marginTop: 24, opacity: 0.85 }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14, flexWrap: 'wrap' }}>
        <div style={{
          width: 36, height: 36, borderRadius: 10, flexShrink: 0,
          background: `${accent}1a`, border: `1px solid ${accent}33`,
          display: 'flex', alignItems: 'center', justifyContent: 'center', color: accent,
        }}>
          <Icon />
        </div>
        <div style={{ flex: 1, minWidth: 220 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6, flexWrap: 'wrap' }}>
            <h3 style={{ fontSize: 16, fontWeight: 600 }}>{title}</h3>
            <Badge variant="neutral">Requires an account</Badge>
          </div>
          <p style={{ fontSize: 13, color: 'var(--text-tertiary)', lineHeight: 1.65, marginBottom: 14 }}>
            {description}
          </p>
          <button
            onClick={onSignIn}
            className="btn-3d"
            style={{
              padding: '9px 18px', borderRadius: 10,
              background: 'rgba(99,102,241,0.14)', border: '1px solid rgba(99,102,241,0.3)',
              color: '#a5b4fc', fontSize: 13, fontWeight: 600, cursor: 'pointer',
            }}
          >
            Sign in to enable
          </button>
        </div>
      </div>
    </GlassCard>
  )
}

export default function SettingsPage() {
  const { data: v3Health, error: v3Error, refetch: refetchV3 } = useV3Health()

  // Opened by the sign-in placeholders below, so the account-gated sections
  // can be enabled without navigating away from Settings.
  const [authOpen, setAuthOpen] = useState(false)
  // Whether a language model is actually phrasing answers. The card below used
  // to assert the server key was in use regardless of whether it worked.
  const { data: llmStatus } = useApi(() => api.getLlmStatus(), [])

  const [testForm, setTestForm] = useState({ userId: DEFAULT_USER })
  const [testResult, setTestResult] = useState(null)
  const [testLoading, setTestLoading] = useState(false)

  const [deleteConfirmText, setDeleteConfirmText] = useState('')
  const [deleteStep, setDeleteStep] = useState('idle') // idle | confirming | deleting | done
  // Opt-in, and reset whenever the flow is dismissed - a destructive choice
  // must never be silently carried over into the next attempt.
  const [deleteAccountToo, setDeleteAccountToo] = useState(false)
  const [collection, setCollection] = useState(null)
  const [collectionBusy, setCollectionBusy] = useState(false)
  const [deleteResult, setDeleteResult] = useState(null)
  const currentUser = activeUser()
  const authed = isAuthed()

  const [researchOptIn, setResearchOptInState] = useState(null)
  const [researchBusy, setResearchBusy] = useState(false)
  useEffect(() => {
    if (!authed) return
    api.getResearchStatus().then(r => setResearchOptInState(r.opted_in)).catch(() => {})
  }, [authed])

  const toggleResearchOptIn = async () => {
    setResearchBusy(true)
    try {
      const r = await api.setResearchOptIn(!researchOptIn)
      setResearchOptInState(r.opted_in)
    } catch { /* leave state unchanged on failure */ }
    setResearchBusy(false)
  }

  const [llmSettings, setLlmSettingsState] = useState(null)
  const [llmProvider, setLlmProvider] = useState('openai')
  const [llmApiKey, setLlmApiKey] = useState('')
  const [llmBaseUrl, setLlmBaseUrl] = useState('')
  const [llmBusy, setLlmBusy] = useState(false)
  const [llmError, setLlmError] = useState(null)
  const [llmSaved, setLlmSaved] = useState(false)

  const loadLlmSettings = () => {
    if (!authed) return
    api.getLlmSettings().then(s => {
      setLlmSettingsState(s)
      if (s.provider) setLlmProvider(s.provider)
      setLlmBaseUrl(s.base_url || '')
    }).catch(() => {})
  }
  useEffect(loadLlmSettings, [authed])

  const saveLlmSettings = async () => {
    setLlmBusy(true); setLlmError(null); setLlmSaved(false)
    try {
      const s = await api.setLlmSettings(llmProvider, llmApiKey, llmBaseUrl, undefined)
      setLlmSettingsState(s)
      setLlmApiKey('')
      setLlmSaved(true)
      setTimeout(() => setLlmSaved(false), 2500)
    } catch (err) {
      setLlmError(err?.response?.data?.detail || err.message)
    }
    setLlmBusy(false)
  }

  const clearLlmSettingsHandler = async () => {
    setLlmBusy(true); setLlmError(null)
    try {
      await api.clearLlmSettings()
      setLlmSettingsState({ provider: null, has_key: false, key_preview: null, base_url: null, model: null })
      setLlmApiKey(''); setLlmBaseUrl(''); setLlmProvider('openai')
    } catch (err) {
      setLlmError(err?.response?.data?.detail || err.message)
    }
    setLlmBusy(false)
  }

  useEffect(() => {
    let alive = true
    api.getCollectionStatus()
      .then(s => { if (alive) setCollection(s) })
      .catch(() => { if (alive) setCollection(null) })
    return () => { alive = false }
  }, [])

  const toggleCollection = async () => {
    if (!collection) return
    setCollectionBusy(true)
    try {
      // The server returns the authoritative state; render that rather than
      // assuming the write did what was asked.
      setCollection(await api.setCollectionPaused(!collection.paused))
    } catch (e) {
      setCollection(c => c && { ...c, error: e?.response?.data?.detail || 'Could not change this.' })
    } finally {
      setCollectionBusy(false)
    }
  }

  const runDelete = async () => {
    setDeleteStep('deleting')
    try {
      const res = await api.deleteAllData(deleteConfirmText, undefined, deleteAccountToo)
      setDeleteResult(res)
      setDeleteStep('done')
      // The account is gone; the token in localStorage now points at nothing.
      if (res?.account?.deleted) clearAuth()
    } catch (err) {
      setDeleteResult({ error: err?.response?.data?.detail || err.message })
      setDeleteStep('done')
    }
  }

  const runTest = async (endpoint) => {
    setTestLoading(true)
    setTestResult(null)
    try {
      let res
      const userId = testForm.userId
      switch (endpoint) {
        case 'identity': res = await api.getCurrentIdentity(userId); break
        case 'evidence': res = await api.getEvidence(userId); break
        case 'reflections': res = await api.getReflections(userId); break
        case 'traces': res = await api.getTraces(userId); break
        case 'metrics': res = await api.getCognitiveMetrics(userId); break
        case 'summary': res = await api.getCognitiveSummary(userId); break
        default: res = { error: 'unknown endpoint' }
      }
      setTestResult({ success: true, data: res })
    } catch (err) {
      setTestResult({ success: false, error: err?.response?.data?.detail || err.message })
    } finally {
      setTestLoading(false)
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 32 }}>
        <div style={{ width: 68, height: 68, flexShrink: 0, margin: '-8px 0' }}>
          <CharacterCreature3D size={68} variant="gear" confidence={v3Health ? 0.8 : 0.3} thinking={testLoading} showLabels={false} />
        </div>
        <div>
          <h1 className="gradient-text" style={{ fontSize: 32, fontWeight: 800, letterSpacing: '-0.03em', marginBottom: 6 }}>Settings</h1>
          <p style={{ color: 'var(--text-tertiary)', fontSize: 15 }}>System configuration and connectivity</p>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginBottom: 32 }}>
        {/* Backend Status */}
        <GlassCard gradient>
          <div style={{ marginBottom: 20 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
              <div style={{ width: 36, height: 36, borderRadius: 10, background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#818cf8' }}>
                <CpuIcon />
              </div>
              <h3 style={{ fontSize: 16, fontWeight: 600 }}>Backend Status</h3>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 12px', borderRadius: 6, background: 'rgba(148,163,184,0.04)' }}>
                <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>AIMirror Backend (port 8000)</span>
                <Badge variant={v3Health ? 'emerald' : 'danger'} dot>{v3Health ? 'Online' : v3Error ? 'Unreachable' : 'Offline'}</Badge>
              </div>
              {v3Error && (
                <div style={{ fontSize: 11, color: '#f87171', padding: '0 12px' }}>
                  {typeof v3Error === 'string' ? v3Error : 'Request failed'}
                </div>
              )}
              {v3Health?.database && (
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 12px', borderRadius: 6, background: 'rgba(148,163,184,0.04)' }}>
                  <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>PostgreSQL (Neon)</span>
                  <Badge variant={v3Health.database.status === 'healthy' ? 'emerald' : 'danger'} dot>
                    {v3Health.database.status === 'healthy' ? 'Connected' : 'Disconnected'}
                  </Badge>
                </div>
              )}
            </div>
            <button onClick={() => refetchV3()} style={{
              display: 'flex', alignItems: 'center', gap: 6, marginTop: 16,
              padding: '8px 14px', borderRadius: 8, border: '1px solid var(--border-subtle)',
              background: 'transparent', color: 'var(--text-tertiary)', fontSize: 13,
              cursor: 'pointer', fontWeight: 500,
            }}>
              <RefreshIcon /> Check Status
            </button>
          </div>
        </GlassCard>

        {/* API Test */}
        <GlassCard gradient>
          <div style={{ marginBottom: 20 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
              <div style={{ width: 36, height: 36, borderRadius: 10, background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#34d399' }}>
                <NetworkIcon />
              </div>
              <h3 style={{ fontSize: 16, fontWeight: 600 }}>API Test</h3>
            </div>
            <div style={{ marginBottom: 12 }}>
              <label style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4, display: 'block' }}>User ID</label>
              <input
                value={testForm.userId}
                onChange={e => setTestForm({ ...testForm, userId: e.target.value })}
                style={{
                  width: '100%', padding: '8px 12px', borderRadius: 6,
                  background: 'rgba(30,41,59,0.5)', border: '1px solid var(--border-subtle)',
                  color: 'var(--text-primary)', fontSize: 13, outline: 'none',
                }}
              />
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 16 }}>
              {['identity', 'evidence', 'reflections', 'traces', 'metrics', 'summary'].map(ep => (
                <button key={ep} onClick={() => runTest(ep)} disabled={testLoading} style={{
                  padding: '5px 10px', borderRadius: 6, border: '1px solid var(--border-subtle)',
                  background: 'transparent', color: 'var(--text-tertiary)', fontSize: 11,
                  cursor: 'pointer', textTransform: 'capitalize',
                }}>
                  {ep}
                </button>
              ))}
            </div>
            {testLoading && <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>Testing...</div>}
            {testResult && (
              <div style={{ padding: '8px 12px', borderRadius: 6, background: testResult.success ? 'rgba(16,185,129,0.08)' : 'rgba(239,68,68,0.08)', border: `1px solid ${testResult.success ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)'}` }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                  {testResult.success ? <CheckIcon /> : <XIcon />}
                  <span style={{ fontSize: 13, fontWeight: 600, color: testResult.success ? '#34d399' : '#f87171' }}>
                    {testResult.success ? 'Success' : 'Failed'}
                  </span>
                </div>
                <pre style={{ fontSize: 11, color: 'var(--text-tertiary)', overflow: 'auto', maxHeight: 150, marginTop: 4 }}>
                  {JSON.stringify(testResult.success ? testResult.data : testResult.error, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </GlassCard>
      </div>

      <GlassCard>
        <div style={{ marginBottom: 20 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600 }}>About</h3>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--border-subtle)', fontSize: 13 }}>
            <span style={{ color: 'var(--text-muted)' }}>Version</span>
            <span style={{ color: 'var(--text-secondary)' }}>2.0.0</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--border-subtle)', fontSize: 13 }}>
            <span style={{ color: 'var(--text-muted)' }}>Pipeline</span>
            <span style={{ color: 'var(--text-secondary)' }}>V3 Cognitive Pipeline</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--border-subtle)', fontSize: 13 }}>
            <span style={{ color: 'var(--text-muted)' }}>Frontend</span>
            <span style={{ color: 'var(--text-secondary)' }}>React 18 + Vite 5</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', fontSize: 13 }}>
            <span style={{ color: 'var(--text-muted)' }}>Backend</span>
            <span style={{ color: 'var(--text-secondary)' }}>FastAPI + PostgreSQL (Neon)</span>
          </div>
        </div>
      </GlassCard>

      <GlassCard gradient style={{ marginTop: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
          <div style={{
            width: 36, height: 36, borderRadius: 10,
            background: collection?.paused ? 'rgba(251,191,36,0.12)' : 'rgba(16,185,129,0.1)',
            border: `1px solid ${collection?.paused ? 'rgba(251,191,36,0.3)' : 'rgba(16,185,129,0.2)'}`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: collection?.paused ? '#fbbf24' : '#34d399',
          }}>
            <CompassIcon />
          </div>
          <div>
            <h3 style={{ fontSize: 16, fontWeight: 600 }}>Collection</h3>
            <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              Whether this system is allowed to record what you do. Enforced on the server,
              so it applies to the extension too.
            </p>
          </div>
        </div>

        {collection === null ? (
          <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>Checking…</div>
        ) : (
          <div style={{
            display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap',
            padding: '12px 14px', borderRadius: 10,
            background: collection.paused ? 'rgba(251,191,36,0.07)' : 'rgba(16,185,129,0.06)',
            border: `1px solid ${collection.paused ? 'rgba(251,191,36,0.25)' : 'rgba(16,185,129,0.2)'}`,
          }}>
            <div style={{ flex: '1 1 300px', minWidth: 0 }}>
              <div style={{
                fontSize: 14, fontWeight: 700,
                color: collection.paused ? '#fbbf24' : '#34d399', marginBottom: 3,
              }}>
                {collection.paused ? 'Paused' : 'Collecting'}
                {collection.paused && collection.paused_at && (
                  <span style={{ fontWeight: 400, color: 'var(--text-muted)', fontSize: 12 }}>
                    {' '}since {new Date(collection.paused_at).toLocaleDateString()}
                  </span>
                )}
              </div>
              {/* The scope sentence comes from the server, so every surface
                  showing this state says the same thing about what it covers. */}
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                {collection.note}
              </div>
              {collection.error && (
                <div style={{ fontSize: 12, color: '#f87171', marginTop: 6 }}>{collection.error}</div>
              )}
            </div>
            <button
              onClick={toggleCollection}
              disabled={collectionBusy}
              style={{
                padding: '9px 16px', borderRadius: 10, fontSize: 13, fontWeight: 600,
                cursor: collectionBusy ? 'wait' : 'pointer',
                border: `1px solid ${collection.paused ? 'rgba(16,185,129,0.35)' : 'rgba(251,191,36,0.35)'}`,
                background: collection.paused ? 'rgba(16,185,129,0.12)' : 'rgba(251,191,36,0.12)',
                color: collection.paused ? '#34d399' : '#fbbf24',
              }}
            >
              {collectionBusy ? 'Saving…' : collection.paused ? 'Resume collecting' : 'Pause collecting'}
            </button>
          </div>
        )}
      </GlassCard>

      <GlassCard gradient style={{ marginTop: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
          <div style={{ width: 36, height: 36, borderRadius: 10, background: 'rgba(244,63,94,0.1)', border: '1px solid rgba(244,63,94,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fb7185' }}>
            <AlertIcon />
          </div>
          <div>
            <h3 style={{ fontSize: 16, fontWeight: 600 }}>Data & Privacy</h3>
            <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>Every behavioural row this platform holds for {currentUser} — export it or permanently delete it. Your account is separate, and you choose whether it goes too.</p>
          </div>
        </div>

        <div style={{ display: 'flex', gap: 10, marginBottom: 16 }}>
          <a href={api.exportAllDataUrl()} download={`${currentUser}_all_data.json`} target="_blank" rel="noreferrer" style={{
            padding: '10px 16px', borderRadius: 10, border: '1px solid var(--border-subtle)',
            background: 'transparent', color: 'var(--text-secondary)', fontSize: 13,
            textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 8,
          }}>
            <DownloadIcon /> Export all my data (JSON)
          </a>
        </div>

        {deleteStep === 'idle' && (
          <button onClick={() => setDeleteStep('confirming')} style={{
            padding: '10px 16px', borderRadius: 10, border: '1px solid rgba(244,63,94,0.3)',
            background: 'rgba(244,63,94,0.08)', color: '#fb7185', fontSize: 13, fontWeight: 600, cursor: 'pointer',
          }}>
            Delete all my data
          </button>
        )}

        {deleteStep === 'confirming' && (
          <div style={{ padding: 16, borderRadius: 10, background: 'rgba(244,63,94,0.06)', border: '1px solid rgba(244,63,94,0.25)' }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#fb7185', marginBottom: 6 }}>
              This permanently deletes every behavioural row for "{currentUser}" — behavior objects, evidence,
              inferences, reflections, identity, snapshots, chat history. This cannot be undone.
            </div>
            <label style={{
              display: 'flex', alignItems: 'flex-start', gap: 8, marginBottom: 10,
              fontSize: 12, color: 'var(--text-secondary)', cursor: 'pointer',
            }}>
              <input
                type="checkbox"
                checked={deleteAccountToo}
                onChange={e => setDeleteAccountToo(e.target.checked)}
                style={{ marginTop: 2, cursor: 'pointer' }}
              />
              <span>
                Also delete my account — the login itself, plus the email, display name,
                password hash and any stored LLM API key. Without this they stay, and you
                remain signed in.
              </span>
            </label>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 10 }}>
              Type <strong style={{ color: 'var(--text-secondary)' }}>{currentUser}</strong> to confirm.
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <input
                value={deleteConfirmText}
                onChange={e => setDeleteConfirmText(e.target.value)}
                placeholder={currentUser}
                style={{
                  flex: 1, padding: '8px 12px', borderRadius: 6,
                  background: '#1e293b', border: '1px solid rgba(244,63,94,0.3)',
                  color: '#f8fafc', fontSize: 13, outline: 'none', colorScheme: 'dark',
                }}
              />
              <button
                onClick={runDelete}
                disabled={deleteConfirmText !== currentUser}
                style={{
                  padding: '8px 16px', borderRadius: 6, border: 'none',
                  background: deleteConfirmText === currentUser ? '#e11d48' : 'rgba(148,163,184,0.15)',
                  color: 'white', fontSize: 13, fontWeight: 600,
                  cursor: deleteConfirmText === currentUser ? 'pointer' : 'not-allowed',
                }}
              >
                Permanently delete
              </button>
              <button onClick={() => { setDeleteStep('idle'); setDeleteConfirmText(''); setDeleteAccountToo(false) }} style={{
                padding: '8px 16px', borderRadius: 6, border: '1px solid var(--border-subtle)',
                background: 'transparent', color: 'var(--text-tertiary)', fontSize: 13, cursor: 'pointer',
              }}>
                Cancel
              </button>
            </div>
          </div>
        )}

        {deleteStep === 'deleting' && (
          <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>Deleting…</div>
        )}

        {deleteStep === 'done' && deleteResult && (
          <div style={{ padding: 16, borderRadius: 10, background: deleteResult.error ? 'rgba(239,68,68,0.08)' : 'rgba(16,185,129,0.08)', border: `1px solid ${deleteResult.error ? 'rgba(239,68,68,0.2)' : 'rgba(16,185,129,0.2)'}` }}>
            {deleteResult.error ? (
              <div style={{ fontSize: 13, color: '#f87171' }}>{deleteResult.error}</div>
            ) : (
              <>
                <div style={{ fontSize: 13, fontWeight: 600, color: '#34d399', marginBottom: 6 }}>
                  Deleted {deleteResult.total_deleted} rows across {Object.values(deleteResult.deleted_rows_by_table).filter(v => v > 0).length} tables.
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                  {Object.entries(deleteResult.deleted_rows_by_table).filter(([, v]) => v > 0).map(([t, v]) => `${t}: ${v}`).join(' · ')}
                </div>
                {deleteResult.account?.deleted && (
                  <div style={{ fontSize: 12, color: '#34d399', marginTop: 8 }}>
                    Account deleted. You have been signed out.
                  </div>
                )}
                {deleteResult.account?.reason === 'owns_organization' && (
                  <div style={{ fontSize: 12, color: '#fbbf24', marginTop: 8 }}>
                    {deleteResult.account.note}
                  </div>
                )}
                {deleteResult.retained?.account_exists && (
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 8 }}>
                    {deleteResult.retained.note}
                  </div>
                )}
              </>
            )}
            <button onClick={() => { setDeleteStep('idle'); setDeleteConfirmText(''); setDeleteResult(null); setDeleteAccountToo(false) }} style={{
              marginTop: 10, padding: '6px 12px', borderRadius: 6, border: '1px solid var(--border-subtle)',
              background: 'transparent', color: 'var(--text-tertiary)', fontSize: 12, cursor: 'pointer',
            }}>
              Close
            </button>
          </div>
        )}
      </GlassCard>

      {authed && (
        <GlassCard gradient style={{ marginTop: 24 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
            <div style={{ width: 36, height: 36, borderRadius: 10, background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#818cf8' }}>
              <NetworkIcon />
            </div>
            <div>
              <h3 style={{ fontSize: 16, fontWeight: 600 }}>AI Provider</h3>
              <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                {llmSettings?.has_key
                  ? `Using your own ${llmSettings.provider} key (${llmSettings.key_preview})`
                  : llmSettings?.provider === 'ollama'
                    ? 'Using your configured Ollama endpoint'
                    : llmStatus?.llm_phrasing_available === false
                      // Previously claimed the shared key was in use whether or
                      // not it worked, so a user had no way to know why answers
                      // read like a template.
                      ? 'The shared key is not currently working — answers are written deterministically. Add your own key below for natural-language phrasing.'
                      : 'Using the server’s shared key — bring your own for priority access'}
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', gap: 10, marginBottom: 12, flexWrap: 'wrap' }}>
            <select
              value={llmProvider}
              onChange={e => setLlmProvider(e.target.value)}
              style={{
                padding: '8px 12px', borderRadius: 8, background: 'rgba(30,41,59,0.5)',
                border: '1px solid var(--border-subtle)', color: 'var(--text-primary)', fontSize: 13, outline: 'none',
              }}
            >
              <option value="openai">OpenAI</option>
              <option value="anthropic">Anthropic</option>
              <option value="gemini">Gemini</option>
              <option value="ollama">Ollama / custom endpoint</option>
            </select>
            {llmProvider !== 'ollama' && (
              <input
                type="password"
                value={llmApiKey}
                onChange={e => setLlmApiKey(e.target.value)}
                placeholder={llmSettings?.provider === llmProvider && llmSettings?.has_key ? 'Key saved — enter a new one to replace it' : 'API key'}
                style={{
                  flex: 1, minWidth: 200, padding: '8px 12px', borderRadius: 8,
                  background: 'rgba(30,41,59,0.5)', border: '1px solid var(--border-subtle)',
                  color: 'var(--text-primary)', fontSize: 13, outline: 'none', colorScheme: 'dark',
                }}
              />
            )}
          </div>

          {llmProvider === 'ollama' && (
            <div style={{ marginBottom: 12 }}>
              <input
                value={llmBaseUrl}
                onChange={e => setLlmBaseUrl(e.target.value)}
                placeholder="https://your-ollama-endpoint.example.com/v1"
                style={{
                  width: '100%', padding: '8px 12px', borderRadius: 8,
                  background: 'rgba(30,41,59,0.5)', border: '1px solid var(--border-subtle)',
                  color: 'var(--text-primary)', fontSize: 13, outline: 'none', marginBottom: 6,
                }}
              />
              <p style={{ fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.5 }}>
                Must be reachable from the server, not just your own computer — a laptop's
                <code style={{ margin: '0 4px' }}>localhost:11434</code> only works when you're running
                the AIMirror backend locally yourself. Leave blank for that local-dev case.
              </p>
            </div>
          )}

          {llmError && <div style={{ color: '#f87171', fontSize: 12, marginBottom: 10 }}>{llmError}</div>}

          <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <button
              onClick={saveLlmSettings}
              disabled={llmBusy || (llmProvider !== 'ollama' && !llmApiKey)}
              style={{
                padding: '9px 16px', borderRadius: 8, border: 'none',
                background: 'var(--accent-gradient)', color: 'white', fontSize: 13, fontWeight: 600,
                cursor: llmBusy ? 'wait' : 'pointer',
                opacity: (llmProvider !== 'ollama' && !llmApiKey) ? 0.5 : 1,
              }}
            >
              {llmSaved ? 'Saved ✓' : 'Save'}
            </button>
            {llmSettings?.has_key || llmSettings?.provider ? (
              <button
                onClick={clearLlmSettingsHandler}
                disabled={llmBusy}
                style={{
                  padding: '9px 16px', borderRadius: 8, border: '1px solid var(--border-subtle)',
                  background: 'transparent', color: 'var(--text-tertiary)', fontSize: 13, cursor: llmBusy ? 'wait' : 'pointer',
                }}
              >
                Revert to server default
              </button>
            ) : null}
          </div>
        </GlassCard>
      )}

      {!authed && (
        <SignInRequired
          icon={NetworkIcon}
          accent="#818cf8"
          title="AI Provider"
          description="Bring your own OpenAI, Anthropic or Gemini key — or point at your own Ollama endpoint — instead of sharing the server's. Keys are encrypted at rest and never shown again in full."
          onSignIn={() => setAuthOpen(true)}
        />
      )}

      {authed && (
        <GlassCard gradient style={{ marginTop: 24 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
            <div style={{ width: 36, height: 36, borderRadius: 10, background: 'rgba(34,211,238,0.1)', border: '1px solid rgba(34,211,238,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#22d3ee' }}>
              <CompassIcon />
            </div>
            <div>
              <h3 style={{ fontSize: 16, fontWeight: 600 }}>Research Participation</h3>
              <p style={{ fontSize: 12, color: 'var(--text-muted)', maxWidth: 520 }}>
                Off by default. If you opt in, your behavior objects, evidence, inferences, and identity
                snapshots become part of a bulk export researchers can pull — keyed to a one-way hashed
                participant ID, never your username. Turning it back off removes you from every future
                export (already-downloaded exports can't be recalled).
              </p>
            </div>
          </div>
          <button
            onClick={toggleResearchOptIn}
            disabled={researchOptIn === null || researchBusy}
            style={{
              display: 'flex', alignItems: 'center', gap: 8,
              padding: '10px 16px', borderRadius: 10, border: '1px solid var(--border-subtle)',
              background: researchOptIn ? 'rgba(16,185,129,0.1)' : 'transparent',
              color: researchOptIn ? '#34d399' : 'var(--text-secondary)',
              fontSize: 13, fontWeight: 600,
              cursor: researchBusy ? 'wait' : 'pointer',
            }}
          >
            {researchOptIn ? <CheckIcon /> : null}
            {researchOptIn === null ? 'Loading…' : researchOptIn ? 'Opted in — click to opt out' : 'Opt in to research export'}
          </button>
        </GlassCard>
      )}

      {!authed && (
        <SignInRequired
          icon={CompassIcon}
          accent="#22d3ee"
          title="Research Participation"
          description="Optionally contribute a de-identified copy of your cognitive data to research. Participant IDs are salted hashes — never your username or email — and you can opt out at any time."
          onSignIn={() => setAuthOpen(true)}
        />
      )}

      {authOpen && <AuthModal onClose={() => setAuthOpen(false)} />}
    </div>
  )
}
