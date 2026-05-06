export type StepStatus = 'pending' | 'running' | 'done' | 'error'
export type JobStatus = 'uploading' | 'running' | 'done' | 'error'

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
