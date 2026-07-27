import { useState } from 'react'
import GlassCard from '../../components/ui/GlassCard'
import Badge from '../../components/ui/Badge'
import CharacterCreature3D from '../../components/character/CharacterCreature3D'

const PIPELINE_STAGES = [
  { name: 'Behavior Gateway', desc: 'Normalizes events from any source (Chrome extension, dashboard, mobile) into one platform-neutral BehaviorEvent shape.' },
  { name: 'Content Intelligence', desc: 'Keyword-dictionary enrichment and text expansion on caption/hashtags/title — deterministic, no LLM.' },
  { name: 'Knowledge Consolidation', desc: 'Clusters events into Behavior Objects by topic and creator, tracking lifecycle state (emerging/growing/stable/declining).' },
  { name: 'Evidence', desc: 'Aggregates Behavior Objects into weighted, typed evidence with an explicit confidence and explanation.' },
  { name: 'Inference', desc: '8 deterministic rules (e.g. LearningMotivationRule, CreatorDependenceRule) turn evidence into labeled, confidence-scored inferences.' },
  { name: 'Reflection', desc: 'Periodic summaries synthesizing behavior objects, evidence, and inferences into a plain-language narrative.' },
  { name: 'Identity', desc: 'The full computational self-model: behavior/interest/creator profiles, attention/exploration/consistency/habit/motivation sub-profiles, dominant topics, confidence.' },
  { name: 'Snapshot', desc: 'An immutable, versioned freeze of Identity — the character reads from a Snapshot, never the live mutable Identity, so mid-conversation mutations can\'t corrupt an in-flight response.' },
  { name: 'Self Model', desc: 'Strong/uncertain beliefs derived from the snapshot, with their own confidence.' },
  { name: 'Runtime Builder', desc: 'Assembles the live CharacterCore + CharacterState — memory references, reasoning context, inference history — fresh on every query.' },
  { name: 'Planner → Retriever → Ranker → Fusion', desc: 'Detects intent, retrieves relevant memory, ranks by relevance, fuses into a coherent fact set with conflicts resolved.' },
  { name: 'Decision Engine', desc: 'Filters/prioritizes fused facts into what\'s actually worth saying.' },
  { name: 'Context Builder', desc: 'Assembles the final prompt context — facts, citations, directives.' },
  { name: 'LLM Verbalizer', desc: 'The ONLY place an LLM is used — turns the already-decided facts into natural language. It never reasons, infers, or decides; it translates.' },
]

const GLOSSARY = [
  { term: 'Behavior Object', def: 'A consolidated cluster of events sharing a topic or creator, with confidence/importance/stability scores that grow with real occurrence count (calibrated to realistic usage, not synthetic scale) and a lifecycle state.' },
  { term: 'Evidence', def: 'A typed, weighted claim about behavior, built from one or more Behavior Objects, with an explicit human-readable explanation.' },
  { term: 'Inference', def: 'A labeled conclusion (e.g. "Strong learning orientation") produced by one of 8 deterministic rule classes in backend/reasoning/rules.py, each with its own confidence calibration.' },
  { term: 'Identity', def: 'The live, versioned, mutable computational model of a user — everything from topic diversity to habit strength to motivation signals.' },
  { term: 'Identity Snapshot', def: 'An immutable, timestamped freeze of Identity at a point in time. Only created when the identity has shifted enough to clear the Eq.2 significance threshold — not on every single update.' },
  { term: 'Self Model', def: 'The subset of an Identity Snapshot expressed as beliefs ("strong" vs "uncertain") the character can reference about itself.' },
  { term: 'Character Core / State', def: 'The actual runtime object the chat talks through — assembled fresh per query by RuntimeBuilder from the latest snapshot, self-model, inferences, reflections, and memory references. Not a separate mock personality.' },
  { term: 'RL Policy', def: 'A real online contextual bandit (epsilon-greedy, Q-values per context/action pair) that learns which behavioral nudge helps in each state, updated by observed alignment change after every ingest — not a static heuristic.' },
  { term: 'Filter Bubble Score', def: 'creator_graph.dependence_score — how concentrated a user\'s attention is on a small set of creators, surfaced as a headline metric on the Behavior page.' },
  { term: 'Platform / Surface', def: 'Every event carries a platform ("instagram" | "youtube") and, for YouTube, a surface ("watch" | "shorts") — added when YouTube was integrated as a second ingestion source alongside the original Instagram-only extension.' },
]

function Section({ title, badge, children, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <GlassCard gradient style={{ marginBottom: 20 }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          width: '100%', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          background: 'none', border: 'none', cursor: 'pointer', padding: 0, marginBottom: open ? 16 : 0,
        }}
      >
        <h3 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)' }}>{title}</h3>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {badge}
          <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>{open ? '▲' : '▼'}</span>
        </div>
      </button>
      {open && children}
    </GlassCard>
  )
}

export default function DocumentationPage() {
  return (
    <div style={{ maxWidth: 980, margin: '0 auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 32 }}>
        <div style={{ width: 72, height: 72, flexShrink: 0, margin: '-10px 0' }}>
          <CharacterCreature3D size={72} variant="tome" confidence={0.7} showLabels={false} />
        </div>
        <div>
          <h1 className="gradient-text" style={{ fontSize: 32, fontWeight: 800, letterSpacing: '-0.03em', marginBottom: 6 }}>Documentation</h1>
          <p style={{ color: 'var(--text-tertiary)', fontSize: 15 }}>Architecture, concepts, and the explainability philosophy behind AIMirror</p>
        </div>
      </div>

      <Section title="Core Philosophy" badge={<Badge variant="indigo">read this first</Badge>}>
        <div style={{ fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.8 }}>
          <p style={{ marginBottom: 12 }}>
            <strong>Identity emerges from behavior, not from a prompt.</strong> Nothing about who you are
            in this system is written by an LLM. Topic clustering, creator affinity, motivation scoring,
            risk assessment, and reinforcement learning are all deterministic, rule-based code you can
            read in this repository.
          </p>
          <p style={{ marginBottom: 12 }}>
            <strong>The LLM is a verbalization layer, never the intelligence.</strong> By the time a query
            reaches the language model, every fact it will mention has already been decided by the
            deterministic pipeline. The LLM's only job is turning already-decided facts into readable
            prose — it is explicitly instructed not to invent follow-up questions or facts not provided
            to it.
          </p>
          <p>
            <strong>Everything must be explainable.</strong> Every score on every page cites its source —
            which table, which rule, which real event. The Explainability Panel (via "Why did the AI say
            this?" in Chat, or the Pipeline/Trace pages) shows the literal stage-by-stage execution that
            produced any given answer.
          </p>
        </div>
      </Section>

      <Section title="Cognitive Pipeline" badge={<Badge variant="neutral">{PIPELINE_STAGES.length} stages</Badge>}>
        <p style={{ fontSize: 13, color: 'var(--text-tertiary)', marginBottom: 16 }}>
          Every ingested event and every chat query flows through this chain, in order. See it running live on the{' '}
          <a href="/pipeline" style={{ color: '#818cf8' }}>Pipeline page</a>.
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {PIPELINE_STAGES.map((s, i) => (
            <div key={s.name} style={{ display: 'flex', gap: 12, padding: '10px 14px', borderRadius: 8, background: 'rgba(148,163,184,0.04)' }}>
              <div style={{
                width: 22, height: 22, borderRadius: '50%', flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: 'rgba(99,102,241,0.15)', color: '#a5b4fc', fontSize: 11, fontWeight: 700,
              }}>{i + 1}</div>
              <div>
                <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>{s.name}</div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.5, marginTop: 2 }}>{s.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </Section>

      <Section title="Glossary" badge={<Badge variant="neutral">{GLOSSARY.length} terms</Badge>}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {GLOSSARY.map(g => (
            <div key={g.term} style={{ paddingBottom: 12, borderBottom: '1px solid var(--border-subtle)' }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#a5b4fc', marginBottom: 4 }}>{g.term}</div>
              <div style={{ fontSize: 13, color: 'var(--text-tertiary)', lineHeight: 1.6 }}>{g.def}</div>
            </div>
          ))}
        </div>
      </Section>

      <Section title="Data Sources" badge={<Badge variant="neutral">2 platforms</Badge>}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <div style={{ padding: 16, borderRadius: 10, background: 'rgba(236,72,153,0.06)', border: '1px solid rgba(236,72,153,0.15)' }}>
            <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 6 }}>📸 Instagram Reels</div>
            <p style={{ fontSize: 12.5, color: 'var(--text-tertiary)', lineHeight: 1.6 }}>
              Chrome extension content script watches the viewport for the active Reel, extracts
              creator/caption/hashtags/audio/watch-time/engagement, and batches events to the backend.
            </p>
          </div>
          <div style={{ padding: 16, borderRadius: 10, background: 'rgba(244,63,94,0.06)', border: '1px solid rgba(244,63,94,0.15)' }}>
            <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 6 }}>▶️ YouTube (Watch + Shorts)</div>
            <p style={{ fontSize: 12.5, color: 'var(--text-tertiary)', lineHeight: 1.6 }}>
              A second content script tracks both long-form watch pages and Shorts. Metadata is read
              from YouTube's own embedded page data when fresh, with a DOM-based fallback and a
              staleness guard for single-page-app navigation. Real accumulated watch-time, not
              wall-clock.
            </p>
          </div>
        </div>
      </Section>

      <Section title="Privacy & Data Handling" badge={<Badge variant="rose">important</Badge>} defaultOpen={false}>
        <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.8 }}>
          <p style={{ marginBottom: 10 }}>
            Every table this platform writes is keyed by user_id and owned by that user. Two real,
            working actions are available on the <a href="/settings" style={{ color: '#818cf8' }}>Settings page</a>:
          </p>
          <ul style={{ paddingLeft: 20, margin: 0, lineHeight: 1.9 }}>
            <li><strong>Export all my data</strong> — every row across every user-owned table as one downloadable JSON bundle.</li>
            <li><strong>Delete all my data</strong> — a real, permanent cascading delete across all 18 user-owned tables, gated by a server-side type-your-user-id confirmation (not just a UI affordance — the backend independently verifies the confirmation text matches before deleting anything).</li>
          </ul>
        </div>
      </Section>
    </div>
  )
}
