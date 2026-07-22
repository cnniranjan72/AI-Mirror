import { useRef, useEffect } from 'react'

export default function GlassCard({ children, className = '', gradient = false, hover = true, padding = 'xl', animate = false, style = {} }) {
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

  return (
    <div
      ref={cardRef}
      className={`card ${gradient ? 'card-gradient' : ''} ${animate ? 'animate-fade' : ''} ${className}`}
      style={{ padding: padMap[padding] || padMap.xl, ...style }}
    >
      {children}
    </div>
  )
}
