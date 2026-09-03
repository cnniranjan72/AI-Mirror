import { useState, useEffect, useRef, useCallback } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import {
  DashboardIcon, IdentityIcon, MemoryIcon, EvidenceIcon, BehaviorIcon,
  PlanningIcon, DecisionIcon, PipelineIcon, AnalyticsIcon, ChatIcon, SettingsIcon,
  SearchIcon, ChevronLeftIcon, ZapIcon, AlertIcon, CpuIcon, DownloadIcon,
  UploadIcon, BookIcon, CompassIcon, ClockIcon, NetworkIcon, DiaryIcon, TargetIcon, BuildingIcon,
  BrainIcon
} from '../../icons/icons'
import { api, isAuthed, displayName } from '../../api/client'
import { useMediaQuery } from '../../hooks/useMotion'
import AuthModal from '../auth/AuthModal'

/**
 * Navigation grouped by what the user is trying to DO, not by which service
 * happens to serve it. Twenty-four destinations in one flat list is a wall:
 * everything looks equally important, so nothing is findable without reading
 * all of it. The groups below are the product's actual mental model —
 * get data in, understand the twin, see how it reasons, look after yourself,
 * take something away, then the machinery underneath.
 */
const navSections = [
  {
    label: 'Overview',
    items: [
      { path: '/dashboard', label: 'Dashboard', icon: DashboardIcon },
      { path: '/import', label: 'Import', icon: UploadIcon },
      { path: '/timeline', label: 'Timeline', icon: ClockIcon },
    ],
  },
  {
    label: 'Your twin',
    items: [
      { path: '/identity', label: 'Identity', icon: IdentityIcon },
      { path: '/restore', label: 'Restore Points', icon: ClockIcon },
      { path: '/character', label: 'Character', icon: CpuIcon },
      { path: '/behavior', label: 'Behavior', icon: BehaviorIcon },
      { path: '/moved-on', label: 'Moved On', icon: ClockIcon },
      { path: '/memory', label: 'Memory', icon: MemoryIcon },
      { path: '/graph', label: 'Knowledge Graph', icon: NetworkIcon },
      { path: '/diary', label: 'Diary', icon: DiaryIcon },
    ],
  },
  {
    label: 'Reasoning',
    items: [
      { path: '/evidence', label: 'Evidence', icon: EvidenceIcon },
      { path: '/contested', label: 'Contested Claims', icon: AlertIcon },
      { path: '/blind-spots', label: 'Blind Spots', icon: SearchIcon },
      { path: '/planning', label: 'Planning', icon: PlanningIcon },
      { path: '/decision', label: 'Decision', icon: DecisionIcon },
      { path: '/learning', label: 'Learning', icon: ZapIcon },
      { path: '/pipeline', label: 'Pipeline', icon: PipelineIcon },
    ],
  },
  {
    label: 'Act on it',
    items: [
      { path: '/chat', label: 'Chat', icon: ChatIcon },
      { path: '/goals', label: 'Goals', icon: TargetIcon },
      { path: '/guardian', label: 'Guardian', icon: AlertIcon },
    ],
  },
  {
    label: 'Share & export',
    items: [
      { path: '/mirror', label: 'Algorithmic Mirror', icon: EvidenceIcon },
      { path: '/provenance', label: 'Interest Provenance', icon: CompassIcon },
      { path: '/calibration', label: 'Accuracy Ledger', icon: TargetIcon },
      { path: '/drift', label: 'Identity Drift', icon: CompassIcon },
      { path: '/xray', label: 'Reasoning X-Ray', icon: NetworkIcon },
      { path: '/counterfactual', label: 'What Would Change It', icon: BrainIcon },
      { path: '/space', label: 'Behaviour Space', icon: MemoryIcon },
      { path: '/report', label: 'Report', icon: BookIcon },
      { path: '/insights', label: 'Insights Export', icon: DownloadIcon },
      { path: '/analytics', label: 'Analytics', icon: AnalyticsIcon },
      { path: '/org', label: 'Organization', icon: BuildingIcon },
    ],
  },
  {
    label: 'Help & system',
    items: [
      { path: '/guide', label: 'Guide', icon: CompassIcon },
      { path: '/documentation', label: 'Documentation', icon: BookIcon },
      { path: '/settings', label: 'Settings', icon: SettingsIcon },
    ],
  },
]

// Flat view, still needed by the command palette's filter.
const navItems = navSections.flatMap(s => s.items)

export default function Sidebar({ collapsed, onToggle, mobileOpen = false, onCloseMobile }) {
  const navigate = useNavigate()
  // Below this width the rail becomes an overlay drawer. That is a behaviour
  // change (it traps focus-adjacent interaction and closes on navigate), not a
  // styling one, so it branches in JS rather than in a media query.
  const isMobile = useMediaQuery('(max-width: 900px)')
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

  // One nav row. Extracted when the flat list became sections so the row's
  // active rail, icon and Guardian alert badge are defined once rather than
  // duplicated per group.
  const renderNavItem = (item) => {
    const Icon = item.icon
    const alerts = item.path === '/guardian' ? guardianAlertCount : 0
    return (
      <NavLink
        key={item.path}
        to={item.path}
        end={item.path === '/dashboard'}
        // On mobile the rail is an overlay covering the page; leaving it open
        // after a tap would hide the page the tap just navigated to.
        onClick={() => { if (isMobile && onCloseMobile) onCloseMobile() }}
        className={({ isActive }) => `aim-nav-item${isActive ? ' active' : ''}`}
        style={({ isActive }) => ({
          display: 'flex', alignItems: 'center', gap: 12,
          padding: collapsed ? '10px 0' : '10px 12px',
          marginBottom: 2,
          borderRadius: 8,
          textDecoration: 'none',
          fontSize: 14, fontWeight: isActive ? 600 : 500,
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
                background: 'var(--accent-gradient-aurora)', backgroundSize: '200% auto',
                boxShadow: '0 0 8px rgba(99,102,241,0.6)',
              }} />
            )}
            <div style={{ width: 20, height: 20, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, position: 'relative' }}>
              <Icon />
              {alerts > 0 && (
                <div className="animate-pulse" style={{
                  position: 'absolute', top: -4, right: collapsed ? -4 : -6,
                  minWidth: 14, height: 14, borderRadius: 7, padding: '0 3px',
                  background: '#f43f5e', color: 'white', fontSize: 9, fontWeight: 700,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  border: '1.5px solid rgba(15,23,42,0.85)',
                  boxShadow: '0 0 8px rgba(244,63,94,0.5)',
                }}>
                  {alerts > 9 ? '9+' : alerts}
                </div>
              )}
            </div>
            {!collapsed && <span>{item.label}</span>}
            {!collapsed && alerts > 0 && (
              <div className="animate-pulse" style={{
                marginLeft: 'auto', minWidth: 18, height: 18, borderRadius: 9, padding: '0 5px',
                background: '#f43f5e', color: 'white', fontSize: 10, fontWeight: 700,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                boxShadow: '0 0 8px rgba(244,63,94,0.5)',
              }}>
                {alerts > 9 ? '9+' : alerts}
              </div>
            )}
          </>
        )}
      </NavLink>
    )
  }

  const handleSearchNav = (result) => {
    navigate(result.url || `/${result.type}?id=${result.id}`)
    setCmdOpen(false)
    setCmdQuery('')
  }

  return (
    <>
      {/* Backdrop for the mobile drawer. Also the dismiss target — a drawer
          with no way out but the toggle is a trap on a phone. */}
      {isMobile && mobileOpen && (
        <div
          onClick={onCloseMobile}
          aria-hidden="true"
          style={{
            position: 'fixed', inset: 0, zIndex: 99,
            background: 'rgba(2,6,23,0.6)', backdropFilter: 'blur(4px)',
            WebkitBackdropFilter: 'blur(4px)',
            animation: 'fadeIn 0.2s ease-out both',
          }}
        />
      )}

      <aside style={{
        // Mobile gets a fixed-width overlay drawer instead of a rail that
        // reserves layout space. Previously the mobile breakpoint set
        // --sidebar-width to 0, which hid the sidebar with nothing to open it —
        // the app simply had no navigation below 768px.
        width: isMobile ? 280 : (collapsed ? 'var(--sidebar-collapsed)' : 'var(--sidebar-width)'),
        transform: isMobile && !mobileOpen ? 'translateX(-100%)' : 'translateX(0)',
        height: '100vh', position: 'fixed', top: 0, left: 0,
        // Slightly translucent over a vertical wash, so the ambient WebGL
        // field reads faintly through the rail instead of the sidebar being a
        // flat slab pasted over a living background.
        background: 'linear-gradient(180deg, rgba(15,23,42,0.92) 0%, rgba(15,23,42,0.86) 55%, rgba(23,32,51,0.9) 100%)',
        backdropFilter: 'blur(26px) saturate(1.6)',
        WebkitBackdropFilter: 'blur(26px) saturate(1.6)',
        borderRight: '1px solid var(--border-subtle)',
        // A lit inner edge on the right — the same trick the cards use to
        // suggest the surface has thickness.
        boxShadow: 'inset -1px 0 0 rgba(148,163,184,0.06), 8px 0 40px -20px rgba(2,6,23,0.9)',
        display: 'flex', flexDirection: 'column',
        transition: 'width 0.3s cubic-bezier(0.16,1,0.3,1), transform 0.3s cubic-bezier(0.16,1,0.3,1)',
        zIndex: 100, overflow: 'hidden',
      }}>
        {/* Accent seam running down the rail's outer edge. */}
        <div aria-hidden="true" style={{
          position: 'absolute', top: 0, bottom: 0, right: 0, width: 1,
          background: 'linear-gradient(180deg, transparent, rgba(34,211,238,0.35) 18%, rgba(99,102,241,0.35) 50%, rgba(236,72,153,0.28) 82%, transparent)',
          opacity: 0.7, pointerEvents: 'none',
        }} />
        {/* Brand */}
        <div style={{
          height: 'var(--topbar-height)', display: 'flex', alignItems: 'center',
          padding: collapsed ? '0 16px' : '0 20px', gap: 12,
          borderBottom: '1px solid var(--border-subtle)', flexShrink: 0,
        }}>
          <div className="aim-brand-mark btn-3d" style={{
            width: 34, height: 34, borderRadius: 11,
            background: 'var(--accent-gradient-aurora)',
            backgroundSize: '200% auto',
            boxShadow: '0 0 22px -4px rgba(99,102,241,0.85), inset 0 1px 0 rgba(255,255,255,0.28)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 16, fontWeight: 800, color: 'white', flexShrink: 0,
          }}>A</div>
          {!collapsed && (
            <span className="gradient-text" style={{ fontSize: 17, fontWeight: 800 }}>
              AIMirror
            </span>
          )}
        </div>

        {/* Search */}
        {!collapsed && (
          <div style={{ padding: '12px 12px 8px' }}>
            <button
              onClick={() => setCmdOpen(true)}
              className="aim-search-trigger"
              style={{
                width: '100%', display: 'flex', alignItems: 'center', gap: 8,
                padding: '8px 12px', borderRadius: 8,
                background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)',
                color: 'var(--text-muted)', fontSize: 13, cursor: 'pointer',
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
          {navSections.map((section, si) => (
            <div key={section.label} style={{ marginBottom: collapsed ? 6 : 14 }}>
              {/* Section labels are the whole point of the grouping, but they
                  are pure text — in the collapsed icon-only rail they would be
                  noise, so a hairline stands in for the break instead. */}
              {!collapsed ? (
                <div style={{
                  fontSize: 10, fontWeight: 700, letterSpacing: '0.12em',
                  textTransform: 'uppercase', color: 'var(--text-muted)',
                  padding: '6px 12px 6px', opacity: 0.75,
                }}>
                  {section.label}
                </div>
              ) : si > 0 ? (
                <div aria-hidden="true" style={{
                  height: 1, margin: '8px 16px',
                  background: 'linear-gradient(90deg, transparent, rgba(148,163,184,0.18), transparent)',
                }} />
              ) : null}
              {section.items.map(item => renderNavItem(item))}
            </div>
          ))}
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

        {/* Collapse toggle — desktop only. Collapsing an overlay drawer to an
            icon rail makes no sense on a phone; there, closing it is the
            equivalent gesture and the backdrop already provides it. */}
        {!isMobile && (
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
        )}
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
