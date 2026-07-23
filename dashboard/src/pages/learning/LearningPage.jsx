import { useState } from 'react'
import { useApi } from '../../hooks/useApi'
import { api } from '../../api/client'
import GlassCard from '../../components/ui/GlassCard'
import StatCard from '../../components/ui/StatCard'
import Badge from '../../components/ui/Badge'
import { ZapIcon, TargetIcon, ActivityIcon, BrainIcon } from '../../icons/icons'

const ACTION_LABELS = {
  reduce_session: 'Reduce session length',
  diversify_content: 'Explore new content',
  increase_engagement: 'Engage more deeply',
  maintain_balance: 'Maintain balance',
}
const CTX_LABELS = {
  weak_intentionality: 'Low intentionality',
  weak_diversity: 'Low diversity',
  weak_depth: 'Low depth',
  weak_wellbeing: 'Low wellbeing',
  unknown: 'Unclassified',
}

function qColor(q) {
  // red (low) -> amber -> emerald (high)
  if (q >= 0.66) return '#10b981'
  if (q >= 0.4) return '#f59e0b'
  return '#f43f5e'
}

export default function LearningPage() {
  const { data: policy, loading, refetch } = useApi(() => api.getRlPolicy(), [])
  const { data: history } = useApi(() => api.getRlHistory(), [])
  const [busy, setBusy] = useState(null)

  const rows = Array.isArray(policy) ? policy : []
  const hist = Array.isArray(history) ? history : []

  // Group by context
  const byContext = {}
  rows.forEach(r => { (byContext[r.context_key] ||= []).push(r) })
  const contexts = Object.keys(byContext)

  const totalSamples = rows.reduce((s, r) => s + (r.n || 0), 0)
  const bestArm = rows.length ? rows.reduce((a, b) => (b.q_value > a.q_value ? b : a)) : null

  const sendFeedback = async (ctx, action, reward) => {
    setBusy(`${ctx}:${action}:${reward}`)
    try { await api.sendRlFeedback(ctx, action, reward); await refetch() }
    finally { setBusy(null) }
  }

  return (
    <div>
      <div style={{ marginBottom: 32 }}>
        <h1 className="gradient-text" style={{ fontSize: 32, fontWeight: 800, letterSpacing: '-0.03em', marginBottom: 6 }}>Learning</h1>
        <p style={{ color: 'var(--text-tertiary)', fontSize: 15 }}>
          Reinforcement-learning policy — a contextual bandit that learns which nudge helps in each state
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 16, marginBottom: 32 }}>
        <StatCard label="Learned States" value={contexts.length} icon={TargetIcon} accent="indigo" loading={loading} />
        <StatCard label="Policy Entries" value={rows.length} icon={ZapIcon} accent="violet" loading={loading} />
        <StatCard label="Total Updates" value={totalSamples} icon={ActivityIcon} accent="emerald" loading={loading} />
        <StatCard label="Best Action Q" value={bestArm ? bestArm.q_value.toFixed(2) : '--'} icon={BrainIcon} accent="amber" loading={loading} />
      </div>

      {/* Policy table */}
      <GlassCard gradient>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600 }}>Learned Policy (Q-values)</h3>
          <Badge variant="neutral">epsilon-greedy</Badge>
        </div>
        <p style={{ fontSize: 13, color: 'var(--text-tertiary)', marginBottom: 20 }}>
          For each behavioural state, the value it has learned for each nudge. Higher = more effective at improving alignment. Rate a suggestion 👍/👎 to teach it.
        </p>

        {loading ? (
          <div style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)' }}>Loading…</div>
        ) : contexts.length === 0 ? (
          <div style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)', fontSize: 14 }}>
            No policy learned yet. As data is ingested (or you rate suggestions), the bandit fills in.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            {contexts.map(ctx => {
              const best = byContext[ctx].reduce((a, b) => (b.q_value > a.q_value ? b : a))
              return (
                <div key={ctx}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
                    <Badge variant="indigo">{CTX_LABELS[ctx] || ctx}</Badge>
                    <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                      preferred: <span style={{ color: 'var(--text-secondary)' }}>{ACTION_LABELS[best.action_id] || best.action_id}</span>
                    </span>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {byContext[ctx].sort((a, b) => b.q_value - a.q_value).map(r => (
                      <div key={r.action_id} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                        <div style={{ width: 170, fontSize: 13, color: 'var(--text-secondary)' }}>
                          {ACTION_LABELS[r.action_id] || r.action_id}
                        </div>
                        <div style={{ flex: 1, height: 20, background: 'rgba(148,163,184,0.08)', borderRadius: 6, overflow: 'hidden', position: 'relative' }}>
                          <div style={{ width: `${r.q_value * 100}%`, height: '100%', background: qColor(r.q_value), borderRadius: 6, transition: 'width 0.4s' }} />
                          <span style={{ position: 'absolute', right: 8, top: 1, fontSize: 11, color: 'var(--text-secondary)' }}>
                            Q {r.q_value.toFixed(2)} · n{r.n}
                          </span>
                        </div>
                        <div style={{ display: 'flex', gap: 4 }}>
                          <button
                            onClick={() => sendFeedback(ctx, r.action_id, 0.9)}
                            disabled={busy === `${ctx}:${r.action_id}:0.9`}
                            title="This nudge helps"
                            style={{ padding: '2px 8px', borderRadius: 6, border: '1px solid rgba(16,185,129,0.3)', background: 'rgba(16,185,129,0.1)', color: '#34d399', cursor: 'pointer', fontSize: 13 }}
                          >👍</button>
                          <button
                            onClick={() => sendFeedback(ctx, r.action_id, 0.1)}
                            disabled={busy === `${ctx}:${r.action_id}:0.1`}
                            title="This nudge doesn't help"
                            style={{ padding: '2px 8px', borderRadius: 6, border: '1px solid rgba(244,63,94,0.3)', background: 'rgba(244,63,94,0.1)', color: '#fb7185', cursor: 'pointer', fontSize: 13 }}
                          >👎</button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </GlassCard>

      {/* Action history */}
      <GlassCard gradient style={{ marginTop: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600 }}>Recent Suggestions</h3>
          <Badge variant="neutral">{hist.length}</Badge>
        </div>
        {hist.length === 0 ? (
          <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)', fontSize: 14 }}>No actions logged yet</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {hist.slice(0, 12).map((h, i) => (
              <div key={h.id || i} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '8px 12px', borderRadius: 8, background: 'rgba(148,163,184,0.04)' }}>
                <Badge variant="violet">{ACTION_LABELS[h.action_type] || h.action_type}</Badge>
                <div style={{ flex: 1, fontSize: 12, color: 'var(--text-muted)' }}>
                  {h.state?.context_key ? (CTX_LABELS[h.state.context_key] || h.state.context_key) : ''}
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>
                  {h.created_at ? new Date(h.created_at).toLocaleString() : ''}
                </div>
              </div>
            ))}
          </div>
        )}
      </GlassCard>
    </div>
  )
}
