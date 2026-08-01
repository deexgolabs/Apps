import { describe, it, expect, beforeEach } from 'vitest'
import { getOrCreateVisitorHash } from './analytics'

describe('getOrCreateVisitorHash', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('creates a hash and persists it in localStorage', () => {
    const hash = getOrCreateVisitorHash('42')
    expect(hash).toBeTruthy()
    expect(localStorage.getItem('visitor_hash_42')).toBe(hash)
  })

  it('returns the same hash on subsequent calls for the same app', () => {
    const first = getOrCreateVisitorHash('42')
    const second = getOrCreateVisitorHash('42')
    expect(second).toBe(first)
  })

  it('uses separate hashes per app id', () => {
    const hashA = getOrCreateVisitorHash('1')
    const hashB = getOrCreateVisitorHash('2')
    expect(hashA).not.toBe(hashB)
  })
})
