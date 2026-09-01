import { useNavigate } from 'react-router-dom'
import { api } from '../../api/client'
import { useApi } from '../../hooks/useApi'
import GlassCard from '../../components/ui/GlassCard'
import Badge from '../../components/ui/Badge'
import Reveal from '../../components/motion/Reveal'

/**
 * Interest Provenance — chosen vs fed.
 *
 * The design constraint that shapes everything here: "you never sought this
 * out" and "we have no way to tell" both come from zero deliberate signals,
 * and mean opposite things. So an account without search history gets a page
 * that explains it cannot measure agency — not a page telling someone every
 * interest they have was manufactured.
 */

const VERDICT = {
  fed:     { label: 'Fed to you',   color: 'var(--rose-400)',    variant: 'danger',
             note: 'Heavily watched, with no evidence you ever went looking for it.' },
  mixed:   { label: 'Mixed',        color: 'var(--amber-400)',   variant: 'amber',
             note: 'Some seeking, mostly exposure.' },
  chosen:  { label: 'Chosen',       color: 'var(--emerald-400)', variant: 'emerald',
             note: 'You searched for or engaged with this repeatedly.' },
  unknown: { label: 'Not measurable', color: 'var(--text-muted)', variant: 'neutral',
             note: 'Too little exposure, or no deliberate-signal data to weigh it against.' },
}

function AgencyBar({ agency, verdict }) {
  const pct = agency == null ? 0 : Math.round(agency * 100)
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 150 }}>
      <div style={{ flex: 1, height: 6, borderRadius: 3, background: 'rgba(148,163,184,0.14)', overflow: 'hidden' }}>
        <div className="grow-w" style={{
          height: '100%', width: `${pct}%`, borderRadius: 3,
          background: VERDICT[verdict].color,
        }} />
      </div>
      <span className="tabular" style={{ fontSize: 12, color: 'var(--text-muted)', minWidth: 54, textAlign: 'right' }}>
        {agency == null ? '—' : `${pct}% sought`}
      </span>
    </div>
  )
}

export default function ProvenancePage() {
  const navigate = useNavigate()
  const { data, loading, error } = useApi(() => api.getProvenanceReport())
  const { data: timeline } = useApi(() => api.getProvenanceTimeline())

  const summary = data?.summary || {}
  const fedShare = summary.fed_share_of_attention

  return (
    <div>
      <Reveal variant="depth">
        <div style={{ marginBottom: 28 }}>
          <h1 className="gradient-text" style={{ fontSize: 34, fontWeight: 800, marginBottom: 6 }}>
            Interest Provenance
          </h1>
          <p style={{ color: 'var(--text-tertiary)', fontSize: 15, maxWidth: 730, lineHeight: 1.6 }}>
            Which of your interests did you go looking for, and which were put in front of
            you until they stuck? Seeking is measured from searches and explicit engagement;
            exposure is measured from what you watched.
          </p>
        </div>
      </Reveal>

      {loading && <GlassCard><div style={{ padding: 28, color: 'var(--text-muted)' }}>Weighing seeking against exposure…</div></GlassCard>}

      {error && (
        <GlassCard>
          <div className="empty-state">
            <div className="empty-state-icon">⚠️</div>
            <div className="empty-state-title">Couldn't load provenance</div>
            <div className="empty-state-description">{String(error)}</div>
          </div>
        </GlassCard>
      )}

      {/* The honest empty state, and the common one: agency is unmeasurable
          without search history, and saying so is the whole point. */}
      {!loading && !error && data && !data.measurable && (
        <Reveal variant="depth">
          <GlassCard gradient style={{ marginBottom: 22 }}>
            <div style={{ padding: '24px 8px', textAlign: 'center' }}>
              <div style={{ fontSize: 40, marginBottom: 14 }}>🧭</div>
              <h3 style={{ fontSize: 19, fontWeight: 700, marginBottom: 10 }}>
                Agency isn't measurable for this account yet
              </h3>
              <p style={{ fontSize: 14, color: 'var(--text-tertiary)', lineHeight: 1.7, maxWidth: 620, margin: '0 auto 8px' }}>
                Deciding whether you chose an interest requires evidence you went looking for
                it. That means search history — the strongest signal available, and one your
                browsing data doesn't contain on its own.
              </p>
              <p style={{ fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.7, maxWidth: 620, margin: '0 auto 20px' }}>
                <strong>This page will not guess.</strong> Reporting every topic as "fed to you"
                because there's nothing to weigh it against would be exactly the wrong answer.
              </p>
              <button
                onClick={() => navigate('/import')}
                className="btn-3d btn-aurora"
                style={{ padding: '12px 24px', borderRadius: 12, border: 'none', color: 'white', fontSize: 14, fontWeight: 700, cursor: 'pointer' }}
              >
                Import Takeout with search history →
              </button>
            </div>
          </GlassCard>
        </Reveal>
      )}

      {!loading && !error && data && (
        <>
          {data.measurable && (
            <Reveal variant="depth">
              <GlassCard gradient style={{ marginBottom: 22 }}>
                {fedShare != null && (
                  <div style={{ fontSize: 20, fontWeight: 700, marginBottom: 14, color: fedShare > 0.4 ? 'var(--rose-400)' : 'var(--emerald-400)' }}>
                    {Math.round(fedShare * 100)}% of your judged watching went to topics
                    you never sought out
                  </div>
                )}
                <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                  <Badge variant="danger">{summary.fed} fed</Badge>
                  <Badge variant="amber">{summary.mixed} mixed</Badge>
                  <Badge variant="emerald">{summary.chosen} chosen</Badge>
                  <Badge variant="neutral">{summary.unknown} not measurable</Badge>
                  <Badge variant="indigo">{summary.search_signals} searches</Badge>
                  <Badge variant="indigo">{summary.engagement_signals} engagements</Badge>
                </div>
              </GlassCard>
            </Reveal>
          )}

          <Reveal variant="depth">
            <GlassCard gradient style={{ marginBottom: 22 }}>
              <h3 style={{ fontSize: 17, fontWeight: 700, marginBottom: 16 }}>Every tracked topic</h3>
              {(data.topics || []).length === 0 ? (
                <div style={{ color: 'var(--text-muted)', fontSize: 13.5, padding: '8px 0' }}>
                  No topics tracked yet — import some history first.
                </div>
              ) : (
                <div style={{ display: 'grid', gap: 10 }}>
                  {data.topics.map((t, i) => (
                    <div key={i} style={{
                      padding: '13px 15px', borderRadius: 11,
                      background: 'rgba(148,163,184,0.05)',
                      borderLeft: `2px solid ${VERDICT[t.verdict].color}`,
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 14, flexWrap: 'wrap', marginBottom: 6 }}>
                        <span style={{ fontSize: 14.5, fontWeight: 600, minWidth: 130 }}>{t.topic}</span>
                        <AgencyBar agency={t.agency} verdict={t.verdict} />
                        <Badge variant={VERDICT[t.verdict].variant}>{VERDICT[t.verdict].label}</Badge>
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                        {t.exposure} views · {t.searches} searches
                        {t.semantic_searches > 0 && ` (${t.semantic_searches} matched by meaning)`}
                        {' · '}{t.engagements} engagements
                        {t.example_searches?.length > 0 && (
                          <span style={{ color: 'var(--text-tertiary)' }}>
                            {'  ·  '}e.g. “{t.example_searches.join('”, “')}”
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </GlassCard>
          </Reveal>

          {/* The temporal half: when a topic arrived and how fast it grew.
              A stacked bar per month, so a fed topic swallowing the mix is
              visible as a shape rather than a number. */}
          {timeline?.topics?.length > 0 && (
            <Reveal variant="depth">
              <GlassCard gradient style={{ marginBottom: 22 }}>
                <div style={{ marginBottom: 4 }}>
                  <h3 style={{ fontSize: 17, fontWeight: 700 }}>How it happened</h3>
                  <div style={{ fontSize: 12.5, color: 'var(--text-muted)' }}>
                    Share of each month's watching, by topic. Red is fed, green is chosen.
                  </div>
                </div>

                {timeline.summary?.fed_share_latest_month != null && timeline.summary?.fed_share_first_month != null && (
                  <div style={{ fontSize: 14, color: 'var(--text-secondary)', margin: '14px 0 18px', lineHeight: 1.6 }}>
                    Topics you never sought went from{' '}
                    <strong style={{ color: 'var(--text-primary)' }}>
                      {Math.round(timeline.summary.fed_share_first_month * 100)}%
                    </strong>{' '}
                    of your watching in the first month to{' '}
                    <strong style={{ color: 'var(--rose-400)' }}>
                      {Math.round(timeline.summary.fed_share_latest_month * 100)}%
                    </strong>{' '}
                    in the most recent.
                  </div>
                )}

                <div style={{ display: 'flex', alignItems: 'flex-end', gap: 8, minHeight: 150, marginBottom: 10 }}>
                  {timeline.buckets.map(bucket => (
                    <div key={bucket.month} style={{ flex: 1, minWidth: 34, textAlign: 'center' }}>
                      <div style={{
                        height: 120, display: 'flex', flexDirection: 'column-reverse',
                        borderRadius: 6, overflow: 'hidden',
                        background: 'rgba(148,163,184,0.08)',
                        // A month too sparse to score is drawn hollow rather
                        // than as a confident stack of shares.
                        opacity: bucket.reliable ? 1 : 0.3,
                      }}>
                        {bucket.reliable && timeline.topics.map(t => {
                          const share = bucket.shares[t.topic] || 0
                          if (!share) return null
                          return (
                            <div
                              key={t.topic}
                              title={`${t.topic}: ${Math.round(share * 100)}% (${t.verdict})`}
                              style={{ height: `${share * 100}%`, background: VERDICT[t.verdict].color, opacity: 0.85 }}
                            />
                          )
                        })}
                      </div>
                      <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 6 }}>
                        {bucket.month.slice(5)}
                      </div>
                    </div>
                  ))}
                </div>

                <div style={{ display: 'grid', gap: 7, marginTop: 14 }}>
                  {timeline.topics.slice(0, 8).map(t => (
                    <div key={t.topic} style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 12.5, flexWrap: 'wrap' }}>
                      <span style={{ width: 9, height: 9, borderRadius: 2, background: VERDICT[t.verdict].color, flexShrink: 0 }} />
                      <span style={{ fontWeight: 600, minWidth: 100 }}>{t.topic}</span>
                      <span style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: 11.5 }}>
                        first seen {t.first_month} · peaked {t.peak_month} at {Math.round(t.peak_share * 100)}%
                        {t.verdict === 'fed' && t.months_to_peak === 0 && ' · peaked the month it appeared'}
                      </span>
                    </div>
                  ))}
                </div>
              </GlassCard>
            </Reveal>
          )}

          <Reveal variant="depth">
            <GlassCard>
              <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 10 }}>How this is measured</h3>
              <ul style={{ margin: 0, paddingLeft: 18, display: 'grid', gap: 9 }}>
                {(timeline?.caveats || data.caveats || []).map((c, i) => (
                  <li key={i} style={{ fontSize: 13, color: 'var(--text-tertiary)', lineHeight: 1.7 }}>{c}</li>
                ))}
              </ul>
            </GlassCard>
          </Reveal>
        </>
      )}
    </div>
  )
}
