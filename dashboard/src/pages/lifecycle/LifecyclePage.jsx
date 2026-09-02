import { api } from '../../api/client'
import { useApi } from '../../hooks/useApi'
import GlassCard from '../../components/ui/GlassCard'
import Badge from '../../components/ui/Badge'
import AsyncState from '../../components/ui/AsyncState'

/**
 * Moved On — what someone is still doing, and what they have drifted out of.
 *
 * The lifecycle is one of the architecture's stated contributions and it had
 * never worked. Every one of 226 behaviour objects on the deployed instance
 * was growing or emerging; stable, declining, dormant and archived had not once
 * occurred in the product's history. State was written only when a topic turned
 * up in an ingest batch, and a topic somebody has abandoned never turns up
 * again, so the code that would have retired it could not run. Ninety-six
 * behaviours unseen for over a month were still growing, the oldest last seen
 * 600 days earlier.
 *
 * With state evaluated as of now, the more interesting half of a watch history
 * becomes visible: not what someone is into, which every recommender already
 * claims to know, but what they have let go of. A feed has no commercial reason
 * to tell anyone that.
 *
 * Every row carries its reason. "You have moved on from this" is a claim about
 * someone's life, and the page should be able to say on what basis.
 */

const TONE = {
  emerging: { colour: '#22d3ee', label: 'new' },
  growing: { colour: '#34d399', label: 'building' },
  stable: { colour: '#a3e635', label: 'steady' },
  declining: { colour: '#fbbf24', label: 'tailing off' },
  dormant: { colour: '#fb7185', label: 'gone quiet' },
  archived: { colour: '#94a3b8', label: 'long past' },
}

function Row({ item }) {
  const tone = TONE[item.state] || TONE.stable
  const gap = item.days_since_last_seen

  return (
    <GlassCard style={{ marginBottom: 10 }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, flexWrap: 'wrap' }}>
        <span style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)' }}>
          {item.topic}
        </span>
        <span style={{
          padding: '2px 9px', borderRadius: 999, fontSize: 11, fontWeight: 600,
          color: tone.colour, border: `1px solid ${tone.colour}55`,
          background: `${tone.colour}14`,
        }}>
          {tone.label}
        </span>
        <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
          {item.occurrences} time{item.occurrences === 1 ? '' : 's'}
        </span>
        {gap != null && (
          <span style={{ marginLeft: 'auto', fontSize: 13, fontWeight: 700, color: tone.colour }}>
            {gap < 1 ? 'today' : `${Math.round(gap)}d ago`}
          </span>
        )}
      </div>
      {item.basis && (
        <p style={{ fontSize: 12, color: 'var(--text-tertiary)', margin: '8px 0 0', lineHeight: 1.6 }}>
          {item.basis}
        </p>
      )}
    </GlassCard>
  )
}

function Group({ title, blurb, items }) {
  if (!items?.length) return null
  return (
    <div style={{ marginBottom: 24 }}>
      <h2 style={{ fontSize: 17, fontWeight: 700, color: 'var(--text-primary)', margin: '0 0 6px' }}>
        {title} <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>({items.length})</span>
      </h2>
      <p style={{ fontSize: 13, color: 'var(--text-tertiary)', margin: '0 0 12px', maxWidth: 720, lineHeight: 1.6 }}>
        {blurb}
      </p>
      {items.map((it) => <Row key={it.topic} item={it} />)}
    </div>
  )
}

export default function LifecyclePage() {
  const { data, loading, error, refetch } = useApi(() => api.getLifecycle(), [])

  const counts = data?.counts || {}
  const pastCount = (counts.dormant || 0) + (counts.archived || 0)

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 className="gradient-text" style={{ fontSize: 32, fontWeight: 800, letterSpacing: '-0.03em', marginBottom: 6 }}>
          Moved On
        </h1>
        <p style={{ color: 'var(--text-tertiary)', fontSize: 15, maxWidth: 760 }}>
          What you are still watching, what is tailing off, and what you have set aside.
          A subject counts as past when the silence is long against the rhythm it used to
          keep — not against a fixed number of days.
        </p>
      </div>

      <AsyncState loading={loading} error={error} onRetry={refetch}>
        {!data?.measurable ? (
          <GlassCard gradient>
            <Badge variant="slate">Nothing to show yet</Badge>
            <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginTop: 10, lineHeight: 1.6 }}>
              {data?.note}
            </p>
          </GlassCard>
        ) : (
          <>
            <GlassCard gradient style={{ marginBottom: 20 }}>
              <div style={{ display: 'flex', gap: 26, flexWrap: 'wrap', alignItems: 'baseline' }}>
                <div>
                  <div style={{ fontSize: 26, fontWeight: 800, color: '#34d399' }}>
                    {data.current?.length || 0}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>still current</div>
                </div>
                <div>
                  <div style={{ fontSize: 26, fontWeight: 800, color: '#fbbf24' }}>
                    {data.fading?.length || 0}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>tailing off</div>
                </div>
                <div>
                  <div style={{ fontSize: 26, fontWeight: 800, color: '#fb7185' }}>
                    {pastCount}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>set aside</div>
                </div>
                <div style={{ flex: '1 1 280px', fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                  {data.note}
                </div>
              </div>
            </GlassCard>

            <Group
              title="Still current"
              blurb="Seen recently enough, relative to how often this subject usually appears."
              items={data.current}
            />

            <Group
              title="Tailing off"
              blurb="Still present, but most of the activity sits in the earlier half of this
                     subject's life rather than the recent half."
              items={data.fading}
            />

            <Group
              title="Set aside"
              blurb="Quiet for long enough, against the rhythm this subject used to keep, that
                     the system no longer treats it as something you are doing. It is kept
                     rather than deleted, because having moved on from something is itself
                     part of the picture."
              items={data.past}
            />
          </>
        )}
      </AsyncState>
    </div>
  )
}
