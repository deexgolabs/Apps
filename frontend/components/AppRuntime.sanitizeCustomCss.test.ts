import { describe, expect, it } from 'vitest'
import { sanitizeCustomCss } from './AppRuntime'

describe('sanitizeCustomCss', () => {
  it('leaves normal CSS untouched', () => {
    const css = '.app-header { border-radius: 0 0 16px 16px; color: #fff; }'
    expect(sanitizeCustomCss(css)).toBe(css)
  })

  it('strips an attempt to close the style tag', () => {
    const css = 'body{}</style><img src=x onerror=alert(1)>'
    const result = sanitizeCustomCss(css)
    expect(result).not.toContain('</style')
  })

  it('strips an attempt to inject a script tag', () => {
    const css = 'body{}<script>alert(1)</script>'
    const result = sanitizeCustomCss(css)
    expect(result.toLowerCase()).not.toContain('<script')
  })

  it('is case-insensitive', () => {
    const css = 'a{}</STYLE><SCRIPT>x</SCRIPT>'
    const result = sanitizeCustomCss(css)
    expect(result.toLowerCase()).not.toContain('</style')
    expect(result.toLowerCase()).not.toContain('<script')
  })
})
