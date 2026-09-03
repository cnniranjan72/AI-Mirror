import { useState } from 'react'
import { api } from '../../api/client'
import { useApi } from '../../hooks/useApi'
import GlassCard from '../../components/ui/GlassCard'
import Badge from '../../components/ui/Badge'
import AsyncState from '../../components/ui/AsyncState'

/**
 * Contested Claims — what this system's own evidence argues against.
 *
 * Every other page here shows the product's conclusions. This one shows where
 * they are weakest, which is the only version of "transparent" that costs
 * anything to publish.
 *
 * The mechanism behind it existed on paper for a long time and produced
 * nothing: four fields on the evidence model, database columns, an index, a
 * write path, a read path and a consumer, with no stage that ever filled them
 * in. Across the stored evidence in the deployed instance all four were
 * populated exactly zero times, so every belief came out with a net evidence
 * strength of precisely 1.0 and the uncertainty this product claims to track
 * never once fired.
 *
 * Worse, skipping was being counted as interest: the collectors filtered
 * events by topic and filed all of them as supporting, so scrolling past four
 * hundred cooking reels produced strong evidence of interest in cooking.
 *
 * Two decisions carry this page. Claims are ordered by how contested they are
 * rather than how confident, because a confident claim with a third of its
 * evidence pointing the other way deserves attention more than a tentative one
 * nobody disputes — and every other surface already sorts by confidence. And
 * each claim can name the specific content behind the disagreement, because a
 * page that says "18 of 63 observations argue against this" without showing
 * the eighteen is asking to be trusted about being untrustworthy.
 */

function shareColour(share) {
  if (share >= 0.5) return '#fb7185'
  if (share >= 0.25) return '#fbbf24'
  return '#34d399'
}

function Claim({ claim }) {
  const [open, setOpen] = useState(false)
  const colour = shareColour(claim.contradicted_share)
  const supportedShare = claim.observed ? claim.supported / claim.observed : 0

  return (
    <GlassCard style={{ marginBottom: 12 }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, flexWrap: 'wrap' }}>
        <span style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-primary)' }}>
          {claim.subject}
        </span>
        <Badge variant="slate">{claim.kind}</Badge>
        <span style={{ marginLeft: 'auto', fontSize: 20, fontWeight: 800, color: colour }}>
          {Math.round(claim.contradicted_share * 100)}%
        </span>
      </div>

      <p style={{ fontSize: 13, color: 'var(--text-secondary)', margin: '8px 0 12px', lineHeight: 1.6 }}>
        {claim.explanation}
      </p>

      {/* Supported against contradicted, in proportion. The bar is the claim:
          how much of what was seen actually backs it up. */}
      <div style={{ display: 'flex', height: 8, borderRadius: 999, overflow: 'hidden', background: 'rgba(148,163,184,0.14)' }}>
        <div style={{ width: `${supportedShare * 100}%`, background: '#34d399' }} />
        <div style={{ width: `${claim.contradicted_share * 100}%`, background: colour }} />
      </div>

      <div style={{ display: 'flex', gap: 22, flexWrap: 'wrap', marginTop: 12 }}>
        <div>
          <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)' }}>
            {claim.supported} <span style={{ fontWeight: 400, color: 'var(--text-muted)' }}>watched</span>
          </div>
        </div>
        <div>
          <div style={{ fontSize: 15, fontWeight: 700, color: colour }}>
            {claim.contradicted} <span style={{ fontWeight: 400, color: 'var(--text-muted)' }}>skipped</span>
          </div>
        </div>
        <div>
          <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-secondary)' }}>
            {claim.confidence.toFixed(2)}
            {claim.net_confidence !== null && claim.net_confidence !== undefined && (
              <>
                <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>&nbsp;&rarr;&nbsp;</span>
                {claim.net_confidence.toFixed(2)}
              </>
            )}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
            confidence after counter-evidence
          </div>
        </div>
      </div>

      {claim.note && (
        <p style={{ fontSize: 12, color: 'var(--text-tertiary)', marginTop: 12, lineHeight: 1.6 }}>
          {claim.note}
        </p>
      )}

      {claim.examples?.length > 0 && (
        <>
          <button
            onClick={() => setOpen(!open)}
            style={{
              marginTop: 10, padding: '5px 11px', borderRadius: 8, cursor: 'pointer',
              fontSize: 12, background: 'transparent', color: 'var(--text-secondary)',
              border: '1px solid var(--border-subtle)',
            }}
          >
            {open ? 'Hide' : 'Show'} what was skipped
          </button>

          {open && (
            <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 6 }}>
              {claim.examples.map((ex, i) => (
                <div
                  key={i}
                  style={{
                    display: 'flex', gap: 10, alignItems: 'baseline',
                    padding: '7px 10px', borderRadius: 8,
                    background: 'rgba(148,163,184,0.07)', fontSize: 12,
                  }}
                >
                  <span style={{ color: 'var(--text-secondary)', flex: 1, minWidth: 0 }}>
                    {ex.caption || 'untitled'}
                  </span>
                  {ex.creator && (
                    <span style={{ color: 'var(--text-muted)' }}>{ex.creator}</span>
                  )}
                  <span style={{ color: colour, fontWeight: 700, whiteSpace: 'nowrap' }}>
                    {ex.watch_time}s
                  </span>
                </div>
              ))}
              {claim.contradicted > claim.examples.length && (
                <p style={{ fontSize: 11, color: 'var(--text-muted)', margin: '2px 0 0' }}>
                  Showing {claim.examples.length} of {claim.contradicted}. The count above is
                  the full one.
                </p>
              )}
            </div>
          )}
        </>
      )}
    </GlassCard>
  )
}

export default function ContestedPage() {
  const { data, loading, error, refetch } = useApi(() => api.getContestedClaims(), [])

  const claims = data?.claims || []
  const summary = data?.summary

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 className="gradient-text" style={{ fontSize: 32, fontWeight: 800, letterSpacing: '-0.03em', marginBottom: 6 }}>
          Contested Claims
        </h1>
        <p style={{ color: 'var(--text-tertiary)', fontSize: 15, maxWidth: 760 }}>
          Where this system's own evidence argues against its own conclusions. Content
          you scrolled straight past is counted against the claim it belongs to rather
          than for it, and the claims that lose most are listed first.
        </p>
      </div>

      <AsyncState loading={loading} error={error} onRetry={refetch}>
        {!data?.measurable ? (
          <GlassCard gradient>
            <Badge variant="slate">Nothing to weigh yet</Badge>
            <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginTop: 10, lineHeight: 1.6 }}>
              {data?.note}
            </p>
          </GlassCard>
        ) : (
          <>
            {/* Evidence written before the counter-evidence producer existed
                carries no attended/skipped split. Every one of the 341 rows on
                the deployed instance was such a row, and this page was telling
                those accounts that "every observation behind every claim was
                actually watched" - a confident statement about a check that had
                never run. Not finding a contradiction and not having looked are
                different things. */}
            {data.unchecked > 0 && (
              <GlassCard style={{ marginBottom: 16, borderColor: 'rgba(251,191,36,0.4)' }}>
                <Badge variant="amber">
                  {data.stale_evidence ? 'Not yet checked' : 'Partly checked'}
                </Badge>
                <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 8, lineHeight: 1.6 }}>
                  {data.note}
                </p>
              </GlassCard>
            )}

            <GlassCard gradient style={{ marginBottom: 16 }}>
              <div style={{ display: 'flex', gap: 28, flexWrap: 'wrap', alignItems: 'baseline' }}>
                <div>
                  <div style={{ fontSize: 26, fontWeight: 800, color: shareColour(summary.contradicting_share) }}>
                    {Math.round(summary.contradicting_share * 100)}%
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                    {data.stale_evidence
                      ? 'of observations — not yet measured'
                      : 'of observations argue against'}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 26, fontWeight: 800, color: 'var(--text-secondary)' }}>
                    {summary.claims_contested}
                    <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>
                      &thinsp;/&thinsp;{summary.claims_examined}
                    </span>
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>claims contested</div>
                </div>
                {data.unchecked === 0 && (
                  <div style={{ flex: '1 1 280px', fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                    {data.note}
                  </div>
                )}
              </div>
            </GlassCard>

            {claims.length === 0 ? (
              <GlassCard>
                <Badge variant={data.stale_evidence ? 'slate' : 'emerald'}>
                  {data.stale_evidence ? 'Nothing checked yet' : 'Nothing contested'}
                </Badge>
                <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginTop: 10, lineHeight: 1.6 }}>
                  {data.stale_evidence
                    ? `These claims were recorded before the system began weighing skipped
                       content against them, so no contradiction has been looked for. The
                       next time this account ingests activity they will be reconsidered.`
                    : `Every observation behind every claim was actually watched. That is a
                       real result rather than a default: an account that skips nothing
                       produces no counter-evidence, and this page would say so either way.`}
                </p>
              </GlassCard>
            ) : (
              claims.map((c) => <Claim key={c.evidence_id} claim={c} />)
            )}
          </>
        )}
      </AsyncState>
    </div>
  )
}
