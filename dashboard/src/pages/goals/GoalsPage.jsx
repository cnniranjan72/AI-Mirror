import { useState, useEffect, useCallback } from 'react'
import { api } from '../../api/client'
import GlassCard from '../../components/ui/GlassCard'
import Badge from '../../components/ui/Badge'
import LoadingSkeleton from '../../components/ui/LoadingSkeleton'
import CharacterCreature3D from '../../components/character/CharacterCreature3D'
import { XIcon, CheckIcon } from '../../icons/icons'

const TYPE_META = {
  increase: { label: 'Do more of', icon: '↑', color: '#34d399' },
  decrease: { label: 'Do less of', icon: '↓', color: '#f87171' },
  maintain: { label: 'Keep steady', icon: '→', color: '#818cf8' },
}

function AlignmentBar({ score }) {
  const color = score >= 0.6 ? '#34d399' : score >= 0.35 ? '#fbbf24' : '#f87171'
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>
        <span>Alignment</span><span style={{ fontWeight: 700, color }}>{Math.round(score * 100)}%</span>
      </div>
      <div style={{ height: 7, borderRadius: 4, background: 'rgba(148,163,184,0.1)', overflow: 'hidden' }}>
        <div style={{ height: '100%', width: `${score * 100}%`, background: color, borderRadius: 4, transition: 'width 0.6s cubic-bezier(0.16,1,0.3,1)' }} />
      </div>
    </div>
  )
}

function GoalCard({ goal, onUpdate, onDelete }) {
  const meta = TYPE_META[goal.goal_type] || TYPE_META.maintain
  const isActive = goal.status === 'active'

  return (
    <GlassCard padding="lg" style={{ marginBottom: 12, opacity: isActive ? 1 : 0.6 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12, marginBottom: 10 }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
            <Badge variant="neutral" style={{ color: meta.color, borderColor: `${meta.color}40` }}>{meta.icon} {meta.label}</Badge>
            {goal.target_keywords.map(k => <Badge key={k} variant="indigo">{k}</Badge>)}
            {!isActive && <Badge variant={goal.status === 'completed' ? 'emerald' : 'neutral'}>{goal.status}</Badge>}
          </div>
          <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>{goal.goal_description}</div>
        </div>
        <div style={{ display: 'flex', gap: 4, flexShrink: 0 }}>
          {isActive && (
            <button onClick={() => onUpdate(goal.goal_id, { status: 'completed' })} title="Mark complete"
              style={{ width: 28, height: 28, borderRadius: 6, border: '1px solid var(--border-subtle)', background: 'transparent', color: '#34d399', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <CheckIcon />
            </button>
          )}
          <button onClick={() => onDelete(goal.goal_id)} title="Delete"
            style={{ width: 28, height: 28, borderRadius: 6, border: '1px solid var(--border-subtle)', background: 'transparent', color: 'var(--text-muted)', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <XIcon />
          </button>
        </div>
      </div>

      <AlignmentBar score={goal.alignment_score} />
      <p style={{ fontSize: 12, color: 'var(--text-tertiary)', marginTop: 8, marginBottom: goal.supporting_behaviors.length ? 10 : 0 }}>
        {goal.explanation}
      </p>
      {goal.supporting_behaviors.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {goal.supporting_behaviors.map((b, i) => (
            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
              <span style={{ color: 'var(--text-secondary)' }}>→ {b.topic}</span>
              <span style={{ color: 'var(--text-muted)' }}>{b.lifecycle_state} · {Math.round(b.importance_score * 100)}% importance</span>
            </div>
          ))}
        </div>
      )}
    </GlassCard>
  )
}

function NewGoalForm({ onCreate, creating }) {
  const [description, setDescription] = useState('')
  const [type, setType] = useState('increase')
  const [keywordsInput, setKeywordsInput] = useState('')

  const submit = () => {
    const keywords = keywordsInput.split(',').map(k => k.trim()).filter(Boolean)
    if (!description.trim() || keywords.length === 0) return
    onCreate(description.trim(), type, keywords)
    setDescription(''); setKeywordsInput('')
  }

  return (
    <GlassCard gradient style={{ marginBottom: 20 }}>
      <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 14 }}>Set a new goal</h3>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <input
          value={description}
          onChange={e => setDescription(e.target.value)}
          placeholder="e.g. Spend more time on deep technical content"
          style={{ padding: '10px 12px', borderRadius: 8, border: '1px solid var(--border-subtle)', background: 'rgba(148,163,184,0.04)', color: 'var(--text-primary)', fontSize: 13 }}
        />
        <div style={{ display: 'flex', gap: 10 }}>
          <select
            value={type}
            onChange={e => setType(e.target.value)}
            style={{ padding: '10px 12px', borderRadius: 8, border: '1px solid var(--border-subtle)', background: 'rgba(148,163,184,0.04)', color: 'var(--text-primary)', fontSize: 13 }}
          >
            <option value="increase">Do more of</option>
            <option value="decrease">Do less of</option>
            <option value="maintain">Keep steady</option>
          </select>
          <input
            value={keywordsInput}
            onChange={e => setKeywordsInput(e.target.value)}
            placeholder="Real topics/keywords to track, comma-separated (e.g. rust, tutorial)"
            style={{ flex: 1, padding: '10px 12px', borderRadius: 8, border: '1px solid var(--border-subtle)', background: 'rgba(148,163,184,0.04)', color: 'var(--text-primary)', fontSize: 13 }}
          />
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <button
            onClick={submit}
            disabled={creating}
            style={{
              padding: '9px 20px', borderRadius: 8, border: 'none',
              background: creating ? 'rgba(148,163,184,0.15)' : 'var(--accent-gradient)',
              color: 'white', fontSize: 13, fontWeight: 600, cursor: creating ? 'wait' : 'pointer',
            }}
          >
            {creating ? 'Scoring against your real behavior…' : 'Create goal'}
          </button>
        </div>
      </div>
    </GlassCard>
  )
}

export default function GoalsPage() {
  const [goals, setGoals] = useState([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState('active')

  const load = useCallback(() => {
    setLoading(true)
    api.getGoals(undefined, filter === 'all' ? undefined : filter)
      .then(res => setGoals(res.goals))
      .catch(err => setError(err?.response?.data?.detail || err.message || 'Failed to load goals'))
      .finally(() => setLoading(false))
  }, [filter])

  useEffect(() => { load() }, [load])

  const handleCreate = async (description, type, keywords) => {
    setCreating(true); setError(null)
    try {
      await api.createGoal(description, type, keywords)
      load()
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || 'Failed to create goal')
    } finally {
      setCreating(false)
    }
  }

  const handleUpdate = async (goalId, updates) => {
    await api.updateGoal(goalId, updates)
    load()
  }

  const handleDelete = async (goalId) => {
    await api.deleteGoal(goalId)
    load()
  }

  const avgAlignment = goals.length ? goals.reduce((s, g) => s + g.alignment_score, 0) / goals.length : 0

  return (
    <div style={{ maxWidth: 780, margin: '0 auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 24 }}>
        <div style={{ width: 68, height: 68, flexShrink: 0, margin: '-8px 0' }}>
          <CharacterCreature3D size={68} variant="beacon" confidence={avgAlignment || 0.35} thinking={loading || creating} showLabels={false} />
        </div>
        <div>
          <h1 className="gradient-text" style={{ fontSize: 32, fontWeight: 800, letterSpacing: '-0.03em', marginBottom: 6 }}>
            Goals
          </h1>
          <p style={{ color: 'var(--text-tertiary)', fontSize: 15 }}>
            Set a real intention, tracked against what you actually do
          </p>
        </div>
      </div>

      <NewGoalForm onCreate={handleCreate} creating={creating} />

      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        {['active', 'completed', 'paused', 'all'].map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            style={{
              padding: '6px 14px', borderRadius: 100, fontSize: 12, fontWeight: 600, cursor: 'pointer', textTransform: 'capitalize',
              border: `1px solid ${filter === f ? 'rgba(99,102,241,0.4)' : 'var(--border-subtle)'}`,
              background: filter === f ? 'rgba(99,102,241,0.15)' : 'transparent',
              color: filter === f ? '#a5b4fc' : 'var(--text-tertiary)',
            }}
          >
            {f}
          </button>
        ))}
      </div>

      {error && <GlassCard style={{ marginBottom: 16 }}><div style={{ color: '#f87171', fontSize: 13 }}>{error}</div></GlassCard>}

      {loading && <LoadingSkeleton type="card" count={2} />}

      {!loading && goals.length === 0 && (
        <GlassCard>
          <div style={{ textAlign: 'center', padding: '24px 0', color: 'var(--text-tertiary)', fontSize: 13 }}>
            No {filter !== 'all' ? filter : ''} goals yet. Set one above — it's scored against your real behavior objects immediately, not a placeholder.
          </div>
        </GlassCard>
      )}

      {!loading && goals.map(g => (
        <GoalCard key={g.goal_id} goal={g} onUpdate={handleUpdate} onDelete={handleDelete} />
      ))}
    </div>
  )
}
