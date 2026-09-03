import { useState } from 'react'
import { api } from '../../api/client'
import { useApi } from '../../hooks/useApi'
import GlassCard from '../../components/ui/GlassCard'
import Badge from '../../components/ui/Badge'
import AsyncState from '../../components/ui/AsyncState'

/**
 * Restore Points — going back to a version of the model you recognise.
 *
 * The architecture has claimed rollback since the first paper draft. The method
 * existed: IdentityEvolutionEngine.rollback_to_snapshot, which logs "Rolled
 * back to snapshot X", returns None, and carries the comment "Placeholder -
 * would return reconstructed identity". Nothing had ever called it, and across
 * 35 stored snapshots is_active was TRUE on every one.
 *
 * Restoring by writing a snapshot back over the identity row would not have
 * worked. Identity construction runs from scratch on every ingest — the
 * existing identity supplies only its id and version counter, and all nine
 * sub-profiles are recomputed from behaviour objects — so a restored row lasts
 * until the next event arrives. The control would appear to work and then
 * quietly undo itself, which is the failure a person is least able to detect.
 *
 * What does hold is choosing which snapshot is the active one, because
 * architectural invariant 2 already says user-facing reads come from a frozen
 * snapshot rather than the live identity. The pin points that mechanism where
 * the person chose.
 *
 * The copy is deliberate about what this does and does not do. "Restore" in
 * most products means something was thrown away; here nothing is. Saying so
 * plainly matters more than sounding decisive.
 */

function fmt(iso) {
  if (!iso) return 'unknown'
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      year: 'numeric', month: 'short', day: 'numeric',
    })
  } catch {
    return iso.slice(0, 10)
  }
}

export default function RestorePage() {
  const { data, loading, error, refetch } = useApi(() => api.getRestorePoints(), [])
  const [busy, setBusy] = useState(null)
  const [reason, setReason] = useState('')
  const [failed, setFailed] = useState(null)

  const points = data?.points || []

  async function pin(snapshotId) {
    setBusy(snapshotId)
    setFailed(null)
    try {
      await api.setRestorePoint(snapshotId, reason)
      setReason('')
      await refetch()
    } catch (e) {
      setFailed(e?.message || 'Could not pin that snapshot.')
    } finally {
      setBusy(null)
    }
  }

  async function unpin() {
    setBusy('unpin')
    setFailed(null)
    try {
      await api.setRestorePoint(null, null)
      await refetch()
    } catch (e) {
      setFailed(e?.message || 'Could not unpin.')
    } finally {
      setBusy(null)
    }
  }

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 className="gradient-text" style={{ fontSize: 32, fontWeight: 800, letterSpacing: '-0.03em', marginBottom: 6 }}>
          Restore Points
        </h1>
        <p style={{ color: 'var(--text-tertiary)', fontSize: 15, maxWidth: 760 }}>
          A snapshot is kept whenever the model of you shifts far enough to be worth
          recording. If it has drifted somewhere you don't recognise, you can send it
          back to an earlier one.
        </p>
      </div>

      <AsyncState loading={loading} error={error} onRetry={refetch}>
        {!data?.measurable ? (
          <GlassCard gradient>
            <Badge variant="slate">Nothing to go back to</Badge>
            <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginTop: 10, lineHeight: 1.6 }}>
              {data?.note}
            </p>
          </GlassCard>
        ) : (
          <>
            {data.pin_broken && (
              <GlassCard style={{ marginBottom: 16, borderColor: 'rgba(251,113,133,0.4)' }}>
                <Badge variant="rose">Pin no longer resolves</Badge>
                <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 8, lineHeight: 1.6 }}>
                  {data.note}
                </p>
              </GlassCard>
            )}

            <GlassCard gradient style={{ marginBottom: 20 }}>
              <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', alignItems: 'baseline' }}>
                <div>
                  <div style={{ fontSize: 26, fontWeight: 800, color: data.pinned ? '#fbbf24' : '#34d399' }}>
                    {data.pinned ? 'Pinned' : 'Live'}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                    {data.pinned ? 'reading from an earlier snapshot' : 'reading the newest snapshot'}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 26, fontWeight: 800, color: 'var(--text-secondary)' }}>
                    {points.length}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>restore points</div>
                </div>
                <div style={{ flex: '1 1 300px', fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                  {!data.pin_broken && data.note}
                  {data.pin_reason && (
                    <div style={{ marginTop: 6, fontStyle: 'italic' }}>
                      Your note: &ldquo;{data.pin_reason}&rdquo;
                    </div>
                  )}
                </div>
                {data.pinned && (
                  <button
                    onClick={unpin}
                    disabled={busy === 'unpin'}
                    style={{
                      padding: '8px 14px', borderRadius: 9, cursor: 'pointer', fontSize: 13,
                      border: '1px solid rgba(52,211,153,0.4)', background: 'rgba(52,211,153,0.10)',
                      color: '#34d399', fontWeight: 600,
                    }}
                  >
                    {busy === 'unpin' ? 'Working…' : 'Return to newest'}
                  </button>
                )}
              </div>
            </GlassCard>

            {failed && (
              <GlassCard style={{ marginBottom: 16, borderColor: 'rgba(251,113,133,0.4)' }}>
                <p style={{ fontSize: 13, color: '#fb7185', margin: 0 }}>{failed}</p>
              </GlassCard>
            )}

            {!data.pinned && (
              <div style={{ marginBottom: 16 }}>
                <input
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder="Optional: why are you going back? (shown beside the pin later)"
                  maxLength={280}
                  style={{
                    width: '100%', padding: '9px 12px', borderRadius: 9, fontSize: 13,
                    border: '1px solid var(--border-subtle)', background: 'rgba(148,163,184,0.06)',
                    color: 'var(--text-primary)',
                  }}
                />
              </div>
            )}

            {points.map((p) => (
              <GlassCard key={p.snapshot_id} style={{
                marginBottom: 10,
                borderColor: p.is_pinned ? 'rgba(251,191,36,0.45)' : undefined,
              }}>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, flexWrap: 'wrap' }}>
                  <span style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)' }}>
                    Version {p.version}
                  </span>
                  <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{fmt(p.at)}</span>
                  {p.is_latest && <Badge variant="emerald">newest</Badge>}
                  {p.is_pinned && <Badge variant="amber">in use</Badge>}
                  <span style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--text-muted)' }}>
                    confidence {p.confidence.toFixed(2)}
                  </span>
                </div>

                {p.topics?.length > 0 && (
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 9 }}>
                    {p.topics.map((t) => (
                      <span key={t} style={{
                        padding: '3px 9px', borderRadius: 999, fontSize: 11,
                        background: 'rgba(148,163,184,0.10)', color: 'var(--text-secondary)',
                      }}>{t}</span>
                    ))}
                  </div>
                )}

                {p.changes && (
                  <p style={{ fontSize: 12, color: 'var(--text-tertiary)', margin: '10px 0 0', lineHeight: 1.6 }}>
                    Going back here would
                    {p.changes.topics_lost.length > 0 && <> drop <b>{p.changes.topics_lost.join(', ')}</b></>}
                    {p.changes.topics_lost.length > 0 && p.changes.topics_gained.length > 0 && ' and'}
                    {p.changes.topics_gained.length > 0 && <> bring back <b>{p.changes.topics_gained.join(', ')}</b></>}
                    {p.changes.topics_lost.length === 0 && p.changes.topics_gained.length === 0 && ' keep the same topics'}
                    {p.changes.confidence_delta !== 0 && (
                      <>, with confidence {p.changes.confidence_delta > 0 ? 'higher' : 'lower'} by{' '}
                        {Math.abs(p.changes.confidence_delta).toFixed(2)}</>
                    )}.
                  </p>
                )}

                {!p.is_pinned && !p.is_latest && (
                  <button
                    onClick={() => pin(p.snapshot_id)}
                    disabled={busy === p.snapshot_id}
                    style={{
                      marginTop: 11, padding: '6px 12px', borderRadius: 8, cursor: 'pointer',
                      fontSize: 12, border: '1px solid var(--border-subtle)',
                      background: 'transparent', color: 'var(--text-secondary)',
                    }}
                  >
                    {busy === p.snapshot_id ? 'Working…' : 'Use this version'}
                  </button>
                )}
              </GlassCard>
            ))}

            <p style={{ fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.7, marginTop: 18 }}>
              Using an earlier version changes what the system shows and answers with. It
              deletes nothing: your events, behaviours and every snapshot stay exactly as
              they are, and the live model carries on updating underneath — which is why
              you can return to the newest at any time.
            </p>
          </>
        )}
      </AsyncState>
    </div>
  )
}
