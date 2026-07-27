import { describe, expect, it } from 'vitest'
import { parseCustomFields } from './moduleFields'

describe('parseCustomFields', () => {
  it('parses a plain label as a required-false texto field', () => {
    const fields = parseCustomFields('Nome')
    expect(fields).toEqual([{ key: 'Nome', label: 'Nome', type: 'texto', required: false }])
  })

  it('marks fields ending in * as required and strips the marker', () => {
    const fields = parseCustomFields('Nome*')
    expect(fields).toEqual([{ key: 'Nome', label: 'Nome', type: 'texto', required: true }])
  })

  it('parses numero and data types, defaulting unknown types to texto', () => {
    const fields = parseCustomFields('Telefone:numero\nData de nascimento:data\nMensagem:algo_invalido')
    expect(fields.map((f) => f.type)).toEqual(['numero', 'data', 'texto'])
  })

  it('combines required marker with an explicit type', () => {
    const fields = parseCustomFields('Telefone*:numero')
    expect(fields[0]).toEqual({ key: 'Telefone', label: 'Telefone', type: 'numero', required: true })
  })

  it('ignores blank lines', () => {
    const fields = parseCustomFields('Nome*\n\nTelefone:numero\n')
    expect(fields).toHaveLength(2)
  })

  it('returns empty array for empty input', () => {
    expect(parseCustomFields('')).toEqual([])
  })
})
