import { useState, Suspense } from 'react'
import { Routes, Route } from 'react-router-dom'
import { Canvas } from '@react-three/fiber'
import { View } from '@react-three/drei'
import Sidebar from './Sidebar'
import ErrorBoundary from '../ErrorBoundary'
import LoadingSkeleton from '../ui/LoadingSkeleton'

import LandingPage from '../../pages/LandingPage'
import Overview from '../../pages/Overview'
import IngestionPage from '../../pages/ingestion/IngestionPage'
import TimelinePage from '../../pages/timeline/TimelinePage'
import KnowledgeGraphPage from '../../pages/graph/KnowledgeGraphPage'
import DiaryPage from '../../pages/diary/DiaryPage'
import IdentityPage from '../../pages/identity/IdentityPage'
import MemoryPage from '../../pages/memory/MemoryPage'
import EvidencePage from '../../pages/evidence/EvidencePage'
import BehaviorPage from '../../pages/behavior/BehaviorPage'
import PlanningPage from '../../pages/planning/PlanningPage'
import DecisionPage from '../../pages/decision/DecisionPage'
import LearningPage from '../../pages/learning/LearningPage'
import GuardianPage from '../../pages/guardian/GuardianPage'
import CharacterPage from '../../pages/character/CharacterPage'
import InsightsPage from '../../pages/insights/InsightsPage'
import PipelinePage from '../../pages/pipeline/PipelinePage'
import TracePage from '../../pages/trace/TracePage'
import AnalyticsPage from '../../pages/analytics/AnalyticsPage'
import ChatPage from '../../pages/chat/ChatPage'
import SettingsPage from '../../pages/settings/SettingsPage'
import GuidePage from '../../pages/guide/GuidePage'
import DocumentationPage from '../../pages/documentation/DocumentationPage'

const PageLoading = () => (
  <div style={{ padding: '32px' }}>
    <LoadingSkeleton type="card" count={3} />
    <div style={{ height: 24 }} />
    <LoadingSkeleton type="chart" />
  </div>
)

export default function AppShell() {
  const [collapsed, setCollapsed] = useState(false)
  const sidebarWidth = collapsed ? 'var(--sidebar-collapsed)' : 'var(--sidebar-width)'

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      {/* Every CharacterCreature3D on every page renders into this single shared
          canvas via <View> instead of mounting its own <Canvas>. Route changes
          swap which View is in the DOM, not the WebGL context itself — this is
          what keeps navigation from tearing down/recreating a context on every
          page (the source of the react-three-fiber StrictMode unmount warning). */}
      <Canvas
        gl={{ alpha: true, antialias: true }}
        dpr={[1, 2]}
        style={{ position: 'fixed', inset: 0, width: '100vw', height: '100vh', pointerEvents: 'none', zIndex: 0 }}
      >
        <View.Port />
      </Canvas>

      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed(c => !c)} />

      <main style={{
        marginLeft: sidebarWidth,
        flex: 1,
        minHeight: '100vh',
        transition: 'margin-left 0.3s cubic-bezier(0.16,1,0.3,1)',
        display: 'flex', flexDirection: 'column',
      }}>
        <div style={{
          flex: 1,
          padding: '32px',
          maxWidth: 1440,
          width: '100%',
          margin: '0 auto',
        }}>
          <ErrorBoundary>
            <Suspense fallback={<PageLoading />}>
              <Routes>
                <Route path="/" element={<LandingPage />} />
                <Route path="/dashboard" element={<Overview />} />
                <Route path="/import" element={<IngestionPage />} />
                <Route path="/timeline" element={<TimelinePage />} />
                <Route path="/graph" element={<KnowledgeGraphPage />} />
                <Route path="/diary" element={<DiaryPage />} />
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
                <Route path="/pipeline" element={<PipelinePage />} />
                <Route path="/trace/:traceId" element={<TracePage />} />
                <Route path="/analytics" element={<AnalyticsPage />} />
                <Route path="/chat" element={<ChatPage />} />
                <Route path="/guide" element={<GuidePage />} />
                <Route path="/documentation" element={<DocumentationPage />} />
                <Route path="/settings" element={<SettingsPage />} />
              </Routes>
            </Suspense>
          </ErrorBoundary>
        </div>

        <footer style={{
          textAlign: 'center', padding: '20px',
          fontSize: 12, color: 'var(--text-muted)',
          borderTop: '1px solid var(--border-subtle)',
        }}>
          AIMirror — Cognitive Digital Twin
        </footer>
      </main>
    </div>
  )
}
