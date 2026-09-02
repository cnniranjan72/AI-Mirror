import { useState } from 'react'
import { api } from '../../api/client'
import GlassCard from '../../components/ui/GlassCard'
import Badge from '../../components/ui/Badge'
import Reveal from '../../components/motion/Reveal'

/**
 * What would change its mind?
 *
 * The only question here that a language-model-driven system could not answer
 * honestly. Because every stage before verbalization is deterministic, the
 * pipeline can be re-run over a hypothetical history and the difference in the
 * output is caused by the difference in the input and nothing else. Ask a
 * stochastic model the same thing twice and the answers differ for reasons that
 * have nothing to do with the hypothetical.
 *
 * The scenarios are deliberately extreme. A subtle one produces a movement too
 * small to read against normal variation, and the useful thing to learn is
 * which measures are sensitive and roughly how much it takes to move them —
 * not to model a plausible next month.
 *
 * Every screen states that nothing was saved, because the honest version of
 * this feature is one where asking the question cannot answer it.
 */

const SCENARIOS = [
  {
    id: 'entertainment',
    label: 'Switch to short entertainment',
    blurb: '80 comedy and meme clips, a few seconds each, from creators you do not watch',
    build: () => make(80, ['comedy', 'memes', 'pranks'],
      ['laughs_daily', 'meme_lord', 'prank_central'], 4),
  },
  {
    id: 'study',
    label: 'Switch to long-form study',
    blurb: '60 tutorials and lectures, several minutes each',
    build: () => make(60, ['machine learning', 'compilers', 'statistics'],
      ['ai_daily', 'systems_deep', 'stats_prof'], 220),
  },
  {
    id: 'one_creator',
    label: 'Watch one creator only',
    blurb: '70 clips from a single account, nothing else',
    build: () => make(70, ['daily vlog'], ['single_channel'], 60),
  },
  {
    id: 'broaden',
    label: 'Spread out wildly',
    blurb: '90 clips across nine unrelated topics and nine creators',
    build: () => make(90,
      ['cooking', 'chess', 'gardening', 'astronomy', 'boxing',
       'pottery', 'finance', 'hiking', 'jazz'],
      ['chef_a', 'gm_b', 'grow_c', 'space_d', 'ring_e',
       'clay_f', 'money_g', 'trail_h', 'horn_i'], 45),
  },
]

function make(n, topics, creators, watch) {
  return Array.from({ length: n }, (_, i) => ({
    reel_id: `cf_${i}`,
    username: creators[i % creators.length],
    caption: `${topics[i % topics.length]}: clip ${i}`,
    hashtags: [`#${topics[i % topics.length].split(' ')[0]}`],
    watch_time: watch,
    platform: 'instagram',
  }))
}

export default function CounterfactualPage() {
  const [running, setRunning] = useState(null)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const run = async (scenario) => {
    setRunning(scenario.id); setError(null); setResult(null)
    try {
      const r = await api.runCounterfactual(scenario.build())
      setResult({ ...r, scenario })
    } catch (e) {
      setError(e?.response?.data?.detail || 'The hypothetical run failed.')
    } finally {
      setRunning(null)
    }
  }

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 className="gradient-text" style={{ fontSize: 32, fontWeight: 800, letterSpacing: '-0.03em', marginBottom: 6 }}>
          What would change its mind?
        </h1>
        <p style={{ color: 'var(--text-tertiary)', fontSize: 15, maxWidth: 740 }}>
          Pick something you did not do. The system re-runs its reasoning over your real
          history plus that, and reports what it would then believe. Nothing is saved —
          asking the question cannot answer it.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 12, marginBottom: 22 }}>
        {SCENARIOS.map(s => (
          <button
            key={s.id}
            onClick={() => run(s)}
            disabled={running !== null}
            style={{
              textAlign: 'left', padding: '14px 16px', borderRadius: 12,
              border: `1px solid ${result?.scenario?.id === s.id ? 'rgba(99,102,241,0.45)' : 'var(--border-subtle)'}`,
              background: result?.scenario?.id === s.id ? 'rgba(99,102,241,0.10)' : 'rgba(148,163,184,0.04)',
              cursor: running ? 'wait' : 'pointer', color: 'inherit',
            }}
          >
            <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 4 }}>
              {running === s.id ? 'Running…' : s.label}
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.5 }}>{s.blurb}</div>
          </button>
        ))}
      </div>

      {error && (
        <GlassCard><div style={{ fontSize: 13, color: '#f87171' }}>{error}</div></GlassCard>
      )}

      {result && !result.measurable && (
        <GlassCard gradient>
          <Badge variant="slate">Nothing to compare</Badge>
          <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginTop: 10, lineHeight: 1.6 }}>
            {result.note}
          </p>
        </GlassCard>
      )}

      {result?.measurable && (
        <>
          <Reveal>
            <GlassCard gradient style={{ marginBottom: 18 }}>
              <div style={{ display: 'flex', gap: 28, flexWrap: 'wrap', alignItems: 'baseline', marginBottom: 12 }}>
                <div>
                  <div style={{ fontSize: 30, fontWeight: 800, color: '#a5b4fc' }}>
                    {result.shift?.toFixed(3)}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                    how far it would move you
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 30, fontWeight: 800, color: 'var(--text-secondary)' }}>
                    {result.snapshot_threshold}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                    the line for recording a new version of you
                  </div>
                </div>
                <div style={{ flex: '1 1 220px' }}>
                  <Badge variant={result.would_warrant_snapshot ? 'amber' : 'emerald'}>
                    {result.would_warrant_snapshot
                      ? 'enough to rewrite your profile'
                      : 'not enough to rewrite your profile'}
                  </Badge>
                </div>
              </div>
              <p style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.6 }}>
                {result.added_events} hypothetical events, replayed alongside{' '}
                {result.real_events_replayed} of your real ones. {result.note}
              </p>
            </GlassCard>
          </Reveal>

          <Reveal delay={0.05}>
            <GlassCard>
              <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 4 }}>What would move</h3>
              <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16 }}>
                {result.moves.length} of the seventeen measures would change;{' '}
                {result.unchanged} would stay where they are.
              </p>
              {result.moves.length === 0 ? (
                <p style={{ fontSize: 13, color: 'var(--text-tertiary)' }}>
                  Nothing would move measurably. The model of you is not sensitive to this.
                </p>
              ) : result.moves.map(m => (
                <div key={m.dimension} style={{
                  display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap',
                  padding: '10px 0', borderTop: '1px solid var(--border-subtle)',
                }}>
                  <div style={{ flex: '1 1 220px', minWidth: 0 }}>
                    <div style={{ fontSize: 14, fontWeight: 600 }}>{m.dimension}</div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{m.meaning}</div>
                  </div>
                  <div style={{ fontSize: 12, fontFamily: 'var(--font-mono)', color: 'var(--text-tertiary)' }}>
                    {m.from.toFixed(2)} → {m.to.toFixed(2)}
                  </div>
                  <Badge variant={m.delta > 0 ? 'emerald' : 'amber'}>
                    {m.delta > 0 ? '+' : ''}{m.delta.toFixed(2)}
                  </Badge>
                </div>
              ))}
            </GlassCard>
          </Reveal>
        </>
      )}
    </div>
  )
}
