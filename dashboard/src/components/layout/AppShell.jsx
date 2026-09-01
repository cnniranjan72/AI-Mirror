import { useState, Suspense, lazy } from 'react'
import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { Canvas } from '@react-three/fiber'
import { View } from '@react-three/drei'
import Sidebar from './Sidebar'
import ErrorBoundary from '../ErrorBoundary'
import LoadingSkeleton from '../ui/LoadingSkeleton'
import SetupToast from '../ui/SetupToast'
import { isAuthed } from '../../api/client'
import { useMediaQuery } from '../../hooks/useMotion'

// Lazy-loaded so each route's code (and the vendor chunks it pulls in —
// three.js/drei/react-force-graph-3d/recharts) ships only when that route is
// actually visited, instead of all 23 pages loading on first paint. The
// Suspense boundary below already existed but was a no-op until these were
// lazy — nothing else had to change to activate it.
const LandingPage = lazy(() => import('../../pages/LandingPage'))
const Overview = lazy(() => import('../../pages/Overview'))
const IngestionPage = lazy(() => import('../../pages/ingestion/IngestionPage'))
const TimelinePage = lazy(() => import('../../pages/timeline/TimelinePage'))
const KnowledgeGraphPage = lazy(() => import('../../pages/graph/KnowledgeGraphPage'))
const DiaryPage = lazy(() => import('../../pages/diary/DiaryPage'))
const GoalsPage = lazy(() => import('../../pages/goals/GoalsPage'))
const OrgPage = lazy(() => import('../../pages/org/OrgPage'))
const IdentityPage = lazy(() => import('../../pages/identity/IdentityPage'))
const MemoryPage = lazy(() => import('../../pages/memory/MemoryPage'))
const EvidencePage = lazy(() => import('../../pages/evidence/EvidencePage'))
const BehaviorPage = lazy(() => import('../../pages/behavior/BehaviorPage'))
const PlanningPage = lazy(() => import('../../pages/planning/PlanningPage'))
const DecisionPage = lazy(() => import('../../pages/decision/DecisionPage'))
const LearningPage = lazy(() => import('../../pages/learning/LearningPage'))
const GuardianPage = lazy(() => import('../../pages/guardian/GuardianPage'))
const CharacterPage = lazy(() => import('../../pages/character/CharacterPage'))
const InsightsPage = lazy(() => import('../../pages/insights/InsightsPage'))
const ReportPage = lazy(() => import('../../pages/report/ReportPage'))
const MirrorPage = lazy(() => import('../../pages/mirror/MirrorPage'))
const PipelinePage = lazy(() => import('../../pages/pipeline/PipelinePage'))
const TracePage = lazy(() => import('../../pages/trace/TracePage'))
const AnalyticsPage = lazy(() => import('../../pages/analytics/AnalyticsPage'))
const ChatPage = lazy(() => import('../../pages/chat/ChatPage'))
const SettingsPage = lazy(() => import('../../pages/settings/SettingsPage'))
const GuidePage = lazy(() => import('../../pages/guide/GuidePage'))
const DocumentationPage = lazy(() => import('../../pages/documentation/DocumentationPage'))

// Shown while a lazy route chunk is in flight. The top bar is the part that
// matters: chunk fetches are usually too fast for skeletons to register, but
// long enough that a click with zero feedback feels broken.
const PageLoading = () => (
  <>
    <div className="route-progress" />
    <div style={{ padding: '32px' }}>
      <LoadingSkeleton type="card" count={3} />
      <div style={{ height: 24 }} />
      <LoadingSkeleton type="chart" />
    </div>
  </>
)

export default function AppShell() {
  const [collapsed, setCollapsed] = useState(false)
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const isMobile = useMediaQuery('(max-width: 900px)')
  // On mobile the sidebar floats over the page, so the content must not
  // reserve a gutter for it.
  const sidebarWidth = isMobile ? 0 : (collapsed ? 'var(--sidebar-collapsed)' : 'var(--sidebar-width)')
  const location = useLocation()

  // "/" is the public entry point — a first-time visitor with no account has
  // nothing to navigate yet, so it renders standalone without the 21-item
  // internal app sidebar. Signed-in visitors have no reason to see the
  // marketing page at all and go straight to their dashboard.
  if (location.pathname === '/') {
    if (isAuthed()) return <Navigate to="/dashboard" replace />
    return (
      <Suspense fallback={<PageLoading />}>
        <LandingPage />
      </Suspense>
    )
  }

  // Default to the sign-in/landing gate for everyone else too — a
  // bookmarked or direct link to an inner route while signed out used to
  // silently show the demo account's data with no gate at all. The demo
  // account itself is untouched; it just now requires the explicit opt-in
  // set by LandingPage.jsx's "Load Demo Data" / "Already have data?" CTAs
  // instead of being the silent default.
  if (!isAuthed() && localStorage.getItem('aim_demo_mode') !== 'true') {
    return <Navigate to="/" replace />
  }

  return (
    // position/zIndex are load-bearing: the ambient WebGL field renders at
    // z-index 0 as a sibling of this shell inside #root. Without an explicit
    // positive layer here, this content is non-positioned and would paint
    // BELOW that canvas. See the layering contract in motion.css.
    <div style={{ display: 'flex', minHeight: '100vh', position: 'relative', zIndex: 1 }}>
      {/* Every CharacterCreature3D on every page renders into this single shared
          canvas via <View> instead of mounting its own <Canvas>. Route changes
          swap which View is in the DOM, not the WebGL context itself — this is
          what keeps navigation from tearing down/recreating a context on every
          page (the source of the react-three-fiber StrictMode unmount warning).

          zIndex sits above normal page content (GlassCards etc. are unpositioned,
          z-index:auto) but below Sidebar (100) and modals (1000) — it MUST be
          above regular content, not behind it: GlassCard uses backdrop-filter,
          which blurs whatever renders behind the card. A hologram rendered by
          this canvas at z-index 0 (below the DOM) inside a GlassCard was getting
          its crisp geometry blurred into an unrecognizable glow blob by the
          card's own 20px backdrop-filter — this canvas being transparent
          everywhere except the actual 3D pixels, plus pointerEvents:none, makes
          sitting above content safe (nothing else is ever visually covered). */}
      <Canvas
        gl={{ alpha: true, antialias: true }}
        dpr={[1, 2]}
        style={{ position: 'fixed', inset: 0, width: '100vw', height: '100vh', pointerEvents: 'none', zIndex: 50 }}
      >
        <View.Port />
      </Canvas>

      <Sidebar
        collapsed={collapsed}
        onToggle={() => setCollapsed(c => !c)}
        mobileOpen={mobileNavOpen}
        onCloseMobile={() => setMobileNavOpen(false)}
      />

      <main style={{
        marginLeft: sidebarWidth,
        flex: 1,
        minHeight: '100vh',
        transition: 'margin-left 0.3s cubic-bezier(0.16,1,0.3,1)',
        display: 'flex', flexDirection: 'column',
      }}>
        {/* Mobile top bar. Without it there is no way to reach navigation at
            all below 900px — the drawer has no trigger. */}
        {isMobile && (
          <div style={{
            position: 'sticky', top: 0, zIndex: 90,
            display: 'flex', alignItems: 'center', gap: 12,
            padding: '12px 16px',
            background: 'rgba(15,23,42,0.86)',
            backdropFilter: 'blur(20px) saturate(1.5)',
            WebkitBackdropFilter: 'blur(20px) saturate(1.5)',
            borderBottom: '1px solid var(--border-subtle)',
          }}>
            <button
              onClick={() => setMobileNavOpen(true)}
              aria-label="Open navigation"
              aria-expanded={mobileNavOpen}
              className="btn-3d"
              style={{
                width: 40, height: 40, borderRadius: 11, flexShrink: 0,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: 'var(--bg-surface)', border: '1px solid var(--border-strong)',
                color: 'var(--text-secondary)', cursor: 'pointer',
              }}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <line x1="3" y1="6" x2="21" y2="6" />
                <line x1="3" y1="12" x2="21" y2="12" />
                <line x1="3" y1="18" x2="21" y2="18" />
              </svg>
            </button>
            <div className="aim-brand-mark" style={{
              width: 30, height: 30, borderRadius: 9,
              background: 'var(--accent-gradient-aurora)', backgroundSize: '200% auto',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 14, fontWeight: 800, color: 'white', flexShrink: 0,
            }}>A</div>
            <span className="gradient-text" style={{ fontSize: 16, fontWeight: 800 }}>AIMirror</span>
          </div>
        )}

        <div style={{
          flex: 1,
          padding: isMobile ? '20px 16px' : '32px',
          maxWidth: 1440,
          width: '100%',
          margin: '0 auto',
        }}>
          <ErrorBoundary>
            <Suspense fallback={<PageLoading />}>
              {/* Keyed on pathname so React tears down and remounts this
                  wrapper on every navigation, which is what replays the
                  .route-view entrance. Keying the <Routes> element itself
                  would remount the router internals instead. */}
              <div key={location.pathname} className="route-view">
              <Routes>
                <Route path="/dashboard" element={<Overview />} />
                <Route path="/import" element={<IngestionPage />} />
                <Route path="/timeline" element={<TimelinePage />} />
                <Route path="/graph" element={<KnowledgeGraphPage />} />
                <Route path="/diary" element={<DiaryPage />} />
                <Route path="/goals" element={<GoalsPage />} />
                <Route path="/org" element={<OrgPage />} />
                <Route path="/identity" element={<IdentityPage />} />
                <Route path="/memory" element={<MemoryPage />} />
                <Route path="/evidence" element={<EvidencePage />} />
                <Route path="/behavior" element={<BehaviorPage />} />
                <Route path="/planning" element={<PlanningPage />} />
                <Route path="/decision" element={<DecisionPage />} />
                <Route path="/learning" element={<LearningPage />} />
                <Route path="/guardian" element={<GuardianPage />} />
                <Route path="/character" element={<CharacterPage />} />
                <Route path="/insights" element={<InsightsPage />} />
                <Route path="/report" element={<ReportPage />} />
                <Route path="/mirror" element={<MirrorPage />} />
                <Route path="/pipeline" element={<PipelinePage />} />
                <Route path="/trace/:traceId" element={<TracePage />} />
                <Route path="/analytics" element={<AnalyticsPage />} />
                <Route path="/chat" element={<ChatPage />} />
                <Route path="/guide" element={<GuidePage />} />
                <Route path="/documentation" element={<DocumentationPage />} />
                <Route path="/settings" element={<SettingsPage />} />
              </Routes>
              </div>
            </Suspense>
          </ErrorBoundary>
        </div>

        <footer style={{
          textAlign: 'center', padding: '20px',
          fontSize: 12, color: 'var(--text-muted)',
          borderTop: '1px solid var(--border-subtle)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
        }}>
          <span className="pulse-dot" style={{
            width: 6, height: 6, borderRadius: '50%',
            background: 'var(--emerald-400)', color: 'var(--emerald-400)', display: 'inline-block',
          }} />
          AIMirror — Cognitive Digital Twin
        </footer>
      </main>

      <SetupToast />
    </div>
  )
}
