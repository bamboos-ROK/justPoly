export type StepStatus = 'pending' | 'running' | 'done' | 'error'
export type JobStatus = 'uploading' | 'uploaded' | 'queued' | 'running' | 'done' | 'error'

export interface UploadItem {
  local_id: string
  file: File
  filename: string
  size_bytes: number
  upload_status: 'pending' | 'uploading' | 'uploaded' | 'error'
  upload_progress: number
  job_id?: string
  input_url?: string
  error?: string
}

export interface PipelineStep {
  name: string
  status: StepStatus
  log_tail: string
}

export interface Job {
  job_id: string
  status: JobStatus
  step: string | null
  steps: PipelineStep[]
  input_filename: string
  output_url: string | null
  error: string | null
  started_at: string | null
  finished_at: string | null
}

export interface OutputFile {
  job_id: string
  filename: string
  input_url: string
  output_url: string
  size_bytes: number
  created_at: string
}

export interface PipelineParams {
  tris_ratio: number
  texture_ratio: number
  target_tris?: number
  texture_size?: number
  skip_high_poly_cleanup: boolean
  skip_cage: boolean
}
