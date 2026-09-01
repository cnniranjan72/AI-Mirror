import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../api/client'
import { useApi } from '../../hooks/useApi'
import GlassCard from '../../components/ui/GlassCard'
import Badge from '../../components/ui/Badge'
import Reveal from '../../components/motion/Reveal'
import CountUp from '../../components/motion/CountUp'
import { AlertIcon, CheckIcon, TargetIcon } from '../../icons/icons'

/**
 * The Algorithmic Mirror.
 *
 * Both Meta and Google already let you SEE the interests they target you on.
 * What none of them let you do is check whether those interests are true —
 * that requires an independent, evidence-based model of the same person, which
 * is what the pipeline produces.
 *
 * The design job here is restraint. It would be trivial to render this as
 * "the platform is wrong about you 68% of the time", and that number would be
 * dishonest: this only ever compares against the history the user imported.
 * So the caveats are not fine print at the bottom, the untestable claims get
 * their own bucket instead of being counted as failures, and below a coverage
 * floor the page leads with "not enough data to judge" rather than a verdict.
 */

const VERDICTS = {
  corroborated: {
    label: 'Corroborated',
    blurb: 'Your behaviour supports this.',
    color: 'var(--emerald-400)',
    variant: 'emerald',
  },
  unsupported: {
    label: 'Unsupported by your data',
    blurb: 'Nothing in the history you imported supports this claim.',
    color: 'var(--amber-400)',
    variant: 'amber',
  },
  not_comparable: {
    label: 'Not testable',
    blurb: 'Demographic or life-event inferences a watch history cannot check.',
    color: 'var(--text-muted)',
    variant: 'neutral',
  },
  missed: {
    label: 'Missing from their profile',
    blurb: "Well-evidenced interests the platform doesn't target you on.",
    color: 'var(--cyan-400)',
    variant: 'indigo',
  },
}

function Bucket({ kind, count, children }) {
  const meta = VERDICTS[kind]
  return (
    <GlassCard gradient style={{ marginBottom: 22 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', gap: 16, marginBottom: 16, flexWrap: 'wrap' }}>
        <div>
          <h3 style={{ fontSize: 17, fontWeight: 700, marginBottom: 4, color: meta.color }}>
            {meta.label}
          </h3>
          <div style={{ fontSize: 12.5, color: 'var(--text-muted)' }}>{meta.blurb}</div>
        </div>
        <Badge variant={meta.variant}>{count}</Badge>
      </div>
      {children}
    </GlassCard>
  )
}

function Row({ children, accent }) {
  return (
    <div style={{
      padding: '12px 14px', borderRadius: 10, marginBottom: 8,
      background: 'rgba(148,163,184,0.05)',
      borderLeft: `2px solid ${accent || 'transparent'}`,
    }}>
      {children}
    </div>
  )
}

export default function MirrorPage() {
  const navigate = useNavigate()
  const { data, loading, error } = useApi(() => api.getMirrorReport())

  const summary = data?.summary || {}
  const share = summary.supported_share

  const headline = useMemo(() => {
    if (!data) return null
    if (!data.claims_total) return null
    if (!data.verdict_reliable) {
      return {
        text: 'Not enough of your history to judge this profile yet',
        tone: 'var(--amber-400)',
      }
    }
    if (share == null) return null
    return {
      text: `${Math.round(share * 100)}% of testable claims are supported by your behaviour`,
      tone: share >= 0.6 ? 'var(--emerald-400)' : 'var(--amber-400)',
    }
  }, [data, share])

  return (
    <div>
      <Reveal variant="depth">
        <div style={{ marginBottom: 28 }}>
          <h1 className="gradient-text" style={{ fontSize: 34, fontWeight: 800, marginBottom: 6 }}>
            Algorithmic Mirror
          </h1>
          <p style={{ color: 'var(--text-tertiary)', fontSize: 15, maxWidth: 720, lineHeight: 1.6 }}>
            What the platform says you're interested in, checked against what you
            actually did. Their claims come from your own data export; the evidence
            comes from your behaviour.
          </p>
        </div>
      </Reveal>

      {loading && (
        <GlassCard><div style={{ padding: 28, color: 'var(--text-muted)' }}>Comparing profiles…</div></GlassCard>
      )}

      {error && (
        <GlassCard>
          <div className="empty-state">
            <div className="empty-state-icon">⚠️</div>
            <div className="empty-state-title">Couldn't load the comparison</div>
            <div className="empty-state-description">{String(error)}</div>
          </div>
        </GlassCard>
      )}

      {/* Nothing to compare against yet — this is the normal first-run state,
          and it has to explain how to get the data rather than look broken. */}
      {!loading && !error && data && !data.claims_total && (
        <Reveal variant="depth">
          <GlassCard gradient>
            <div style={{ padding: '28px 8px', textAlign: 'center' }}>
              <div style={{ fontSize: 40, marginBottom: 14 }}>🪞</div>
              <h3 style={{ fontSize: 19, fontWeight: 700, marginBottom: 10 }}>
                No platform profile imported yet
              </h3>
              <p style={{ fontSize: 14, color: 'var(--text-tertiary)', lineHeight: 1.7, maxWidth: 560, margin: '0 auto 20px' }}>
                To audit a platform's profile of you, AIMirror needs the list of interests
                it targets you on. That list ships inside your own data export — Instagram's
                under <em>Ads information</em>, Google's under <em>My Ad Center</em>. Import
                the export and this page fills itself in.
              </p>
              <button
                onClick={() => navigate('/import')}
                className="btn-3d btn-aurora"
                style={{ padding: '12px 24px', borderRadius: 12, border: 'none', color: 'white', fontSize: 14, fontWeight: 700, cursor: 'pointer' }}
              >
                Import a data export →
              </button>
            </div>
          </GlassCard>
        </Reveal>
      )}

      {!loading && !error && data && data.claims_total > 0 && (
        <>
          <Reveal variant="depth">
            <GlassCard gradient style={{ marginBottom: 22 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 18, flexWrap: 'wrap' }}>
                <div style={{ color: headline?.tone, display: 'flex', alignItems: 'center', gap: 12 }}>
                  {data.verdict_reliable ? <TargetIcon /> : <AlertIcon />}
                  <span style={{ fontSize: 20, fontWeight: 700, lineHeight: 1.3 }}>
                    {headline?.text}
                  </span>
                </div>
              </div>

              <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginTop: 16 }}>
                <Badge variant="neutral">{data.claims_total} claims imported</Badge>
                <Badge variant="emerald">{summary.corroborated} corroborated</Badge>
                <Badge variant="amber">{summary.unsupported} unsupported</Badge>
                <Badge variant="neutral">{summary.not_comparable} not testable</Badge>
                {data.coverage != null && (
                  <Badge variant="indigo">
                    <CountUp value={`${Math.round(data.coverage * 100)}%`} /> data coverage
                  </Badge>
                )}
              </div>

              {/* Caveats sit directly under the headline, not in a footer.
                  A number this provocative has to carry its limits with it. */}
              <ul style={{ margin: '18px 0 0', paddingLeft: 18, display: 'grid', gap: 8 }}>
                {(data.caveats || []).map((caveat, i) => (
                  <li key={i} style={{ fontSize: 12.5, color: 'var(--text-muted)', lineHeight: 1.65 }}>
                    {caveat}
                  </li>
                ))}
              </ul>
            </GlassCard>
          </Reveal>

          <Reveal variant="depth">
            <Bucket kind="corroborated" count={summary.corroborated || 0}>
              {(data.corroborated || []).length === 0
                ? <div style={{ color: 'var(--text-muted)', fontSize: 13.5, padding: '8px 0' }}>
                    None of their claims are supported by your imported history.
                  </div>
                : data.corroborated.map((c, i) => (
                    <Row key={i} accent="var(--emerald-400)">
                      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', marginBottom: 4 }}>
                        <span style={{ fontSize: 14, fontWeight: 600 }}>{c.label}</span>
                        <span style={{ display: 'inline-flex', gap: 8, alignItems: 'center' }}>
                          <Badge variant="emerald">{c.evidence.observations} observations</Badge>
                          <Badge variant="neutral">{c.platform}</Badge>
                        </span>
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                        matched your topic “{c.evidence.topic}” on: {c.evidence.matched_on.join(', ')}
                      </div>
                    </Row>
                  ))}
            </Bucket>
          </Reveal>

          <Reveal variant="depth">
            <Bucket kind="unsupported" count={summary.unsupported || 0}>
              {(data.unsupported || []).length === 0
                ? <div style={{ color: 'var(--text-muted)', fontSize: 13.5, padding: '8px 0' }}>
                    Every testable claim they make is supported.
                  </div>
                : data.unsupported.map((c, i) => (
                    <Row key={i} accent="var(--amber-400)">
                      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
                        <span style={{ fontSize: 14, fontWeight: 600 }}>{c.label}</span>
                        <Badge variant="neutral">{c.platform}</Badge>
                      </div>
                      {/* A near-miss is shown rather than hidden: the reader
                          should be able to disagree with the threshold. */}
                      {c.weak_match && (
                        <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
                          Closest match was “{c.weak_match.topic}” with only{' '}
                          {c.weak_match.observations} observation
                          {c.weak_match.observations === 1 ? '' : 's'} — too few to call it support.
                        </div>
                      )}
                    </Row>
                  ))}
            </Bucket>
          </Reveal>

          <Reveal variant="depth">
            <Bucket kind="missed" count={summary.missed || 0}>
              {(data.missed || []).length === 0
                ? <div style={{ color: 'var(--text-muted)', fontSize: 13.5, padding: '8px 0' }}>
                    Nothing well-evidenced is missing from their profile.
                  </div>
                : data.missed.map((m, i) => (
                    <Row key={i} accent="var(--cyan-400)">
                      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
                        <span style={{ fontSize: 14, fontWeight: 600 }}>{m.topic}</span>
                        <Badge variant="indigo">{m.observations} observations</Badge>
                      </div>
                    </Row>
                  ))}
            </Bucket>
          </Reveal>

          {(data.not_comparable || []).length > 0 && (
            <Reveal variant="depth">
              <Bucket kind="not_comparable" count={summary.not_comparable || 0}>
                <div style={{ fontSize: 12.5, color: 'var(--text-muted)', lineHeight: 1.65, marginBottom: 12 }}>
                  These are excluded from the score above. They may well be accurate —
                  a watch history simply has no way to test them, and counting them as
                  failures would inflate the headline number.
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {data.not_comparable.map((c, i) => (
                    <Badge key={i} variant="neutral">{c.label}</Badge>
                  ))}
                </div>
              </Bucket>
            </Reveal>
          )}

          <Reveal variant="depth">
            <GlassCard>
              <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 10 }}>How this is decided</h3>
              <div style={{ fontSize: 13, color: 'var(--text-tertiary)', lineHeight: 1.75, display: 'grid', gap: 10 }}>
                <p>
                  Their claims are imported verbatim from your export and stored separately
                  from your behaviour — they are never fed into the pipeline, so the model
                  doing the checking stays independent of the profile being checked.
                </p>
                <p>
                  A claim counts as corroborated only when it matches a topic with at least
                  three observations behind it; a single sighting is a coincidence, not
                  support. Every match shows the words it matched on, so you can judge it.
                </p>
                <p>
                  <strong>No language model is involved.</strong> Each verdict is a
                  deterministic comparison over cited evidence, which is what makes the
                  result auditable rather than an opinion.
                </p>
              </div>
            </GlassCard>
          </Reveal>
        </>
      )}
    </div>
  )
}
