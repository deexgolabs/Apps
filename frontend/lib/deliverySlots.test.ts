import { describe, expect, it } from 'vitest'
import { generateDeliverySlots, parsePickupPoints } from './deliverySlots'

describe('parsePickupPoints', () => {
  it('parses "Nome: Endereço" lines', () => {
    const points = parsePickupPoints('Loja Centro: Rua A, 123\nLoja Zona Sul: Av. B, 456')
    expect(points).toEqual([
      { name: 'Loja Centro', address: 'Rua A, 123' },
      { name: 'Loja Zona Sul', address: 'Av. B, 456' },
    ])
  })

  it('allows a bare name with no address', () => {
    expect(parsePickupPoints('Loja Única')).toEqual([{ name: 'Loja Única', address: '' }])
  })

  it('keeps extra colons as part of the address', () => {
    expect(parsePickupPoints('Loja: Rua A: esquina com B')).toEqual([
      { name: 'Loja', address: 'Rua A: esquina com B' },
    ])
  })

  it('ignores blank lines and returns empty array for empty input', () => {
    expect(parsePickupPoints('\n\n')).toEqual([])
    expect(parsePickupPoints('')).toEqual([])
  })
})

describe('generateDeliverySlots', () => {
  it('generates hoje/amanhã options for each configured window', () => {
    const now = new Date(2026, 0, 1, 8, 0) // 08:00, well before any window
    const slots = generateDeliverySlots('11:00-12:00\n18:00-19:00', now)
    expect(slots).toEqual([
      { label: 'Hoje 11:00-12:00', value: 'Hoje 11:00-12:00' },
      { label: 'Hoje 18:00-19:00', value: 'Hoje 18:00-19:00' },
      { label: 'Amanhã 11:00-12:00', value: 'Amanhã 11:00-12:00' },
      { label: 'Amanhã 18:00-19:00', value: 'Amanhã 18:00-19:00' },
    ])
  })

  it('skips today windows that already started, but keeps tomorrow', () => {
    const now = new Date(2026, 0, 1, 12, 30) // 12:30 -- the 11-12 window already passed
    const slots = generateDeliverySlots('11:00-12:00\n18:00-19:00', now)
    expect(slots).toEqual([
      { label: 'Hoje 18:00-19:00', value: 'Hoje 18:00-19:00' },
      { label: 'Amanhã 11:00-12:00', value: 'Amanhã 11:00-12:00' },
      { label: 'Amanhã 18:00-19:00', value: 'Amanhã 18:00-19:00' },
    ])
  })

  it('ignores malformed lines', () => {
    expect(generateDeliverySlots('não é um horário', new Date(2026, 0, 1, 8, 0))).toEqual([])
  })

  it('returns empty array for empty config', () => {
    expect(generateDeliverySlots('', new Date())).toEqual([])
  })
})
