import { create } from 'zustand'
import type { Job, UploadItem } from './types'

interface AppStore {
  uploadItems: UploadItem[]
  jobsById: Record<string, Job>
  selectedJobId: string | null
  pollingId: ReturnType<typeof setInterval> | null
  setUploadItems: (items: UploadItem[]) => void
  updateUploadItem: (local_id: string, patch: Partial<UploadItem>) => void
  mergeJobs: (jobs: Job[]) => void
  removeJobData: (job_id: string) => void
  setSelectedJobId: (id: string | null) => void
  setPollingId: (id: ReturnType<typeof setInterval> | null) => void
}

export const useStore = create<AppStore>((set) => ({
  uploadItems: [],
  jobsById: {},
  selectedJobId: null,
  pollingId: null,

  setUploadItems: (items) => set({ uploadItems: items }),

  updateUploadItem: (local_id, patch) =>
    set((s) => ({
      uploadItems: s.uploadItems.map((i) =>
        i.local_id === local_id ? { ...i, ...patch } : i
      ),
    })),

  mergeJobs: (jobs) =>
    set((s) => {
      const next = { ...s.jobsById }
      for (const j of jobs) next[j.job_id] = j
      return { jobsById: next }
    }),

  removeJobData: (job_id) =>
    set((s) => ({
      jobsById: Object.fromEntries(Object.entries(s.jobsById).filter(([k]) => k !== job_id)),
      uploadItems: s.uploadItems.filter((i) => i.job_id !== job_id),
    })),

  setSelectedJobId: (id) => set({ selectedJobId: id }),
  setPollingId: (id) => set({ pollingId: id }),
}))
