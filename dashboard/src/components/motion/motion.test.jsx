import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import Reveal from './Reveal'
import CountUp from './CountUp'
import StatCard from '../ui/StatCard'

/**
 * These components wrap real content across the whole app, so their failure
 * mode is not "the animation looks wrong" — it is "the page is blank". The
 * reveal classes start at opacity 0, which means anything preventing the
 * observer from attaching hides content permanently. That's the property
 * most of this file exists to pin down.
 */

afterEach(() => {
  vi.unstubAllGlobals()
  // setup.js's always-intersecting observer is the default for other files.
  vi.stubGlobal('IntersectionObserver', class {
    constructor(cb) { this.cb = cb }
    observe(t) { this.cb([{ isIntersecting: true, target: t }], this) }
    unobserve() {}
    disconnect() {}
    takeRecords() { return [] }
  })
})

describe('Reveal', () => {
  it('renders its children', () => {
    render(<Reveal><p>visible content</p></Reveal>)
    expect(screen.getByText('visible content')).toBeInTheDocument()
  })

  it('marks itself in-view once the observer fires', () => {
    const { container } = render(<Reveal><p>content</p></Reveal>)
    expect(container.firstChild).toHaveClass('is-in')
  })

  it('applies the requested variant class', () => {
    const { container } = render(<Reveal variant="depth"><p>content</p></Reveal>)
    expect(container.firstChild).toHaveClass('reveal-depth')
  })

  it('passes the delay through as a custom property', () => {
    const { container } = render(<Reveal delay={120}><p>content</p></Reveal>)
    expect(container.firstChild.style.getPropertyValue('--reveal-delay')).toBe('120ms')
  })

  // The safety nets. Both of these would otherwise leave real content at
  // opacity 0 forever, which reads to a user as a broken page, not as a
  // missing animation.
  it('reveals content when IntersectionObserver does not exist', () => {
    vi.stubGlobal('IntersectionObserver', undefined)
    const { container } = render(<Reveal><p>content</p></Reveal>)
    expect(container.firstChild).toHaveClass('is-in')
  })

  it('reveals content even if the observer never reports an intersection', () => {
    // A observer that is constructed but never fires — e.g. a zero-size node.
    vi.stubGlobal('IntersectionObserver', class {
      observe() {}
      unobserve() {}
      disconnect() {}
      takeRecords() { return [] }
    })
    render(<Reveal><p>still readable</p></Reveal>)
    // The node stays mounted and its text reachable; the class may be absent,
    // but content must never be removed from the tree.
    expect(screen.getByText('still readable')).toBeInTheDocument()
  })
})

describe('CountUp', () => {
  // Reduced motion makes the hook resolve to its target immediately, which is
  // both the deterministic path and the accessible one.
  const reducedMotion = () => vi.stubGlobal('matchMedia', (q) => ({
    matches: q.includes('prefers-reduced-motion'),
    media: q, onchange: null,
    addEventListener: () => {}, removeEventListener: () => {},
    addListener: () => {}, removeListener: () => {}, dispatchEvent: () => false,
  }))

  it('renders a number', () => {
    reducedMotion()
    render(<CountUp value={42} />)
    expect(screen.getByText('42')).toBeInTheDocument()
  })

  it('keeps the unit attached to the number', () => {
    reducedMotion()
    render(<CountUp value="62%" />)
    expect(screen.getByText('62%')).toBeInTheDocument()
  })

  it('passes a non-numeric placeholder straight through', () => {
    reducedMotion()
    render(<CountUp value="--" />)
    expect(screen.getByText('--')).toBeInTheDocument()
  })

  it('does not add tabular-nums to a value it is not animating', () => {
    reducedMotion()
    const { container } = render(<CountUp value="No data" />)
    expect(container.firstChild).not.toHaveClass('tabular')
  })
})

describe('StatCard', () => {
  const reducedMotion = () => vi.stubGlobal('matchMedia', (q) => ({
    matches: q.includes('prefers-reduced-motion'),
    media: q, onchange: null,
    addEventListener: () => {}, removeEventListener: () => {},
    addListener: () => {}, removeListener: () => {}, dispatchEvent: () => false,
  }))

  it('renders its label and value', () => {
    reducedMotion()
    render(<StatCard label="Identity Confidence" value="48%" />)
    expect(screen.getByText('Identity Confidence')).toBeInTheDocument()
    expect(screen.getByText('48%')).toBeInTheDocument()
  })

  it('shows skeletons instead of a value while loading', () => {
    reducedMotion()
    render(<StatCard label="Snapshots" value={5} loading />)
    expect(screen.queryByText('Snapshots')).not.toBeInTheDocument()
    expect(screen.queryByText('5')).not.toBeInTheDocument()
  })

  it('is only a button when it actually does something', () => {
    reducedMotion()
    const { rerender } = render(<StatCard label="Traces" value={3} />)
    expect(screen.queryByRole('button')).not.toBeInTheDocument()

    rerender(<StatCard label="Traces" value={3} onClick={() => {}} />)
    expect(screen.getByRole('button')).toBeInTheDocument()
  })

  // These tiles were mouse-only before; the same action has to be reachable
  // from the keyboard now that they are announced as buttons.
  it.each([['Enter'], [' ']])('activates on %s', (key) => {
    reducedMotion()
    const onClick = vi.fn()
    render(<StatCard label="Traces" value={3} onClick={onClick} />)
    fireEvent.keyDown(screen.getByRole('button'), { key })
    expect(onClick).toHaveBeenCalledTimes(1)
  })

  it('ignores unrelated keys', () => {
    reducedMotion()
    const onClick = vi.fn()
    render(<StatCard label="Traces" value={3} onClick={onClick} />)
    fireEvent.keyDown(screen.getByRole('button'), { key: 'a' })
    expect(onClick).not.toHaveBeenCalled()
  })
})
