import { cloneElement, isValidElement } from 'react'
import { useInView } from '../../hooks/useMotion'

/**
 * Scroll-triggered entrance. Adds `.is-in` once the element enters the
 * viewport; motion.css owns the actual transition, so this component stays a
 * few lines and costs one render per element for its whole lifetime.
 *
 *   <Reveal variant="depth" delay={120}><GlassCard>…</GlassCard></Reveal>
 *
 * `asChild` applies the classes to the child element instead of wrapping it
 * in a <div> — useful inside grids, where an extra wrapper changes which
 * element is the grid item. It passes a ref to the child, so the child MUST
 * be a DOM element or a forwardRef component; a plain function component
 * would swallow the ref. (useInView fails open if that happens, so the
 * content still shows — but the animation is lost, so prefer the wrapper.)
 */
export default function Reveal({
  children,
  variant = 'up',        // up | left | right | scale | depth | blur
  delay = 0,
  threshold = 0.15,
  once = true,
  asChild = false,
  className = '',
  style = {},
  ...rest
}) {
  const [ref, inView] = useInView({ threshold, once })

  const variantClass = variant && variant !== 'up' ? ` reveal-${variant}` : ''
  const cls = `reveal${variantClass}${inView ? ' is-in' : ''} ${className}`.trim()
  const mergedStyle = { '--reveal-delay': `${delay}ms`, ...style }

  if (asChild && isValidElement(children)) {
    return cloneElement(children, {
      ref,
      className: `${children.props.className || ''} ${cls}`.trim(),
      style: { ...mergedStyle, ...(children.props.style || {}) },
    })
  }

  return (
    <div ref={ref} className={cls} style={mergedStyle} {...rest}>
      {children}
    </div>
  )
}
