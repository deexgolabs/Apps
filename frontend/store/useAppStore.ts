import { create } from 'zustand'
import type { App } from '@/types'

interface AppStore {
  apps: App[]
  currentApp: App | null
  loading: boolean
  setApps: (apps: App[]) => void
  setCurrentApp: (app: App | null) => void
  addApp: (app: App) => void
  updateApp: (app: App) => void
  removeApp: (appId: number) => void
  setLoading: (loading: boolean) => void
}

export const useAppStore = create<AppStore>((set) => ({
  apps: [],
  currentApp: null,
  loading: false,
  setApps: (apps) => set({ apps }),
  setCurrentApp: (currentApp) => set({ currentApp }),
  addApp: (app) => set((state) => ({ apps: [...state.apps, app] })),
  updateApp: (app) =>
    set((state) => ({
      apps: state.apps.map((a) => (a.id === app.id ? app : a)),
      currentApp: state.currentApp?.id === app.id ? app : state.currentApp,
    })),
  removeApp: (appId) =>
    set((state) => ({
      apps: state.apps.filter((a) => a.id !== appId),
    })),
  setLoading: (loading) => set({ loading }),
}))
