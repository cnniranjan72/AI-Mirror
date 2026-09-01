import { describe, it, expect } from 'vitest'
import { parseAnimatableValue } from './useMotion'

/**
 * parseAnimatableValue is what lets <CountUp> be dropped in front of values
 * the dashboard was already rendering, without any call site changing. Those
 * call sites pass wildly different shapes — "62%", "v33", "--", raw numbers —
 * from a dozen endpoints, so the parser's job is as much about what it
 * REFUSES to animate as what it does.
 */
describe('parseAnimatableValue', () => {
  it('animates a plain integer', () => {
    expect(parseAnimatableValue(42)).toEqual({ prefix: '', num: 42, suffix: '', decimals: 0 })
  })

  it('keeps one decimal place for a fractional number', () => {
    const parsed = parseAnimatableValue(3.5)
    expect(parsed.num).toBe(3.5)
    expect(parsed.decimals).toBe(1)
  })

  it('splits a trailing unit off so the unit is preserved verbatim', () => {
    expect(parseAnimatableValue('62%')).toEqual({ prefix: '', num: 62, suffix: '%', decimals: 0 })
  })

  it('splits a leading prefix, as used by identity version labels', () => {
    expect(parseAnimatableValue('v33')).toEqual({ prefix: 'v', num: 33, suffix: '', decimals: 0 })
  })

  it('handles a prefix and a suffix at once', () => {
    expect(parseAnimatableValue('~1.5k')).toEqual({ prefix: '~', num: 1.5, suffix: 'k', decimals: 1 })
  })

  it('reads decimal places from the string, not from the parsed float', () => {
    // 1.50 -> 1.5 numerically; the display should still keep two places.
    expect(parseAnimatableValue('1.50s').decimals).toBe(2)
  })

  it('preserves a negative sign as part of the number', () => {
    const parsed = parseAnimatableValue('-12%')
    expect(parsed.num).toBe(-12)
    expect(parsed.suffix).toBe('%')
  })

  // The refusals matter most: a wrong "0" in place of a placeholder would
  // read as real data that happens to be zero.
  it.each([
    ['--', 'the app-wide empty placeholder'],
    ['No data', 'an empty-state label'],
    ['', 'an empty string'],
  ])('refuses to animate %s (%s)', (value) => {
    expect(parseAnimatableValue(value)).toBeNull()
  })

  it.each([
    [null], [undefined], [{}], [[]], [NaN], [Infinity],
  ])('refuses non-values like %s', (value) => {
    expect(parseAnimatableValue(value)).toBeNull()
  })
})
