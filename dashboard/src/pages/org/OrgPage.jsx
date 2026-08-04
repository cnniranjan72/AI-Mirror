import { useState, useEffect, useCallback } from 'react'
import { api, isAuthed } from '../../api/client'
import GlassCard from '../../components/ui/GlassCard'
import Badge from '../../components/ui/Badge'
import AsyncState from '../../components/ui/AsyncState'
import AuthModal from '../../components/auth/AuthModal'
import { BuildingIcon, CopyIcon, CheckIcon, XIcon } from '../../icons/icons'

export default function OrgPage() {
  const authed = isAuthed()
  const [authOpen, setAuthOpen] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [org, setOrg] = useState(null)
  const [members, setMembers] = useState([])
  const [invites, setInvites] = useState([])

  const [createName, setCreateName] = useState('')
  const [joinCode, setJoinCode] = useState('')
  const [busy, setBusy] = useState(false)
  const [actionError, setActionError] = useState(null)
  const [copiedCode, setCopiedCode] = useState(null)

  const load = useCallback(async () => {
    if (!authed) { setLoading(false); return }
    setLoading(true); setError(null)
    try {
      const { org } = await api.getMyOrg()
      setOrg(org)
      if (org) {
        const [m, i] = await Promise.all([
          api.getOrgMembers(),
          org.role === 'owner' ? api.listOrgInvites() : Promise.resolve({ invites: [] }),
        ])
        setMembers(m.members || [])
        setInvites(i.invites || [])
      }
    } catch (err) {
      setError(err?.response?.data?.detail || err.message)
    }
    setLoading(false)
  }, [authed])

  useEffect(() => { load() }, [load])

  const withBusy = async (fn) => {
    setBusy(true); setActionError(null)
    try { await fn(); await load() }
    catch (err) { setActionError(err?.response?.data?.detail || err.message) }
    setBusy(false)
  }

  const handleCreate = () => createName.trim() && withBusy(() => api.createOrg(createName.trim()))
  const handleJoin = () => joinCode.trim() && withBusy(() => api.joinOrg(joinCode.trim()))
  const handleInvite = () => withBusy(() => api.createOrgInvite())
  const handleRemove = (username) => withBusy(() => api.removeOrgMember(username))
  const handleLeave = () => {
    if (!window.confirm('Leave this organization?')) return
    withBusy(() => api.leaveOrg())
  }

  const copyCode = (code) => {
    navigator.clipboard?.writeText(code)
    setCopiedCode(code)
    setTimeout(() => setCopiedCode(null), 1500)
  }

  if (!authed) {
    return (
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 32 }}>
          <div style={{ width: 44, height: 44, borderRadius: 12, background: 'rgba(99,102,241,0.12)', border: '1px solid rgba(99,102,241,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#818cf8' }}>
            <BuildingIcon />
          </div>
          <div>
            <h1 className="gradient-text" style={{ fontSize: 32, fontWeight: 800, letterSpacing: '-0.03em' }}>Organization</h1>
            <p style={{ color: 'var(--text-tertiary)', fontSize: 15 }}>Shared seats for teams — sign in to create or join one</p>
          </div>
        </div>
        <GlassCard gradient>
          <p style={{ fontSize: 14, color: 'var(--text-tertiary)', marginBottom: 16 }}>
            Organizations need an account of your own first — every member still gets their own private
            cognitive twin, an org just groups accounts for shared billing and roster management.
          </p>
          <button onClick={() => setAuthOpen(true)} style={{
            padding: '10px 20px', borderRadius: 10, border: 'none',
            background: 'var(--accent-gradient)', color: 'white', fontSize: 14, fontWeight: 600, cursor: 'pointer',
          }}>
            Sign up / Sign in
          </button>
        </GlassCard>
        {authOpen && <AuthModal onClose={() => setAuthOpen(false)} />}
      </div>
    )
  }

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 32 }}>
        <div style={{ width: 44, height: 44, borderRadius: 12, background: 'rgba(99,102,241,0.12)', border: '1px solid rgba(99,102,241,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#818cf8' }}>
          <BuildingIcon />
        </div>
        <div>
          <h1 className="gradient-text" style={{ fontSize: 32, fontWeight: 800, letterSpacing: '-0.03em' }}>Organization</h1>
          <p style={{ color: 'var(--text-tertiary)', fontSize: 15 }}>
            {org ? `${org.name} · ${org.member_count} member${org.member_count === 1 ? '' : 's'}` : 'Create a workspace or join one with an invite code'}
          </p>
        </div>
      </div>

      <AsyncState loading={loading} error={error} onRetry={load}>
        {!org ? (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
            <GlassCard gradient>
              <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>Create an organization</h3>
              <p style={{ fontSize: 13, color: 'var(--text-tertiary)', marginBottom: 16 }}>
                You become the owner — you can invite members and manage the roster, never their data.
              </p>
              <div style={{ display: 'flex', gap: 8 }}>
                <input value={createName} onChange={e => setCreateName(e.target.value)} placeholder="Organization name"
                  style={{ flex: 1, padding: '10px 12px', borderRadius: 8, background: 'rgba(30,41,59,0.5)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)', fontSize: 13, outline: 'none' }} />
                <button onClick={handleCreate} disabled={busy || !createName.trim()} style={{
                  padding: '10px 16px', borderRadius: 8, border: 'none',
                  background: 'var(--accent-gradient)', color: 'white', fontSize: 13, fontWeight: 600,
                  cursor: busy ? 'wait' : 'pointer', opacity: createName.trim() ? 1 : 0.5,
                }}>
                  Create
                </button>
              </div>
            </GlassCard>
            <GlassCard gradient>
              <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>Join with an invite code</h3>
              <p style={{ fontSize: 13, color: 'var(--text-tertiary)', marginBottom: 16 }}>
                Ask your org owner for an invite code from their Organization page.
              </p>
              <div style={{ display: 'flex', gap: 8 }}>
                <input value={joinCode} onChange={e => setJoinCode(e.target.value)} placeholder="Invite code"
                  style={{ flex: 1, padding: '10px 12px', borderRadius: 8, background: 'rgba(30,41,59,0.5)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)', fontSize: 13, outline: 'none' }} />
                <button onClick={handleJoin} disabled={busy || !joinCode.trim()} style={{
                  padding: '10px 16px', borderRadius: 8, border: '1px solid var(--border-strong)',
                  background: 'transparent', color: 'var(--text-primary)', fontSize: 13, fontWeight: 600,
                  cursor: busy ? 'wait' : 'pointer', opacity: joinCode.trim() ? 1 : 0.5,
                }}>
                  Join
                </button>
              </div>
            </GlassCard>
            {actionError && <div style={{ gridColumn: '1 / -1', color: '#f87171', fontSize: 13 }}>{actionError}</div>}
          </div>
        ) : (
          <>
            <GlassCard gradient style={{ marginBottom: 24 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                <div>
                  <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>Workspace</div>
                  <div style={{ fontSize: 18, fontWeight: 700 }}>{org.name}</div>
                </div>
                <Badge variant={org.role === 'owner' ? 'indigo' : 'neutral'}>{org.role}</Badge>
              </div>

              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16, lineHeight: 1.6 }}>
                Members each keep a fully private cognitive twin — this page shows roster info only
                (name, role, join date). No member's behavior, evidence, or identity data is visible here,
                to anyone, ever.
              </div>

              <div style={{ overflow: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead>
                    <tr style={{ textAlign: 'left', color: 'var(--text-muted)', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                      <th style={{ padding: '8px 12px' }}>Member</th>
                      <th style={{ padding: '8px 12px' }}>Role</th>
                      <th style={{ padding: '8px 12px' }}>Joined</th>
                      {org.role === 'owner' && <th style={{ padding: '8px 12px' }} />}
                    </tr>
                  </thead>
                  <tbody>
                    {members.map(m => (
                      <tr key={m.username} style={{ borderTop: '1px solid var(--border-subtle)' }}>
                        <td style={{ padding: '10px 12px' }}>{m.display_name || m.username}</td>
                        <td style={{ padding: '10px 12px' }}><Badge variant={m.org_role === 'owner' ? 'indigo' : 'neutral'}>{m.org_role}</Badge></td>
                        <td style={{ padding: '10px 12px', color: 'var(--text-muted)' }}>{new Date(m.created_at).toLocaleDateString()}</td>
                        {org.role === 'owner' && (
                          <td style={{ padding: '10px 12px', textAlign: 'right' }}>
                            {m.org_role !== 'owner' && (
                              <button onClick={() => handleRemove(m.username)} disabled={busy} title="Remove from org" style={{
                                background: 'transparent', border: 'none', color: '#f87171', cursor: 'pointer', fontSize: 16,
                              }}>
                                <XIcon />
                              </button>
                            )}
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </GlassCard>

            {org.role === 'owner' && (
              <GlassCard gradient style={{ marginBottom: 24 }}>
                <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>Invite members</h3>
                <button onClick={handleInvite} disabled={busy} style={{
                  padding: '10px 16px', borderRadius: 8, border: 'none',
                  background: 'var(--accent-gradient)', color: 'white', fontSize: 13, fontWeight: 600,
                  cursor: busy ? 'wait' : 'pointer', marginBottom: 16,
                }}>
                  Generate invite code
                </button>
                {invites.length > 0 && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {invites.map(inv => (
                      <div key={inv.code} style={{
                        display: 'flex', alignItems: 'center', gap: 12, padding: '8px 12px',
                        borderRadius: 8, background: 'rgba(148,163,184,0.04)', fontSize: 12,
                      }}>
                        <code style={{ color: 'var(--indigo-300)', fontFamily: 'var(--font-mono)' }}>{inv.code}</code>
                        <span style={{ color: 'var(--text-muted)' }}>{inv.use_count}/{inv.max_uses ?? '∞'} used</span>
                        <button onClick={() => copyCode(inv.code)} title="Copy code" style={{
                          marginLeft: 'auto', background: 'transparent', border: 'none', color: 'var(--text-tertiary)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4,
                        }}>
                          {copiedCode === inv.code ? <CheckIcon /> : <CopyIcon />}
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </GlassCard>
            )}

            {actionError && <div style={{ color: '#f87171', fontSize: 13, marginBottom: 16 }}>{actionError}</div>}

            <button onClick={handleLeave} disabled={busy} style={{
              padding: '10px 16px', borderRadius: 10, border: '1px solid rgba(244,63,94,0.3)',
              background: 'rgba(244,63,94,0.08)', color: '#fb7185', fontSize: 13, fontWeight: 600, cursor: busy ? 'wait' : 'pointer',
            }}>
              Leave organization
            </button>
          </>
        )}
      </AsyncState>
    </div>
  )
}
