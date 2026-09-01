import { Component } from 'react'

/**
 * Error boundary for decorative 3D. A shader that fails to compile on some
 * driver, a lost context, or an out-of-memory Canvas must never take a page
 * with it — every scene in this app is presentation over content that works
 * without it, so the correct recovery is always "render nothing and move on".
 *
 * Deliberately silent in the UI: there is no user-actionable failure here and
 * a visible error card would be worse than the missing decoration. The console
 * warning is kept so it's still diagnosable in the field.
 */
export default class SceneBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { failed: false }
  }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  componentDidCatch(error) {
    console.warn('[AIMirror] 3D scene disabled after error:', error?.message || error)
  }

  render() {
    if (this.state.failed) return this.props.fallback ?? null
    return this.props.children
  }
}
