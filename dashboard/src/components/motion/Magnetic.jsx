import { useRef, useEffect } from 'react'
import { useReducedMotion } from '../../hooks/useMotion'

/**
 * Magnetic hover: the element leans toward the cursor while it's nearby and
 * springs back when it leaves. Used on primary CTAs, where the pull is what
 * makes a button feel physically present rather than just coloured.
 *
 * Transforms are written directly to the node (no state) so a hovered button
 * never re-renders the page around it.
 */
export default function Magnetic({ children, strength = 0.32, radius = 90, className = '', style = {}, ...rest }) {
  const ref = useRef(null)
  const raf = useRef(0)
  const reduced = useReducedMotion()

  useEffect(() => {
    const el = ref.current
    if (!el || reduced) return

    const onMove = (e) => {
      if (raf.current) return
      raf.current = requestAnimationFrame(() => {
        raf.current = 0
        const rect = el.getBoundingClientRect()
        const cx = rect.left + rect.width / 2
        const cy = rect.top + rect.height / 2
        const dx = e.clientX - cx
        const dy = e.clientY - cy
        // Fall off with distance so the pull eases in as the cursor
        // approaches instead of snapping on at the hit-box edge.
        const dist = Math.hypot(dx, dy)
        const falloff = Math.max(0, 1 - dist / (Math.max(rect.width, rect.height) / 2 + radius))
        el.style.transform = `translate3d(${dx * strength * falloff}px, ${dy * strength * falloff}px, 0)`
      })
    }
    const onLeave = () => {
      if (raf.current) { cancelAnimationFrame(raf.current); raf.current = 0 }
      el.style.transform = 'translate3d(0,0,0)'
    }

    // Listening on window (not the element) is what lets the button react
    // before the cursor actually reaches it.
    window.addEventListener('pointermove', onMove, { passive: true })
    el.addEventListener('pointerleave', onLeave)
    return () => {
      window.removeEventListener('pointermove', onMove)
      el.removeEventListener('pointerleave', onLeave)
      if (raf.current) cancelAnimationFrame(raf.current)
    }
  }, [strength, radius, reduced])

  return (
    <div
      ref={ref}
      className={className}
      style={{ display: 'inline-flex', transition: 'transform 420ms var(--ease-spring)', ...style }}
      {...rest}
    >
      {children}
    </div>
  )
}
