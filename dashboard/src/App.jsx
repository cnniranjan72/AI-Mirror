import { lazy, Suspense } from 'react'
import { BrowserRouter as Router } from 'react-router-dom'
import AppShell from './components/layout/AppShell'
import { useIdleReady } from './hooks/useMotion'
// Order matters: motion.css is the override layer and must load LAST, or
// App.css's older .empty-state / .skeleton / .card rules win over it. (It was
// imported before App.css at first, which silently disabled those overrides.)
import './styles/design-system.css'
import './App.css'
import './styles/motion.css'

// Lazy, not static: this pulls in three.js/fiber/drei (~1MB raw). Importing it
// at the top level would put that chunk on the critical path for every visitor
// before a single pixel of dashboard renders.
const AmbientField = lazy(() => import('./three/AmbientField'))

/**
 * Mounts the ambient WebGL field only once the browser has gone idle, so the
 * three.js fetch never competes with the app's first data requests. The page
 * is fully usable before this appears, and equally usable if it never does.
 */
function DeferredAmbientField() {
  const ready = useIdleReady(700)
  if (!ready) return null
  return (
    <Suspense fallback={null}>
      <AmbientField />
    </Suspense>
  )
}

function App() {
  return (
    <Router>
      {/* Inside the Router but outside AppShell, for two reasons: it needs
          useLocation to tint itself per route, and living above the shell
          means route changes never unmount it — one WebGL context is acquired
          for the whole session instead of one per navigation. It renders
          behind #root and self-disables on unsupported/low-end setups. */}
      <DeferredAmbientField />
      <AppShell />
    </Router>
  )
}

export default App
