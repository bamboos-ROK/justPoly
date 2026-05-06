import { create } from 'zustand'
import type { Job } from './types'

interface AppStore {
  activeJob: Job | null
  setActiveJob: (job: Job | null) => void
  updateJob: (updates: Partial<Job>) => void
  pollingId: ReturnType<typeof setInterval> | null
  setPollingId: (id: ReturnType<typeof setInterval> | null) => void
}

export const useStore = create<AppStore>((set) => ({
  activeJob: null,
  setActiveJob: (job) => set({ activeJob: job }),
  updateJob: (updates) =>
    set((state) => ({
      activeJob: state.activeJob ? { ...state.activeJob, ...updates } : null,
    })),
  pollingId: null,
  setPollingId: (id) => set({ pollingId: id }),
}))
