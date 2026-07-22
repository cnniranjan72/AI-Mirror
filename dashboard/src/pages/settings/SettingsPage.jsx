import { useState } from 'react'
import { useHealth, useV3Health } from '../../hooks/useApi'
import { api } from '../../api/client'
import GlassCard from '../../components/ui/GlassCard'
import Badge from '../../components/ui/Badge'
import { RefreshIcon, CpuIcon, NetworkIcon, CheckIcon, XIcon } from '../../icons/icons'

export default function SettingsPage() {
  const { data: health, refetch: refetchHealth } = useHealth()
  const { data: v3Health, refetch: refetchV3 } = useV3Health()

  const [testForm, setTestForm] = useState({ userId: 'user_123' })
  const [testResult, setTestResult] = useState(null)
  const [testLoading, setTestLoading] = useState(false)

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
      <div style={{ marginBottom: 32 }}>
        <h1 className="gradient-text" style={{ fontSize: 32, fontWeight: 800, letterSpacing: '-0.03em', marginBottom: 6 }}>Settings</h1>
        <p style={{ color: 'var(--text-tertiary)', fontSize: 15 }}>System configuration and connectivity</p>
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
                <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>V3 Backend (port 8000)</span>
                <Badge variant={v3Health ? 'emerald' : 'danger'} dot>{v3Health ? 'Online' : 'Offline'}</Badge>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 12px', borderRadius: 6, background: 'rgba(148,163,184,0.04)' }}>
                <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>Legacy Backend (port 3000)</span>
                <Badge variant={health ? 'emerald' : 'danger'} dot>{health ? 'Online' : 'Offline'}</Badge>
              </div>
            </div>
            <button onClick={() => { refetchHealth(); refetchV3() }} style={{
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
    </div>
  )
}
