/**
 * Motion primitives — the shared behavioural layer under every animated
 * surface in the app (scroll reveals, 3D tilt, count-ups, the ambient WebGL
 * field's pointer parallax).
 *
 * Two rules everything here follows:
 *  1. `prefers-reduced-motion` is honoured at the SOURCE, not by each caller —
 *     a hook that would animate simply resolves to its final value instantly.
 *  2. Continuous pointer/scroll signals are exposed as REFS, never state.
 *     A 60fps `setState` from pointermove would re-render the whole page tree
 *     on every mouse pixel; the 3D scenes read `.current` inside `useFrame`
 *     instead, so the React tree stays completely still while things move.
 */
import { useState, useEffect, useRef, useCallback } from 'react'

/** True when the OS asks for reduced motion. Live — follows the setting. */
export function useReducedMotion() {
  const [reduced, setReduced] = useState(() =>
    typeof window !== 'undefined' &&
    window.matchMedia?.('(prefers-reduced-motion: reduce)').matches === true
  )
  useEffect(() => {
    const mq = window.matchMedia?.('(prefers-reduced-motion: reduce)')
    if (!mq) return
    const onChange = (e) => setReduced(e.matches)
    // Safari <14 only has the deprecated listener API.
    mq.addEventListener ? mq.addEventListener('change', onChange) : mq.addListener(onChange)
    return () => {
      mq.removeEventListener ? mq.removeEventListener('change', onChange) : mq.removeListener(onChange)
    }
  }, [])
  return reduced
}

/**
 * Coarse device capability tier, used to decide how much WebGL work is safe.
 * Deliberately pessimistic: a phone or a 4-core laptop gets the cheap scene
 * rather than a janky expensive one.
 */
export function useDeviceTier() {
  const [tier] = useState(() => {
    if (typeof window === 'undefined') return 'low'
    const cores = navigator.hardwareConcurrency || 4
    const mem = navigator.deviceMemory || 4
    const narrow = window.innerWidth < 900
    const coarse = window.matchMedia?.('(pointer: coarse)').matches
    if (narrow || coarse || cores <= 4 || mem <= 4) return 'low'
    if (cores >= 8 && mem >= 8) return 'high'
    return 'mid'
  })
  return tier
}

/**
 * Fires once when an element scrolls into view. `once` is the default because
 * these drive entrance animations — re-triggering on every scroll-by makes a
 * long page feel like it's flickering rather than arriving.
 */
export function useInView({ threshold = 0.15, rootMargin = '0px 0px -60px 0px', once = true } = {}) {
  const ref = useRef(null)
  const [inView, setInView] = useState(false)

  useEffect(() => {
    const el = ref.current
    // Safety net, not an optimisation: the reveal classes start at opacity 0,
    // so anything that prevents the observer from attaching would hide real
    // content permanently. Both escape hatches below fail OPEN — a missing
    // node (e.g. the ref never landed on an element) or a browser without
    // IntersectionObserver shows the content immediately instead.
    if (!el) { setInView(true); return }
    if (typeof IntersectionObserver === 'undefined') { setInView(true); return }

    const io = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        setInView(true)
        if (once) io.disconnect()
      } else if (!once) {
        setInView(false)
      }
    }, { threshold, rootMargin })

    io.observe(el)
    return () => io.disconnect()
  }, [threshold, rootMargin, once])

  return [ref, inView]
}

/**
 * Normalised pointer position (-1..1 on both axes, origin at viewport centre)
 * as a ref. Also tracks a smoothed scroll ratio so scenes can drift with the
 * page. Nothing here ever triggers a React render.
 */
export function usePointerField() {
  const field = useRef({ x: 0, y: 0, scroll: 0, active: false })

  useEffect(() => {
    const onMove = (e) => {
      const w = window.innerWidth || 1
      const h = window.innerHeight || 1
      field.current.x = (e.clientX / w) * 2 - 1
      field.current.y = -((e.clientY / h) * 2 - 1)
      field.current.active = true
    }
    // Returning to rest when the pointer leaves avoids the scene being frozen
    // at whatever extreme angle the cursor exited at.
    const onLeave = () => { field.current.active = false }
    const onScroll = () => {
      const max = Math.max(1, document.documentElement.scrollHeight - window.innerHeight)
      field.current.scroll = Math.min(1, Math.max(0, window.scrollY / max))
    }

    window.addEventListener('pointermove', onMove, { passive: true })
    window.addEventListener('pointerleave', onLeave, { passive: true })
    window.addEventListener('scroll', onScroll, { passive: true })
    onScroll()
    return () => {
      window.removeEventListener('pointermove', onMove)
      window.removeEventListener('pointerleave', onLeave)
      window.removeEventListener('scroll', onScroll)
    }
  }, [])

  return field
}

/** 0..1 progress of the window's vertical scroll, as state (for progress bars). */
export function useScrollProgress() {
  const [progress, setProgress] = useState(0)
  useEffect(() => {
    let frame = 0
    const update = () => {
      frame = 0
      const max = Math.max(1, document.documentElement.scrollHeight - window.innerHeight)
      setProgress(Math.min(1, Math.max(0, window.scrollY / max)))
    }
    // rAF-coalesced: scroll fires far more often than we can usefully paint.
    const onScroll = () => { if (!frame) frame = requestAnimationFrame(update) }
    window.addEventListener('scroll', onScroll, { passive: true })
    update()
    return () => { window.removeEventListener('scroll', onScroll); if (frame) cancelAnimationFrame(frame) }
  }, [])
  return progress
}

const easeOutExpo = (t) => (t >= 1 ? 1 : 1 - Math.pow(2, -10 * t))

/**
 * Animates a number toward `target`. Animating from the PREVIOUS value (not
 * always from zero) matters here: these stats live-refresh, and replaying
 * 0 -> 62 every poll would read as the data resetting each time.
 */
export function useCountUp(target, { duration = 1100, decimals = 0 } = {}) {
  const reduced = useReducedMotion()
  const numeric = typeof target === 'number' && Number.isFinite(target)
  const [display, setDisplay] = useState(numeric ? target : 0)
  const fromRef = useRef(numeric ? target : 0)
  const rafRef = useRef(0)

  useEffect(() => {
    if (!numeric) return
    if (reduced || duration <= 0) { fromRef.current = target; setDisplay(target); return }

    const from = fromRef.current
    if (from === target) return
    const start = performance.now()

    const step = (now) => {
      const t = Math.min(1, (now - start) / duration)
      const eased = easeOutExpo(t)
      const value = from + (target - from) * eased
      const rounded = decimals > 0
        ? Math.round(value * 10 ** decimals) / 10 ** decimals
        : Math.round(value)
      setDisplay(rounded)
      if (t < 1) rafRef.current = requestAnimationFrame(step)
      else fromRef.current = target
    }

    rafRef.current = requestAnimationFrame(step)
    return () => cancelAnimationFrame(rafRef.current)
  }, [target, duration, decimals, reduced, numeric])

  return numeric ? display : target
}

/**
 * Splits a display value into an animatable number plus whatever wraps it, so
 * a count-up can be dropped in front of the values these pages already pass
 * ("62%", "v33", "1.2k", "--", plain numbers) without any caller changing.
 * Returns null when there's no number to animate — the caller then just
 * renders the original value untouched.
 */
export function parseAnimatableValue(value) {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return { prefix: '', num: value, suffix: '', decimals: Number.isInteger(value) ? 0 : 1 }
  }
  if (typeof value !== 'string') return null
  const m = value.match(/^([^\d\-+.]*)([-+]?\d*\.?\d+)(.*)$/)
  if (!m) return null
  const num = parseFloat(m[2])
  if (!Number.isFinite(num)) return null
  const decimalPart = m[2].split('.')[1]
  return { prefix: m[1] || '', num, suffix: m[3] || '', decimals: decimalPart ? decimalPart.length : 0 }
}

/**
 * 3D tilt on pointer move. Writes CSS custom properties directly on the node
 * (--rx/--ry/--mx/--my) instead of going through React state — the transform
 * and the glare highlight are then pure CSS, so a hovered card costs no
 * renders at all.
 */
export function useTilt({ max = 9, scale = 1.015, glare = true, disabled = false } = {}) {
  const ref = useRef(null)
  const reduced = useReducedMotion()
  const raf = useRef(0)

  const apply = useCallback((rx, ry, mx, my, active) => {
    const el = ref.current
    if (!el) return
    el.style.setProperty('--rx', `${rx}deg`)
    el.style.setProperty('--ry', `${ry}deg`)
    el.style.setProperty('--mx', `${mx}%`)
    el.style.setProperty('--my', `${my}%`)
    el.style.setProperty('--tilt-scale', active ? String(scale) : '1')
    el.style.setProperty('--glare', active && glare ? '1' : '0')
  }, [scale, glare])

  useEffect(() => {
    const el = ref.current
    if (!el || reduced || disabled) return

    const onMove = (e) => {
      if (raf.current) return
      raf.current = requestAnimationFrame(() => {
        raf.current = 0
        const rect = el.getBoundingClientRect()
        if (!rect.width || !rect.height) return
        const px = (e.clientX - rect.left) / rect.width
        const py = (e.clientY - rect.top) / rect.height
        apply(
          (0.5 - py) * max * 2,
          (px - 0.5) * max * 2,
          px * 100,
          py * 100,
          true,
        )
      })
    }
    const onLeave = () => {
      if (raf.current) { cancelAnimationFrame(raf.current); raf.current = 0 }
      apply(0, 0, 50, 50, false)
    }

    el.addEventListener('pointermove', onMove)
    el.addEventListener('pointerleave', onLeave)
    return () => {
      el.removeEventListener('pointermove', onMove)
      el.removeEventListener('pointerleave', onLeave)
      if (raf.current) cancelAnimationFrame(raf.current)
    }
  }, [apply, max, reduced, disabled])

  return ref
}

/**
 * Flips true once the browser is idle (or after `timeout` ms, whichever comes
 * first). Used to hold back purely decorative work — the ambient WebGL scene
 * pulls a ~1MB three.js chunk, and fetching that in parallel with the page's
 * first data requests would trade real time-to-content for decoration.
 *
 * requestIdleCallback isn't in Safari, hence the setTimeout fallback.
 */
export function useIdleReady(timeout = 800) {
  const [ready, setReady] = useState(false)

  useEffect(() => {
    let cancelled = false
    const done = () => { if (!cancelled) setReady(true) }

    if (typeof window !== 'undefined' && 'requestIdleCallback' in window) {
      const id = window.requestIdleCallback(done, { timeout })
      return () => { cancelled = true; window.cancelIdleCallback?.(id) }
    }
    const id = setTimeout(done, timeout)
    return () => { cancelled = true; clearTimeout(id) }
  }, [timeout])

  return ready
}

/**
 * True while the document is visible. Every render loop in the app gates on
 * this — a backgrounded tab that keeps driving WebGL is pure battery burn
 * (and browsers throttle it into stutter anyway).
 */
export function usePageVisible() {
  const [visible, setVisible] = useState(() =>
    typeof document === 'undefined' ? true : document.visibilityState !== 'hidden'
  )
  useEffect(() => {
    const onChange = () => setVisible(document.visibilityState !== 'hidden')
    document.addEventListener('visibilitychange', onChange)
    return () => document.removeEventListener('visibilitychange', onChange)
  }, [])
  return visible
}
