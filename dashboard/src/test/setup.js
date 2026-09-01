import '@testing-library/jest-dom/vitest'
import { vi, afterEach } from 'vitest'
import { cleanup } from '@testing-library/react'

// jsdom implements neither of these, and both are load-bearing in this app:
// every scroll reveal is gated on IntersectionObserver, and useMediaQuery
// drives the desktop-rail vs mobile-drawer branch. Without stubs, any
// component touching them throws on render rather than failing a real
// assertion.

// Reveals resolve to "visible" immediately: these tests assert on content,
// and animation state would otherwise hide everything behind opacity 0.
class MockIntersectionObserver {
  constructor(callback) {
    this.callback = callback
  }
  observe(target) {
    this.callback([{ isIntersecting: true, target }], this)
  }
  unobserve() {}
  disconnect() {}
  takeRecords() { return [] }
}

vi.stubGlobal('IntersectionObserver', MockIntersectionObserver)

// Defaults to "does not match", i.e. desktop and no reduced-motion preference.
// Individual tests override window.matchMedia when they need the other branch.
vi.stubGlobal('matchMedia', (query) => ({
  matches: false,
  media: query,
  onchange: null,
  addEventListener: () => {},
  removeEventListener: () => {},
  addListener: () => {},
  removeListener: () => {},
  dispatchEvent: () => false,
}))

// Scenes are decorative and never assert-worthy; jsdom has no WebGL context,
// so anything that probes for one should cleanly get "unsupported".
HTMLCanvasElement.prototype.getContext = () => null

afterEach(() => {
  cleanup()
})
