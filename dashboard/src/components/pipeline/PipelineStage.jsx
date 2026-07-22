import { useState } from 'react'
import Badge from '../ui/Badge'
import { CheckIcon, XIcon, ClockIcon, AlertIcon, ZapIcon, PlayIcon, StopIcon } from '../../icons/icons'

const stageColorMap = {
  'Behavior Gateway': '#6366f1',
  'Content Intelligence': '#8b5cf6',
  'Knowledge Consolidation': '#7c3aed',
  'Behavior Objects': '#a78bfa',
  'Evidence': '#ec4899',
  'Inference': '#f472b6',
  'Reflection': '#f43f5e',
  'Memory': '#10b981',
  'Identity': '#34d399',
  'Snapshot': '#059669',
  'Runtime': '#06b6d4',
  'Planner': '#0ea5e9',
  'Retriever': '#3b82f6',
  'Fusion': '#6366f1',
  'Decision': '#8b5cf6',
  'Context': '#a78bfa',
  'LLM': '#ec4899',
  'Response': '#10b981',
}

const stageDescriptions = {
  'Behavior Gateway': 'Ingests raw behavioral events from extension',
  'Content Intelligence': 'Extracts content features and metadata',
  'Knowledge Consolidation': 'Consolidates knowledge into structured format',
  'Behavior Objects': 'Creates behavior object representations',
  'Evidence': 'Collects evidence across behavioral dimensions',
  'Inference': 'Generates inferences from collected evidence',
  'Reflection': 'Produces cognitive reflections and insights',
  'Memory': 'Stores in episodic/semantic memory stores',
  'Identity': 'Updates cognitive identity profile',
  'Snapshot': 'Creates identity snapshot if significant shift',
  'Runtime': 'Builds runtime context for query processing',
  'Planner': 'Creates execution plan with intent detection',
  'Retriever': 'Retrieves relevant memories and evidence',
  'Fusion': 'Fuses retrieved information coherently',
  'Decision': 'Makes decisions on information to include',
  'Context': 'Builds final context for LLM',
  'LLM': 'Generates natural language response',
  'Response': 'Returns final response',
}

export default function PipelineStage({ name, status = 'idle', latency, index, error, output }) {
  const [expanded, setExpanded] = useState(false)
  const color = stageColorMap[name] || '#6366f1'
  const isActive = status === 'running' || status === 'active'
  const isDone = status === 'success' || status === 'completed'
  const isError = status === 'error' || status === 'failed'

  return (
    <div style={{
      animation: `fadeIn 0.3s ease-out ${index * 0.04}s both`,
    }}>
      <div
        onClick={() => setExpanded(!expanded)}
        style={{
          display: 'flex', alignItems: 'center', gap: 12,
          padding: '12px 16px', borderRadius: 10,
          background: isActive
            ? `linear-gradient(135deg, ${color}15, ${color}08)`
            : isError
              ? 'rgba(239,68,68,0.08)'
              : 'rgba(148,163,184,0.03)',
          border: `1px solid ${
            isActive ? `${color}40` : isError ? 'rgba(239,68,68,0.2)' : 'var(--border-subtle)'
          }`,
          cursor: 'pointer', transition: 'all 0.3s ease',
          position: 'relative', overflow: 'hidden',
        }}
      >
        {/* Animated pulse for active */}
        {isActive && (
          <div style={{
            position: 'absolute', inset: 0,
            background: `radial-gradient(circle at 30% 50%, ${color}10, transparent 70%)`,
            animation: 'pulse 2s ease-in-out infinite',
          }} />
        )}

        {/* Status indicator */}
        <div style={{
          width: 28, height: 28, borderRadius: 8,
          background: isActive ? `${color}20` : isDone ? 'rgba(16,185,129,0.15)' : isError ? 'rgba(239,68,68,0.15)' : 'rgba(148,163,184,0.08)',
          border: `1px solid ${
            isActive ? `${color}40` : isDone ? 'rgba(16,185,129,0.25)' : isError ? 'rgba(239,68,68,0.25)' : 'var(--border-subtle)'
          }`,
          display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
          color: isActive ? color : isDone ? '#34d399' : isError ? '#f87171' : 'var(--text-muted)',
        }}>
          {isActive ? <ZapIcon /> : isDone ? <CheckIcon /> : isError ? <XIcon /> : <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--text-muted)' }} />}
        </div>

        {/* Info */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: isActive ? color : 'var(--text-secondary)' }}>
              {name}
            </span>
            {isActive && <Badge variant="info" style={{ fontSize: 9, padding: '1px 6px' }}>LIVE</Badge>}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{stageDescriptions[name]}</div>
        </div>

        {/* Latency */}
        <div style={{ textAlign: 'right' }}>
          {latency !== undefined && (
            <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-tertiary)' }}>
              {Math.round(latency)}ms
            </div>
          )}
          {isActive && <div style={{ fontSize: 10, color, marginTop: 2 }}>Processing...</div>}
          {isDone && <div style={{ fontSize: 10, color: '#34d399', marginTop: 2 }}>Complete</div>}
          {isError && <div style={{ fontSize: 10, color: '#f87171', marginTop: 2 }}>Failed</div>}
        </div>
      </div>

      {/* Expanded details */}
      {expanded && (output || error) && (
        <div style={{
          marginTop: 4, padding: '12px 16px', borderRadius: 8,
          background: 'rgba(0,0,0,0.2)', border: '1px solid var(--border-subtle)',
          fontSize: 12, color: 'var(--text-tertiary)',
          fontFamily: 'var(--font-mono)', whiteSpace: 'pre-wrap', lineHeight: 1.6,
        }}>
          {error && <div style={{ color: '#f87171', marginBottom: 8 }}>Error: {error}</div>}
          {output && <div>{typeof output === 'string' ? output : JSON.stringify(output, null, 2)}</div>}
        </div>
      )}
    </div>
  )
}
