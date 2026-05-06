import type { OutputFile } from '../types'
import { jsonFetch } from './client'

export function listOutputs(): Promise<OutputFile[]> {
  return fetch('/api/outputs').then((r) => jsonFetch<OutputFile[]>(r))
}
