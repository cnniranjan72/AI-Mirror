import { useApi } from '../../hooks/useApi'
import { api } from '../../api/client'
import GlassCard from '../../components/ui/GlassCard'
import StatCard from '../../components/ui/StatCard'
import Badge from '../../components/ui/Badge'
import { CpuIcon, BrainIcon, TargetIcon, LayersIcon, ZapIcon } from '../../icons/icons'
import CharacterCreature3D from '../../components/character/CharacterCreature3D'

function qColor(q) {
  if (q >= 0.66) return '#10b981'
  if (q >= 0.4) return '#f59e0b'
  return '#f43f5e'
}

// Tint the character orb by the RL policy's average learned Q-value — a
// genuine (if coarse) proxy for "how well is the character's behavior
// currently performing", not an arbitrary color choice.
function avgQColor(policy) {
  if (!policy || policy.length === 0) return null
  const avg = policy.reduce((sum, p) => sum + (p.q_value || 0), 0) / policy.length
  return qColor(avg)
}

export default function CharacterPage() {
  const { data: state, loading } = useApi(() => api.getCharacterState(), [])
  const { data: activity } = useApi(() => api.getCharacterActivity(), [])
  const { data: learning } = useApi(() => api.getCharacterLearningSummary(), [])

  const mem = state?.memory || {}
  const totalMemory = Object.values(mem).reduce((a, b) => a + (b || 0), 0)

  return (
    <div>
      <div style={{ marginBottom: 32 }}>
        <h1 className="gradient-text" style={{ fontSize: 32, fontWeight: 800, letterSpacing: '-0.03em', marginBottom: 6 }}>Character</h1>
        <p style={{ color: 'var(--text-tertiary)', fontSize: 15 }}>
          The live digital twin your chat actually talks through — built fresh on every query, tuned by reinforcement learning
        </p>
      </div>

      {!loading && state && !state.built && (
        <GlassCard gradient>
          <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)' }}>
            Character runtime could not be built: {(state.errors || []).join(', ') || 'no identity yet'}
          </div>
        </GlassCard>
      )}

      {(loading || state?.built) && (
        <>
          <GlassCard gradient>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '4px 4px' }}>
              <div style={{ flex: '0 0 auto' }}>
                <CharacterCreature3D
                  size={260}
                  variant="robot"
                  confidence={state?.identity_snapshot?.overall_confidence ?? 0.3}
                  topics={state?.identity_snapshot?.dominant_topics ?? []}
                  moodColor={avgQColor(learning?.policy)}
                  thinking={loading}
                  showLabels
                />
              </div>
              <div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>
                  Live character state
                </div>
                <div style={{ fontSize: 15, color: 'var(--text-secondary)', lineHeight: 1.6, maxWidth: 480 }}>
                  This isn't a decorative avatar — its glow tracks identity confidence
                  ({Math.round((state?.identity_snapshot?.overall_confidence || 0) * 100)}%),
                  the swirling labels are its {(state?.identity_snapshot?.dominant_topics || []).length || 0} dominant
                  topics, and its hologram tint reflects the average learned Q-value across the RL policy.
                  It pulses and spins faster whenever a runtime rebuild or chat query is in flight.
                </div>
              </div>
            </div>
          </GlassCard>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 16, margin: '24px 0 32px' }}>
            <StatCard label="Identity Version" value={state ? `v${state.identity_snapshot?.version}` : '--'} icon={LayersIcon} accent="indigo" loading={loading} />
            <StatCard label="Confidence" value={state ? `${Math.round((state.identity_snapshot?.overall_confidence || 0) * 100)}%` : '--'} icon={TargetIcon} accent="violet" loading={loading} />
            <StatCard label="Active Inferences" value={state?.inference_count ?? '--'} icon={BrainIcon} accent="emerald" loading={loading} />
            <StatCard label="Memory References" value={totalMemory} icon={CpuIcon} accent="amber" loading={loading} />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginBottom: 24 }}>
            {/* Identity + self-model */}
            <GlassCard gradient>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                <h3 style={{ fontSize: 16, fontWeight: 600 }}>What the Character Knows</h3>
                <Badge variant="indigo">{state?.core_id?.slice(0, 18)}…</Badge>
              </div>
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 6 }}>Dominant topics</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {(state?.identity_snapshot?.dominant_topics || []).map(t => <Badge key={t} variant="indigo">{t}</Badge>)}
                </div>
              </div>
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 6 }}>Self-model confidence</div>
                <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-secondary)' }}>
                  {Math.round((state?.self_model?.overall_confidence || 0) * 100)}%
                </div>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Strong beliefs</div>
                  <div style={{ fontSize: 18, fontWeight: 700, color: '#34d399' }}>{state?.self_model?.strong_beliefs?.length || 0}</div>
                </div>
                <div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Uncertain beliefs</div>
                  <div style={{ fontSize: 18, fontWeight: 700, color: '#fbbf24' }}>{state?.self_model?.uncertain_beliefs?.length || 0}</div>
                </div>
              </div>
              <div style={{ marginTop: 16, fontSize: 11, color: 'var(--text-muted)' }}>
                Runtime build time: {state?.build_time_ms}ms
              </div>
            </GlassCard>

            {/* Recent activity */}
            <GlassCard gradient>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                <h3 style={{ fontSize: 16, fontWeight: 600 }}>Recent Conversations</h3>
                <Badge variant="neutral">{activity?.length || 0}</Badge>
              </div>
              <div style={{ maxHeight: 280, overflow: 'auto', display: 'flex', flexDirection: 'column', gap: 8 }}>
                {(activity || []).length === 0 ? (
                  <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>No conversations yet</div>
                ) : activity.map((t, i) => (
                  <div key={t.trace_id || i} style={{ padding: '8px 12px', borderRadius: 8, background: 'rgba(148,163,184,0.04)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Badge variant={t.success ? 'emerald' : 'danger'}>{t.intent_type || 'query'}</Badge>
                      <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>v{t.snapshot_version} · {Math.round(t.total_ms || 0)}ms</span>
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {t.query}
                    </div>
                  </div>
                ))}
              </div>
            </GlassCard>
          </div>

          {/* How RL is tuning the character */}
          <GlassCard gradient>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <h3 style={{ fontSize: 16, fontWeight: 600 }}>Being Tuned by Reinforcement Learning</h3>
              <Badge variant="violet">{learning?.policy_size || 0} learned states</Badge>
            </div>
            <p style={{ fontSize: 13, color: 'var(--text-tertiary)', marginBottom: 16 }}>
              Every conversation and ingest updates this policy — see the full learning loop on the <a href="/learning" style={{ color: '#818cf8' }}>Learning page</a>.
            </p>
            {learning?.last_action && (
              <div style={{ padding: 12, borderRadius: 8, background: 'rgba(99,102,241,0.06)', marginBottom: 12 }}>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 4 }}>Last action taken</div>
                <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{learning.last_action.action_type}</div>
              </div>
            )}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {(learning?.policy || []).slice(0, 5).map((p, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <div style={{ width: 140, fontSize: 12, color: 'var(--text-muted)' }}>{p.context_key}</div>
                  <div style={{ flex: 1, height: 6, background: 'rgba(148,163,184,0.1)', borderRadius: 3, overflow: 'hidden' }}>
                    <div style={{ width: `${p.q_value * 100}%`, height: '100%', background: qColor(p.q_value) }} />
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', width: 50 }}>{p.action_id}</div>
                </div>
              ))}
            </div>
          </GlassCard>
        </>
      )}
    </div>
  )
}
