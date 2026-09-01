import { useTilt } from '../../hooks/useMotion'

/**
 * Pointer-tracking 3D tilt with a specular glare. The hook writes CSS custom
 * properties straight onto the node, so hovering never re-renders React.
 *
 * The two-element structure is required, not stylistic — see the `.tilt` /
 * `.tilt-inner` note in motion.css.
 */
export default function Tilt({
  children,
  max = 9,
  scale = 1.015,
  glare = true,
  disabled = false,
  className = '',
  innerClassName = '',
  style = {},
  innerStyle = {},
  ...rest
}) {
  const ref = useTilt({ max, scale, glare, disabled })

  return (
    <div className={`tilt ${className}`.trim()} style={style} {...rest}>
      <div ref={ref} className={`tilt-inner ${innerClassName}`.trim()} style={innerStyle}>
        {children}
      </div>
    </div>
  )
}
