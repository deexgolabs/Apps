import { afterEach, describe, expect, it, vi } from 'vitest'
import { printComanda } from './printComanda'

function fakePrintWindow() {
  let written = ''
  return {
    document: {
      open: vi.fn(),
      write: vi.fn((html: string) => {
        written = html
      }),
      close: vi.fn(),
    },
    getWritten: () => written,
  }
}

describe('printComanda', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('writes a printable document with app name, title, items and total', () => {
    const win = fakePrintWindow()
    vi.spyOn(window, 'open').mockReturnValue(win as unknown as Window)

    printComanda({
      appName: 'Pizzaria do João',
      title: 'Pedido #42',
      subtitle: 'Mesa 3',
      lines: [
        { label: 'Pizza Grande', qty: 2, unitPrice: 30, total: 60 },
        { label: 'Refrigerante', qty: 1, unitPrice: 8, total: 8 },
      ],
      total: 68,
    })

    const html = win.getWritten()
    expect(html).toContain('Pizzaria do João')
    expect(html).toContain('Pedido #42')
    expect(html).toContain('Mesa 3')
    expect(html).toContain('2x Pizza Grande')
    expect(html).toContain('R$ 60.00')
    expect(html).toContain('R$ 68.00')
    expect(html).toContain('window.print()')
    expect(win.document.open).toHaveBeenCalled()
    expect(win.document.close).toHaveBeenCalled()
  })

  it('escapes HTML-sensitive characters in labels and footer', () => {
    const win = fakePrintWindow()
    vi.spyOn(window, 'open').mockReturnValue(win as unknown as Window)

    printComanda({
      appName: 'App <Teste>',
      title: 'Pedido "especial"',
      lines: [{ label: '<script>alert(1)</script>', total: 1 }],
      total: 1,
      footer: 'obs: cliente & "vip"',
    })

    const html = win.getWritten()
    expect(html).not.toContain('<script>alert(1)</script>')
    expect(html).toContain('&lt;script&gt;')
    expect(html).toContain('App &lt;Teste&gt;')
    expect(html).toContain('&quot;especial&quot;')
    expect(html).toContain('cliente &amp; &quot;vip&quot;')
  })

  it('shows a placeholder when there are no items', () => {
    const win = fakePrintWindow()
    vi.spyOn(window, 'open').mockReturnValue(win as unknown as Window)

    printComanda({ appName: 'Loja', title: 'Mesa 1', lines: [], total: 0 })

    expect(win.getWritten()).toContain('Nenhum item')
  })

  it('throws when the browser blocks the popup', () => {
    vi.spyOn(window, 'open').mockReturnValue(null)

    expect(() =>
      printComanda({ appName: 'Loja', title: 'Mesa 1', lines: [], total: 0 })
    ).toThrow('popup-blocked')
  })
})
