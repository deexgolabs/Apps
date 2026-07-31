import api from './api'
import { useAuthStore } from '@/store/useAuthStore'

interface LoginData {
  email: string
  password: string
}

interface RegisterData {
  email: string
  password: string
  full_name: string
  referral_code?: string
}

export const authService = {
  async register(data: RegisterData) {
    const response = await api.post('/api/auth/register', data)
    const { access_token, user } = response.data

    useAuthStore.setState({
      token: access_token,
      user,
      isAuthenticated: true,
    })

    localStorage.setItem('token', access_token)
    return response.data
  },

  async login(data: LoginData) {
    const response = await api.post('/api/auth/login', data)
    if (response.data.requires_2fa) return response.data

    const { access_token, user } = response.data

    useAuthStore.setState({
      token: access_token,
      user,
      isAuthenticated: true,
    })

    localStorage.setItem('token', access_token)
    return response.data
  },

  async verify2fa(tempToken: string, code: string) {
    const response = await api.post('/api/auth/2fa/verify-login', { temp_token: tempToken, code })
    const { access_token, user } = response.data

    useAuthStore.setState({
      token: access_token,
      user,
      isAuthenticated: true,
    })

    localStorage.setItem('token', access_token)
    return response.data
  },

  logout() {
    useAuthStore.setState({
      token: null,
      user: null,
      isAuthenticated: false,
    })
    localStorage.removeItem('token')
  },

  async loadTokenFromStorage() {
    const token = localStorage.getItem('token')
    if (!token) return

    useAuthStore.setState({ token })
    try {
      const response = await api.get('/api/users/me')
      useAuthStore.setState({ user: response.data, isAuthenticated: true })
    } catch {
      authService.logout()
    }
  },
}
