import { useRef, useEffect } from 'react'
import Tilt from '../motion/Tilt'

/**
 * The app's general content surface. The existing contract is unchanged —
 * every page that renders <GlassCard gradient> keeps working exactly as it
 * did — with two additions:
 *
 *  - the cursor-tracking `--x`/`--y` this already published now actually
 *    drives something visible (the `.spotlight` glow in motion.css), where
 *    before they were written on every mousemove and never read;
 *  - `tilt` opts a card into 3D. It's off by default because most of these
 *    wrap charts and tables, and tilting a data grid hurts legibility — it's
 *    for the small showcase cards.
 */
export default function GlassCard({
  children,
  className = '',
  gradient = false,
  hover = true,
  padding = 'xl',
  animate = false,
  tilt = false,
  style = {},
  ...rest
}) {
  const cardRef = useRef(null)
  const padMap = { sm: '12px', md: '16px', lg: '20px', xl: '24px', '2xl': '32px' }

  useEffect(() => {
    if (!hover || !cardRef.current) return
    const card = cardRef.current
    const handleMove = (e) => {
      const rect = card.getBoundingClientRect()
      const x = (e.clientX - rect.left) / rect.width
      const y = (e.clientY - rect.top) / rect.height
      card.style.setProperty('--x', x)
      card.style.setProperty('--y', y)
    }
    card.addEventListener('mousemove', handleMove)
    return () => card.removeEventListener('mousemove', handleMove)
  }, [hover])

  const card = (
    <div
      ref={cardRef}
      className={`card ${gradient ? 'card-gradient' : ''} ${hover ? 'spotlight' : ''} ${animate ? 'animate-fade' : ''} ${className}`.trim()}
      style={{ padding: padMap[padding] || padMap.xl, height: tilt ? '100%' : undefined, ...style }}
      {...rest}
    >
      {children}
    </div>
  )

  if (!tilt) return card

  return (
    <Tilt max={6} scale={1.012} style={{ height: '100%' }} innerStyle={{ height: '100%' }}>
      {card}
    </Tilt>
  )
}
