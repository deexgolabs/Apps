import { describe, expect, it } from 'vitest'
import { computeFrete, parseFreteRules } from './frete'

describe('parseFreteRules', () => {
  it('parses valid lines into prefix/price pairs', () => {
    const rules = parseFreteRules('01:10.00\n02:15.50\n')
    expect(rules).toEqual([
      { prefix: '01', price: 10.0 },
      { prefix: '02', price: 15.5 },
    ])
  })

  it('trims whitespace around prefix and value', () => {
    const rules = parseFreteRules(' 01 : 10.00 \n')
    expect(rules).toEqual([{ prefix: '01', price: 10.0 }])
  })

  it('ignores blank lines', () => {
    const rules = parseFreteRules('01:10.00\n\n\n02:5.00')
    expect(rules).toHaveLength(2)
  })

  it('drops lines with no prefix or non-numeric price', () => {
    const rules = parseFreteRules(':10.00\n01:abc\n01:10.00')
    expect(rules).toEqual([{ prefix: '01', price: 10.0 }])
  })

  it('returns empty array for empty or falsy input', () => {
    expect(parseFreteRules('')).toEqual([])
  })
})

describe('computeFrete', () => {
  const regras = '01:10.00\n013:20.00\n02:5.00'

  it('returns 0 when cep is empty', () => {
    expect(computeFrete(regras, '')).toBe(0)
  })

  it('returns 0 when no rule matches the cep', () => {
    expect(computeFrete(regras, '99999000')).toBe(0)
  })

  it('matches the first rule whose prefix the cep starts with, not the longest', () => {
    // '013...' bate tanto com '01' quanto com '013' — a semântica é "primeira
    // regra que bate", igual ao backend (compute_frete em app/utils.py).
    expect(computeFrete(regras, '01312345')).toBe(10.0)
  })

  it('matches a later rule when earlier ones do not apply', () => {
    expect(computeFrete(regras, '02000000')).toBe(5.0)
  })
})
