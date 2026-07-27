import { useState } from 'react'
import { useV3Health } from '../../hooks/useApi'
import { api, DEFAULT_USER, activeUser } from '../../api/client'
import GlassCard from '../../components/ui/GlassCard'
import Badge from '../../components/ui/Badge'
import { RefreshIcon, CpuIcon, NetworkIcon, CheckIcon, XIcon, DownloadIcon, AlertIcon } from '../../icons/icons'
import CharacterCreature3D from '../../components/character/CharacterCreature3D'

export default function SettingsPage() {
  const { data: v3Health, refetch: refetchV3 } = useV3Health()

  const [testForm, setTestForm] = useState({ userId: DEFAULT_USER })
  const [testResult, setTestResult] = useState(null)
  const [testLoading, setTestLoading] = useState(false)

  const [deleteConfirmText, setDeleteConfirmText] = useState('')
  const [deleteStep, setDeleteStep] = useState('idle') // idle | confirming | deleting | done
  const [deleteResult, setDeleteResult] = useState(null)
  const currentUser = activeUser()

  const runDelete = async () => {
    setDeleteStep('deleting')
    try {
      const res = await api.deleteAllData(deleteConfirmText)
      setDeleteResult(res)
      setDeleteStep('done')
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
                <Badge variant={v3Health ? 'emerald' : 'danger'} dot>{v3Health ? 'Online' : 'Offline'}</Badge>
              </div>
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
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
          <div style={{ width: 36, height: 36, borderRadius: 10, background: 'rgba(244,63,94,0.1)', border: '1px solid rgba(244,63,94,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fb7185' }}>
            <AlertIcon />
          </div>
          <div>
            <h3 style={{ fontSize: 16, fontWeight: 600 }}>Data & Privacy</h3>
            <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>Every row this platform holds for {currentUser}, across every table — export it or permanently delete it.</p>
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
              This permanently deletes every row for "{currentUser}" — behavior objects, evidence, inferences,
              reflections, identity, snapshots, chat history, everything. This cannot be undone.
            </div>
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
              <button onClick={() => { setDeleteStep('idle'); setDeleteConfirmText('') }} style={{
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
              </>
            )}
            <button onClick={() => { setDeleteStep('idle'); setDeleteConfirmText(''); setDeleteResult(null) }} style={{
              marginTop: 10, padding: '6px 12px', borderRadius: 6, border: '1px solid var(--border-subtle)',
              background: 'transparent', color: 'var(--text-tertiary)', fontSize: 12, cursor: 'pointer',
            }}>
              Close
            </button>
          </div>
        )}
      </GlassCard>
    </div>
  )
}
