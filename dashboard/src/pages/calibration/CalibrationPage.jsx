import { useState, useCallback } from 'react'
import { api } from '../../api/client'
import { useApi } from '../../hooks/useApi'
import GlassCard from '../../components/ui/GlassCard'
import Badge from '../../components/ui/Badge'
import AsyncState from '../../components/ui/AsyncState'
import Reveal from '../../components/motion/Reveal'
import CountUp from '../../components/motion/CountUp'
import { CheckIcon, XIcon, AlertIcon, TargetIcon } from '../../icons/icons'

/**
 * The Accuracy Ledger.
 *
 * Every other page here audits somebody else — the Mirror checks a platform's
 * claims, Provenance asks whether an interest was chosen or fed. This one
 * turns the same question on AIMirror: when it told you something about
 * yourself, was it right?
 *
 * The design job is to resist making the system look good. Two specific
 * temptations, both refused:
 *
 * 1. Leading with an accuracy percentage. Accuracy is trivially gamed by
 *    never claiming anything confidently, so the headline is CALIBRATION —
 *    when it says 0.8, is it right 80% of the time? — and an overconfident
 *    band is called out even when overall accuracy looks fine.
 *
 * 2. Drawing a bar for a bucket with four samples. A rate from a handful of
 *    clicks is noise wearing a decimal point. The server returns
 *    observed_rate: null below its floor and this renders that as "needs N
 *    more", never as an empty bar that reads like 0%.
 *
 * Every rate is shown with its 95% interval, because the point estimate on
 * ten answers is not the answer.
 */

const ASSESSMENTS = {
  calibrated: {
    label: 'Calibrated',
    variant: 'emerald',
    blurb: 'It was right about as often as it claimed.',
  },
  overconfident: {
    label: 'Overconfident',
    variant: 'rose',
    blurb: 'It was right LESS often than it claimed. This is the failure that matters.',
  },
  underconfident: {
    label: 'Underconfident',
    variant: 'amber',
    blurb: 'It was right more often than it claimed — hedging more than it needed to.',
  },
  insufficient_data: {
    label: 'Not enough answers',
    variant: 'slate',
    blurb: 'No rate is shown, because one from this few answers would be noise.',
  },
}

function Bar({ bucket }) {
  const known = bucket.observed_rate !== null && bucket.observed_rate !== undefined
  const claimed = bucket.claimed_confidence

  return (
    <div style={{ marginBottom: 18 }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 6 }}>
        <span style={{ fontSize: 13, fontWeight: 600, minWidth: 74 }}>
          {bucket.range}
        </span>
        <Badge variant={ASSESSMENTS[bucket.assessment]?.variant || 'slate'}>
          {ASSESSMENTS[bucket.assessment]?.label || bucket.assessment}
        </Badge>
        <span style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--text-tertiary)' }}>
          {known
            ? `${bucket.correct}/${bucket.samples} correct`
            : `${bucket.samples} of ${bucket.samples + (bucket.needed || 0)} answers`}
        </span>
      </div>

      <div style={{
        position: 'relative', height: 26, borderRadius: 8,
        background: 'rgba(148,163,184,0.10)', overflow: 'hidden',
      }}>
        {known ? (
          <div style={{
            width: `${bucket.observed_rate * 100}%`, height: '100%',
            background: bucket.assessment === 'overconfident'
              ? 'linear-gradient(90deg, rgba(244,63,94,0.55), rgba(244,63,94,0.30))'
              : bucket.assessment === 'underconfident'
                ? 'linear-gradient(90deg, rgba(251,191,36,0.55), rgba(251,191,36,0.30))'
                : 'linear-gradient(90deg, rgba(16,185,129,0.55), rgba(16,185,129,0.30))',
            transition: 'width .5s ease',
          }} />
        ) : (
          // Deliberately NOT a zero-width bar: an empty track reads as 0%.
          <div style={{
            position: 'absolute', inset: 0, display: 'flex', alignItems: 'center',
            paddingLeft: 10, fontSize: 11, color: 'var(--text-muted)',
            fontStyle: 'italic',
          }}>
            {bucket.needed} more answer{bucket.needed === 1 ? '' : 's'} needed before this can be scored
          </div>
        )}

        {/* Where the system CLAIMED it would land. The gap is the finding. */}
        <div
          title={`Claimed ${Math.round(claimed * 100)}%`}
          style={{
            position: 'absolute', top: 0, bottom: 0, left: `${claimed * 100}%`,
            width: 2, background: 'var(--text-secondary)', opacity: 0.85,
          }}
        />
      </div>

      {known && (
        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
          claimed {Math.round(claimed * 100)}% · observed {Math.round(bucket.observed_rate * 100)}%
          {bucket.interval && (
            <> · 95% CI {Math.round(bucket.interval[0] * 100)}–{Math.round(bucket.interval[1] * 100)}%</>
          )}
        </div>
      )}
    </div>
  )
}

export default function CalibrationPage() {
  const { data: report, loading, error, refetch } = useApi(() => api.getCalibrationReport(), [])
  const { data: open, refetch: refetchOpen } = useApi(() => api.getOpenClaims(), [])
  const { data: answered, refetch: refetchAnswered } = useApi(() => api.getAnsweredClaims(), [])
  const [busy, setBusy] = useState(null)
  const [notice, setNotice] = useState(null)

  const answer = useCallback(async (claim, verdict) => {
    setBusy(`${claim.claim_id}:${verdict}`)
    try {
      await api.sendClaimVerdict(claim.claim_id, verdict, claim.claim_type)
      setNotice(null)
      await Promise.all([refetchOpen(), refetchAnswered(), refetch()])
    } catch (e) {
      setNotice(
        e?.response?.status === 429
          ? 'Too many answers at once — try again shortly.'
          : (e?.response?.data?.detail || 'Could not record that answer.')
      )
    } finally {
      setBusy(null)
    }
  }, [refetch, refetchOpen, refetchAnswered])

  const buckets = report?.buckets || []
  const claims = Array.isArray(open) ? open : []
  const answers = Array.isArray(answered) ? answered : []

  return (
    <div>
      <div style={{ marginBottom: 28 }}>
        <h1 className="gradient-text" style={{ fontSize: 32, fontWeight: 800, letterSpacing: '-0.03em', marginBottom: 6 }}>
          Accuracy Ledger
        </h1>
        <p style={{ color: 'var(--text-tertiary)', fontSize: 15, maxWidth: 720 }}>
          This product argues that a system which profiles you should be accountable for
          whether it is right. So here is its own scorecard — not just how often it was
          correct, but whether its confidence was honest.
        </p>
      </div>

      {notice && (
        <div role="status" style={{
          padding: '10px 14px', marginBottom: 18, borderRadius: 10, fontSize: 13,
          border: '1px solid rgba(244,63,94,0.25)', background: 'rgba(244,63,94,0.08)',
          color: 'var(--text-secondary)',
        }}>{notice}</div>
      )}

      <AsyncState loading={loading} error={error} onRetry={refetch}>
        <Reveal>
          <GlassCard gradient style={{ marginBottom: 24 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
              <TargetIcon />
              <h3 style={{ fontSize: 16, fontWeight: 600 }}>Is its confidence honest?</h3>
            </div>

            {report?.measurable ? (
              <>
                <div style={{ display: 'flex', gap: 28, flexWrap: 'wrap', marginBottom: 16 }}>
                  <div>
                    <div style={{ fontSize: 30, fontWeight: 800 }}>
                      <CountUp to={Math.round((report.accuracy || 0) * 100)} />%
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                      marked correct
                      {report.accuracy_interval && (
                        <> · CI {Math.round(report.accuracy_interval[0] * 100)}–{Math.round(report.accuracy_interval[1] * 100)}%</>
                      )}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: 30, fontWeight: 800 }}>{report.brier_score ?? '—'}</div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                      Brier score · lower is better, 0.25 = hedging everything
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: 30, fontWeight: 800 }}>{report.summary.scored}</div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                      answers scored
                      {report.summary.unsure > 0 && <> · {report.summary.unsure} unsure, not scored</>}
                    </div>
                  </div>
                </div>
                <p style={{ fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                  {report.verdict}
                </p>
              </>
            ) : (
              <div>
                <Badge variant="slate">Not enough answers yet</Badge>
                <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginTop: 10, lineHeight: 1.6 }}>
                  {report?.verdict ||
                    'Answer some of the claims below and this will start scoring itself.'}
                </p>
              </div>
            )}
          </GlassCard>
        </Reveal>

        {buckets.some(b => b.samples > 0) && (
          <Reveal delay={0.05}>
            <GlassCard style={{ marginBottom: 24 }}>
              <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 4 }}>
                By how sure it claimed to be
              </h3>
              <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 18 }}>
                The vertical line is what it claimed. The bar is what actually happened.
                A bar short of the line means it was overconfident.
              </p>
              {buckets.map(b => <Bar key={b.range} bucket={b} />)}
            </GlassCard>
          </Reveal>
        )}

        <Reveal delay={0.1}>
          <GlassCard>
            <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 4 }}>
              Claims awaiting your verdict
            </h3>
            <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 18 }}>
              Most confident first — a confident claim that turns out to be wrong is the
              most useful thing you can tell it.
            </p>

            {claims.length === 0 ? (
              <p style={{ fontSize: 13, color: 'var(--text-tertiary)' }}>
                Nothing waiting. New claims appear here as the pipeline makes them.
              </p>
            ) : claims.map(claim => (
              <div key={claim.claim_id} style={{
                padding: '12px 0', borderTop: '1px solid var(--border-subtle)',
                display: 'flex', alignItems: 'flex-start', gap: 12, flexWrap: 'wrap',
              }}>
                <div style={{ flex: '1 1 320px', minWidth: 0 }}>
                  <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 2 }}>{claim.label}</div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                    {claim.description}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 4 }}>
                    it claims {Math.round(claim.confidence * 100)}% confidence
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 6 }}>
                  {[
                    { verdict: 'right', label: 'Right', icon: CheckIcon, color: '#34d399', border: 'rgba(16,185,129,0.3)', bg: 'rgba(16,185,129,0.1)' },
                    { verdict: 'wrong', label: 'Wrong', icon: XIcon, color: '#fb7185', border: 'rgba(244,63,94,0.3)', bg: 'rgba(244,63,94,0.1)' },
                    { verdict: 'unsure', label: 'Not sure', icon: AlertIcon, color: 'var(--text-tertiary)', border: 'var(--border-subtle)', bg: 'transparent' },
                  ].map(({ verdict, label, icon: Icon, color, border, bg }) => (
                    <button
                      key={verdict}
                      onClick={() => answer(claim, verdict)}
                      disabled={busy === `${claim.claim_id}:${verdict}`}
                      title={label}
                      style={{
                        display: 'flex', alignItems: 'center', gap: 5,
                        padding: '6px 10px', borderRadius: 8, cursor: 'pointer',
                        border: `1px solid ${border}`, background: bg, color,
                        fontSize: 12, fontWeight: 600,
                      }}
                    >
                      <Icon /> {label}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </GlassCard>
        </Reveal>

        {answers.length > 0 && (
          <Reveal delay={0.15}>
            <GlassCard style={{ marginTop: 24 }}>
              <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 4 }}>
                Your answers
              </h3>
              <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 18 }}>
                Change any of these. A correction you cannot reverse is a trap rather
                than a control — and marking a claim wrong stops the system asserting it,
                so you should be able to take that back.
              </p>

              {answers.map(a => (
                <div key={`${a.claim_type}:${a.claim_id}`} style={{
                  padding: '12px 0', borderTop: '1px solid var(--border-subtle)',
                  display: 'flex', alignItems: 'flex-start', gap: 12, flexWrap: 'wrap',
                }}>
                  <div style={{ flex: '1 1 300px', minWidth: 0 }}>
                    <div style={{
                      fontSize: 14, fontWeight: 600, marginBottom: 2,
                      textDecoration: a.verdict === 'wrong' ? 'line-through' : 'none',
                      opacity: a.still_claimed ? 1 : 0.6,
                    }}>{a.label}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>
                      you said <strong>{a.verdict}</strong> · it claimed{' '}
                      {Math.round(a.confidence_at_verdict * 100)}%
                      {!a.still_claimed && ' · the system no longer makes this claim'}
                    </div>
                  </div>

                  {a.still_claimed ? (
                    <div style={{ display: 'flex', gap: 6 }}>
                      {['right', 'wrong', 'unsure'].map(v => (
                        <button
                          key={v}
                          onClick={() => answer({ claim_id: a.live_claim_id, claim_type: a.claim_type }, v)}
                          disabled={a.verdict === v || busy === `${a.live_claim_id}:${v}`}
                          style={{
                            padding: '5px 10px', borderRadius: 8, fontSize: 12, fontWeight: 600,
                            border: '1px solid var(--border-subtle)',
                            background: a.verdict === v ? 'rgba(99,102,241,0.18)' : 'transparent',
                            color: a.verdict === v ? '#a5b4fc' : 'var(--text-tertiary)',
                            cursor: a.verdict === v ? 'default' : 'pointer',
                          }}
                        >{v}</button>
                      ))}
                    </div>
                  ) : (
                    <span style={{ fontSize: 11, color: 'var(--text-muted)', fontStyle: 'italic' }}>
                      nothing to change
                    </span>
                  )}
                </div>
              ))}
            </GlassCard>
          </Reveal>
        )}
      </AsyncState>
    </div>
  )
}
