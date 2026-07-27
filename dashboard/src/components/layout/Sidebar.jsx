import { useState, useEffect, useRef, useCallback } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import {
  DashboardIcon, IdentityIcon, MemoryIcon, EvidenceIcon, BehaviorIcon,
  PlanningIcon, DecisionIcon, PipelineIcon, AnalyticsIcon, ChatIcon, SettingsIcon,
  SearchIcon, ChevronLeftIcon, ZapIcon, AlertIcon, CpuIcon, DownloadIcon
} from '../../icons/icons'
import { api, isAuthed, displayName } from '../../api/client'
import AuthModal from '../auth/AuthModal'

const navItems = [
  { path: '/dashboard', label: 'Dashboard', icon: DashboardIcon },
  { path: '/identity', label: 'Identity', icon: IdentityIcon },
  { path: '/character', label: 'Character', icon: CpuIcon },
  { path: '/memory', label: 'Memory', icon: MemoryIcon },
  { path: '/evidence', label: 'Evidence', icon: EvidenceIcon },
  { path: '/behavior', label: 'Behavior', icon: BehaviorIcon },
  { path: '/planning', label: 'Planning', icon: PlanningIcon },
  { path: '/decision', label: 'Decision', icon: DecisionIcon },
  { path: '/learning', label: 'Learning', icon: ZapIcon },
  { path: '/guardian', label: 'Guardian', icon: AlertIcon },
  { path: '/insights', label: 'Insights Export', icon: DownloadIcon },
  { path: '/pipeline', label: 'Pipeline', icon: PipelineIcon },
  { path: '/analytics', label: 'Analytics', icon: AnalyticsIcon },
  { path: '/chat', label: 'Chat', icon: ChatIcon },
  { path: '/settings', label: 'Settings', icon: SettingsIcon },
]

export default function Sidebar({ collapsed, onToggle }) {
  const navigate = useNavigate()
  const [authOpen, setAuthOpen] = useState(false)
  const authed = isAuthed()
  const name = displayName()
  const [cmdOpen, setCmdOpen] = useState(false)
  const [cmdQuery, setCmdQuery] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [searching, setSearching] = useState(false)
  const cmdRef = useRef(null)
  const inputRef = useRef(null)
  const searchTimeout = useRef(null)

  useEffect(() => {
    const handler = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault(); setCmdOpen(true)
      }
      if (e.key === 'Escape') { setCmdOpen(false); setCmdQuery('') }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  useEffect(() => {
    if (cmdOpen && inputRef.current) inputRef.current.focus()
  }, [cmdOpen])

  const [guardianAlertCount, setGuardianAlertCount] = useState(0)
  useEffect(() => {
    let cancelled = false
    const check = () => api.getGuardianUnacknowledgedCount().then(d => {
      if (!cancelled) setGuardianAlertCount(d.count || 0)
    }).catch(() => {})
    check()
    const id = setInterval(check, 60000)
    return () => { cancelled = true; clearInterval(id) }
  }, [])

  useEffect(() => {
    if (!cmdOpen) { setSearchResults([]); setCmdQuery('') }
  }, [cmdOpen])

  const doSearch = useCallback(async (q) => {
    if (!q || q.length < 2) { setSearchResults([]); return }
    setSearching(true)
    try {
      const d = await api.search(q, 15)
      setSearchResults(d.results || [])
    } catch { setSearchResults([]) }
    setSearching(false)
  }, [])

  useEffect(() => {
    if (searchTimeout.current) clearTimeout(searchTimeout.current)
    searchTimeout.current = setTimeout(() => doSearch(cmdQuery), 300)
    return () => { if (searchTimeout.current) clearTimeout(searchTimeout.current) }
  }, [cmdQuery, doSearch])

  const filtered = cmdQuery
    ? navItems.filter(i => i.label.toLowerCase().includes(cmdQuery.toLowerCase()))
    : navItems

  const handleCmdNav = (path) => {
    navigate(path)
    setCmdOpen(false)
    setCmdQuery('')
  }

  const handleSearchNav = (result) => {
    navigate(result.url || `/${result.type}?id=${result.id}`)
    setCmdOpen(false)
    setCmdQuery('')
  }

  return (
    <>
      <aside style={{
        width: collapsed ? 'var(--sidebar-collapsed)' : 'var(--sidebar-width)',
        height: '100vh', position: 'fixed', top: 0, left: 0,
        background: 'rgba(15,23,42,0.85)', backdropFilter: 'blur(24px) saturate(1.5)',
        WebkitBackdropFilter: 'blur(24px) saturate(1.5)',
        borderRight: '1px solid var(--border-subtle)',
        display: 'flex', flexDirection: 'column',
        transition: 'width 0.3s cubic-bezier(0.16,1,0.3,1)',
        zIndex: 100, overflow: 'hidden',
      }}>
        {/* Brand */}
        <div style={{
          height: 'var(--topbar-height)', display: 'flex', alignItems: 'center',
          padding: collapsed ? '0 16px' : '0 20px', gap: 12,
          borderBottom: '1px solid var(--border-subtle)', flexShrink: 0,
        }}>
          <div style={{
            width: 32, height: 32, borderRadius: 10,
            background: 'var(--accent-gradient)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 16, fontWeight: 700, color: 'white', flexShrink: 0,
          }}>A</div>
          {!collapsed && (
            <span style={{ fontSize: 16, fontWeight: 700, letterSpacing: '-0.02em', color: 'var(--text-primary)' }}>
              AIMirror
            </span>
          )}
        </div>

        {/* Search */}
        {!collapsed && (
          <div style={{ padding: '12px 12px 8px' }}>
            <button
              onClick={() => setCmdOpen(true)}
              style={{
                width: '100%', display: 'flex', alignItems: 'center', gap: 8,
                padding: '8px 12px', borderRadius: 8,
                background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)',
                color: 'var(--text-muted)', fontSize: 13, cursor: 'pointer',
                transition: 'all 0.2s',
              }}
            >
              <SearchIcon />
              <span style={{ flex: 1, textAlign: 'left' }}>Search...</span>
              <kbd style={{ fontSize: 10, padding: '2px 5px', borderRadius: 4, background: 'rgba(148,163,184,0.1)', color: 'var(--text-muted)' }}>
                ⌘K
              </kbd>
            </button>
          </div>
        )}

        {/* Navigation */}
        <nav style={{ flex: 1, overflow: 'hidden auto', padding: collapsed ? '8px 0' : '8px 12px' }}>
          {navItems.map((item, i) => {
            const Icon = item.icon
            return (
              <NavLink
                key={item.path}
                to={item.path}
                end={item.path === '/dashboard'}
                style={({ isActive }) => ({
                  display: 'flex', alignItems: 'center', gap: 12,
                  padding: collapsed ? '10px 0' : '10px 12px',
                  marginBottom: 2,
                  borderRadius: 8,
                  textDecoration: 'none',
                  color: isActive ? 'var(--indigo-400)' : 'var(--text-tertiary)',
                  background: isActive ? 'rgba(99,102,241,0.1)' : 'transparent',
                  fontSize: 14, fontWeight: isActive ? 600 : 500,
                  transition: 'all 0.15s ease',
                  justifyContent: collapsed ? 'center' : 'flex-start',
                  position: 'relative',
                })}
              >
                {({ isActive }) => (
                  <>
                    {isActive && !collapsed && (
                      <div style={{
                        position: 'absolute', left: 0, top: '50%', transform: 'translateY(-50%)',
                        width: 3, height: 20, borderRadius: '0 3px 3px 0',
                        background: 'var(--accent-gradient)',
                      }} />
                    )}
                    <div style={{ width: 20, height: 20, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, position: 'relative' }}>
                      <Icon />
                      {item.path === '/guardian' && guardianAlertCount > 0 && (
                        <div style={{
                          position: 'absolute', top: -4, right: collapsed ? -4 : -6,
                          minWidth: 14, height: 14, borderRadius: 7, padding: '0 3px',
                          background: '#f43f5e', color: 'white', fontSize: 9, fontWeight: 700,
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                          border: '1.5px solid rgba(15,23,42,0.85)',
                        }}>
                          {guardianAlertCount > 9 ? '9+' : guardianAlertCount}
                        </div>
                      )}
                    </div>
                    {!collapsed && <span>{item.label}</span>}
                    {!collapsed && item.path === '/guardian' && guardianAlertCount > 0 && (
                      <div style={{
                        marginLeft: 'auto', minWidth: 18, height: 18, borderRadius: 9, padding: '0 5px',
                        background: '#f43f5e', color: 'white', fontSize: 10, fontWeight: 700,
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                      }}>
                        {guardianAlertCount > 9 ? '9+' : guardianAlertCount}
                      </div>
                    )}
                  </>
                )}
              </NavLink>
            )
          })}
        </nav>

        {/* User / auth */}
        <div style={{ padding: collapsed ? '8px 0' : '8px 12px', borderTop: '1px solid var(--border-subtle)' }}>
          {authed ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, justifyContent: collapsed ? 'center' : 'space-between' }}>
              {!collapsed && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
                  <div style={{ width: 28, height: 28, borderRadius: 8, flexShrink: 0, background: 'var(--accent-gradient)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontSize: 12, fontWeight: 700 }}>
                    {(name || '?').charAt(0).toUpperCase()}
                  </div>
                  <span style={{ fontSize: 13, color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{name}</span>
                </div>
              )}
              <button
                onClick={() => { api.logout(); window.location.href = '/dashboard' }}
                title="Sign out"
                style={{ padding: '6px 10px', borderRadius: 6, border: '1px solid var(--border-subtle)', background: 'transparent', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 12 }}
              >
                {collapsed ? '⎋' : 'Sign out'}
              </button>
            </div>
          ) : (
            <button
              onClick={() => setAuthOpen(true)}
              style={{
                width: '100%', padding: '10px 12px', borderRadius: 8,
                background: 'rgba(99,102,241,0.12)', border: '1px solid rgba(99,102,241,0.25)',
                color: '#818cf8', cursor: 'pointer', fontSize: 13, fontWeight: 600,
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
              }}
            >
              {collapsed ? '→' : 'Sign in'}
            </button>
          )}
        </div>

        {/* Collapse toggle */}
        <div style={{ padding: collapsed ? '8px 0' : '8px 12px', borderTop: '1px solid var(--border-subtle)' }}>
          <button
            onClick={onToggle}
            style={{
              width: '100%', display: 'flex', alignItems: 'center', gap: 12,
              padding: '10px 12px', borderRadius: 8, justifyContent: collapsed ? 'center' : 'flex-start',
              background: 'transparent', border: 'none', color: 'var(--text-muted)',
              cursor: 'pointer', fontSize: 13,
              transition: 'color 0.2s',
            }}
          >
            <div style={{ transform: collapsed ? 'rotate(180deg)' : 'none', transition: 'transform 0.3s' }}>
              <ChevronLeftIcon />
            </div>
            {!collapsed && <span>Collapse</span>}
          </button>
        </div>
      </aside>

      {/* Auth */}
      {authOpen && <AuthModal onClose={() => setAuthOpen(false)} />}

      {/* Command Palette */}
      {cmdOpen && (
        <div
          style={{
            position: 'fixed', inset: 0, zIndex: 1000,
            display: 'flex', alignItems: 'flex-start', justifyContent: 'center',
            paddingTop: '15vh',
            background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(8px)',
          }}
          onClick={() => { setCmdOpen(false); setCmdQuery('') }}
        >
          <div
            className="animate-scale"
            style={{
              width: 560, maxWidth: '90vw',
              background: 'var(--bg-secondary)', borderRadius: 16,
              border: '1px solid var(--border-strong)',
              boxShadow: 'var(--shadow-xl), var(--shadow-glow)',
              overflow: 'hidden',
            }}
            onClick={e => e.stopPropagation()}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '12px 16px', borderBottom: '1px solid var(--border-subtle)' }}>
              <SearchIcon />
              <input
                ref={inputRef}
                value={cmdQuery}
                onChange={e => setCmdQuery(e.target.value)}
                placeholder="Search pages..."
                style={{
                  flex: 1, background: 'transparent', border: 'none', outline: 'none',
                  color: 'var(--text-primary)', fontSize: 15,
                }}
              />
              <kbd style={{ fontSize: 10, padding: '3px 6px', borderRadius: 4, background: 'rgba(148,163,184,0.1)', color: 'var(--text-muted)' }}>ESC</kbd>
            </div>
            <div style={{ maxHeight: 380, overflow: 'auto', padding: '4px' }}>
              {/* Pages */}
              {filtered.length > 0 && (
                <div style={{ fontSize: 10, color: 'var(--text-muted)', padding: '8px 12px 4px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Pages</div>
              )}
              {filtered.map(item => {
                const Icon = item.icon
                return (
                  <button key={item.path} onClick={() => handleCmdNav(item.path)}
                    style={{ width: '100%', display: 'flex', alignItems: 'center', gap: 12, padding: '10px 12px', borderRadius: 8, background: 'transparent', border: 'none', color: 'var(--text-secondary)', fontSize: 14, cursor: 'pointer' }}>
                    <div style={{ width: 20, height: 20, color: 'var(--text-muted)' }}><Icon /></div>
                    <span>{item.label}</span>
                  </button>
                )
              })}

              {/* Cognitive search results */}
              {cmdQuery && searchResults.length > 0 && (
                <>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)', padding: '8px 12px 4px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', marginTop: 8 }}>
                    Cognitive Entities
                  </div>
                  {searchResults.map((r, i) => (
                    <button key={i} onClick={() => handleSearchNav(r)}
                      style={{ width: '100%', display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px', borderRadius: 8, background: 'transparent', border: 'none', color: 'var(--text-secondary)', fontSize: 13, cursor: 'pointer', textAlign: 'left' }}>
                      <div style={{
                        width: 6, height: 6, borderRadius: 3, flexShrink: 0,
                        background: r.type === 'evidence' ? 'var(--emerald-400)' : r.type === 'memory' ? 'var(--amber-400)' : r.type === 'inference' ? 'var(--violet-400)' : r.type === 'trace' ? 'var(--cyan-400)' : r.type === 'behavior' ? 'var(--pink-400)' : 'var(--indigo-400)',
                      }} />
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.label}</div>
                        <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{r.subtitle}</div>
                      </div>
                      <span style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'capitalize', flexShrink: 0 }}>{r.type}</span>
                    </button>
                  ))}
                </>
              )}

              {cmdQuery && filtered.length === 0 && searchResults.length === 0 && !searching && (
                <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)', fontSize: 14 }}>No results found</div>
              )}
              {searching && (
                <div style={{ padding: 16, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>Searching...</div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  )
}
