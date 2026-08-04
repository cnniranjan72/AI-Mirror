import { useApi } from '../../hooks/useApi'
import { api } from '../../api/client'
import GlassCard from '../../components/ui/GlassCard'
import StatCard from '../../components/ui/StatCard'
import Badge from '../../components/ui/Badge'
import AsyncState from '../../components/ui/AsyncState'
import { AlertIcon, ClockIcon, CheckIcon, TargetIcon } from '../../icons/icons'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import CharacterCreature3D from '../../components/character/CharacterCreature3D'

const RISK_COLOR = { low: '#10b981', moderate: '#f59e0b', elevated: '#f43f5e' }

export default function GuardianPage() {
  const { data: report, loading, error, refetch } = useApi(() => api.getGuardianReport(), [])
  const { data: alertLog, refetch: refetchAlertLog } = useApi(() => api.getGuardianAlertLog(), [])

  const acknowledge = async (alertId) => {
    try {
      await api.acknowledgeGuardianAlert(alertId)
      refetchAlertLog()
    } catch (_) { /* ignore */ }
  }

  const hourly = report?.session_patterns?.hourly_distribution || {}
  const hourlyData = Object.entries(hourly).map(([h, n]) => ({
    hour: `${h}:00`, count: n,
    night: parseInt(h) >= 23 || parseInt(h) < 5,
  }))

  const riskColor = RISK_COLOR[report?.risk_level] || '#94a3b8'
  const alertCategories = [...new Set((report?.content_alerts || []).flatMap(a => a.categories || []))]

  return (
    <div>
      <div style={{ marginBottom: 32 }}>
        <h1 className="gradient-text" style={{ fontSize: 32, fontWeight: 800, letterSpacing: '-0.03em', marginBottom: 6 }}>Guardian</h1>
        <p style={{ color: 'var(--text-tertiary)', fontSize: 15 }}>
          Wellbeing monitoring — content signal, session timing, and usage-pattern insight
        </p>
      </div>

      <AsyncState loading={loading} error={error} onRetry={refetch}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 16, marginBottom: 32 }}>
        <StatCard label="Risk Level" value={report?.risk_level ? report.risk_level.toUpperCase() : '--'} icon={AlertIcon} accent={report?.risk_level === 'elevated' ? 'rose' : report?.risk_level === 'moderate' ? 'amber' : 'emerald'} loading={loading} />
        <StatCard label="Content Alerts" value={report?.content_alerts?.length ?? '--'} icon={AlertIcon} accent="rose" loading={loading} />
        <StatCard label="Positive Highlights" value={report?.positive_highlights?.length ?? '--'} icon={CheckIcon} accent="emerald" loading={loading} />
        <StatCard label="Late-Night Share" value={report ? `${Math.round(report.session_patterns.late_night_share * 100)}%` : '--'} icon={ClockIcon} accent="indigo" loading={loading} />
      </div>

      {/* Risk summary */}
      <GlassCard gradient>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600 }}>Risk Assessment</h3>
          <Badge variant="neutral">explainable, rule-based</Badge>
        </div>
        {loading ? (
          <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)' }}>Loading…</div>
        ) : (
          <>
            <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 16 }}>
              <div style={{ width: 90, height: 90, flexShrink: 0, margin: '-12px 0' }}>
                <CharacterCreature3D
                  size={90}
                  variant="shield"
                  confidence={0.4 + (report?.risk_score || 0) * 0.6}
                  topics={alertCategories}
                  moodColor={riskColor}
                  thinking={loading}
                  showLabels={false}
                />
              </div>
              <div style={{
                width: 64, height: 64, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: `${riskColor}18`, border: `2px solid ${riskColor}`, color: riskColor, fontWeight: 800, fontSize: 18,
                flexShrink: 0,
              }}>
                {Math.round((report?.risk_score || 0) * 100)}
              </div>
              <div>
                <div style={{ fontSize: 14, fontWeight: 600, color: riskColor, textTransform: 'capitalize' }}>{report?.risk_level} risk</div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Composite score from real, independently-computed behavioral signals — shield color and solidity mirror this score</div>
              </div>
            </div>
            {report?.risk_factors?.length > 0 && (
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 8 }}>Contributing factors</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {report.risk_factors.map((f, i) => (
                    <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'flex-start', fontSize: 13, color: 'var(--text-secondary)' }}>
                      <div style={{ width: 5, height: 5, borderRadius: '50%', background: riskColor, marginTop: 7, flexShrink: 0 }} />
                      {f}
                    </div>
                  ))}
                </div>
              </div>
            )}
            <div>
              <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 8 }}>Recommendations</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {(report?.recommendations || []).map((rec, i) => (
                  <div key={i} style={{ padding: '8px 12px', borderRadius: 8, background: 'rgba(99,102,241,0.08)', fontSize: 13, color: 'var(--text-secondary)' }}>{rec}</div>
                ))}
              </div>
            </div>
          </>
        )}
      </GlassCard>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginTop: 24 }}>
        {/* Hourly activity */}
        <GlassCard gradient>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600 }}>Activity by Hour</h3>
            <Badge variant="neutral">red = late night</Badge>
          </div>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={hourlyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.08)" />
              <XAxis dataKey="hour" tick={{ fill: '#64748b', fontSize: 9 }} axisLine={false} tickLine={false} interval={2} />
              <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid rgba(148,163,184,0.2)', borderRadius: 8, fontSize: 12 }} labelStyle={{ color: '#e2e8f0' }} itemStyle={{ color: '#e2e8f0' }} />
              <Bar dataKey="count" radius={[3, 3, 0, 0]}>
                {hourlyData.map((d, i) => <Cell key={i} fill={d.night ? '#f43f5e' : '#6366f1'} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </GlassCard>

        {/* Content alerts */}
        <GlassCard gradient>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600 }}>Content Alerts</h3>
            <Badge variant="rose">{report?.content_alerts?.length || 0}</Badge>
          </div>
          <div style={{ maxHeight: 240, overflow: 'auto', display: 'flex', flexDirection: 'column', gap: 8 }}>
            {(report?.content_alerts || []).length === 0 ? (
              <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>No sensitive-content signal detected</div>
            ) : report.content_alerts.map((a, i) => (
              <div key={i} style={{ padding: '8px 12px', borderRadius: 8, background: 'rgba(244,63,94,0.06)', border: '1px solid rgba(244,63,94,0.15)' }}>
                <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-secondary)', textTransform: 'capitalize' }}>{a.topic}</div>
                <div style={{ display: 'flex', gap: 6, marginTop: 4, flexWrap: 'wrap' }}>
                  {a.categories.map(c => <Badge key={c} variant="rose">{c.replace('_', ' ')}</Badge>)}
                  <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{a.occurrence_count} occurrences</span>
                </div>
              </div>
            ))}
          </div>
        </GlassCard>
      </div>

      {/* Positive highlights */}
      <GlassCard gradient style={{ marginTop: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600 }}>Positive Highlights</h3>
          <Badge variant="emerald">Educational & growing</Badge>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12 }}>
          {(report?.positive_highlights || []).length === 0 ? (
            <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13, gridColumn: '1/-1' }}>No highlights yet</div>
          ) : report.positive_highlights.slice(0, 8).map((h, i) => (
            <div key={i} style={{ padding: 12, borderRadius: 10, background: 'rgba(16,185,129,0.06)', border: '1px solid rgba(16,185,129,0.15)' }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'capitalize' }}>{h.topic}</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                {h.lifecycle_state} · {Math.round(h.completion_rate * 100)}% completion
              </div>
            </div>
          ))}
        </div>
      </GlassCard>

      {/* Alert history — the in-app push-equivalent: a persistent log of
          risk-level state changes, not a snapshot that vanishes when this
          page closes. */}
      <GlassCard gradient style={{ marginTop: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600 }}>Alert History</h3>
          <Badge variant="neutral">{alertLog?.length || 0} logged</Badge>
        </div>
        <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16 }}>
          A new entry is recorded only when the risk level actually changes — this is the closest honest
          equivalent to a push notification without external email/webhook delivery configured.
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {(alertLog || []).length === 0 ? (
            <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>No risk-level changes logged yet</div>
          ) : alertLog.map(a => {
            const c = RISK_COLOR[a.risk_level] || '#94a3b8'
            return (
              <div key={a.alert_id} style={{
                display: 'flex', alignItems: 'center', gap: 12, padding: '10px 12px', borderRadius: 8,
                background: `${c}0d`, border: `1px solid ${c}33`, opacity: a.acknowledged ? 0.6 : 1,
              }}>
                <div style={{ width: 8, height: 8, borderRadius: '50%', background: c, flexShrink: 0 }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: c, textTransform: 'capitalize' }}>
                    {a.risk_level} risk — {Math.round(a.risk_score * 100)}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                    {a.risk_factors.join('; ') || 'No factors recorded'} · {new Date(a.created_at).toLocaleString()}
                  </div>
                </div>
                {!a.acknowledged && (
                  <button onClick={() => acknowledge(a.alert_id)} style={{
                    padding: '5px 10px', borderRadius: 6, border: '1px solid var(--border-subtle)',
                    background: 'transparent', color: 'var(--text-tertiary)', fontSize: 11,
                    cursor: 'pointer', flexShrink: 0,
                  }}>
                    Acknowledge
                  </button>
                )}
              </div>
            )
          })}
        </div>
      </GlassCard>
      </AsyncState>
    </div>
  )
}
