import { uploadGLB, startPipeline, getJob, listJobs } from './jobs'
import { listOutputs, deleteOutput } from './files'

export const api = { uploadGLB, startPipeline, getJob, listJobs, listOutputs, deleteOutput }
