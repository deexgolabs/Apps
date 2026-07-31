import { beforeEach, describe, expect, it, vi } from 'vitest'
import api from './api'
import { useAuthStore } from '@/store/useAuthStore'

// @ts-expect-error - acessando o handler registrado direto pra testar sem precisar de rede real
const rejectedHandler = api.interceptors.response.handlers[0].rejected

beforeEach(() => {
  useAuthStore.setState({ token: 'sometoken', user: null, isAuthenticated: true })
  localStorage.setItem('token', 'sometoken')
  delete (window as any).location
  ;(window as any).location = { href: '' }
})

describe('api response interceptor', () => {
  it('forces logout on 401 from an authenticated request', async () => {
    const error = { response: { status: 401 }, config: { headers: { Authorization: 'Bearer sometoken' } } }
    await expect(rejectedHandler(error)).rejects.toBe(error)

    expect(useAuthStore.getState().isAuthenticated).toBe(false)
    expect(localStorage.getItem('token')).toBeNull()
    expect(window.location.href).toBe('/auth/login')
  })

  it('does not force logout on 401 from an unauthenticated request (e.g. wrong login password)', async () => {
    const error = { response: { status: 401 }, config: { headers: {} } }
    await expect(rejectedHandler(error)).rejects.toBe(error)

    expect(useAuthStore.getState().isAuthenticated).toBe(true)
    expect(localStorage.getItem('token')).toBe('sometoken')
    expect(window.location.href).toBe('')
  })
})
