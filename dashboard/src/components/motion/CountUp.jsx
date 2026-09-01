import { useCountUp, parseAnimatableValue } from '../../hooks/useMotion'

/**
 * Animates the numeric part of a display value while preserving whatever
 * wraps it — "62%" counts the 62, "v33" counts the 33, "--" and "No data"
 * pass straight through untouched.
 *
 * That tolerance is the point: these pages already pass pre-formatted strings
 * from a dozen different endpoints, so this can be dropped in without any
 * caller having to separate its number from its unit.
 */
export default function CountUp({ value, duration = 1100, className = '', style = {} }) {
  const parsed = parseAnimatableValue(value)
  // Hooks can't be conditional — run it with a stable no-op target when the
  // value isn't numeric, and ignore the result below.
  const animated = useCountUp(parsed ? parsed.num : 0, {
    duration,
    decimals: parsed ? parsed.decimals : 0,
  })

  if (!parsed) {
    return <span className={className} style={style}>{value}</span>
  }

  const shown = parsed.decimals > 0 ? animated.toFixed(parsed.decimals) : animated
  return (
    <span className={`tabular ${className}`.trim()} style={style}>
      {parsed.prefix}{shown}{parsed.suffix}
    </span>
  )
}
