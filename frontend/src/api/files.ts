import type { OutputFile } from '../types'
import { jsonFetch } from './client'

export function listOutputs(): Promise<OutputFile[]> {
  return fetch('/outputs').then((r) => jsonFetch<OutputFile[]>(r))
}
