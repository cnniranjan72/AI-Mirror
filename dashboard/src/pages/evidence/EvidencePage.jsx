import { useState } from 'react'
import { useEvidence, useInferences } from '../../hooks/useApi'
import GlassCard from '../../components/ui/GlassCard'
import StatCard from '../../components/ui/StatCard'
import Badge from '../../components/ui/Badge'
import AsyncState from '../../components/ui/AsyncState'
import { LayersIcon, BrainIcon, TargetIcon } from '../../icons/icons'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import EvidenceDrawer from '../../components/explain/EvidenceDrawer'
import CharacterCreature3D from '../../components/character/CharacterCreature3D'

const evidenceTypes = ['behavioral', 'temporal', 'topical', 'creator', 'interaction']
const COLORS = ['#6366f1', '#8b5cf6', '#ec4899', '#10b981', '#f59e0b']

export default function EvidencePage() {
  const { data: evidence, loading: evLoading, error: evError, refetch: refetchEvidence } = useEvidence()
  const { data: inferences, loading: infLoading } = useInferences()
  const [selectedType, setSelectedType] = useState('all')
  const [selectedEvidence, setSelectedEvidence] = useState(null)

  const evidenceList = Array.isArray(evidence) ? evidence : (evidence?.evidence || [])
  const inferencesList = Array.isArray(inferences) ? inferences : (inferences?.inferences || [])

  const filtered = selectedType === 'all'
    ? evidenceList
    : evidenceList.filter(e => e.evidence_type === selectedType)

  const typeCounts = evidenceTypes.map(t => ({
    name: t,
    count: evidenceList.filter(e => e.evidence_type === t).length,
  }))
  const avgConfidence = evidenceList.length
    ? evidenceList.reduce((s, e) => s + (e.confidence || 0), 0) / evidenceList.length
    : 0.3

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 32 }}>
        <div style={{ width: 68, height: 68, flexShrink: 0, margin: '-8px 0' }}>
          <CharacterCreature3D size={68} variant="archive" confidence={avgConfidence} thinking={evLoading} showLabels={false} />
        </div>
        <div>
          <h1 className="gradient-text" style={{ fontSize: 32, fontWeight: 800, letterSpacing: '-0.03em', marginBottom: 6 }}>Evidence</h1>
          <p style={{ color: 'var(--text-tertiary)', fontSize: 15 }}>Reasoning evidence and inference analysis</p>
        </div>
      </div>

      <AsyncState loading={evLoading} error={evError} onRetry={refetchEvidence}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 16, marginBottom: 32 }}>
        <StatCard label="Total Evidence" value={evidenceList.length} icon={LayersIcon} accent="indigo" loading={evLoading} />
        <StatCard label="Inferences" value={inferencesList.length} icon={BrainIcon} accent="violet" loading={infLoading} />
        <StatCard label="Avg Confidence" value={evidenceList.length ? `${Math.round(evidenceList.reduce((s, e) => s + (e.confidence || 0), 0) / evidenceList.length * 100)}%` : '--'} icon={TargetIcon} accent="emerald" loading={evLoading} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginBottom: 32 }}>
        <GlassCard gradient>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600 }}>Evidence by Type</h3>
            <Badge variant="neutral">Distribution</Badge>
          </div>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={typeCounts}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.08)" />
              <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 12 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid rgba(148,163,184,0.2)', borderRadius: 8, fontSize: 12 }} labelStyle={{ color: '#e2e8f0' }} itemStyle={{ color: '#e2e8f0' }} />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {typeCounts.map((_, i) => <Cell key={i} fill={COLORS[i]} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </GlassCard>

        <GlassCard gradient>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600 }}>Evidence Explorer</h3>
            <div style={{ display: 'flex', gap: 6 }}>
              {['all', ...evidenceTypes].map(t => (
                <button key={t} onClick={() => setSelectedType(t)} style={{
                  padding: '2px 8px', borderRadius: 6, border: 'none',
                  background: selectedType === t ? 'rgba(99,102,241,0.15)' : 'transparent',
                  color: selectedType === t ? 'var(--indigo-400)' : 'var(--text-muted)',
                  fontSize: 11, fontWeight: 500, cursor: 'pointer', textTransform: 'capitalize',
                }}>{t}</button>
              ))}
            </div>
          </div>
          <div style={{ maxHeight: 280, overflow: 'auto' }}>
            {filtered.length === 0 ? (
              <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>No evidence found</div>
            ) : filtered.slice(0, 20).map((ev, i) => (
              <div
                key={ev.evidence_id || i}
                onClick={() => setSelectedEvidence(ev.evidence_id)}
                style={{
                  display: 'flex', gap: 10, padding: '8px 0', cursor: 'pointer',
                  borderBottom: '1px solid var(--border-subtle)',
                  animation: `fadeIn 0.3s ease-out ${i * 0.03}s both`,
                  transition: 'all 0.15s',
                }}
                onMouseEnter={e => e.currentTarget.style.background = 'rgba(99,102,241,0.04)'}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
              >
                <Badge variant={['indigo', 'violet', 'pink', 'emerald', 'amber'][evidenceTypes.indexOf(ev.evidence_type)]}
                  style={{ flexShrink: 0, fontSize: 10 }}>{ev.evidence_type}</Badge>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13, color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {ev.explanation || ev.evidence_id}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                    Confidence: {ev.confidence ? `${Math.round(ev.confidence * 100)}%` : '--'} · Weight: {ev.weight || '--'}
                  </div>
                </div>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', alignSelf: 'center' }}>→</div>
              </div>
            ))}
          </div>
        </GlassCard>
      </div>

      <GlassCard gradient>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600 }}>Inferences</h3>
          <Badge variant="neutral">{inferencesList.length} total</Badge>
        </div>
        {inferencesList.length === 0 ? (
          <div style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)', fontSize: 14 }}>No inferences generated yet</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {inferencesList.slice(0, 20).map((inf, i) => (
              <div key={inf.inference_id || i} style={{
                padding: '12px 16px', borderRadius: 8,
                background: 'rgba(148,163,184,0.04)',
                border: '1px solid var(--border-subtle)',
                animation: `fadeIn 0.3s ease-out ${i * 0.03}s both`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                  <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>
                    {inf.inference_type || `Inference ${i + 1}`}
                  </span>
                  <Badge variant={inf.confidence > 0.7 ? 'emerald' : inf.confidence > 0.4 ? 'warning' : 'danger'}>
                    {inf.confidence ? `${Math.round(inf.confidence * 100)}%` : '--'}
                  </Badge>
                </div>
                <div style={{ fontSize: 13, color: 'var(--text-tertiary)', lineHeight: 1.5 }}>
                  {inf.description || inf.explanation || 'No description'}
                </div>
              </div>
            ))}
          </div>
        )}
      </GlassCard>
      </AsyncState>

      {selectedEvidence && (
        <EvidenceDrawer evidenceId={selectedEvidence} onClose={() => setSelectedEvidence(null)} />
      )}
    </div>
  )
}
