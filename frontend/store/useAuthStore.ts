import { create } from 'zustand'
import type { User } from '@/types'

interface AuthStore {
  token: string | null
  user: User | null
  isAuthenticated: boolean
  setToken: (token: string) => void
  setUser: (user: User) => void
  logout: () => void
}

const initialToken = typeof window !== 'undefined' ? localStorage.getItem('token') : null

export const useAuthStore = create<AuthStore>((set) => ({
  token: initialToken,
  user: null,
  isAuthenticated: !!initialToken,
  setToken: (token) => set({ token, isAuthenticated: !!token }),
  setUser: (user) => set({ user }),
  logout: () => set({ token: null, user: null, isAuthenticated: false }),
}))
