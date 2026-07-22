import { useState, useEffect } from 'react'
import Badge from '../ui/Badge'
import ExplainabilityPanel from '../explain/ExplainabilityPanel'
import { api } from '../../api/client'

function TreeNode({ icon, label, confidence, latency, children, color = 'var(--indigo-400)', onClick, isSelected }) {
  const [hovered, setHovered] = useState(false)
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
      <div
        onClick={onClick}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        style={{
          padding: '10px 18px', borderRadius: 10, cursor: onClick ? 'pointer' : 'default',
          background: isSelected ? 'rgba(99,102,241,0.15)' : hovered ? 'rgba(148,163,184,0.08)' : 'rgba(0,0,0,0.2)',
          border: `1px solid ${isSelected ? 'rgba(99,102,241,0.3)' : hovered ? 'rgba(148,163,184,0.2)' : 'var(--border-subtle)'}`,
          transition: 'all 0.15s', textAlign: 'center', minWidth: 120,
        }}
      >
        <div style={{ fontSize: 18, marginBottom: 4 }}>{icon}</div>
        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 2 }}>{label}</div>
        {confidence != null && (
          <div style={{ fontSize: 12, fontWeight: 600, color: confidence > 0.7 ? 'var(--emerald-400)' : confidence > 0.4 ? 'var(--amber-400)' : 'var(--rose-400)' }}>
            {Math.round(confidence * 100)}%
          </div>
        )}
        {latency != null && (
          <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>{Math.round(latency)}ms</div>
        )}
      </div>
      {children}
    </div>
  )
}

function Arrow({ label }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2, padding: '2px 0' }}>
      <div style={{ width: 2, height: 20, background: 'var(--border-subtle)' }} />
      {label && <span style={{ fontSize: 9, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>{label}</span>}
      <svg width="10" height="10" viewBox="0 0 10 10" style={{ color: 'var(--text-muted)' }}>
        <path d="M5 10 L0 4 H10 Z" fill="currentColor" />
      </svg>
    </div>
  )
}

function CandidatesRow({ candidates, onSelect }) {
  if (!candidates?.length) return null
  return (
    <div style={{ display: 'flex', gap: 8, justifyContent: 'center', flexWrap: 'wrap' }}>
      {candidates.map((c, i) => (
        <div key={i} onClick={() => onSelect?.(c)}
          style={{
            padding: '8px 14px', borderRadius: 8, cursor: 'pointer',
            background: 'rgba(148,163,184,0.04)', border: '1px solid var(--border-subtle)',
            textAlign: 'center', minWidth: 80, transition: 'all 0.15s',
          }}
          onMouseEnter={e => e.currentTarget.style.borderColor = 'rgba(99,102,241,0.3)'}
          onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--border-subtle)'}
        >
          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{c.label || c.name || `Candidate ${i + 1}`}</div>
          <div style={{
            fontSize: 14, fontWeight: 700, marginTop: 2,
            color: c.confidence > 0.7 ? 'var(--emerald-400)' : c.confidence > 0.4 ? 'var(--amber-400)' : 'var(--rose-400)',
          }}>
            {c.confidence ? `${Math.round(c.confidence * 100)}%` : '--'}
          </div>
          {/* Mini confidence bar */}
          <div style={{ marginTop: 4, height: 3, borderRadius: 2, background: 'var(--border-subtle)', overflow: 'hidden' }}>
            <div style={{
              height: '100%', borderRadius: 2,
              width: c.confidence ? `${Math.round(c.confidence * 100)}%` : '0%',
              background: 'var(--accent-gradient)',
            }} />
          </div>
        </div>
      ))}
    </div>
  )
}

export default function DecisionTree({ traceId, onExplain }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!traceId) return
    setLoading(true)
    api.getExplain(traceId)
      .then(d => { setData(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [traceId])

  if (loading) {
    return <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>Loading decision tree...</div>
  }

  if (!data || data.error) {
    return <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>No decision data available</div>
  }

  const candidates = data.decision?.candidates || []
  const selectedCandidate = candidates.find(c => c.selected) || candidates[0]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 0, padding: '20px 0' }}>
      {/* Query */}
      <TreeNode icon="💬" label={data.query?.slice(0, 40) || 'Query'} onClick={() => onExplain?.(traceId)} />
      <Arrow label="Intent: " />

      {/* Planner */}
      <TreeNode
        icon="📋" label="Planner" color="var(--violet-400)"
        confidence={data.planner?.plan_confidence || data.planner?.intent_confidence}
        onClick={() => onExplain?.(traceId)}
      >
        <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 4 }}>{data.planner?.reasoning_mode || data.planner?.intent}</div>
      </TreeNode>
      <Arrow label="Rank" />

      {/* Candidates */}
      {candidates.length > 0 && (
        <>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 8, fontWeight: 600 }}>Candidate Decisions</div>
          <CandidatesRow candidates={candidates} onSelect={() => onExplain?.(traceId)} />
          <Arrow label="Best" />
        </>
      )}

      {/* Selected Decision */}
      <TreeNode
        icon="⚖️" label="Selected Decision" color="var(--emerald-400)"
        confidence={data.decision?.aggregate_confidence}
        onClick={() => onExplain?.(traceId)}
      >
        <div style={{ display: 'flex', gap: 8, justifyContent: 'center', marginTop: 4 }}>
          <Badge variant="neutral">{data.decision?.input_facts || 0} in</Badge>
          <Badge variant="neutral">{data.decision?.output_facts || 0} out</Badge>
          {(data.decision?.conflicts || 0) > 0 && <Badge variant="rose">{data.decision.conflicts} conflicts</Badge>}
        </div>
      </TreeNode>
      <Arrow label="Assemble" />

      {/* Context */}
      <TreeNode
        icon="🔗" label="Context Builder" color="var(--amber-400)"
        latency={data.context?.context_build_ms}
        onClick={() => onExplain?.(traceId)}
      >
        <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 4 }}>
          {data.context?.retrieved_count || 0} retrieved · {(data.context?.token_count || 0).toLocaleString()} tokens
        </div>
      </TreeNode>
      <Arrow label="Generate" />

      {/* LLM */}
      <TreeNode
        icon="🤖" label="LLM" color="var(--pink-400)"
        latency={data.llm?.latency_ms}
        onClick={() => onExplain?.(traceId)}
      >
        <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 4 }}>
          {data.llm?.model || data.llm?.provider || 'gpt-4o'} · {data.llm?.tokens || 0} tokens
        </div>
      </TreeNode>
      <Arrow label="Respond" />

      {/* Response */}
      <TreeNode icon="✨" label="Response" color="var(--emerald-400)" onClick={() => onExplain?.(traceId)}>
        <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 4, maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {(data.response || data.query || '').slice(0, 60)}
        </div>
      </TreeNode>

      {/* Summary bar */}
      <div style={{ display: 'flex', gap: 8, marginTop: 16, flexWrap: 'wrap', justifyContent: 'center' }}>
        <Badge variant="indigo">trace: {(traceId || '').slice(0, 12)}</Badge>
        <Badge variant={data.success ? 'emerald' : 'rose'}>{data.success ? 'Success' : 'Failed'}</Badge>
        <Badge variant="neutral">{Math.round(data.total_ms)}ms total</Badge>
      </div>
    </div>
  )
}
