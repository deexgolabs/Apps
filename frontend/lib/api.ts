import axios from 'axios'
import { useAuthStore } from '@/store/useAuthStore'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Só força logout se a chamada IA autenticada (tinha Authorization) e foi
    // rejeitada — um 401 de /login ou /2fa/verify-login (senha/código errado,
    // sem token ainda) é erro esperado que a própria tela já trata, não uma
    // sessão expirada.
    const wasAuthenticated = !!error.config?.headers?.Authorization
    if (error.response?.status === 401 && wasAuthenticated && typeof window !== 'undefined') {
      useAuthStore.setState({ token: null, user: null, isAuthenticated: false })
      localStorage.removeItem('token')
      window.location.href = '/auth/login'
    }
    return Promise.reject(error)
  }
)

// Instância sem interceptors, para rotas públicas (ex: login/cadastro do usuário final
// do app publicado). Um 401 nessas chamadas não deve deslogar o dono da conta.
export const publicApi = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export default api
