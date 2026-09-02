import { Link } from 'react-router-dom'
import { api } from '../../api/client'
import { useApi } from '../../hooks/useApi'
import GlassCard from '../../components/ui/GlassCard'
import Badge from '../../components/ui/Badge'
import AsyncState from '../../components/ui/AsyncState'

/**
 * Blind Spots — what the system does not know about you, and which kind of
 * not-knowing it is.
 *
 * The uncertainty map has existed since the original schema. It is stored for
 * every user, indexed, read into the character runtime, consulted by the
 * decision engine and injected into the context the language model sees. It
 * was never once shown to the person it described.
 *
 * It also conflated two different claims. A topic the system had reasoned
 * about and found itself unsure of got a measured uncertainty; a topic no
 * belief addressed at all got a flat 0.8 and went into the same dictionary in
 * the same scale. Across the deployed instance 19 of 50 domain values were
 * that constant, and they reached the language model as confident statements
 * of doubt about subjects nothing had ever been concluded about.
 *
 * The page is ordered by how uncomfortable the answer is. "There is data here
 * and no opinion" comes first, because it is the finding a user can act on and
 * the one a product is least inclined to volunteer. Numbers come after, and
 * never without the beliefs that produced them.
 */

function Section({ title, blurb, children, tone = 'slate' }) {
  return (
    <div style={{ marginBottom: 22 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
        <h2 style={{ fontSize: 17, fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
          {title}
        </h2>
        <Badge variant={tone}>{tone === 'rose' ? 'no opinion' : tone === 'amber' ? 'weak' : 'settled'}</Badge>
      </div>
      <p style={{ fontSize: 13, color: 'var(--text-tertiary)', margin: '0 0 12px', maxWidth: 720, lineHeight: 1.6 }}>
        {blurb}
      </p>
      {children}
    </div>
  )
}

function DomainRow({ item }) {
  const pct = Math.round(item.uncertainty * 100)
  const colour = item.poorly_understood ? '#fbbf24' : '#34d399'

  return (
    <GlassCard style={{ marginBottom: 10 }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, flexWrap: 'wrap' }}>
        <span style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)' }}>
          {item.domain}
        </span>
        <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
          {item.belief_count} belief{item.belief_count === 1 ? '' : 's'}
        </span>
        <span style={{ marginLeft: 'auto', fontSize: 19, fontWeight: 800, color: colour }}>
          {pct}%
        </span>
      </div>

      <div style={{ height: 6, borderRadius: 999, marginTop: 8, background: 'rgba(148,163,184,0.14)', overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: colour }} />
      </div>

      {item.beliefs?.length > 0 && (
        <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 5 }}>
          {item.beliefs.map((b, i) => (
            <div key={i} style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'flex', gap: 8 }}>
              <span style={{ flex: 1, minWidth: 0 }}>{b.statement}</span>
              {b.contested && <Badge variant="rose">contested</Badge>}
            </div>
          ))}
        </div>
      )}
    </GlassCard>
  )
}

export default function BlindSpotsPage() {
  const { data, loading, error, refetch } = useApi(() => api.getBlindSpots(), [])

  const assessed = data?.assessed || []
  const unexamined = data?.unexamined || []
  const weak = assessed.filter((a) => a.poorly_understood)
  const settled = assessed.filter((a) => !a.poorly_understood)
  const cov = data?.coverage

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 className="gradient-text" style={{ fontSize: 32, fontWeight: 800, letterSpacing: '-0.03em', marginBottom: 6 }}>
          Blind Spots
        </h1>
        <p style={{ color: 'var(--text-tertiary)', fontSize: 15, maxWidth: 760 }}>
          What this system does not know about you. Having no opinion about a subject
          and being unsure about it are different things, and they are kept apart here.
        </p>
      </div>

      <AsyncState loading={loading} error={error} onRetry={refetch}>
        {!data?.measurable ? (
          <GlassCard gradient>
            <Badge variant="slate">Nothing to report yet</Badge>
            <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginTop: 10, lineHeight: 1.6 }}>
              {data?.note}
            </p>
          </GlassCard>
        ) : (
          <>
            {data.stale_model && (
              <GlassCard style={{ marginBottom: 16, borderColor: 'rgba(251,191,36,0.35)' }}>
                <Badge variant="amber">Built before this distinction existed</Badge>
                <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 8, lineHeight: 1.6 }}>
                  {data.note}
                </p>
              </GlassCard>
            )}

            <GlassCard gradient style={{ marginBottom: 20 }}>
              <div style={{ display: 'flex', gap: 28, flexWrap: 'wrap', alignItems: 'baseline' }}>
                <div>
                  <div style={{ fontSize: 26, fontWeight: 800, color: '#a5b4fc' }}>
                    {cov.assessed}<span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>&thinsp;/&thinsp;{cov.topics}</span>
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>topics it has a view on</div>
                </div>
                <div>
                  <div style={{ fontSize: 26, fontWeight: 800, color: unexamined.length ? '#fb7185' : '#34d399' }}>
                    {cov.unexamined}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>with no opinion at all</div>
                </div>
                <div>
                  <div style={{ fontSize: 26, fontWeight: 800, color: 'var(--text-secondary)' }}>
                    {data.contested_beliefs}<span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>&thinsp;/&thinsp;{data.belief_count}</span>
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                    beliefs its own evidence disputes
                  </div>
                </div>
                {!data.stale_model && (
                  <div style={{ flex: '1 1 260px', fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                    {data.note}
                  </div>
                )}
              </div>
            </GlassCard>

            {unexamined.length > 0 && (
              <Section
                tone="rose"
                title="It has nothing to say about these"
                blurb="These subjects appear in your activity, but no belief the system holds
                       addresses them. This is not a low-confidence reading — it is the absence
                       of one, and it is reported as such rather than as a number nobody measured."
              >
                <GlassCard>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    {unexamined.map((d) => (
                      <span
                        key={d}
                        style={{
                          padding: '5px 11px', borderRadius: 999, fontSize: 13,
                          border: '1px solid rgba(251,113,133,0.35)',
                          background: 'rgba(251,113,133,0.08)',
                          color: 'var(--text-secondary)',
                        }}
                      >
                        {d}
                      </span>
                    ))}
                  </div>
                </GlassCard>
              </Section>
            )}

            {weak.length > 0 && (
              <Section
                tone="amber"
                title="It is unsure about these"
                blurb="Beliefs exist here and they are weak. This is a measurement, taken from
                       the confidence of the beliefs that mention each subject — which are shown
                       underneath, because a number without its basis is not an explanation."
              >
                {weak.map((a) => <DomainRow key={a.domain} item={a} />)}
              </Section>
            )}

            {settled.length > 0 && (
              <Section
                tone="slate"
                title="It is reasonably confident about these"
                blurb="Low measured uncertainty. Confidence is not correctness — the Accuracy
                       Ledger scores these claims against your own verdicts, and Contested
                       Claims shows where the underlying evidence disagrees with itself."
              >
                {settled.map((a) => <DomainRow key={a.domain} item={a} />)}
              </Section>
            )}

            <p style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.7, marginTop: 18 }}>
              Related:{' '}
              <Link to="/contested" style={{ color: '#a5b4fc' }}>Contested Claims</Link>{' '}
              for beliefs whose own evidence argues against them, and{' '}
              <Link to="/calibration" style={{ color: '#a5b4fc' }}>the Accuracy Ledger</Link>{' '}
              for how often confident claims turn out to be right.
            </p>
          </>
        )}
      </AsyncState>
    </div>
  )
}
