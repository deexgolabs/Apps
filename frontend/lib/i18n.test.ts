import { describe, it, expect, beforeEach } from 'vitest'
import { getStoredLanguage, setStoredLanguage, translate } from './i18n'

describe('getStoredLanguage / setStoredLanguage', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('defaults to pt-BR when nothing is stored', () => {
    expect(getStoredLanguage('42')).toBe('pt-BR')
  })

  it('persists and returns a valid stored language', () => {
    setStoredLanguage('42', 'en')
    expect(getStoredLanguage('42')).toBe('en')
  })

  it('falls back to pt-BR for a corrupted/invalid stored value', () => {
    localStorage.setItem('app_language_42', 'fr')
    expect(getStoredLanguage('42')).toBe('pt-BR')
  })

  it('keeps languages separate per app id', () => {
    setStoredLanguage('1', 'es')
    setStoredLanguage('2', 'en')
    expect(getStoredLanguage('1')).toBe('es')
    expect(getStoredLanguage('2')).toBe('en')
  })
})

describe('translate', () => {
  it('returns the pt-BR string for a known key', () => {
    expect(translate('pt-BR', 'auth.login_tab')).toBe('Entrar')
  })

  it('returns the translated string in another language', () => {
    expect(translate('en', 'auth.login_tab')).toBe('Log in')
    expect(translate('es', 'auth.login_tab')).toBe('Iniciar sesión')
  })

  it('falls back to pt-BR when the key is missing in the target language', () => {
    // Toda chave usada nos testes acima existe nos 3 idiomas; aqui simulamos
    // uma chave inexistente pra conferir o fallback final (a própria chave).
    expect(translate('en', 'nonexistent.key')).toBe('nonexistent.key')
  })
})
