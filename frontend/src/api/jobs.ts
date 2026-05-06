import type { Job, PipelineParams } from '../types'
import { jsonFetch } from './client'

export function uploadGLB(file: File, onProgress: (pct: number) => void): Promise<{ job_id: string; input_url: string }> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', `/upload?filename=${encodeURIComponent(file.name)}`)
    xhr.setRequestHeader('Content-Type', 'application/octet-stream')
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress((e.loaded / e.total) * 100)
    }
    xhr.onload = () => {
      if (xhr.status === 200) {
        resolve(JSON.parse(xhr.responseText))
      } else {
        reject(new Error(`Upload failed: ${xhr.statusText}`))
      }
    }
    xhr.onerror = () => reject(new Error('Network error'))
    xhr.send(file)
  })
}

export function startPipeline(job_id: string, params: Partial<PipelineParams> = {}): Promise<Job> {
  return fetch('/jobs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ job_id, params }),
  }).then((r) => jsonFetch<Job>(r))
}

export function getJob(job_id: string): Promise<Job> {
  return fetch(`/jobs/${job_id}`).then((r) => jsonFetch<Job>(r))
}

export function listJobs(): Promise<Job[]> {
  return fetch('/jobs').then((r) => jsonFetch<Job[]>(r))
}
