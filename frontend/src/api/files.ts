import type { OutputFile } from '../types'
import { jsonFetch } from './client'

export function listOutputs(): Promise<OutputFile[]> {
  return fetch('/api/outputs').then((r) => jsonFetch<OutputFile[]>(r))
}

export function deleteOutput(job_id: string): Promise<void> {
  return fetch(`/api/outputs/${job_id}`, { method: 'DELETE' }).then((r) => {
    if (!r.ok) throw new Error(`Delete failed: ${r.status}`)
  })
}
